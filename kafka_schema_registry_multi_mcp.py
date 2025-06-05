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

# Import OAuth functionality
from oauth_provider import (
    ENABLE_AUTH, require_scopes, get_oauth_scopes_info, get_fastmcp_config
)

# Initialize FastMCP with OAuth configuration
mcp_config = get_fastmcp_config("Kafka Schema Registry Multi-Registry MCP Server")
mcp = FastMCP(**mcp_config)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import common library functionality
from schema_registry_common import (
    RegistryConfig,
    RegistryClient,
    MigrationTask,
    MultiRegistryManager,
    check_readonly_mode,
    build_context_url,
    get_default_client,
    format_schema_as_avro_idl,
    get_schema_with_metadata,
    export_schema as common_export_schema,
    export_subject as common_export_subject,
    export_context as common_export_context,
    export_global as common_export_global,
    clear_context_batch as common_clear_context_batch,
    SINGLE_REGISTRY_URL,
    SINGLE_REGISTRY_USER,
    SINGLE_REGISTRY_PASSWORD,
    SINGLE_READONLY
)

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
    # Registry management operations
    "list_registries": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_registry_info": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "test_registry_connection": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "test_all_registries": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "compare_registries": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "set_default_registry": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_default_registry": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "check_readonly_mode": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Subject and schema operations (all are quick)
    "get_subjects": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "list_subjects": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_schema": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_schema_versions": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "register_schema": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "check_compatibility": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "delete_subject": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Configuration operations (all are quick)
    "get_global_config": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "update_global_config": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_subject_config": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "update_subject_config": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Mode operations (all are quick)
    "get_mode": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "update_mode": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_subject_mode": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "update_subject_mode": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Operation info (quick)
    "get_operation_info_tool": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Task progress monitoring operations (all are quick)
    "get_comparison_progress": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "list_comparison_tasks": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "watch_comparison_progress": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_migration_progress": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_cleanup_progress": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "list_migration_tasks": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "list_cleanup_tasks": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_task_progress": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "get_task_result": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "list_all_active_tasks": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    
    # Long-running operations using task queue
    "migrate_context": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},  # Now generates config files only
    "migrate_schema": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_context_batch": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_multiple_contexts_batch": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "compare_contexts_across_registries": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "compare_different_contexts": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
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

    def shutdown_sync(self) -> None:
        """Synchronous shutdown for use in exit handlers."""
        self._shutdown = True
        
        # Cancel all running tasks
        for task in self.list_tasks(status=TaskStatus.RUNNING):
            if task._future:
                try:
                    task._future.cancel()
                except RuntimeError:
                    # Event loop might be closed already
                    pass
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now().isoformat()
        
        # Reset the queue
        self.reset_queue()
        
        # Shutdown the executor
        if self._executor:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                # Fallback for older Python versions or if shutdown fails
                try:
                    self._executor.shutdown(wait=True)
                except Exception:
                    pass
            self._executor = None

# Initialize task manager
task_manager = AsyncTaskManager()

# Register cleanup handler
def cleanup_task_manager():
    """Cleanup function to be called at exit"""
    if task_manager:
        task_manager.shutdown_sync()

atexit.register(cleanup_task_manager)

# Configuration - Single Registry Mode (backward compatibility)
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
READONLY = os.getenv("READONLY", "false").lower() in ("true", "1", "yes", "on")

# Multi-registry configuration - supports up to 8 instances
MAX_REGISTRIES = 8

# RegistryConfig moved to schema_registry_common

# MigrationTask moved to schema_registry_common

# RegistryClient moved to schema_registry_common

# Initialize registry manager using the common library
registry_manager = MultiRegistryManager()

# check_readonly_mode function moved to schema_registry_common

# ===== REGISTRY MANAGEMENT TOOLS =====

