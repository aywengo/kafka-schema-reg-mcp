#!/usr/bin/env python3
"""
Enhanced Task Management Module with MCP Context Integration

This module extends the original task management functionality to integrate with
MCP's Context object for better progress reporting and logging capabilities.

Key improvements:
1. Direct integration with MCP Context for progress reporting
2. Automatic logging of task lifecycle events
3. Support for progress tokens from MCP requests
4. Enhanced error handling with context-aware logging
5. Better async/await patterns for context usage
"""

import asyncio
import atexit
import inspect
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

# Import the original task management components
from task_management import (
    TaskStatus,
    TaskType,
)

if TYPE_CHECKING:
    from fastmcp.server.context import Context

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class EnhancedAsyncTask:
    """Enhanced async task with MCP Context support."""

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
    _context: Optional["Context"] = field(default=None, repr=False)
    _progress_token: Optional[str] = field(default=None, repr=False)
    _last_reported_progress: float = field(default=-1.0, repr=False)

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
            "metadata": self.metadata,
        }


class EnhancedAsyncTaskManager:
    """Enhanced async task manager with MCP Context integration."""

    def __init__(self):
        self.tasks: Dict[str, EnhancedAsyncTask] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        self._shutdown = False

    def create_task(
        self, task_type: TaskType, metadata: Optional[Dict[str, Any]] = None, context: Optional["Context"] = None
    ) -> EnhancedAsyncTask:
        """Create a new async task with optional MCP Context."""
        if self._shutdown:
            raise RuntimeError("TaskManager is shutting down")

        task_id = str(uuid.uuid4())
        task = EnhancedAsyncTask(
            id=task_id,
            type=task_type,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            metadata=metadata,
            _context=context,
            _progress_token=self._extract_progress_token(context) if context else None,
        )

        with self._lock:
            self.tasks[task_id] = task

        # Log task creation if context available
        if context:
            asyncio.create_task(
                self._log_task_event(context, f"Created {task_type.value} task", task_id=task_id, level="info")
            )

        return task

    def _extract_progress_token(self, context: "Context") -> Optional[str]:
        """Extract progress token from MCP context if available."""
        try:
            if context and hasattr(context, "request_context"):
                meta = context.request_context.meta
                if meta and hasattr(meta, "progressToken"):
                    token = meta.progressToken
                    return str(token) if token is not None else None
        except Exception:
            pass
        return None

    async def _log_task_event(self, context: "Context", message: str, task_id: str, level: str = "info") -> None:
        """Log task events through MCP context."""
        try:
            log_message = f"[Task {task_id[:8]}] {message}"
            if level == "debug":
                await context.debug(log_message, logger_name="TaskManager")
            elif level == "warning":
                await context.warning(log_message, logger_name="TaskManager")
            elif level == "error":
                await context.error(log_message, logger_name="TaskManager")
            else:
                await context.info(log_message, logger_name="TaskManager")
        except Exception as e:
            logger.warning(f"Failed to log through MCP context: {e}")

    async def execute_task(self, task: EnhancedAsyncTask, func: Callable, *args, **kwargs) -> None:
        """Execute a task asynchronously with context integration."""
        if self._shutdown:
            task.status = TaskStatus.CANCELLED
            task.error = "TaskManager is shutting down"
            return

        context = task._context

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()

            # Log task start
            if context:
                await self._log_task_event(context, f"Started executing {task.type.value} task", task.id, level="info")

            # Create future for the task
            loop = asyncio.get_event_loop()
            task._future = loop.create_future()

            # If function expects context, inject it
            if context and self._function_expects_context(func):
                kwargs["context"] = context
                kwargs["task_id"] = task.id

            # Run the function
            def run_in_thread():
                try:
                    if task._cancelled or self._shutdown:
                        raise asyncio.CancelledError()

                    result = func(*args, **kwargs)
                    if inspect.iscoroutine(result):
                        # Run coroutine in the event loop
                        result = asyncio.run_coroutine_threadsafe(result, loop).result()

                    if not task._cancelled and not self._shutdown:
                        loop.call_soon_threadsafe(task._future.set_result, result)
                except Exception as e:
                    if not task._cancelled and not self._shutdown:
                        loop.call_soon_threadsafe(task._future.set_exception, e)

            self._executor.submit(run_in_thread)

            # Wait for completion
            try:
                result = await task._future
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0

                # Report final progress
                if context and task._progress_token:
                    await context.report_progress(100.0, 100.0, "Completed")

                # Log completion
                if context:
                    await self._log_task_event(
                        context, f"Completed {task.type.value} task successfully", task.id, level="info"
                    )

            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.error = "Task was cancelled"

                if context:
                    await self._log_task_event(context, f"Cancelled {task.type.value} task", task.id, level="warning")

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)

                if context:
                    await self._log_task_event(
                        context, f"Failed {task.type.value} task: {str(e)}", task.id, level="error"
                    )

        finally:
            task.completed_at = datetime.now().isoformat()
            task._future = None

    def _function_expects_context(self, func: Callable) -> bool:
        """Check if a function expects a context parameter."""
        try:
            sig = inspect.signature(func)
            return "context" in sig.parameters or "ctx" in sig.parameters
        except Exception:
            return False

    async def update_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> None:
        """Update task progress with MCP context reporting."""
        task = self.get_task(task_id)
        if not task:
            return

        task.progress = min(max(progress, 0.0), 100.0)

        # Report progress through MCP context if available
        if task._context and task._progress_token:
            # Only report if progress changed significantly (>1%)
            if abs(task.progress - task._last_reported_progress) > 1.0:
                try:
                    await task._context.report_progress(task.progress, 100.0, message)
                    task._last_reported_progress = task.progress
                except Exception as e:
                    logger.warning(f"Failed to report progress through MCP: {e}")

        # Log significant progress milestones
        if task._context and task.progress in [25.0, 50.0, 75.0]:
            await self._log_task_event(
                task._context,
                f"Progress: {int(task.progress)}%" + (f" - {message}" if message else ""),
                task_id,
                level="debug",
            )

    def get_task(self, task_id: str) -> Optional[EnhancedAsyncTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def list_tasks(
        self, task_type: Optional[TaskType] = None, status: Optional[TaskStatus] = None
    ) -> List[EnhancedAsyncTask]:
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

            # Log cancellation
            if task._context:
                await self._log_task_event(task._context, "Task cancellation requested", task_id, level="warning")

            return True

        return False

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
                        pass
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now().isoformat()

            # Clear all tasks
            self.tasks.clear()

            # Reset the ThreadPoolExecutor
            if self._executor:
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    try:
                        self._executor.shutdown(wait=False)
                    except Exception:
                        pass
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


# Helper function to create a task with context from tool functions
def create_context_aware_task(
    task_type: TaskType, metadata: Optional[Dict[str, Any]] = None, context: Optional["Context"] = None
) -> EnhancedAsyncTask:
    """
    Create a task that automatically uses MCP context if available.

    This helper function should be used by tool functions to create tasks
    that can leverage MCP's progress reporting and logging capabilities.

    Example usage in a tool function:
    ```python
    @server.tool
    def my_long_running_tool(data: str, ctx: Context) -> dict:
        task = create_context_aware_task(
            TaskType.EXPORT,
            metadata={"data": data},
            context=ctx
        )
        # ... rest of implementation
    ```
    """
    if not hasattr(create_context_aware_task, "_manager"):
        create_context_aware_task._manager = EnhancedAsyncTaskManager()  # type: ignore

    manager = cast(EnhancedAsyncTaskManager, create_context_aware_task._manager)  # type: ignore
    return manager.create_task(task_type, metadata, context)


# Enhanced progress reporter for use within task functions
class ProgressReporter:
    """
    Helper class for reporting progress from within task functions.

    Usage:
    ```python
    async def my_task_function(data, context: Context, task_id: str):
        reporter = ProgressReporter(task_id, context)

        # Report progress
        await reporter.update(25.0, "Processing first batch")

        # Report with automatic increment
        async with reporter.phase("Processing items", total=100) as phase:
            for i, item in enumerate(items):
                await phase.update_item(i)
    ```
    """

    def __init__(self, task_id: str, context: Optional["Context"] = None):
        self.task_id = task_id
        self.context = context
        self._manager = getattr(create_context_aware_task, "_manager", None)

    async def update(self, progress: float, message: Optional[str] = None):
        """Update progress with optional message."""
        if self._manager:
            await self._manager.update_progress(self.task_id, progress, message)

    class Phase:
        """Context manager for progress phases."""

        def __init__(self, reporter: "ProgressReporter", message: str, total: int):
            self.reporter = reporter
            self.message = message
            self.total = total
            self.current = 0
            self.base_progress = 0.0
            self.phase_weight = 100.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                # Complete the phase
                await self.reporter.update(self.base_progress + self.phase_weight, f"{self.message} - Completed")

        async def update_item(self, index: int):
            """Update progress for processing an item."""
            self.current = index + 1
            progress = self.base_progress + (self.current / self.total) * self.phase_weight
            await self.reporter.update(progress, f"{self.message} - {self.current}/{self.total}")

    def phase(self, message: str, total: int) -> Phase:
        """Create a progress phase context manager."""
        return self.Phase(self, message, total)


# Create global enhanced task manager instance
enhanced_task_manager = EnhancedAsyncTaskManager()


# Register cleanup handler
def cleanup_enhanced_task_manager():
    """Cleanup function to be called at exit"""
    if enhanced_task_manager:
        enhanced_task_manager.shutdown_sync()


atexit.register(cleanup_enhanced_task_manager)


# Export the enhanced manager as the default for backward compatibility
# This allows existing code to work without modification
task_manager = enhanced_task_manager
