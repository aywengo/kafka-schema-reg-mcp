#!/usr/bin/env python3
"""
Kafka Schema Registry Multi-Registry MCP Server

A comprehensive Message Control Protocol (MCP) server that provides tools for interacting with
multiple Kafka Schema Registry instances, including advanced schema management, cross-registry
comparison, migration, synchronization, and all original single-registry operations.

Features:
- 48 MCP Tools total (20 original + 28 new multi-registry tools)
- Multi-Registry Support: Connect to multiple Schema Registry instances
- Cross-Registry Comparison: Compare schemas, contexts, and entire registries
- Schema Migration: Move schemas between registries with conflict detection
- Synchronization: Keep registries in sync with scheduled operations
- Export/Import: Advanced bulk operations for data migration
- READONLY Mode: Production safety for all registries
- Backward Compatibility: All existing tools work with optional registry parameter
- Async Task Queue: Background processing for long-running operations

=== MCP CLIENT ASYNC OPERATION GUIDANCE ===

This server implements TWO async patterns for MCP client awareness:

1. **DIRECT PATTERN** (Quick Operations < 5 seconds):
   - Operations return results immediately
   - Examples: test_all_registries, compare_registries, get_subjects
   - MCP clients should use standard timeouts (10-30 seconds)

2. **TASK QUEUE PATTERN** (Medium/Long Operations > 5 seconds):
   - Operations return task_id immediately and run in background
   - Examples: migrate_context, migrate_schema, clear_context_batch
   - MCP clients should:
     * Call operation to get task_id
     * Poll get_task_status(task_id) for progress
     * Handle async completion/errors
     * Set longer timeouts (60+ seconds) for initial call

**Operation Classification:**
- QUICK (< 5 seconds): Direct async execution
- MEDIUM (5-30 seconds): Task queue with progress tracking  
- LONG (> 30 seconds): Task queue with background processing

Use get_operation_info_tool() to discover operation characteristics.

**Task Management:**
- get_task_status(task_id): Monitor progress and get results
- list_tasks(): See all running/completed tasks
- cancel_task(task_id): Cancel running operations
- reset_task_queue(): Clean up completed tasks

This design prevents MCP client timeouts and provides better UX for long operations.
"""

import os
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import asyncio
import logging
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import uuid
import threading
import time
from enum import Enum
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import inspect
import atexit

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import base64
import aiohttp

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Task status enum
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Task type enum
class TaskType(Enum):
    MIGRATION = "migration"
    SYNC = "sync"
    CLEANUP = "cleanup"
    EXPORT = "export"
    IMPORT = "import"

# Operation classification for MCP client awareness
class OperationDuration(Enum):
    QUICK = "quick"        # < 5 seconds
    MEDIUM = "medium"      # 5-30 seconds  
    LONG = "long"          # > 30 seconds

class AsyncPattern(Enum):
    DIRECT = "direct"      # Direct async execution (blocks MCP client)
    TASK_QUEUE = "task_queue"  # Background task execution (non-blocking)

# Operation metadata for MCP client guidance
OPERATION_METADATA = {
    "test_all_registries": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "compare_registries": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "migrate_context": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "migrate_schema": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_context_batch": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_multiple_contexts_batch": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_context_across_registries_batch": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "compare_contexts_across_registries": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
}

def get_operation_info(operation_name: str) -> Dict[str, Any]:
    """Get operation metadata for MCP client guidance."""
    metadata = OPERATION_METADATA.get(operation_name, {
        "duration": OperationDuration.QUICK,
        "pattern": AsyncPattern.DIRECT
    })
    return {
        "operation": operation_name,
        "expected_duration": metadata["duration"].value,
        "async_pattern": metadata["pattern"].value,
        "guidance": _get_operation_guidance(metadata)
    }

def _get_operation_guidance(metadata: Dict[str, Any]) -> str:
    """Generate guidance text for operation."""
    if metadata["pattern"] == AsyncPattern.TASK_QUEUE:
        return "Long-running operation. Returns task_id immediately. Use get_task_status() to monitor progress."
    else:
        return "Quick operation. Returns results directly."