@mcp.tool()
@require_scopes("read")
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
@require_scopes("read")
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
@require_scopes("read")
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
@require_scopes("read")
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
@require_scopes("read")
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
def compare_contexts_across_registries(
    source_registry: str,
    target_registry: str,
    source_context: str,
    target_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare contexts across two registries (can be different contexts).
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Context name in source registry
        target_context: Context name in target registry (defaults to source_context if not provided)
    
    Returns:
        Context comparison results
    """
    try:
        # If target_context not provided, use source_context (backward compatibility)
        if target_context is None:
            target_context = source_context
            
        # Create async task
        task = task_manager.create_task(
            TaskType.MIGRATION,
            metadata={
                "operation": "compare_contexts",
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_context
            }
        )
        
        # Start async execution
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _execute_compare_contexts,
                    source_registry=source_registry,
                    target_registry=target_registry,
                    source_context=source_context,
                    target_context=target_context
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            import threading
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_compare_contexts,
                        source_registry=source_registry,
                        target_registry=target_registry,
                        source_context=source_context,
                        target_context=target_context
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
        return {
            "message": "Context comparison started as async task",
            "task_id": task.id,
            "task": task.to_dict()
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _execute_compare_contexts(
    source_registry: str,
    target_registry: str,
    source_context: str,
    target_context: str
) -> Dict[str, Any]:
    """Execute the actual context comparison logic."""
    try:
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (task.metadata and 
                task.metadata.get("operation") == "compare_contexts" and
                task.metadata.get("source_registry") == source_registry and
                task.metadata.get("target_registry") == target_registry):
                current_task = task
                break
        
        def update_progress(progress: float):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
        
        update_progress(5.0)  # Starting
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client or not target_client:
            return {"error": "Invalid registry configuration"}
        
        update_progress(10.0)  # Registry clients obtained
        
        # Get subjects from both registries for their respective contexts
        source_subjects = source_client.get_subjects(source_context)
        update_progress(25.0)  # Source subjects retrieved
        
        target_subjects = target_client.get_subjects(target_context)
        update_progress(40.0)  # Target subjects retrieved
        
        # Compare contexts
        source_only = list(set(source_subjects) - set(target_subjects))
        target_only = list(set(target_subjects) - set(source_subjects))
        common = list(set(source_subjects) & set(target_subjects))
        
        update_progress(50.0)  # Basic comparison completed
        
        # Get detailed comparison for common subjects
        subject_details = []
        total_common = len(common)
        
        if total_common > 0:
            for i, subject in enumerate(common):
                try:
                    source_versions = get_schema_versions(subject, context=source_context, registry=source_registry)
                    target_versions = get_schema_versions(subject, context=target_context, registry=target_registry)
                    
                    # Handle cases where get_schema_versions returns error dict
                    if isinstance(source_versions, dict) and "error" in source_versions:
                        source_versions = []
                    if isinstance(target_versions, dict) and "error" in target_versions:
                        target_versions = []
                    
                    subject_details.append({
                        "subject": subject,
                        "source_versions": len(source_versions) if source_versions else 0,
                        "target_versions": len(target_versions) if target_versions else 0,
                        "version_match": source_versions == target_versions
                    })
                    
                    # Update progress based on subjects processed
                    progress = 50.0 + ((i + 1) / total_common) * 40.0  # 50% to 90%
                    update_progress(progress)
                    
                except Exception as e:
                    subject_details.append({
                        "subject": subject,
                        "error": str(e)
                    })
        else:
            update_progress(90.0)  # No common subjects to analyze
        
        update_progress(95.0)  # Building final result
        
        result = {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "source_context": source_context,
            "target_context": target_context,
            "compared_at": datetime.now().isoformat(),
            "summary": {
                "source_only_subjects": len(source_only),
                "target_only_subjects": len(target_only),
                "common_subjects": len(common),
                "total_source_subjects": len(source_subjects),
                "total_target_subjects": len(target_subjects)
            },
            "subjects": {
                "source_only": source_only,
                "target_only": target_only,
                "common": common
            },
            "subject_details": subject_details
        }
        
        update_progress(100.0)  # Completed
        return result
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def compare_different_contexts(
    source_registry: str,
    source_context: str,
    target_registry: str,
    target_context: str,
    include_schema_analysis: bool = True
) -> Dict[str, Any]:
    """
    Compare different contexts across registries with enhanced analysis.
    
    **MEDIUM-DURATION OPERATION** - Uses task queue pattern.
    
    This function is specifically designed for comparing different contexts 
    (e.g., 'production' context in Registry A vs 'staging' context in Registry B).
    
    Args:
        source_registry: Source registry name
        source_context: Context name in source registry
        target_registry: Target registry name  
        target_context: Context name in target registry
        include_schema_analysis: Include detailed schema version analysis
    
    Returns:
        Task information with task_id for monitoring progress
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.MIGRATION,
            metadata={
                "operation": "compare_different_contexts",
                "source_registry": source_registry,
                "source_context": source_context,
                "target_registry": target_registry,
                "target_context": target_context,
                "include_schema_analysis": include_schema_analysis
            }
        )
        
        # Start async execution
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _execute_compare_different_contexts,
                    source_registry=source_registry,
                    source_context=source_context,
                    target_registry=target_registry,
                    target_context=target_context,
                    include_schema_analysis=include_schema_analysis
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            import threading
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_compare_different_contexts,
                        source_registry=source_registry,
                        source_context=source_context,
                        target_registry=target_registry,
                        target_context=target_context,
                        include_schema_analysis=include_schema_analysis
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
        return {
            "message": f"Comparing '{source_context}' in {source_registry} vs '{target_context}' in {target_registry}",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": get_operation_info("compare_contexts_across_registries")
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _execute_compare_different_contexts(
    source_registry: str,
    source_context: str,
    target_registry: str,
    target_context: str,
    include_schema_analysis: bool = True
) -> Dict[str, Any]:
    """Execute enhanced different contexts comparison."""
    try:
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (task.metadata and 
                task.metadata.get("operation") == "compare_different_contexts" and
                task.metadata.get("source_registry") == source_registry and
                task.metadata.get("target_registry") == target_registry):
                current_task = task
                break
        
        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
                if message:
                    logger.info(f"Progress {progress:.1f}%: {message}")
        
        update_progress(2.0, "Starting comparison")
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client or not target_client:
            return {"error": "Invalid registry configuration"}
        
        update_progress(8.0, "Registry clients obtained")
        
        # Get subjects from both contexts
        source_subjects = source_client.get_subjects(source_context)
        update_progress(20.0, f"Retrieved {len(source_subjects)} subjects from source context")
        
        target_subjects = target_client.get_subjects(target_context)
        update_progress(35.0, f"Retrieved {len(target_subjects)} subjects from target context")
        
        # Calculate differences
        source_only = list(set(source_subjects) - set(target_subjects))
        target_only = list(set(target_subjects) - set(source_subjects))
        common = list(set(source_subjects) & set(target_subjects))
        
        # Calculate similarity metrics
        total_unique_subjects = len(set(source_subjects) | set(target_subjects))
        similarity_percent = (len(common) / max(1, total_unique_subjects)) * 100
        
        update_progress(45.0, f"Basic analysis complete: {len(common)} common subjects")
        
        result = {
            "source_registry": source_registry,
            "source_context": source_context,
            "target_registry": target_registry,
            "target_context": target_context,
            "compared_at": datetime.now().isoformat(),
            "same_registry": source_registry == target_registry,
            "same_context": source_context == target_context,
            "summary": {
                "total_source_subjects": len(source_subjects),
                "total_target_subjects": len(target_subjects),
                "source_only_subjects": len(source_only),
                "target_only_subjects": len(target_only),
                "common_subjects": len(common),
                "similarity_percent": round(similarity_percent, 2),
                "total_unique_subjects": total_unique_subjects
            },
            "subjects": {
                "source_only": source_only,
                "target_only": target_only,
                "common": common
            }
        }
        
        # Enhanced schema analysis for common subjects
        if include_schema_analysis and common:
            update_progress(50.0, f"Starting schema analysis for {len(common)} subjects")
            
            schema_analysis = []
            total_subjects = len(common)
            
            for i, subject in enumerate(common):
                try:
                    # Get versions from both contexts
                    source_versions = get_schema_versions(subject, context=source_context, registry=source_registry)
                    target_versions = get_schema_versions(subject, context=target_context, registry=target_registry)
                    
                    # Handle error cases
                    if isinstance(source_versions, dict) and "error" in source_versions:
                        source_versions = []
                    if isinstance(target_versions, dict) and "error" in target_versions:
                        target_versions = []
                    
                    # Version analysis
                    version_analysis = {
                        "subject": subject,
                        "source_versions": sorted(source_versions) if source_versions else [],
                        "target_versions": sorted(target_versions) if target_versions else [],
                        "source_version_count": len(source_versions) if source_versions else 0,
                        "target_version_count": len(target_versions) if target_versions else 0,
                        "versions_identical": sorted(source_versions) == sorted(target_versions) if source_versions and target_versions else False
                    }
                    
                    # Check latest version compatibility
                    if source_versions and target_versions:
                        latest_source = max(source_versions)
                        latest_target = max(target_versions)
                        version_analysis["latest_source_version"] = latest_source
                        version_analysis["latest_target_version"] = latest_target
                        version_analysis["latest_versions_match"] = latest_source == latest_target
                        
                        # Get latest schema content for comparison
                        try:
                            source_schema = get_schema(subject, version=str(latest_source), context=source_context, registry=source_registry)
                            target_schema = get_schema(subject, version=str(latest_target), context=target_context, registry=target_registry)
                            
                            if (isinstance(source_schema, dict) and "schema" in source_schema and
                                isinstance(target_schema, dict) and "schema" in target_schema):
                                version_analysis["latest_schemas_identical"] = source_schema["schema"] == target_schema["schema"]
                                version_analysis["latest_schema_ids_match"] = source_schema.get("id") == target_schema.get("id")
                            
                        except Exception as schema_e:
                            version_analysis["schema_comparison_error"] = str(schema_e)
                    
                    schema_analysis.append(version_analysis)
                    
                    # Update progress for schema analysis (50% to 85%)
                    analysis_progress = 50.0 + ((i + 1) / total_subjects) * 35.0
                    update_progress(analysis_progress, f"Analyzed {i + 1}/{total_subjects} subjects")
                    
                except Exception as e:
                    schema_analysis.append({
                        "subject": subject,
                        "error": str(e)
                    })
            
            result["schema_analysis"] = schema_analysis
            
            update_progress(90.0, "Computing schema analysis summary")
            
            # Add schema analysis summary
            if schema_analysis:
                identical_schemas = sum(1 for s in schema_analysis if s.get("latest_schemas_identical", False))
                matching_versions = sum(1 for s in schema_analysis if s.get("latest_versions_match", False))
                
                result["schema_summary"] = {
                    "subjects_analyzed": len(schema_analysis),
                    "identical_latest_schemas": identical_schemas,
                    "matching_latest_versions": matching_versions,
                    "schema_compatibility_percent": round((identical_schemas / len(schema_analysis)) * 100, 2) if schema_analysis else 0,
                    "version_compatibility_percent": round((matching_versions / len(schema_analysis)) * 100, 2) if schema_analysis else 0
                }
        else:
            update_progress(85.0, "Skipping schema analysis")
        
        update_progress(98.0, "Finalizing results")
        
        update_progress(100.0, "Comparison completed")
        return result
        
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
@require_scopes("read")
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
@require_scopes("read")
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
@require_scopes("write")
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
@require_scopes("read")
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
@require_scopes("write")
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
@require_scopes("write")
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
@require_scopes("write")
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
@require_scopes("write")
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
@require_scopes("read")
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
@require_scopes("admin")
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
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
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
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            import threading
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_clear_context_batch,
                        context=context,
                        registry=registry,
                        delete_context_after=delete_context_after,
                        dry_run=dry_run
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
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
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (task.metadata and 
                task.metadata.get("operation") == "clear_context_batch" and
                task.metadata.get("context") == context and
                task.metadata.get("registry") == registry):
                current_task = task
                break
        
        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
                if message:
                    logger.info(f"Clear Context Progress {progress:.1f}%: {message}")
        
        update_progress(5.0, f"Starting cleanup of context '{context}' in registry '{registry}'")
        
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
        
        update_progress(10.0, "Registry client connected")
            
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
        
        update_progress(20.0, "Fetching subjects from context")
            
        # Get all subjects in the context
        subjects = registry_client.get_subjects(context)
        subjects_found = len(subjects)
        
        if subjects_found == 0:
            update_progress(100.0, "Context is already empty")
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
        
        update_progress(30.0, f"Found {subjects_found} subjects to {'delete' if not dry_run else 'analyze'}")
            
        if dry_run:
            update_progress(100.0, f"DRY RUN: Would delete {subjects_found} subjects")
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
        
        update_progress(40.0, f"Starting deletion of {subjects_found} subjects")
            
        # Delete subjects in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for subject in subjects:
                futures.append(executor.submit(registry_client.delete_subject, subject, context))
                
            total_futures = len(futures)
            for i, future in enumerate(as_completed(futures)):
                try:
                    if future.result():
                        subjects_deleted += 1
                except Exception as e:
                    errors.append(str(e))
                
                # Update progress for deletions (40% to 85%)
                deletion_progress = 40.0 + ((i + 1) / total_futures) * 45.0
                update_progress(deletion_progress, f"Deleted {subjects_deleted} of {subjects_found} subjects")
        
        update_progress(90.0, "Computing cleanup results")
                    
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
                update_progress(95.0, "Context deletion not supported by API")
            except Exception as e:
                errors.append(f"Failed to delete context: {str(e)}")
        
        update_progress(100.0, f"Cleanup completed - deleted {subjects_deleted} subjects")
                
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
@require_scopes("admin")
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
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _execute_clear_multiple_contexts_batch,
                    contexts=contexts,
                    registry=registry,
                    delete_contexts_after=delete_contexts_after,
                    dry_run=dry_run
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            import threading
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_clear_multiple_contexts_batch,
                        contexts=contexts,
                        registry=registry,
                        delete_contexts_after=delete_contexts_after,
                        dry_run=dry_run
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
        return {
            "message": "Context cleanup started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": get_operation_info("clear_multiple_contexts_batch")
        }
        
    except Exception as e:
        return {"error": str(e)}

def _execute_clear_multiple_contexts_batch(
    contexts: List[str],
    registry: str,
    delete_contexts_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Execute the actual multiple contexts cleanup logic."""
    start_time = time.time()
    total_subjects_found = 0
    total_subjects_deleted = 0
    contexts_deleted = 0
    errors = []
    
    try:
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (task.metadata and 
                task.metadata.get("operation") == "clear_multiple_contexts_batch" and
                task.metadata.get("registry") == registry):
                current_task = task
                break
        
        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
                if message:
                    logger.info(f"Multi-Context Clear Progress {progress:.1f}%: {message}")
        
        update_progress(3.0, f"Starting cleanup of {len(contexts)} contexts in registry '{registry}'")
    
        print(f"🚀 Starting batch cleanup of {len(contexts)} contexts in registry '{registry}'...")
        
        # Get registry client
        registry_client = registry_manager.get_registry(registry)
        if not registry_client:
            return {
                "contexts_processed": 0,
                "total_subjects_found": 0,
                "total_subjects_deleted": 0,
                "contexts_deleted": 0,
                "dry_run": dry_run,
                "duration": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' not found",
                "errors": [f"Registry '{registry}' not found"]
            }
        
        update_progress(8.0, "Registry client connected")
        
        # Check if registry is in read-only mode
        readonly_info = check_readonly_mode(registry)
        if readonly_info and readonly_info.get("mode") == "READONLY":
            return {
                "contexts_processed": 0,
                "total_subjects_found": 0,
                "total_subjects_deleted": 0,
                "contexts_deleted": 0,
                "dry_run": dry_run,
                "duration": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' is in read-only mode",
                "errors": [f"Registry '{registry}' is in read-only mode"]
            }
        
        update_progress(15.0, "Starting context processing")
        
        # Process each context
        total_contexts = len(contexts)
        for i, context in enumerate(contexts, 1):
            print(f"\n📂 Processing context {i}/{len(contexts)}: '{context}'")
            
            try:
                # Get subjects in context
                subjects = registry_client.get_subjects(context)
                total_subjects_found += len(subjects)
                
                context_progress_start = 15.0 + ((i - 1) / total_contexts) * 70.0
                context_progress_end = 15.0 + (i / total_contexts) * 70.0
                
                update_progress(context_progress_start, f"Processing context {i}/{total_contexts}: '{context}' ({len(subjects)} subjects)")
                
                if dry_run:
                    print(f"🔍 DRY RUN: Would delete {len(subjects)} subjects from context '{context}'")
                    continue
                
                # Delete subjects in parallel
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for subject in subjects:
                        future = executor.submit(registry_client.delete_subject, subject, context)
                        futures.append(future)
                    
                    # Wait for all deletions to complete
                    context_deleted_count = 0
                    for future in as_completed(futures):
                        try:
                            future.result()
                            total_subjects_deleted += 1
                            context_deleted_count += 1
                        except Exception as e:
                            errors.append(str(e))
                
                # Delete context if requested
                if delete_contexts_after:
                    try:
                        # Delete context by deleting a dummy subject and then the subject
                        dummy_subject = f"dummy-{uuid.uuid4().hex[:8]}"
                        registry_client.register_schema(
                            subject=dummy_subject,
                            schema_definition={"type": "string"},
                            context=context
                        )
                        registry_client.delete_subject(dummy_subject, context)
                        contexts_deleted += 1
                    except Exception as e:
                        errors.append(f"Failed to delete context '{context}': {str(e)}")
                
                update_progress(context_progress_end, f"Completed context '{context}' - deleted {context_deleted_count} subjects")
            
            except Exception as e:
                errors.append(f"Error processing context '{context}': {str(e)}")
        
        update_progress(90.0, "Computing final results")
        
        duration = time.time() - start_time
        success_rate = (total_subjects_deleted / total_subjects_found * 100) if total_subjects_found > 0 else 0.0
        performance = total_subjects_deleted / duration if duration > 0 else 0.0
        
        message = (
            f"DRY RUN: Would delete {total_subjects_found} subjects from {len(contexts)} contexts"
            if dry_run else
            f"Successfully cleared {len(contexts)} contexts - deleted {total_subjects_deleted}/{total_subjects_found} subjects"
        )
        
        update_progress(100.0, message)
        
        return {
            "contexts_processed": len(contexts),
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "contexts_deleted": contexts_deleted,
            "dry_run": dry_run,
            "duration": duration,
            "success_rate": success_rate,
            "performance": performance,
            "message": message,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        return {
            "contexts_processed": 0,
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "contexts_deleted": contexts_deleted,
            "dry_run": dry_run,
            "duration": time.time() - start_time,
            "success_rate": 0.0,
            "performance": 0.0,
            "message": f"Multi-context cleanup failed: {str(e)}",
            "error": str(e)
        }

@mcp.tool()
@require_scopes("admin")
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
            # Don't pass auth parameter - Authorization header is already set in client.headers
            async with session.delete(
                url,
                headers=client.headers
            ) as response:
                response.raise_for_status()
                return await response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
@require_scopes("admin")
def migrate_schema(
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
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
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
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            import threading
            def run_task():
                asyncio.run(
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
            thread = threading.Thread(target=run_task)
            thread.start()
        
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
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (task.metadata and 
                task.metadata.get("operation") == "migrate_schema" and
                task.metadata.get("subject") == subject and
                task.metadata.get("source_registry") == source_registry and
                task.metadata.get("target_registry") == target_registry):
                current_task = task
                break
        
        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
                if message:
                    logger.info(f"Schema Migration Progress {progress:.1f}%: {message}")
        
        update_progress(3.0, f"Starting migration for subject '{subject}'")
        
        logger.info(f"Starting schema migration for subject '{subject}'")
        logger.info(f"Source: {source_registry} ({source_context}), Target: {target_registry} ({target_context})")
        logger.info(f"Preserve IDs: {preserve_ids}, Dry run: {dry_run}")
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client or not target_client:
            logger.error("Invalid registry configuration")
            return {"error": "Invalid registry configuration"}
        
        update_progress(10.0, "Registry clients connected")
        
        # Check if target registry is in readonly mode
        if not dry_run:
            readonly_check = check_readonly_mode(target_registry)
            if readonly_check:
                logger.error(f"Target registry '{target_registry}' is in readonly mode")
                return {
                    "error": readonly_check["error"],
                    "readonly_mode": True,
                    "target_registry": target_registry
                }
        
        update_progress(11.0, "Target registry verified as writable")
        
        # For source operations, use the subject as-is
        source_subject = subject
        
        # For target operations, we may need to extract the bare subject name
        # if we're migrating to a different context
        target_subject_name = subject
        
        # If the subject has a context prefix, extract the bare subject name for target
        if subject.startswith(":.") and ":" in subject[2:]:
            # Format is :.context:subject
            parts = subject.split(":", 2)
            if len(parts) >= 3:
                # Extract just the subject name for target registration
                target_subject_name = parts[2]
                logger.info(f"Subject has context prefix. Full name: {subject}, bare name: {target_subject_name}")
        
        # Get all versions of the schema from source using the full subject name
        logger.info(f"Fetching versions from source registry for subject '{source_subject}'")
        versions_result = get_schema_versions(source_subject, context=source_context, registry=source_registry)
        if isinstance(versions_result, dict) and "error" in versions_result:
            logger.error(f"Failed to get versions: {versions_result['error']}")
            return versions_result
        if not versions_result:
            logger.error(f"Subject {source_subject} not found in source registry")
            return {"error": f"Subject {source_subject} not found in source registry"}
        
        update_progress(12.0, f"Found {len(versions_result)} versions in source")
        
        # If specific versions are provided, use those; otherwise use all versions
        versions_to_migrate = versions if versions is not None else sorted(versions_result)
        logger.info(f"Versions to migrate: {versions_to_migrate}")
        
        update_progress(15.0, f"Will migrate {len(versions_to_migrate)} versions")
        
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
        
        update_progress(17.0, "Checking target context and subject status")
        
        # Only check subject existence if context exists
        target_subject_exists = False
        if target_context_exists:
            try:
                target_versions = get_schema_versions(target_subject_name, context=target_context, registry=target_registry)
                if isinstance(target_versions, dict) and "error" in target_versions:
                    if "404" in str(target_versions.get("error", "")):
                        # 404 is expected if subject doesn't exist
                        target_subject_exists = False
                    else:
                        logger.debug(f"Error checking target subject existence: {target_versions['error']}")
                else:
                    target_subject_exists = len(target_versions) > 0
                    if target_subject_exists:
                        logger.warning(f"Subject {target_subject_name} already exists in target registry. Will delete before migration.")
            except Exception as e:
                logger.debug(f"Error checking target subject existence: {e}")
        
        update_progress(18.0, "Preparing target registry for migration")
        
        # Store original mode for restoration
        original_mode = None
        if preserve_ids:
            try:
                # If subject exists in target, we need to delete it first
                if target_subject_exists:
                    logger.info(f"Deleting existing subject {target_subject_name} from target registry before migration")
                    await delete_subject(target_subject_name, context=target_context, registry=target_registry)
                    # After deletion, subject no longer exists
                    target_subject_exists = False

                # Now set IMPORT mode on the target subject in target context
                if target_context == ".":
                    subject_mode_url = f"{target_client.config.url}/mode/{target_subject_name}"
                    logger.info(f"Setting IMPORT mode on target subject {target_subject_name} in default context")
                else:
                    subject_mode_url = f"{target_client.config.url}/contexts/{target_context}/mode/{target_subject_name}"
                    logger.info(f"Setting IMPORT mode on target subject {target_subject_name} in context {target_context}")
                    
                logger.info(f"Setting IMPORT mode on target subject {target_context}/{target_subject_name} in target registry.")
                async with aiohttp.ClientSession() as session:
                    # Don't pass auth parameter - Authorization header is already set in target_client.standard_headers
                    async with session.put(
                        subject_mode_url, 
                        json={"mode": "IMPORT"},
                        headers=target_client.standard_headers
                    ) as response:
                        if response.status == 405:
                            logger.warning("IMPORT mode not supported by target registry, will proceed without ID preservation")
                            preserve_ids = False
                        elif response.status != 200:
                            logger.warning(f"Failed to set IMPORT mode on subject: {response.status} - {await response.text()}")
                            preserve_ids = False
                        else:
                            logger.info("Successfully set IMPORT mode on target subject")
                
            except Exception as e:
                logger.warning(f"Error setting IMPORT mode: {e}")
                preserve_ids = False
        
        update_progress(20.0, f"Starting migration of {len(versions_to_migrate)} versions")
        
        # Migrate each version
        migrated_versions = []
        total_versions = len(versions_to_migrate)
        
        for i, version in enumerate(versions_to_migrate):
            try:
                logger.info(f"Processing version {version} of subject '{source_subject}'")
                # Get schema from source
                schema_data = get_schema(source_subject, version=version, context=source_context, registry=source_registry)
                if not schema_data:
                    logger.error(f"Failed to get schema for version {version}")
                    continue
                
                # Register in target
                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate {source_subject} version {version}")
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
                    
                    # Add ID and version if preserving IDs (to maintain sparse version numbers)
                    if preserve_ids and schema_data.get("id"):
                        payload["id"] = schema_data.get("id")
                        payload["version"] = version  # CRITICAL: Include version to preserve sparse numbering
                        logger.info(f"Preserving schema ID {schema_data.get('id')} and version {version}")
                    else:
                        logger.info(f"Not preserving IDs - version {version} will be auto-assigned sequential number in target")
                    
                    # Register schema
                    url = target_client.build_context_url(f"/subjects/{target_subject_name}/versions", target_context)
                    logger.info(f"Registering schema version {version} in target registry")
                    async with aiohttp.ClientSession() as session:
                        # Don't pass auth parameter - Authorization header is already set in target_client.standard_headers
                        async with session.post(
                            url,
                            json=payload,
                            headers=target_client.headers
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                # When preserving IDs, the result should maintain the original version
                                actual_version = result.get("version", version)
                                logger.info(f"Successfully registered version {actual_version} with ID {result.get('id')}")
                                migrated_versions.append({
                                    "version": actual_version,
                                    "id": result.get("id"),
                                    "schema": schema_data.get("schema")
                                })
                            else:
                                error_text = await response.text()
                                logger.error(f"Error migrating version {version}: {error_text}")
                                continue
                
                # Update progress for version migration (50% to 85%)
                version_progress = 50.0 + ((i + 1) / total_versions) * 35.0
                update_progress(version_progress, f"Migrated version {version} ({i + 1}/{total_versions})")
                
            except Exception as e:
                logger.error(f"Error migrating version {version}: {e}")
                continue
        
        # Restore original mode if we changed it
        if preserve_ids and original_mode:
            update_progress(95.0, "Restoring subject mode")
            try:
                # First restore mode on the target subject
                # Construct the correct mode URL based on whether we're using default context or not
                if target_context == ".":
                    subject_mode_url = f"{target_client.config.url}/mode/{target_subject_name}"
                    logger.info(f"Restoring original mode for subject {target_subject_name} in default context")
                else:
                    subject_mode_url = f"{target_client.config.url}/contexts/{target_context}/mode/{target_subject_name}"
                    logger.info(f"Restoring original mode for subject {target_subject_name} in context {target_context}")
                
                async with aiohttp.ClientSession() as session:
                    # Don't pass auth parameter - Authorization header is already set in target_client.standard_headers
                    async with session.put(
                        subject_mode_url,
                        json={"mode": original_mode},
                        headers=target_client.standard_headers
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Restored original subject mode: {original_mode}")
                        else:
                            logger.warning(f"Failed to restore original subject mode: {response.status}")
                
                # Then restore mode on the target context
                context_mode_url = f"{target_client.config.url}/mode"
                logger.info(f"Restoring original context mode: {original_mode}")
                async with aiohttp.ClientSession() as session:
                    # Don't pass auth parameter - Authorization header is already set in target_client.standard_headers
                    async with session.put(
                        context_mode_url,
                        json={"mode": original_mode},
                        headers=target_client.standard_headers
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Restored original context mode: {original_mode}")
                        else:
                            logger.warning(f"Failed to restore original context mode: {response.status}")
            except Exception as e:
                logger.warning(f"Error restoring original mode: {e}")
        
        update_progress(95.0, "Building migration results")
        
        logger.info(f"Migration completed for subject '{subject}'. Migrated {len(migrated_versions)} versions")
        
        result = {
            "task_id": str(uuid.uuid4()),
            "subject": subject,
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
        
        update_progress(100.0, f"Schema migration completed - {len(migrated_versions)} versions migrated")
        
        return result
        
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
def get_oauth_scopes_info() -> Dict[str, Any]:
    """
    Get information about OAuth scopes and permissions in this MCP server.
    
    Returns:
        Dictionary containing scope definitions, required permissions per tool, and test tokens
    """
    return get_oauth_scopes_info()

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

@mcp.tool()
async def get_comparison_progress(task_id: str) -> Dict[str, Any]:
    """
    Get detailed progress information for comparison operations.
    
    Args:
        task_id: Task ID of the comparison operation
    
    Returns:
        Detailed progress information with status and completion percentage
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        # Check if this is a comparison operation
        operation = task.metadata.get("operation", "") if task.metadata else ""
        if not operation.startswith("compare"):
            return {
                "error": f"Task '{task_id}' is not a comparison operation. Operation: {operation}",
                "task_type": operation
            }
        
        # Build detailed progress info
        progress_info = {
            "task_id": task_id,
            "operation": operation,
            "status": task.status.value,
            "progress_percent": round(task.progress, 1),
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }
        
        # Add operation-specific metadata
        if task.metadata:
            if "source_registry" in task.metadata:
                progress_info["source_registry"] = task.metadata["source_registry"]
            if "target_registry" in task.metadata:
                progress_info["target_registry"] = task.metadata["target_registry"]
            if "source_context" in task.metadata:
                progress_info["source_context"] = task.metadata["source_context"]
            if "target_context" in task.metadata:
                progress_info["target_context"] = task.metadata["target_context"]
        
        # Calculate duration if running
        if task.started_at:
            try:
                start_time = datetime.fromisoformat(task.started_at.replace('Z', '+00:00'))
                if task.status == TaskStatus.RUNNING:
                    current_time = datetime.now()
                    duration = (current_time - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["duration_seconds"] = round(duration, 1)
                    
                    # Estimate remaining time based on progress
                    if task.progress > 0:
                        estimated_total = duration / (task.progress / 100.0)
                        remaining = estimated_total - duration
                        progress_info["estimated_remaining_seconds"] = round(max(0, remaining), 1)
                elif task.completed_at:
                    end_time = datetime.fromisoformat(task.completed_at.replace('Z', '+00:00'))
                    duration = (end_time.replace(tzinfo=None) - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["total_duration_seconds"] = round(duration, 1)
            except Exception as date_error:
                # If datetime parsing fails, just skip duration calculation
                logger.debug(f"Could not parse datetime: {date_error}")
        
        # Add progress stage description
        progress_info["progress_stage"] = _get_progress_stage_description(operation, task.progress)
        
        # Add result preview if completed
        if task.status == TaskStatus.COMPLETED and task.result:
            if "summary" in task.result:
                progress_info["result_preview"] = task.result["summary"]
        
        # Add error if failed
        if task.status == TaskStatus.FAILED and task.error:
            progress_info["error"] = task.error
        
        return progress_info
        
    except Exception as e:
        return {"error": str(e)}

def _get_progress_stage_description(operation: str, progress: float) -> str:
    """Get human-readable description of current progress stage."""
    if operation.startswith("compare"):
        if progress < 5:
            return "Initializing comparison"
        elif progress < 15:
            return "Connecting to registries"
        elif progress < 30:
            return "Retrieving subjects from source"
        elif progress < 45:
            return "Retrieving subjects from target"
        elif progress < 55:
            return "Analyzing subject differences"
        elif progress < 85:
            return "Performing detailed schema analysis"
        elif progress < 95:
            return "Computing compatibility metrics"
        elif progress < 100:
            return "Finalizing results"
        else:
            return "Completed"
    elif operation.startswith("migrate"):
        if progress < 5:
            return "Initializing migration"
        elif progress < 15:
            return "Connecting to registries"
        elif progress < 30:
            return "Analyzing source schemas"
        elif progress < 50:
            return "Preparing target registry"
        elif progress < 85:
            return "Migrating schema versions"
        elif progress < 95:
            return "Restoring registry settings"
        elif progress < 100:
            return "Finalizing migration"
        else:
            return "Migration completed"
    elif operation.startswith("clear"):
        if progress < 10:
            return "Initializing cleanup"
        elif progress < 20:
            return "Connecting to registry"
        elif progress < 40:
            return "Scanning for subjects"
        elif progress < 85:
            return "Deleting subjects"
        elif progress < 95:
            return "Computing cleanup results"
        elif progress < 100:
            return "Finalizing cleanup"
        else:
            return "Cleanup completed"
    else:
        # Generic progress descriptions
        if progress < 10:
            return "Starting operation"
        elif progress < 50:
            return "Processing"
        elif progress < 90:
            return "Completing operation"
        elif progress < 100:
            return "Finalizing"
        else:
            return "Completed"

@mcp.tool()
async def list_comparison_tasks(
    include_completed: bool = False,
    registry_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all comparison tasks with their current progress.
    
    Args:
        include_completed: Include completed/failed tasks in results
        registry_filter: Filter tasks by registry name (source or target)
    
    Returns:
        List of comparison tasks with progress information
    """
    try:
        # Get all tasks
        all_tasks = task_manager.list_tasks()
        
        # Filter for comparison operations
        comparison_tasks = []
        for task in all_tasks:
            operation = task.metadata.get("operation", "") if task.metadata else ""
            if operation.startswith("compare"):
                # Apply status filter
                if not include_completed and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    continue
                
                # Apply registry filter
                if registry_filter:
                    source_reg = task.metadata.get("source_registry", "") if task.metadata else ""
                    target_reg = task.metadata.get("target_registry", "") if task.metadata else ""
                    if registry_filter not in [source_reg, target_reg]:
                        continue
                
                # Build task info
                task_info = {
                    "task_id": task.id,
                    "operation": operation,
                    "status": task.status.value,
                    "progress_percent": round(task.progress, 1),
                    "created_at": task.created_at,
                    "progress_stage": _get_progress_stage_description(operation, task.progress)
                }
                
                # Add metadata
                if task.metadata:
                    for key in ["source_registry", "target_registry", "source_context", "target_context"]:
                        if key in task.metadata:
                            task_info[key] = task.metadata[key]
                
                comparison_tasks.append(task_info)
        
        return sorted(comparison_tasks, key=lambda x: x["created_at"], reverse=True)
        
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
async def watch_comparison_progress(
    task_id: str,
    update_interval_seconds: int = 2,
    max_updates: int = 30
) -> Dict[str, Any]:
    """
    Watch progress of a comparison operation with periodic updates.
    
    **Note:** This returns a stream of progress updates. For real-time monitoring,
    call this function and then poll get_comparison_progress() separately.
    
    Args:
        task_id: Task ID to monitor
        update_interval_seconds: Seconds between progress checks
        max_updates: Maximum number of updates to return
    
    Returns:
        Progress monitoring session information
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        operation = task.metadata.get("operation", "") if task.metadata else ""
        if not operation.startswith("compare"):
            return {
                "error": f"Task '{task_id}' is not a comparison operation",
                "task_type": operation
            }
        
        return {
            "message": f"Use get_comparison_progress('{task_id}') to monitor progress",
            "task_id": task_id,
            "operation": operation,
            "current_status": task.status.value,
            "current_progress": round(task.progress, 1),
            "monitoring_guidance": {
                "recommended_interval": f"{update_interval_seconds} seconds",
                "suggested_max_polls": max_updates,
                "stop_when": "status is 'completed', 'failed', or 'cancelled'"
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_migration_progress(task_id: str) -> Dict[str, Any]:
    """
    Get detailed progress information for migration operations.
    
    Args:
        task_id: Task ID of the migration operation
    
    Returns:
        Detailed progress information with status and completion percentage
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        # Check if this is a migration operation
        operation = task.metadata.get("operation", "") if task.metadata else ""
        if not operation.startswith("migrate"):
            return {
                "error": f"Task '{task_id}' is not a migration operation. Operation: {operation}",
                "task_type": operation
            }
        
        # Build detailed progress info
        progress_info = {
            "task_id": task_id,
            "operation": operation,
            "status": task.status.value,
            "progress_percent": round(task.progress, 1),
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "progress_stage": _get_progress_stage_description(operation, task.progress)
        }
        
        # Add operation-specific metadata
        if task.metadata:
            for key in ["source_registry", "target_registry", "source_context", "target_context", "subject", "preserve_ids", "dry_run"]:
                if key in task.metadata:
                    progress_info[key] = task.metadata[key]
        
        # Calculate duration and estimates
        if task.started_at:
            try:
                start_time = datetime.fromisoformat(task.started_at.replace('Z', '+00:00'))
                if task.status == TaskStatus.RUNNING:
                    current_time = datetime.now()
                    duration = (current_time - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["duration_seconds"] = round(duration, 1)
                    
                    if task.progress > 0:
                        estimated_total = duration / (task.progress / 100.0)
                        remaining = estimated_total - duration
                        progress_info["estimated_remaining_seconds"] = round(max(0, remaining), 1)
                elif task.completed_at:
                    end_time = datetime.fromisoformat(task.completed_at.replace('Z', '+00:00'))
                    duration = (end_time.replace(tzinfo=None) - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["total_duration_seconds"] = round(duration, 1)
            except Exception:
                pass
        
        # Add result preview if completed
        if task.status == TaskStatus.COMPLETED and task.result:
            if operation == "migrate_context":
                progress_info["result_preview"] = {
                    "total_subjects": task.result.get("total_subjects", 0),
                    "successful_subjects": task.result.get("successful_subjects", 0),
                    "failed_subjects": task.result.get("failed_subjects", 0),
                    "status": task.result.get("status", "unknown")
                }
            elif operation == "migrate_schema":
                progress_info["result_preview"] = {
                    "subject": task.result.get("subject", ""),
                    "versions_migrated": task.result.get("versions_migrated", 0),
                    "total_versions": task.result.get("total_versions", 0)
                }
        
        if task.status == TaskStatus.FAILED and task.error:
            progress_info["error"] = task.error
        
        return progress_info
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_cleanup_progress(task_id: str) -> Dict[str, Any]:
    """
    Get detailed progress information for cleanup operations.
    
    Args:
        task_id: Task ID of the cleanup operation
    
    Returns:
        Detailed progress information with status and completion percentage
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        # Check if this is a cleanup operation
        operation = task.metadata.get("operation", "") if task.metadata else ""
        if not operation.startswith("clear"):
            return {
                "error": f"Task '{task_id}' is not a cleanup operation. Operation: {operation}",
                "task_type": operation
            }
        
        # Build detailed progress info
        progress_info = {
            "task_id": task_id,
            "operation": operation,
            "status": task.status.value,
            "progress_percent": round(task.progress, 1),
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "progress_stage": _get_progress_stage_description(operation, task.progress)
        }
        
        # Add operation-specific metadata
        if task.metadata:
            for key in ["registry", "context", "contexts", "delete_context_after", "dry_run"]:
                if key in task.metadata:
                    progress_info[key] = task.metadata[key]
        
        # Calculate duration and estimates
        if task.started_at:
            try:
                start_time = datetime.fromisoformat(task.started_at.replace('Z', '+00:00'))
                if task.status == TaskStatus.RUNNING:
                    current_time = datetime.now()
                    duration = (current_time - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["duration_seconds"] = round(duration, 1)
                    
                    if task.progress > 0:
                        estimated_total = duration / (task.progress / 100.0)
                        remaining = estimated_total - duration
                        progress_info["estimated_remaining_seconds"] = round(max(0, remaining), 1)
                elif task.completed_at:
                    end_time = datetime.fromisoformat(task.completed_at.replace('Z', '+00:00'))
                    duration = (end_time.replace(tzinfo=None) - start_time.replace(tzinfo=None)).total_seconds()
                    progress_info["total_duration_seconds"] = round(duration, 1)
            except Exception:
                pass
        
        # Add result preview if completed
        if task.status == TaskStatus.COMPLETED and task.result:
            if "subjects_deleted" in task.result:
                progress_info["result_preview"] = {
                    "subjects_found": task.result.get("subjects_found", 0),
                    "subjects_deleted": task.result.get("subjects_deleted", 0),
                    "success_rate": task.result.get("success_rate", 0),
                    "contexts_processed": task.result.get("contexts_processed", 1)
                }
        
        if task.status == TaskStatus.FAILED and task.error:
            progress_info["error"] = task.error
        
        return progress_info
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def list_migration_tasks(
    include_completed: bool = False,
    registry_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all migration tasks with their current progress.
    
    Args:
        include_completed: Include completed/failed tasks in results
        registry_filter: Filter tasks by registry name (source or target)
    
    Returns:
        List of migration tasks with progress information
    """
    try:
        all_tasks = task_manager.list_tasks()
        
        migration_tasks = []
        for task in all_tasks:
            operation = task.metadata.get("operation", "") if task.metadata else ""
            if operation.startswith("migrate"):
                if not include_completed and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    continue
                
                if registry_filter:
                    source_reg = task.metadata.get("source_registry", "") if task.metadata else ""
                    target_reg = task.metadata.get("target_registry", "") if task.metadata else ""
                    if registry_filter not in [source_reg, target_reg]:
                        continue
                
                task_info = {
                    "task_id": task.id,
                    "operation": operation,
                    "status": task.status.value,
                    "progress_percent": round(task.progress, 1),
                    "created_at": task.created_at,
                    "progress_stage": _get_progress_stage_description(operation, task.progress)
                }
                
                if task.metadata:
                    for key in ["source_registry", "target_registry", "source_context", "target_context", "subject"]:
                        if key in task.metadata:
                            task_info[key] = task.metadata[key]
                
                migration_tasks.append(task_info)
        
        return sorted(migration_tasks, key=lambda x: x["created_at"], reverse=True)
        
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
async def list_cleanup_tasks(
    include_completed: bool = False,
    registry_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all cleanup tasks with their current progress.
    
    Args:
        include_completed: Include completed/failed tasks in results
        registry_filter: Filter tasks by registry name
    
    Returns:
        List of cleanup tasks with progress information
    """
    try:
        all_tasks = task_manager.list_tasks()
        
        cleanup_tasks = []
        for task in all_tasks:
            operation = task.metadata.get("operation", "") if task.metadata else ""
            if operation.startswith("clear"):
                if not include_completed and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    continue
                
                if registry_filter:
                    registry = task.metadata.get("registry", "") if task.metadata else ""
                    if registry_filter != registry:
                        continue
                
                task_info = {
                    "task_id": task.id,
                    "operation": operation,
                    "status": task.status.value,
                    "progress_percent": round(task.progress, 1),
                    "created_at": task.created_at,
                    "progress_stage": _get_progress_stage_description(operation, task.progress)
                }
                
                if task.metadata:
                    for key in ["registry", "context", "contexts", "dry_run"]:
                        if key in task.metadata:
                            task_info[key] = task.metadata[key]
                
                cleanup_tasks.append(task_info)
        
        return sorted(cleanup_tasks, key=lambda x: x["created_at"], reverse=True)
        
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
async def get_task_progress(task_id: str) -> Dict[str, Any]:
    """
    Get detailed progress information for any task (comparison, migration, or cleanup).
    
    This is a unified progress monitoring tool that automatically detects the operation type
    and provides appropriate progress information.
    
    Args:
        task_id: Task ID of any operation
    
    Returns:
        Detailed progress information with status and completion percentage
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        operation = task.metadata.get("operation", "") if task.metadata else ""
        
        # Route to specific progress handler based on operation type
        if operation.startswith("compare"):
            return await get_comparison_progress(task_id)
        elif operation.startswith("migrate"):
            return await get_migration_progress(task_id)
        elif operation.startswith("clear"):
            return await get_cleanup_progress(task_id)
        else:
            # Generic progress info for unknown operation types
            progress_info = {
                "task_id": task_id,
                "operation": operation,
                "status": task.status.value,
                "progress_percent": round(task.progress, 1),
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "progress_stage": _get_progress_stage_description(operation, task.progress)
            }
            
            if task.metadata:
                progress_info["metadata"] = task.metadata
            
            if task.status == TaskStatus.FAILED and task.error:
                progress_info["error"] = task.error
            elif task.status == TaskStatus.COMPLETED and task.result:
                progress_info["result"] = task.result
            
            return progress_info
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def list_all_active_tasks() -> List[Dict[str, Any]]:
    """
    List all currently active tasks (running or pending) across all operation types.
    
    Returns:
        List of all active tasks with progress information
    """
    try:
        all_tasks = task_manager.list_tasks()
        
        active_tasks = []
        for task in all_tasks:
            if task.status in [TaskStatus.RUNNING, TaskStatus.PENDING]:
                operation = task.metadata.get("operation", "") if task.metadata else ""
                
                task_info = {
                    "task_id": task.id,
                    "operation": operation,
                    "operation_type": _categorize_operation(operation),
                    "status": task.status.value,
                    "progress_percent": round(task.progress, 1),
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "progress_stage": _get_progress_stage_description(operation, task.progress)
                }
                
                # Add relevant metadata based on operation type
                if task.metadata:
                    if operation.startswith("compare"):
                        for key in ["source_registry", "target_registry", "source_context", "target_context"]:
                            if key in task.metadata:
                                task_info[key] = task.metadata[key]
                    elif operation.startswith("migrate"):
                        for key in ["source_registry", "target_registry", "subject", "source_context", "target_context"]:
                            if key in task.metadata:
                                task_info[key] = task.metadata[key]
                    elif operation.startswith("clear"):
                        for key in ["registry", "context", "contexts"]:
                            if key in task.metadata:
                                task_info[key] = task.metadata[key]
                
                active_tasks.append(task_info)
        
        return sorted(active_tasks, key=lambda x: x["created_at"], reverse=True)
        
    except Exception as e:
        return [{"error": str(e)}]

def _categorize_operation(operation: str) -> str:
    """Categorize operation type for unified task listing."""
    if operation.startswith("compare"):
        return "comparison"
    elif operation.startswith("migrate"):
        return "migration"
    elif operation.startswith("clear"):
        return "cleanup"
    else:
        return "other"

@mcp.tool()
@require_scopes("admin")
async def migrate_context(
    source_registry: str,
    target_registry: str,
    context: Optional[str] = None,
    target_context: Optional[str] = None,
    preserve_ids: bool = True,
    dry_run: bool = True,
    migrate_all_versions: bool = True
) -> Dict[str, Any]:
    """
    Guide for migrating an entire context using Docker-based Kafka Schema Registry Migrator.
    
    This function generates configuration files and instructions for using the
    kafka-schema-reg-migrator Docker container, which provides a more robust
    migration solution with better error handling and recovery capabilities.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Source context to migrate (default: ".")
        target_context: Target context name (defaults to source context)
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        dry_run: Preview migration without executing
        migrate_all_versions: Migrate all versions or just latest
    
    Returns:
        Migration guide with configuration files and Docker commands
    """
    try:
        # Get registry configurations
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client:
            return {"error": f"Source registry '{source_registry}' not found"}
        if not target_client:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        # Use default context if not specified
        context = context or "."
        target_context = target_context or context
        
        # Generate .env file content
        env_content = f"""# Kafka Schema Registry Migrator Configuration
# Generated by kafka_schema_registry_multi_mcp
# Documentation: https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md

# Source Registry Configuration
SCHEMA_REGISTRY_URL={source_client.config.url}
{f'SCHEMA_REGISTRY_USERNAME={source_client.config.user}' if source_client.config.user else '# SCHEMA_REGISTRY_USERNAME='}
{f'SCHEMA_REGISTRY_PASSWORD={source_client.config.password}' if source_client.config.password else '# SCHEMA_REGISTRY_PASSWORD='}

# Target Registry Configuration
TARGET_SCHEMA_REGISTRY_URL={target_client.config.url}
{f'TARGET_SCHEMA_REGISTRY_USERNAME={target_client.config.user}' if target_client.config.user else '# TARGET_SCHEMA_REGISTRY_USERNAME='}
{f'TARGET_SCHEMA_REGISTRY_PASSWORD={target_client.config.password}' if target_client.config.password else '# TARGET_SCHEMA_REGISTRY_PASSWORD='}

# Migration Options
SOURCE_CONTEXT={context}
TARGET_CONTEXT={target_context}
PRESERVE_SCHEMA_IDS={str(preserve_ids).lower()}
MIGRATE_ALL_VERSIONS={str(migrate_all_versions).lower()}
DRY_RUN={str(dry_run).lower()}

# Additional Options (customize as needed)
# BATCH_SIZE=50
# CONCURRENT_REQUESTS=5
# RETRY_ATTEMPTS=3
# LOG_LEVEL=INFO
"""

        # Generate docker-compose.yml content
        docker_compose_content = f"""version: '3.8'

services:
  schema-registry-migrator:
    image: aywengo/kafka-schema-reg-migrator:latest
    env_file:
      - .env
    environment:
      - MODE=migrate-context
    volumes:
      - ./logs:/app/logs
      - ./backups:/app/backups
    command: ["--source-context", "{context}", "--target-context", "{target_context}"]
"""

        # Generate shell script for easy execution
        shell_script_content = f"""#!/bin/bash
# Kafka Schema Registry Context Migration Script
# Generated by kafka_schema_registry_multi_mcp

echo "🚀 Starting Kafka Schema Registry Context Migration"
echo "Source: {source_registry} (context: {context})"
echo "Target: {target_registry} (context: {target_context})"
echo ""

# Run the migration using Docker
docker run -it --rm \\
  --env-file .env \\
  -v "$(pwd)/logs:/app/logs" \\
  -v "$(pwd)/backups:/app/backups" \\
  aywengo/kafka-schema-reg-migrator:latest \\
  migrate-context \\
  --source-context "{context}" \\
  --target-context "{target_context}" \\
  {'--dry-run' if dry_run else ''} \\
  {'--preserve-ids' if preserve_ids else ''} \\
  {'--all-versions' if migrate_all_versions else '--latest-only'}

echo ""
echo "✅ Migration process completed. Check logs directory for details."
"""

        # Generate migration guide
        guide = {
            "migration_type": "Docker-based Context Migration",
            "tool": "kafka-schema-reg-migrator",
            "documentation": "https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md",
            "source": {
                "registry": source_registry,
                "url": source_client.config.url,
                "context": context
            },
            "target": {
                "registry": target_registry,
                "url": target_client.config.url,
                "context": target_context,
                "readonly": target_client.config.readonly
            },
            "options": {
                "preserve_ids": preserve_ids,
                "dry_run": dry_run,
                "migrate_all_versions": migrate_all_versions
            },
            "files_to_create": {
                ".env": {
                    "description": "Environment configuration file",
                    "content": env_content
                },
                "docker-compose.yml": {
                    "description": "Docker Compose configuration",
                    "content": docker_compose_content
                },
                "migrate-context.sh": {
                    "description": "Migration execution script",
                    "content": shell_script_content,
                    "make_executable": True
                }
            },
            "instructions": [
                "1. Create a new directory for the migration:",
                f"   mkdir schema-migration-{context.replace('.', 'default')}-to-{target_context.replace('.', 'default')}",
                f"   cd schema-migration-{context.replace('.', 'default')}-to-{target_context.replace('.', 'default')}",
                "",
                "2. Create the configuration files:",
                "   - Save the .env content to a file named '.env'",
                "   - Save the docker-compose.yml content to 'docker-compose.yml'",
                "   - Save the shell script to 'migrate-context.sh' and make it executable:",
                "     chmod +x migrate-context.sh",
                "",
                "3. Review and adjust the .env file as needed",
                "",
                "4. Run the migration:",
                "   Option A: Using Docker Compose:",
                "     docker-compose up",
                "   Option B: Using the shell script:",
                "     ./migrate-context.sh",
                "   Option C: Direct Docker command:",
                "     docker run -it --rm --env-file .env aywengo/kafka-schema-reg-migrator:latest",
                "",
                "5. Monitor the migration:",
                "   - Logs will be saved in the ./logs directory",
                "   - Backups (if enabled) will be in ./backups",
                "",
                "6. Verify the migration:",
                "   - Use compare_contexts_across_registries to verify the migration"
            ],
            "warnings": []
        }
        
        # Add warnings if needed
        if target_client.config.readonly:
            guide["warnings"].append(f"⚠️  Target registry '{target_registry}' is marked as READONLY. Ensure it's writable before migration.")
        
        if not dry_run:
            guide["warnings"].append("⚠️  This will perform actual data migration. Consider running with dry_run=True first.")
        
        if preserve_ids:
            guide["warnings"].append("⚠️  ID preservation requires IMPORT mode on target registry. The migrator will handle this automatically.")
        
        return guide
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_task_result(task_id: str) -> Dict[str, Any]:
    """
    Get the complete result of a finished task.
    
    This function returns the full result data for completed tasks, including
    all details that may not be included in the progress preview.
    
    Args:
        task_id: Task ID to get results for
    
    Returns:
        Complete task result data or error if task not found/not completed
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        
        if task.status == TaskStatus.COMPLETED:
            if task.result:
                return {
                    "task_id": task_id,
                    "operation": task.metadata.get("operation", "") if task.metadata else "",
                    "status": "completed",
                    "completed_at": task.completed_at,
                    "result": task.result
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "completed_at": task.completed_at,
                    "result": None,
                    "message": "Task completed but no result data available"
                }
        elif task.status == TaskStatus.FAILED:
            return {
                "task_id": task_id,
                "status": "failed",
                "completed_at": task.completed_at,
                "error": task.error or "Task failed without error message"
            }
        elif task.status == TaskStatus.CANCELLED:
            return {
                "task_id": task_id,
                "status": "cancelled",
                "completed_at": task.completed_at,
                "message": "Task was cancelled"
            }
        else:
            return {
                "task_id": task_id,
                "status": task.status.value,
                "message": f"Task is still {task.status.value}. Use get_task_progress() to monitor.",
                "progress_percent": round(task.progress, 1)
            }
            
    except Exception as e:
        return {"error": str(e)}

# ===== COUNTING TOOLS =====

@mcp.tool()
def count_contexts(registry: Optional[str] = None) -> Dict[str, Any]:
    """
    Count the number of contexts in a registry.
    
    Args:
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing context count and details
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts
            
        return {
            "registry": client.config.name,
            "total_contexts": len(contexts),
            "contexts": contexts,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def count_schemas(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Count the number of schemas in a context or registry.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing schema count and details
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        subjects = client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            return subjects
            
        return {
            "registry": client.config.name,
            "context": context or "default",
            "total_schemas": len(subjects),
            "schemas": subjects,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def count_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Count the number of versions for a specific schema.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing version count and details
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        versions = get_schema_versions(subject, context, registry)
        if isinstance(versions, dict) and "error" in versions:
            return versions
            
        return {
            "registry": client.config.name,
            "context": context or "default",
            "subject": subject,
            "total_versions": len(versions),
            "versions": versions,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_registry_statistics(
    registry: Optional[str] = None,
    include_context_details: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a registry.
    
    Args:
        registry: Optional registry name (uses default if not specified)
        include_context_details: Whether to include detailed context statistics
    
    Returns:
        Dictionary containing registry statistics
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        # Get all contexts
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts
            
        total_schemas = 0
        total_versions = 0
        context_stats = []
        
        # Get statistics for each context
        for context in contexts:
            subjects = client.get_subjects(context)
            if isinstance(subjects, dict) and "error" in subjects:
                continue
                
            context_schemas = len(subjects)
            context_versions = 0
            
            # Count versions for each subject
            for subject in subjects:
                versions = get_schema_versions(subject, context, registry)
                if not isinstance(versions, dict):
                    context_versions += len(versions)
            
            total_schemas += context_schemas
            total_versions += context_versions
            
            if include_context_details:
                context_stats.append({
                    "context": context,
                    "schemas": context_schemas,
                    "versions": context_versions
                })
        
        # Get default context stats
        default_subjects = client.get_subjects()
        if not isinstance(default_subjects, dict):
            default_schemas = len(default_subjects)
            default_versions = 0
            
            for subject in default_subjects:
                versions = get_schema_versions(subject, None, registry)
                if not isinstance(versions, dict):
                    default_versions += len(versions)
            
            total_schemas += default_schemas
            total_versions += default_versions
            
            if include_context_details:
                context_stats.append({
                    "context": "default",
                    "schemas": default_schemas,
                    "versions": default_versions
                })
        
        return {
            "registry": client.config.name,
            "total_contexts": len(contexts),
            "total_schemas": total_schemas,
            "total_versions": total_versions,
            "average_versions_per_schema": round(total_versions / max(total_schemas, 1), 2),
            "contexts": context_stats if include_context_details else None,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    mcp.run() 