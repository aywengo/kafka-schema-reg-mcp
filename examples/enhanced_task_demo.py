#!/usr/bin/env python3
"""
Example script demonstrating the enhanced task management with MCP Context integration.

This script shows how the improvements provide better progress reporting and logging
for long-running operations in the Python MCP SDK.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional, cast

# Import our enhanced modules
from task_management_enhanced import ProgressReporter, TaskType, create_context_aware_task, enhanced_task_manager


# Mock the Context class for demonstration
@dataclass
class MockContext:
    """Mock MCP Context for testing without a full MCP server."""

    progress_token: Optional[str] = "test-progress-token"

    class Meta:
        progressToken = "test-progress-token"

    class RequestContext:
        def __init__(self):
            self.meta = MockContext.Meta()
            self.request_id = "test-request-123"

    def __post_init__(self):
        self.request_context = self.RequestContext()

    async def report_progress(self, progress: float, total: float, message: Optional[str] = None):
        print(f"📊 Progress: {progress:.1f}/{total:.1f} - {message or ''}")

    async def info(self, message: str, logger_name: Optional[str] = None):
        print(f"ℹ️  [{logger_name or 'INFO'}] {message}")

    async def debug(self, message: str, logger_name: Optional[str] = None):
        print(f"🔍 [{logger_name or 'DEBUG'}] {message}")

    async def warning(self, message: str, logger_name: Optional[str] = None):
        print(f"⚠️  [{logger_name or 'WARNING'}] {message}")

    async def error(self, message: str, logger_name: Optional[str] = None):
        print(f"❌ [{logger_name or 'ERROR'}] {message}")


async def simulate_data_processing(
    items: list, context: Optional[MockContext] = None, task_id: Optional[str] = None
) -> dict:
    """Simulated long-running data processing task with progress reporting."""

    # Type cast context for ProgressReporter compatibility
    reporter = ProgressReporter(task_id, cast(Any, context)) if task_id else None  # type: ignore
    processed_items = []

    try:
        # Phase 1: Validation (0-20%)
        if reporter:
            await reporter.update(0.0, "Starting data validation")

        if context:
            await context.info(f"Processing {len(items)} items", logger_name="DataProcessor")

        # Simulate validation
        await asyncio.sleep(0.5)

        if reporter:
            await reporter.update(20.0, "Validation completed")

        # Phase 2: Main processing (20-90%)
        if reporter:
            async with reporter.phase("Processing items", len(items)) as phase:
                for i, item in enumerate(items):
                    # Simulate processing
                    await asyncio.sleep(0.2)
                    processed_items.append(f"processed_{item}")

                    # Update progress
                    await phase.update_item(i)

                    # Log milestone
                    if i == len(items) // 2 and context:
                        await context.debug("Reached halfway point", logger_name="DataProcessor")

        # Phase 3: Finalization (90-100%)
        if reporter:
            await reporter.update(90.0, "Finalizing results")

        # Simulate finalization
        await asyncio.sleep(0.3)

        if reporter:
            await reporter.update(100.0, "Processing completed successfully")

        if context:
            await context.info(f"Successfully processed {len(processed_items)} items", logger_name="DataProcessor")

        return {"status": "success", "processed_count": len(processed_items), "items": processed_items}

    except Exception as e:
        if context:
            await context.error(f"Processing failed: {str(e)}", logger_name="DataProcessor")
        raise


async def main():
    """Demonstrate the enhanced task management features."""

    print("🚀 Enhanced Task Management Demo\n")

    # Create a mock context
    context = MockContext()

    # Scenario 1: Create and execute a task with context
    print("=== Scenario 1: Task with Context Integration ===\n")

    task = create_context_aware_task(
        TaskType.EXPORT, metadata={"description": "Process sample data", "items_count": 5}, context=context
    )

    print(f"✅ Created task: {task.id}\n")

    # Execute the task
    items = ["item1", "item2", "item3", "item4", "item5"]

    await enhanced_task_manager.execute_task(task, simulate_data_processing, items=items)

    print(f"\n✅ Task completed: {task.to_dict()}\n")

    # Scenario 2: Task without context (backward compatibility)
    print("\n=== Scenario 2: Task without Context (Backward Compatible) ===\n")

    task2 = create_context_aware_task(
        TaskType.SYNC, metadata={"description": "Legacy task"}, context=None  # No context
    )

    print(f"✅ Created legacy task: {task2.id}")

    # Simple function without context support
    async def legacy_function(data):
        await asyncio.sleep(1)
        return {"processed": data}

    await enhanced_task_manager.execute_task(task2, legacy_function, data="test_data")

    print(f"✅ Legacy task completed: {task2.result}\n")

    # Show task listing
    print("\n=== Task Summary ===\n")
    all_tasks = enhanced_task_manager.list_tasks()
    for t in all_tasks:
        print(f"📋 Task {t.id[:8]}... - Type: {t.type.value}, Status: {t.status.value}")

    # Demonstrate the comparison
    print("\n=== Benefits Comparison ===\n")
    print("Without Context Integration:")
    print("- ❌ No progress notifications")
    print("- ❌ No structured logging")
    print("- ❌ Limited visibility into task execution")
    print("\nWith Context Integration:")
    print("- ✅ Real-time progress updates via MCP protocol")
    print("- ✅ Structured logging with proper levels")
    print("- ✅ Detailed execution visibility")
    print("- ✅ Automatic lifecycle event tracking")


if __name__ == "__main__":
    asyncio.run(main())
