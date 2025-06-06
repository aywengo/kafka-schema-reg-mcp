#!/usr/bin/env python3
"""
Task Management Module

Handles async task queue operations for long-running Schema Registry operations.
Provides TaskStatus, TaskType, AsyncTask, and AsyncTaskManager classes.
"""

import uuid
import threading
import time
import asyncio
import logging
import inspect
import atexit
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(Enum):
    MIGRATION = "migration"
    SYNC = "sync"
    CLEANUP = "cleanup"
    EXPORT = "export"
    IMPORT = "import"

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
    
    # Long-running operations using task queue
    "migrate_context": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "migrate_schema": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_context_batch": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.TASK_QUEUE},
    "clear_multiple_contexts_batch": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "compare_contexts_across_registries": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    "compare_different_contexts": {"duration": OperationDuration.LONG, "pattern": AsyncPattern.TASK_QUEUE},
    
    # Export operations
    "export_schema": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "export_subject": {"duration": OperationDuration.QUICK, "pattern": AsyncPattern.DIRECT},
    "export_context": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.DIRECT},
    "export_global": {"duration": OperationDuration.MEDIUM, "pattern": AsyncPattern.DIRECT},
}

def get_operation_info(operation_name: str, registry_mode: str) -> Dict[str, Any]:
    """Get operation metadata for MCP client guidance."""
    metadata = OPERATION_METADATA.get(operation_name, {
        "duration": OperationDuration.QUICK,
        "pattern": AsyncPattern.DIRECT
    })
    return {
        "operation": operation_name,
        "expected_duration": metadata["duration"].value,
        "async_pattern": metadata["pattern"].value,
        "guidance": _get_operation_guidance(metadata),
        "registry_mode": registry_mode
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
    
    def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress."""
        task = self.get_task(task_id)
        if task:
            task.progress = min(max(progress, 0.0), 100.0)
    
    def reset_for_testing(self) -> None:
        """Reset task manager state for test isolation."""
        with self._lock:
            # Cancel any running tasks first
            for task in self.tasks.values():
                if task.status == TaskStatus.RUNNING and task._future:
                    task._cancelled = True
                    try:
                        task._future.cancel()
                    except RuntimeError:
                        pass  # Event loop might be closed
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now().isoformat()
            
            # Clear all tasks
            self.tasks.clear()
            
            # Reset the ThreadPoolExecutor to stop all background threads
            if self._executor:
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    try:
                        self._executor.shutdown(wait=False)
                    except Exception:
                        pass
                # Create a new executor
                self._executor = ThreadPoolExecutor(max_workers=10)
    
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
        
        # Shutdown the executor
        if self._executor:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                try:
                    self._executor.shutdown(wait=True)
                except Exception:
                    pass
            self._executor = None

# Create global task manager instance
task_manager = AsyncTaskManager()

# Register cleanup handler
def cleanup_task_manager():
    """Cleanup function to be called at exit"""
    if task_manager:
        task_manager.shutdown_sync()

atexit.register(cleanup_task_manager) 