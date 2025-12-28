#!/usr/bin/env python3
"""
Example: Using the Bulk Operations Wizard

This example demonstrates how to use the Bulk Operations Wizard
for various administrative tasks on Schema Registry.
"""

import asyncio
import logging

from batch_operations import BatchOperations

# Import the wizard and related components
from bulk_operations_wizard import BulkOperationsWizard, BulkOperationType
from elicitation import ElicitationManager
from schema_registry_common import SchemaRegistryClient
# Note: TaskManager removed in v2.2.0 - BulkOperationsWizard now uses FastMCP Progress directly
# This example is deprecated and should be updated to use FastMCP Progress dependency
# from operation_metadata import TaskType  # Only enums available, no TaskManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_bulk_cleanup():
    """Example: Clean up test schemas"""
    print("\n=== Example: Bulk Cleanup of Test Schemas ===\n")

    # Initialize components
    registry = SchemaRegistryClient()
    elicitation = ElicitationManager()
    task_manager = TaskManager()
    batch_ops = BatchOperations(registry)

    # Create wizard instance
    wizard = BulkOperationsWizard(registry, elicitation, task_manager, batch_ops)

    # Start cleanup wizard
    result = await wizard.start_wizard(BulkOperationType.CLEANUP)

    # Check results
    if result["status"] == "success":
        print(f"✅ Successfully cleaned up {result['processed']} schemas")
        print(f"Task ID: {result['task_id']}")
    else:
        print(f"❌ Cleanup failed: {result.get('error', 'Unknown error')}")


async def example_bulk_update():
    """Example: Update compatibility settings"""
    print("\n=== Example: Bulk Update Compatibility Settings ===\n")

    # Initialize components
    registry = SchemaRegistryClient()
    elicitation = ElicitationManager()
    task_manager = TaskManager()
    batch_ops = BatchOperations(registry)

    # Create wizard with custom configuration
    wizard = BulkOperationsWizard(registry, elicitation, task_manager, batch_ops)

    # Configure the operation (example configuration)
    # In real implementation, would pass configuration to wizard

    # Start update wizard
    result = await wizard.start_wizard(BulkOperationType.SCHEMA_UPDATE)

    print(f"Operation result: {result['status']}")


async def example_bulk_migration():
    """Example: Migrate schemas between contexts"""
    print("\n=== Example: Bulk Schema Migration ===\n")

    # Initialize components
    registry = SchemaRegistryClient()
    elicitation = ElicitationManager()
    task_manager = TaskManager()
    batch_ops = BatchOperations(registry)

    wizard = BulkOperationsWizard(registry, elicitation, task_manager, batch_ops)

    # Define progress callback
    def progress_callback(processed: int, total: int, message: str):
        percentage = (processed / total) * 100 if total > 0 else 0
        print(f"Progress: {percentage:.1f}% - {message}")

    # Configure with progress callback (example configuration)
    # In real implementation, would pass configuration to wizard

    # Start migration wizard
    result = await wizard.start_wizard(BulkOperationType.MIGRATION)

    # Monitor the task
    if result["status"] == "success":
        task_id = result["task_id"]

        # Check task status
        while True:
            status = await task_manager.get_task_status(task_id)
            if status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(5)  # Check every 5 seconds

        print(f"Migration completed: {status}")


async def example_with_mock_responses():
    """Example: Demonstrate wizard flow with mock responses"""
    print("\n=== Example: Wizard Flow Demonstration ===\n")

    # This example shows the expected elicitation flow
    # In real usage, these would be interactive prompts

    mock_flow = [
        {"step": 1, "prompt": "What type of bulk operation would you like to perform?", "user_selects": "Cleanup"},
        {"step": 2, "prompt": "What type of cleanup?", "user_selects": "Test schemas"},
        {"step": 3, "prompt": "Select schemas to clean up", "user_selects": ["test-*", "temp-*"]},
        {
            "step": 4,
            "prompt": "Cleanup options",
            "user_selects": {"create_backup": True, "permanent_delete": False, "keep_versions": 3},
        },
        {"step": 5, "prompt": "This will affect 23 schemas. Preview changes?", "user_selects": "Yes"},
        {
            "step": 6,
            "prompt": "Active consumers detected (2 consumers). How should we proceed?",
            "user_selects": "Skip schemas with active consumers",
        },
        {"step": 7, "prompt": "Do you want to proceed with this operation?", "user_selects": "Yes"},
    ]

    print("Expected wizard flow:")
    for step in mock_flow:
        print(f"\nStep {step['step']}: {step['prompt']}")
        print(f"  User selects: {step['user_selects']}")


async def example_error_handling():
    """Example: Handle errors and rollback"""
    print("\n=== Example: Error Handling and Rollback ===\n")

    # Initialize components
    registry = SchemaRegistryClient()
    elicitation = ElicitationManager()
    task_manager = TaskManager()
    batch_ops = BatchOperations(registry)

    wizard = BulkOperationsWizard(registry, elicitation, task_manager, batch_ops)

    # Configure with rollback enabled (example configuration)
    # In real implementation, would pass configuration to wizard

    try:
        result = await wizard.start_wizard(BulkOperationType.CONFIGURATION)

        if result["status"] == "failed":
            print(f"Operation failed: {result['error']}")
            print("Automatic rollback was performed")

    except Exception as e:
        print(f"Unexpected error: {e}")


async def main():
    """Run all examples"""

    # Note: These examples are for demonstration purposes.
    # In a real environment, you would connect to an actual Schema Registry
    # and have interactive elicitation prompts.

    print("Bulk Operations Wizard Examples")
    print("===============================")

    # Demonstrate the wizard flow
    await example_with_mock_responses()

    # Uncomment these to run with actual components:
    # await example_bulk_cleanup()
    # await example_bulk_update()
    # await example_bulk_migration()
    # await example_error_handling()

    print("\n✅ Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