@dataclass
class AsyncTask:
    """Represents an async task in the queue."""
    id: str
    type: TaskType
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    _future: Optional[asyncio.Future] = None
    _cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary, excluding internal fields."""
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "error": self.error,
            "result": self.result,
            "metadata": self.metadata
        }

class AsyncTaskManager:
    """Manages async tasks and their execution."""
    
    def __init__(self):
        self.tasks: Dict[str, AsyncTask] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        self._shutdown = False
    
    def create_task(
        self,
        task_type: TaskType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncTask:
        """Create a new async task."""
        if self._shutdown:
            raise RuntimeError("TaskManager is shutting down")
            
        task_id = str(uuid.uuid4())
        task = AsyncTask(
            id=task_id,
            type=task_type,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            metadata=metadata
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        return task
    
    async def execute_task(
        self,
        task: AsyncTask,
        func: Callable,
        *args,
        **kwargs
    ) -> None:
        """Execute a task asynchronously."""
        if self._shutdown:
            task.status = TaskStatus.CANCELLED
            task.error = "TaskManager is shutting down"
            return
            
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            
            # Create future for the task
            loop = asyncio.get_event_loop()
            task._future = loop.create_future()
            
            # Run the function in thread pool
            def run_in_thread():
                try:
                    if task._cancelled or self._shutdown:
                        raise asyncio.CancelledError()
                    result = func(*args, **kwargs)
                    if inspect.iscoroutine(result):
                        # Run coroutine in the event loop and get the result
                        result = asyncio.run_coroutine_threadsafe(result, loop).result()
                    if not task._cancelled and not self._shutdown:
                        loop.call_soon_threadsafe(
                            task._future.set_result,
                            result
                        )
                except Exception as e:
                    if not task._cancelled and not self._shutdown:
                        loop.call_soon_threadsafe(
                            task._future.set_exception,
                            e
                        )
            
            self._executor.submit(run_in_thread)
            
            # Wait for completion
            try:
                result = await task._future
                task.status = TaskStatus.COMPLETED
                task.result = result
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.error = "Task was cancelled"
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
            
        finally:
            task.completed_at = datetime.now().isoformat()
            task._future = None
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None
    ) -> List[AsyncTask]:
        """List tasks with optional filtering."""
        with self._lock:
            tasks = list(self.tasks.values())
        
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.RUNNING and task._future:
            task._cancelled = True
            task._future.cancel()
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
            return True
        
        return False
    
    async def cancel_all_tasks(self) -> int:
        """Cancel all running tasks."""
        cancelled = 0
        for task in self.list_tasks(status=TaskStatus.RUNNING):
            if await self.cancel_task(task.id):
                cancelled += 1
        return cancelled
    
    def reset_queue(self) -> None:
        """Reset the task queue by removing all completed/failed/cancelled tasks."""
        with self._lock:
            self.tasks = {
                task_id: task
                for task_id, task in self.tasks.items()
                if task.status == TaskStatus.RUNNING
            }
    
    def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress."""
        task = self.get_task(task_id)
        if task:
            task.progress = min(max(progress, 0.0), 100.0)
            
    async def shutdown(self) -> None:
        """Shutdown the task manager and clean up resources."""
        self._shutdown = True
        
        # Cancel all running tasks
        await self.cancel_all_tasks()
        
        # Reset the queue
        self.reset_queue()
        
        # Shutdown the executor
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

# Initialize task manager
task_manager = AsyncTaskManager()

# Register cleanup handler
def cleanup_task_manager():
    """Cleanup function to be called at exit"""
    if task_manager:
        task_manager._shutdown = True
        if task_manager._executor:
            task_manager._executor.shutdown(wait=False)
            task_manager._executor = None

atexit.register(cleanup_task_manager)

# Configuration - Single Registry Mode (backward compatibility)
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
READONLY = os.getenv("READONLY", "false").lower() in ("true", "1", "yes", "on")

# Multi-registry configuration - supports up to 8 instances
MAX_REGISTRIES = 8

@dataclass
class RegistryConfig:
    """Configuration for a Schema Registry instance."""
    name: str
    url: str
    user: str = ""
    password: str = ""
    description: str = ""
    readonly: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MigrationTask:
    """Represents a migration task."""
    id: str
    source_registry: str
    target_registry: str
    scope: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    dry_run: bool = False

@dataclass
class SyncTask:
    """Represents a synchronization task."""
    id: str
    source_registry: str
    target_registry: str
    scope: str
    direction: str
    interval_seconds: int
    status: str
    created_at: str
    last_sync: Optional[str] = None
    next_sync: Optional[str] = None

class RegistryClient:
    """Client for interacting with a single Schema Registry instance."""
    
    def __init__(self, config: RegistryConfig):
        self.config = config
        self.auth = None
        self.headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        self.standard_headers = {"Content-Type": "application/json"}
        
        if config.user and config.password:
            self.auth = HTTPBasicAuth(config.user, config.password)
            credentials = base64.b64encode(f"{config.user}:{config.password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
            self.standard_headers["Authorization"] = f"Basic {credentials}"
    
    def build_context_url(self, base_url: str, context: Optional[str] = None) -> str:
        """Build URL with optional context support."""
        # Handle default context "." as no context
        if context and context != ".":
            return f"{self.config.url}/contexts/{context}{base_url}"
        return f"{self.config.url}{base_url}"
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to this registry."""
        try:
            response = requests.get(f"{self.config.url}/subjects", 
                                  auth=self.auth, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "registry": self.config.name,
                    "url": self.config.url,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "status": "error",
                    "registry": self.config.name,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "status": "error",
                "registry": self.config.name,
                "error": str(e)
            }
    
    def get_subjects(self, context: Optional[str] = None) -> List[str]:
        """Get subjects from this registry."""
        try:
            url = self.build_context_url("/subjects", context)
            response = requests.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
    
    def get_contexts(self) -> List[str]:
        """Get contexts from this registry."""
        try:
            response = requests.get(f"{self.config.url}/contexts", 
                                  auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def delete_subject(self, subject: str, context: Optional[str] = None) -> bool:
        """Delete a subject and all its versions.
        
        Args:
            subject: The subject name to delete
            context: Optional schema context
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            url = self.build_context_url(f"/subjects/{subject}", context)
            response = requests.delete(
                url,
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to delete subject '{subject}': {str(e)}")
            return False

class RegistryManager:
    """Manages multiple Schema Registry instances."""
    
    def __init__(self):
        self.registries: Dict[str, RegistryClient] = {}
        self.default_registry: Optional[str] = None
        self._load_registries()
    
    def _load_registries(self):
        """Load registry configurations from environment variables."""
        # Check for multi-registry mode first (numbered environment variables)
        multi_registry_found = False
        
        for i in range(1, MAX_REGISTRIES + 1):
            name_var = f"SCHEMA_REGISTRY_NAME_{i}"
            url_var = f"SCHEMA_REGISTRY_URL_{i}"
            user_var = f"SCHEMA_REGISTRY_USER_{i}"
            password_var = f"SCHEMA_REGISTRY_PASSWORD_{i}"
            readonly_var = f"READONLY_{i}"
            
            name = os.getenv(name_var, "")
            url = os.getenv(url_var, "")
            
            if name and url:
                multi_registry_found = True
                
                user = os.getenv(user_var, "")
                password = os.getenv(password_var, "")
                readonly = os.getenv(readonly_var, "false").lower() in ("true", "1", "yes", "on")
                
                config = RegistryConfig(
                    name=name,
                    url=url,
                    user=user,
                    password=password,
                    description=f"{name} Schema Registry (instance {i})",
                    readonly=readonly
                )
                
                self.registries[name] = RegistryClient(config)
                
                # Set first registry as default
                if self.default_registry is None:
                    self.default_registry = name
                
                logging.info(f"Loaded registry {i}: {name} at {url} (readonly: {readonly})")
        
        # Single registry mode (backward compatibility) - only if no multi-registry found
        if not multi_registry_found and SCHEMA_REGISTRY_URL:
            default_config = RegistryConfig(
                name="default",
                url=SCHEMA_REGISTRY_URL,
                user=SCHEMA_REGISTRY_USER,
                password=SCHEMA_REGISTRY_PASSWORD,
                description="Default Schema Registry",
                readonly=READONLY
            )
            self.registries["default"] = RegistryClient(default_config)
            self.default_registry = "default"
            logging.info(f"Loaded single registry: default at {SCHEMA_REGISTRY_URL} (readonly: {READONLY})")
        
        if not self.registries:
            logging.warning("No Schema Registry instances configured. Set SCHEMA_REGISTRY_URL for single mode or SCHEMA_REGISTRY_NAME_1/SCHEMA_REGISTRY_URL_1 for multi mode.")
    
    def get_registry(self, name: Optional[str] = None) -> Optional[RegistryClient]:
        """Get a registry client by name, or default if name is None."""
        if name is None:
            name = self.default_registry
        return self.registries.get(name)
    
    def list_registries(self) -> List[str]:
        """List all configured registry names."""
        return list(self.registries.keys())
    
    def get_registry_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a registry."""
        if name not in self.registries:
            return None
        
        client = self.registries[name]
        info = client.config.to_dict()
        info["is_default"] = name == self.default_registry
        
        # Test connection
        connection_test = client.test_connection()
        info["connection_status"] = connection_test["status"]
        if "response_time_ms" in connection_test:
            info["response_time_ms"] = connection_test["response_time_ms"]
        if "error" in connection_test:
            info["connection_error"] = connection_test["error"]
            
        return info
    
    async def test_all_registries_async(self) -> Dict[str, Any]:
        """Test connections to all registries asynchronously."""
        results = {}
        async with aiohttp.ClientSession() as session:
            for name, client in self.registries.items():
                try:
                    async with session.get(f"{client.config.url}/subjects", 
                                         auth=aiohttp.BasicAuth(client.auth[0], client.auth[1]) if client.auth else None,
                                         headers=client.headers,
                                         timeout=10) as response:
                        if response.status == 200:
                            results[name] = {
                                "status": "connected",
                                "url": client.config.url,
                                "response_time_ms": response.elapsed.total_seconds() * 1000
                            }
                        else:
                            results[name] = {
                                "status": "error",
                                "url": client.config.url,
                                "error": f"HTTP {response.status}: {await response.text()}"
                            }
                except Exception as e:
                    results[name] = {
                        "status": "error",
                        "url": client.config.url,
                        "error": str(e)
                    }
        
        return {
            "registry_tests": results,
            "total_registries": len(results),
            "connected": sum(1 for r in results.values() if r.get("status") == "connected"),
            "failed": sum(1 for r in results.values() if r.get("status") == "error")
        }
    
    async def compare_registries_async(self, source: str, target: str) -> Dict[str, Any]:
        """Compare two registries asynchronously."""
        source_client = self.get_registry(source)
        target_client = self.get_registry(target)
        
        if not source_client or not target_client:
            return {"error": "Invalid registry configuration"}
        
        async with aiohttp.ClientSession() as session:
            # Get subjects from both registries
            source_subjects = await self._get_subjects_async(session, source_client)
            target_subjects = await self._get_subjects_async(session, target_client)
            
            return {
                "source": source,
                "target": target,
                "compared_at": datetime.now().isoformat(),
                "subjects": {
                    "source_only": list(set(source_subjects) - set(target_subjects)),
                    "target_only": list(set(target_subjects) - set(source_subjects)),
                    "common": list(set(source_subjects) & set(target_subjects)),
                    "source_total": len(source_subjects),
                    "target_total": len(target_subjects)
                }
            }
    
    async def _get_subjects_async(self, session: aiohttp.ClientSession, client: RegistryClient) -> List[str]:
        """Get subjects from a registry asynchronously."""
        try:
            async with session.get(f"{client.config.url}/subjects",
                                 auth=aiohttp.BasicAuth(client.auth[0], client.auth[1]) if client.auth else None,
                                 headers=client.headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception:
            return []
    
    def is_readonly(self, registry_name: Optional[str] = None) -> bool:
        """Check if a registry is in readonly mode."""
        client = self.get_registry(registry_name)
        if not client:
            return False
        return client.config.readonly
    
    def get_default_registry(self) -> Optional[str]:
        """Get the default registry name."""
        return self.default_registry
    
    def set_default_registry(self, name: str) -> bool:
        """Set the default registry."""
        if name in self.registries:
            self.default_registry = name
            return True
        return False

# Initialize registry manager
registry_manager = RegistryManager()

# Create the MCP server
mcp = FastMCP("Kafka Schema Registry Multi-Registry MCP Server")

def check_readonly_mode(registry_name: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Check if the server or specific registry is in readonly mode and return error if so."""
    
    # If a specific registry is provided, check its readonly setting
    if registry_name:
        client = registry_manager.get_registry(registry_name)
        if client and client.config.readonly:
            return {
                "error": f"Operation blocked: Registry '{registry_name}' is running in READONLY mode. "
                        f"Set READONLY_{registry_name} environment variable to false to enable modifications.",
                "readonly_mode": True,
                "registry": registry_name
            }
    
    # Also check global READONLY setting (backward compatibility)
    if READONLY:
        return {
            "error": "Operation blocked: MCP server is running in global READONLY mode. "
                    "Set READONLY=false to enable modification operations.",
            "readonly_mode": True,
            "global": True
        }
    
    return None

# ===== REGISTRY MANAGEMENT TOOLS =====

@mcp.tool()
def list_registries() -> List[Dict[str, Any]]:
    """
    List all configured Schema Registry instances.
    
    Returns:
        List of registry configurations with connection status
    """
    try:
        result = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                result.append(info)
        return result
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_registry_info(registry_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific registry.
    
    Args:
        registry_name: Name of the registry
    
    Returns:
        Dictionary containing registry details and health information
    """
    try:
        info = registry_manager.get_registry_info(registry_name)
        if info is None:
            return {"error": f"Registry '{registry_name}' not found"}
        return info
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def test_registry_connection(registry_name: str) -> Dict[str, Any]:
    """
    Test connection to a specific registry.
    
    Args:
        registry_name: Name of the registry to test
    
    Returns:
        Connection test results
    """
    try:
        client = registry_manager.get_registry(registry_name)
        if client is None:
            return {"error": f"Registry '{registry_name}' not found"}
        
        return client.test_connection()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def test_all_registries() -> Dict[str, Any]:
    """
    Test connections to all configured registries.
    
    Returns:
        Connection test results for all registries
    """
    try:
        return await registry_manager.test_all_registries_async()
    except Exception as e:
        return {"error": str(e)}

# ===== CROSS-REGISTRY COMPARISON TOOLS =====

@mcp.tool()
async def compare_registries(
    source_registry: str,
    target_registry: str,
    include_contexts: bool = True,
    include_configs: bool = True
) -> Dict[str, Any]:
    """
    Compare two Schema Registry instances and show differences.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        include_contexts: Include context comparison
        include_configs: Include configuration comparison
    
    Returns:
        Comparison results
    """
    try:
        return await registry_manager.compare_registries_async(source_registry, target_registry)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def compare_contexts_across_registries(
    source_registry: str,
    target_registry: str,
    context: str
) -> Dict[str, Any]:
    """
    Compare a specific context across two registries.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Context name to compare
    
    Returns:
        Context comparison results
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.MIGRATION,
            metadata={
                "operation": "compare_contexts",
                "source_registry": source_registry,
                "target_registry": target_registry,
                "context": context
            }
        )
        
        # Start async execution
        asyncio.create_task(
            task_manager.execute_task(
                task,
                _execute_compare_contexts,
                source_registry=source_registry,
                target_registry=target_registry,
                context=context
            )
        )
        
        return {
            "message": "Context comparison started as async task",
            "task_id": task.id,
            "task": task.to_dict()
        }
        
    except Exception as e:
        return {"error": str(e)}

# ===== REGISTRY CONFIGURATION TOOLS =====

@mcp.tool()
def set_default_registry(registry_name: str) -> Dict[str, Any]:
    """
    Set the default registry.
    
    Args:
        registry_name: Name of the registry to set as default
    
    Returns:
        Operation result
    """
    try:
        if registry_manager.set_default_registry(registry_name):
            return {
                "message": f"Default registry set to '{registry_name}'",
                "default_registry": registry_name
            }
        else:
            return {"error": f"Registry '{registry_name}' not found"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_default_registry() -> Dict[str, Any]:
    """
    Get the current default registry.
    
    Returns:
        Default registry information
    """
    try:
        default = registry_manager.get_default_registry()
        if default:
            return {
                "default_registry": default,
                "info": registry_manager.get_registry_info(default)
            }
        else:
            return {"error": "No default registry configured"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_readonly_mode(registry_name: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Check if a registry is in readonly mode.
    
    Args:
        registry_name: Optional registry name to check
    
    Returns:
        Readonly status or None if not readonly
    """
    try:
        if registry_manager.is_readonly(registry_name):
            return {
                "error": f"Operation blocked: Registry '{registry_name}' is in READONLY mode",
                "readonly_mode": True,
                "registry": registry_name
            }
        return None
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subjects(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[str]:
    """
    Get all subjects from a registry, optionally filtered by context.
    
    Args:
        context: Optional schema context to filter by
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of subject names
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        return client.get_subjects(context)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_global_config(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get global configuration settings.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing configuration
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/config", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_global_config(
    compatibility: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update global configuration settings.
    
    Args:
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/config", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_config(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing subject configuration
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/config/{subject}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_config(
    subject: str,
    compatibility: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/config/{subject}", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== MODE MANAGEMENT TOOLS =====

@mcp.tool()
def get_mode(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Get the current mode of the Schema Registry.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the current mode
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/mode", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_mode(
    mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode of the Schema Registry.
    
    Args:
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/mode", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_mode(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Get the mode for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the subject mode
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/mode/{subject}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_mode(
    subject: str,
    mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode for a specific subject.
    
    Args:
        subject: The subject name
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/mode/{subject}", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== ENHANCED SCHEMA TOOLS =====

@mcp.tool()
def get_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[int]:
    """
    Get all versions of a schema for a subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of version numbers
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers=client.headers
        )
        
        # Handle 404 specifically - subject doesn't exist
        if response.status_code == 404:
            return []
            
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_compatibility(
    subject: str,
    schema_definition: Dict[str, Any],
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if a schema is compatible with the latest version.
    
    Args:
        subject: The subject name
        schema_definition: The schema definition to check
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Compatibility check result
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = client.build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== ORIGINAL SCHEMA MANAGEMENT TOOLS (Enhanced with Multi-Registry Support) =====

@mcp.tool()
def register_schema(
    subject: str,
    schema_definition: Dict[str, Any],
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Register a new schema version under the specified subject.
    
    Args:
        subject: The subject name for the schema
        schema_definition: The schema definition as a dictionary
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the schema ID
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = client.build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a specific version of a schema.
    
    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing schema information
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}/versions/{version}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== BATCH CLEANUP TOOLS =====

@mcp.tool()
def clear_context_batch(
    context: str,
    registry: str,
    delete_context_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Clear all subjects in a context using batch operations.
    
    **MEDIUM-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.
    
    Args:
        context: The context to clear
        registry: The registry to operate on
        delete_context_after: Whether to delete the context after clearing subjects
        dry_run: If True, only simulate the operation without making changes
        
    Returns:
        Task information with task_id for monitoring progress
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.CLEANUP,
            metadata={
                "operation": "clear_context_batch",
                "context": context,
                "registry": registry,
                "delete_context_after": delete_context_after,
                "dry_run": dry_run
            }
        )
        
        # Start async execution
        asyncio.create_task(
            task_manager.execute_task(
                task,
                _execute_clear_context_batch,
                context=context,
                registry=registry,
                delete_context_after=delete_context_after,
                dry_run=dry_run
            )
        )
        
        return {
            "message": "Context cleanup started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": get_operation_info("clear_context_batch")
        }
        
    except Exception as e:
        return {"error": str(e)}

def _execute_clear_context_batch(
    context: str,
    registry: str,
    delete_context_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Execute the actual context cleanup logic."""
    start_time = time.time()
    subjects_found = 0
    subjects_deleted = 0
    context_deleted = False
    errors = []
    
    try:
        # Get registry client
        registry_client = registry_manager.get_registry(registry)
        if not registry_client:
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' not found",
                "error": f"Registry '{registry}' not found",
                "registry": registry
            }
            
        # Check if registry is in read-only mode
        readonly_check = check_readonly_mode(registry)
        if readonly_check and readonly_check.get("mode") == "READONLY":
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' is in read-only mode",
                "error": f"Registry '{registry}' is in read-only mode",
                "registry": registry
            }
            
        # Get all subjects in the context
        subjects = registry_client.get_subjects(context)
        subjects_found = len(subjects)
        
        if subjects_found == 0:
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 100.0,
                "performance": 0.0,
                "message": f"Context '{context}' is already empty",
                "registry": registry
            }
            
        if dry_run:
            return {
                "subjects_found": subjects_found,
                "subjects_deleted": 0,
                "context_deleted": delete_context_after,
                "dry_run": True,
                "duration_seconds": time.time() - start_time,
                "success_rate": 100.0,
                "performance": 0.0,
                "message": f"DRY RUN: Would delete {subjects_found} subjects from context '{context}'",
                "registry": registry
            }
            
        # Delete subjects in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for subject in subjects:
                futures.append(executor.submit(registry_client.delete_subject, subject, context))
                
            for future in as_completed(futures):
                try:
                    if future.result():
                        subjects_deleted += 1
                except Exception as e:
                    errors.append(str(e))
                    
        # Calculate metrics
        duration = time.time() - start_time
        success_rate = (subjects_deleted / subjects_found * 100) if subjects_found > 0 else 100.0
        performance = subjects_deleted / duration if duration > 0 else 0.0
        
        # Delete context if requested
        if delete_context_after and subjects_deleted == subjects_found:
            try:
                # Note: Context deletion is not supported in the API
                # This is just a placeholder for future implementation
                context_deleted = False
            except Exception as e:
                errors.append(f"Failed to delete context: {str(e)}")
                
        return {
            "subjects_found": subjects_found,
            "subjects_deleted": subjects_deleted,
            "context_deleted": context_deleted,
            "dry_run": False,
            "duration_seconds": duration,
            "success_rate": success_rate,
            "performance": performance,
            "message": f"Successfully cleared context '{context}' - deleted {subjects_deleted} subjects",
            "errors": errors if errors else None,
            "registry": registry
        }
        
    except Exception as e:
        return {
            "subjects_found": subjects_found,
            "subjects_deleted": subjects_deleted,
            "context_deleted": False,
            "dry_run": dry_run,
            "duration_seconds": time.time() - start_time,
            "success_rate": 0.0,
            "performance": 0.0,
            "message": f"Batch cleanup failed: {str(e)}",
            "error": str(e),
            "registry": registry
        }

@mcp.tool()
def clear_multiple_contexts_batch(
    contexts: List[str],
    registry: str,
    delete_contexts_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Clear multiple contexts in a registry in batch mode.
    
    **LONG-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.
    
    Args:
        contexts: List of context names to clear
        registry: Registry name to clear contexts from
        delete_contexts_after: Whether to delete the contexts after clearing subjects
        dry_run: If True, only simulate the operation without making changes
        
    Returns:
        Task information with task_id for monitoring progress
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.CLEANUP,
            metadata={
                "operation": "clear_multiple_contexts_batch",
                "contexts": contexts,
                "registry": registry,
                "delete_contexts_after": delete_contexts_after,
                "dry_run": dry_run
            }
        )
        
        # Start async execution
        asyncio.create_task(
            task_manager.execute_task(
                task,
                _execute_migrate_context,
                source_registry=source_registry,
                target_registry=target_registry,
                context=context,
                target_context=target_context,
                preserve_ids=preserve_ids,
                dry_run=dry_run,
                migrate_all_versions=migrate_all_versions
            )
        )
        
        return {
            "message": "Context migration started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": get_operation_info("migrate_context")
        }
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def delete_subject(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[int]:
    """
    Delete a subject and all its versions.
    
    Args:
        subject: The subject name to delete
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of deleted version numbers
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}", context)
        
        # Use aiohttp for async HTTP requests
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url,
                auth=aiohttp.BasicAuth(client.auth[0], client.auth[1]) if client.auth else None,
                headers=client.headers
            ) as response:
                response.raise_for_status()
                return await response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def create_context(
    context: str,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new schema context.
    
    Args:
        context: The context name to create
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing creation result
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        # Create context by registering a dummy schema in that context
        # This is a common pattern to create contexts in Schema Registry
        dummy_schema = {
            "type": "record",
            "name": "DummySchema",
            "fields": [
                {"name": "dummy", "type": "string"}
            ]
        }
        
        # Register schema in the new context
        url = client.build_context_url("/subjects/dummy-schema/versions", context)
        
        response = requests.post(
            url,
            json={
                "schema": json.dumps(dummy_schema),
                "schemaType": "AVRO"
            },
            auth=client.auth,
            headers=client.headers
        )
        
        if response.status_code == 200:
            # Now delete the dummy schema
            delete_url = client.build_context_url("/subjects/dummy-schema", context)
            requests.delete(
                delete_url,
                auth=client.auth,
                headers=client.headers
            )
            
            return {
                "message": f"Context '{context}' created successfully",
                "registry": client.config.name
            }
        else:
            return {"error": f"Failed to create context: {response.text}"}
            
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def migrate_schema(
    subject: str,
    source_registry: str,
    target_registry: str,
    dry_run: bool = False,
    preserve_ids: bool = True,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Migrate a schema from one registry to another.
    
    **MEDIUM-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.
    
    Args:
        subject: The subject name
        source_registry: Source registry name
        target_registry: Target registry name
        dry_run: Preview migration without executing
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        source_context: Source context (default: ".")
        target_context: Target context (default: ".")
        versions: Optional list of specific versions to migrate
    
    Returns:
        Task information with task_id for monitoring progress
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.MIGRATION,
            metadata={
                "operation": "migrate_schema",
                "subject": subject,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_context,
                "preserve_ids": preserve_ids,
                "dry_run": dry_run,
                "versions": versions
            }
        )
        
        # Start async execution
        asyncio.create_task(
            task_manager.execute_task(
                task,
                _execute_migrate_schema,
                subject=subject,
                source_registry=source_registry,
                target_registry=target_registry,
                dry_run=dry_run,
                preserve_ids=preserve_ids,
                source_context=source_context,
                target_context=target_context,
                versions=versions
            )
        )
        
        return {
            "message": "Schema migration started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": get_operation_info("migrate_schema")
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _execute_migrate_schema(
    subject: str,
    source_registry: str,
    target_registry: str,
    dry_run: bool = False,
    preserve_ids: bool = True,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Execute the actual schema migration logic."""
    try:
        logger.info(f"Starting schema migration for subject '{subject}'")
        logger.info(f"Source: {source_registry} ({source_context}), Target: {target_registry} ({target_context})")
        logger.info(f"Preserve IDs: {preserve_ids}, Dry run: {dry_run}")
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client or not target_client:
            logger.error("Invalid registry configuration")
            return {"error": "Invalid registry configuration"}
        
        # Extract the actual subject name without context prefix
        actual_subject = subject
        if subject.startswith(":."):
            # Remove the context prefix if it exists
            parts = subject.split(":", 2)
            if len(parts) >= 3:
                actual_subject = parts[2]
                logger.info(f"Extracted actual subject name: {actual_subject} from {subject}")
        
        # Get all versions of the schema from source
        logger.info(f"Fetching versions from source registry for subject '{actual_subject}'")
        versions_result = get_schema_versions(actual_subject, context=source_context, registry=source_registry)
        if isinstance(versions_result, dict) and "error" in versions_result:
            logger.error(f"Failed to get versions: {versions_result['error']}")
            return versions_result
        if not versions_result:
            logger.error(f"Subject {actual_subject} not found in source registry")
            return {"error": f"Subject {actual_subject} not found in source registry"}
        
        # If specific versions are provided, use those; otherwise use all versions
        versions_to_migrate = versions if versions is not None else sorted(versions_result)
        logger.info(f"Versions to migrate: {versions_to_migrate}")
        
        # Check if target context exists
        target_context_exists = False
        try:
            contexts = target_client.get_contexts()
            if target_context == ".":
                # Default context always exists
                target_context_exists = True
            else:
                target_context_exists = target_context in contexts
                if not target_context_exists:
                    logger.info(f"Context {target_context} does not exist in target registry, will be created during migration")
        except Exception as e:
            logger.debug(f"Error checking target context existence: {e}")
            # If we can't check contexts, assume it doesn't exist
            target_context_exists = False
        
        # Only check subject existence if context exists
        target_subject_exists = False
        if target_context_exists:
            try:
                target_versions = get_schema_versions(actual_subject, context=target_context, registry=target_registry)
                if isinstance(target_versions, dict) and "error" in target_versions:
                    if "404" in str(target_versions.get("error", "")):
                        # 404 is expected if subject doesn't exist
                        target_subject_exists = False
                    else:
                        logger.debug(f"Error checking target subject existence: {target_versions['error']}")
                else:
                    target_subject_exists = len(target_versions) > 0
                    if target_subject_exists:
                        logger.warning(f"Subject {actual_subject} already exists in target registry. Will delete before migration.")
            except Exception as e:
                logger.debug(f"Error checking target subject existence: {e}")
        else:
            # Target context does not exist, create it before setting IMPORT mode
            logger.info(f"Target context {target_context} does not exist in target registry, creating it before migration")
            create_context_result = create_context(target_context, registry=target_registry)
            if isinstance(create_context_result, dict) and create_context_result.get("error"):
                logger.error(f"Failed to create target context {target_context}: {create_context_result['error']}")
                return {"error": f"Failed to create target context {target_context}: {create_context_result['error']}"}
            target_context_exists = True
            target_subject_exists = False
        
        # Store original mode for restoration
        original_mode = None
        if preserve_ids:
            try:
                # Get current mode
                mode_url = f"{target_client.config.url}/mode"
                async with aiohttp.ClientSession() as session:
                    async with session.get(mode_url) as response:
                        if response.status == 200:
                            mode_data = await response.json()
                            original_mode = mode_data.get("mode")
                            logger.debug(f"Current registry mode: {original_mode}")
                
                # If subject exists in target, we need to delete it first
                if target_subject_exists:
                    logger.info(f"Deleting existing subject {actual_subject} from target registry before migration")
                    await delete_subject(actual_subject, context=target_context, registry=target_registry)
                    # After deletion, subject no longer exists
                    target_subject_exists = False
                
                # Set IMPORT mode at the subject level (not context level)
                mode_url = f"{target_client.config.url}/contexts/{target_context}/mode/{actual_subject}"
                logger.info(f"Setting IMPORT mode for subject '{actual_subject}' in context '{target_context}'")
                async with aiohttp.ClientSession() as session:
                    async with session.put(mode_url, json={"mode": "IMPORT"}) as response:
                        if response.status == 405:
                            logger.warning("IMPORT mode not supported by target registry, will proceed without ID preservation")
                            preserve_ids = False
                        elif response.status != 200:
                            logger.warning(f"Failed to set IMPORT mode: {response.status}")
                            preserve_ids = False
                        else:
                            logger.info("Successfully set IMPORT mode")
            except Exception as e:
                logger.warning(f"Error setting IMPORT mode: {e}")
                preserve_ids = False
        
        # Migrate each version
        migrated_versions = []
        for version in versions_to_migrate:
            try:
                logger.info(f"Processing version {version} of subject '{actual_subject}'")
                # Get schema from source
                schema_data = get_schema(actual_subject, version=version, context=source_context, registry=source_registry)
                if not schema_data:
                    logger.error(f"Failed to get schema for version {version}")
                    continue
                
                # Register in target
                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate {actual_subject} version {version}")
                    migrated_versions.append({
                        "version": version,
                        "id": schema_data.get("id"),
                        "schema": schema_data.get("schema")
                    })
                else:
                    # Prepare registration payload
                    payload = {
                        "schema": schema_data.get("schema"),
                        "schemaType": schema_data.get("schemaType", "AVRO")
                    }
                    
                    # Add ID if preserving IDs
                    if preserve_ids and schema_data.get("id"):
                        payload["id"] = schema_data.get("id")
                        logger.info(f"Preserving schema ID {schema_data.get('id')} for version {version}")
                    
                    # Register schema
                    url = target_client.build_context_url(f"/subjects/{actual_subject}/versions", target_context)
                    logger.info(f"Registering schema version {version} in target registry")
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            json=payload,
                            auth=aiohttp.BasicAuth(target_client.auth[0], target_client.auth[1]) if target_client.auth else None,
                            headers=target_client.headers
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"Successfully registered version {version} with ID {result.get('id')}")
                                migrated_versions.append({
                                    "version": version,
                                    "id": result.get("id"),
                                    "schema": schema_data.get("schema")
                                })
                            else:
                                error_text = await response.text()
                                logger.error(f"Error migrating version {version}: {error_text}")
                                continue
                
            except Exception as e:
                logger.error(f"Error migrating version {version}: {e}")
                continue
        
        # Restore original mode if we changed it
        if preserve_ids and original_mode:
            try:
                mode_url = f"{target_client.config.url}/mode"
                logger.info(f"Restoring original mode: {original_mode}")
                async with aiohttp.ClientSession() as session:
                    async with session.put(mode_url, json={"mode": original_mode}) as response:
                        if response.status == 200:
                            logger.info(f"Restored original mode: {original_mode}")
                        else:
                            logger.warning(f"Failed to restore original mode: {response.status}")
            except Exception as e:
                logger.warning(f"Error restoring original mode: {e}")
        
        logger.info(f"Migration completed for subject '{actual_subject}'. Migrated {len(migrated_versions)} versions")
        return {
            "task_id": str(uuid.uuid4()),
            "subject": actual_subject,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "source_context": source_context,
            "target_context": target_context,
            "migrated_versions": migrated_versions,
            "preserve_ids": preserve_ids,
            "dry_run": dry_run,
            "context_exists": target_context_exists,
            "subject_exists": target_subject_exists,
            "versions_migrated": len(migrated_versions),
            "total_versions": len(versions_to_migrate)
        }
        
    except Exception as e:
        logger.error(f"Error in migrate_schema: {e}")
        return {"error": str(e)}

@mcp.tool()
def list_subjects(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[str]:
    """
    List all subjects in a registry, optionally filtered by context.
    
    Args:
        context: Optional schema context to filter by
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of subject names
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        return client.get_subjects(context)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_operation_info_tool(operation_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about MCP operations, including expected duration and async patterns.
    This helps MCP clients understand which operations are long-running and use task queues.
    
    Args:
        operation_name: Optional specific operation name. If not provided, returns all operations info.
    
    Returns:
        Operation metadata for MCP client guidance
    """
    try:
        if operation_name:
            return get_operation_info(operation_name)
        else:
            # Return all operation metadata
            all_ops = {}
            for op_name in OPERATION_METADATA.keys():
                all_ops[op_name] = get_operation_info(op_name)
            
            # Add summary statistics
            quick_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "quick")
            medium_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "medium")
            long_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "long")
            task_queue_ops = sum(1 for info in all_ops.values() if info["async_pattern"] == "task_queue")
            
            return {
                "operations": all_ops,
                "summary": {
                    "total_operations": len(all_ops),
                    "quick_operations": quick_ops,
                    "medium_operations": medium_ops,
                    "long_operations": long_ops,
                    "task_queue_operations": task_queue_ops,
                    "direct_operations": len(all_ops) - task_queue_ops
                },
                "guidance": {
                    "task_queue_pattern": "Operations that return task_id require polling with get_task_status()",
                    "direct_pattern": "Operations that return results immediately",
                    "timeout_recommendation": "Set MCP client timeouts to at least 60 seconds for medium/long operations"
                }
            }
    except Exception as e:
        return {"error": str(e)}

async def _execute_migrate_context(
    source_registry: str,
    target_registry: str,
    context: Optional[str] = None,
    target_context: Optional[str] = None,
    preserve_ids: bool = True,
    dry_run: bool = True,
    migrate_all_versions: bool = True
) -> Dict[str, Any]:
    """Execute the actual context migration logic."""
    logger.info(f"Starting context migration from {source_registry} to {target_registry}")
    logger.info(f"Source context: {context}, Target context: {target_context or context}")
    logger.info(f"Preserve IDs: {preserve_ids}, Dry run: {dry_run}, Migrate all versions: {migrate_all_versions}")
    
    # Get source client
    source_client = registry_manager.get_registry(source_registry)
    if source_client is None:
        logger.error(f"Source registry '{source_registry}' not found")
        return {"error": f"Source registry '{source_registry}' not found"}
    
    # Get target client
    target_client = registry_manager.get_registry(target_registry)
    if target_client is None:
        logger.error(f"Target registry '{target_registry}' not found")
        return {"error": f"Target registry '{target_registry}' not found"}
    
    # Get all subjects from source context
    logger.info(f"Fetching subjects from source context '{context}' in registry '{source_registry}'")
    subjects = source_client.get_subjects(context)
    if not subjects:
        logger.info(f"No subjects found in context '{context}' of registry '{source_registry}'")
        return {
            "message": f"No subjects found in context '{context}' of registry '{source_registry}'",
            "source_registry": source_registry,
            "target_registry": target_registry,
            "source_context": context,
            "target_context": target_context or context,
            "subjects_migrated": 0,
            "dry_run": dry_run,
            "migrate_all_versions": migrate_all_versions
        }
    
    logger.info(f"Found {len(subjects)} subjects to migrate")
    
    # Initialize results
    migration_results = {
        "successful_subjects": [],
        "failed_subjects": [],
        "skipped_subjects": []
    }
    
    # Use target_context if provided, else default to context
    dest_context = target_context if target_context is not None else context
    logger.info(f"Using target context: {dest_context}")
    
    # Migrate each subject
    for subject in subjects:
        logger.info(f"Processing subject: {subject}")
        try:
            # Get versions for this subject
            logger.info(f"Fetching versions for subject '{subject}' from source registry")
            versions_result = get_schema_versions(subject, context=context, registry=source_registry)
            if isinstance(versions_result, dict) and "error" in versions_result:
                logger.error(f"Failed to get versions for subject '{subject}': {versions_result['error']}")
                migration_results["failed_subjects"].append({
                    "subject": subject,
                    "error": versions_result["error"]
                })
                continue
            
            if not versions_result:
                logger.warning(f"No versions found for subject '{subject}', skipping")
                migration_results["skipped_subjects"].append({
                    "subject": subject,
                    "reason": "No versions found"
                })
                continue
            
            logger.info(f"Found {len(versions_result)} versions for subject '{subject}'")
            
            # If not migrating all versions, only use the latest version
            versions_to_migrate = sorted(versions_result) if migrate_all_versions else [max(versions_result)]
            logger.info(f"Will migrate versions: {versions_to_migrate}")
            
            # Run migrate_schema asynchronously
            logger.info(f"Starting schema migration for subject '{subject}'")
            result = await migrate_schema(
                subject=subject,
                source_registry=source_registry,
                target_registry=target_registry,
                source_context=context,  # Source context
                target_context=dest_context,  # Target context
                preserve_ids=preserve_ids,
                dry_run=dry_run,
                versions=versions_to_migrate  # Pass specific versions to migrate
            )
            
            if "error" in result:
                logger.error(f"Migration failed for subject '{subject}': {result['error']}")
                migration_results["failed_subjects"].append({
                    "subject": subject,
                    "error": result["error"]
                })
            else:
                logger.info(f"Successfully migrated subject '{subject}'")
                migration_results["successful_subjects"].append({
                    "subject": subject,
                    "result": result
                })
                
        except Exception as e:
            logger.error(f"Unexpected error processing subject '{subject}': {str(e)}")
            migration_results["failed_subjects"].append({
                "subject": subject,
                "error": str(e)
            })
    
    # Build final result
    logger.info("Migration completed. Building final results...")
    final_result = {
        "source_registry": source_registry,
        "target_registry": target_registry,
        "source_context": context,
        "target_context": dest_context,
        "preserve_ids": preserve_ids,
        "dry_run": dry_run,
        "migrate_all_versions": migrate_all_versions,
        "total_subjects": len(subjects),
        "successful_subjects": len(migration_results["successful_subjects"]),
        "failed_subjects": len(migration_results["failed_subjects"]),
        "skipped_subjects": len(migration_results["skipped_subjects"]),
        "results": migration_results,
        "status": "completed" if migration_results["failed_subjects"] == [] else "failed",
        "migrated_at": datetime.now().isoformat()
    }
    
    logger.info(f"Migration summary: {final_result['successful_subjects']} successful, "
               f"{final_result['failed_subjects']} failed, {final_result['skipped_subjects']} skipped")
    
    return final_result

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    mcp.run() 