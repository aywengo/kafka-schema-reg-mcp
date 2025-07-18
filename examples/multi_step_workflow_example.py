#!/usr/bin/env python3
"""
Example: Using Multi-Step Elicitation for Schema Migration

This example demonstrates how to use the multi-step elicitation feature
to guide users through a schema migration workflow.
"""

import asyncio
import json

from elicitation import ElicitationManager, ElicitationResponse
from multi_step_elicitation import MultiStepElicitationManager
from workflow_definitions import create_schema_migration_workflow
from workflow_mcp_integration import handle_workflow_elicitation_response


async def simulate_user_responses(
    workflow_manager: MultiStepElicitationManager,
    elicitation_manager: ElicitationManager,
):
    """Simulate user responses for demonstration."""

    # Define our migration scenario responses
    responses = [
        # Step 1: Migration type
        {"migration_type": "single_schema"},
        # Step 2: Schema selection
        {
            "source_registry": "development",
            "schema_name": "com.example.UserProfile",
            "version": "latest",
        },
        # Step 3: Migration options
        {
            "target_registry": "production",
            "target_context": "prod-v2",
            "preserve_ids": "false",
            "conflict_resolution": "skip",
            "create_backup": "true",
        },
        # Step 4: Review and confirm
        {"dry_run": "true", "confirm_migration": "true"},
    ]

    print("🚀 Starting Schema Migration Wizard Demo\n")
    print("=" * 60)

    # Start the workflow
    workflow = create_schema_migration_workflow()
    workflow_manager.register_workflow(workflow)

    request = await workflow_manager.start_workflow(workflow.id)
    if not request:
        print("❌ Failed to start workflow")
        return

    print(f"\n📋 Step 1: {request.title}")
    print(f"   {request.description}")

    # Process each step
    for i, response_values in enumerate(responses):
        # Get the current request from elicitation manager
        if request.id not in elicitation_manager.pending_requests:
            print(f"❌ Request {request.id} not found")
            break

        # Display fields and simulate user input
        print("\n   Fields:")
        for field in request.fields:
            if field.name.startswith("_workflow_"):
                continue  # Skip navigation fields

            value = response_values.get(field.name, field.default)
            field_desc = f"   - {field.description}"
            if field.type == "choice" and field.options:
                field_desc += f" [{', '.join(field.options)}]"
            print(field_desc)
            print(f"     → User enters: {value}")

        # Create response
        response = ElicitationResponse(request_id=request.id, values=response_values, complete=True)

        # Handle the response
        result = await handle_workflow_elicitation_response(elicitation_manager, workflow_manager, response)

        if not result or not isinstance(result, dict):
            print("❌ Error: Invalid response from handle_workflow_elicitation_response")
            break
        if result.get("workflow_completed"):
            # Workflow completed
            print("\n" + "=" * 60)
            print("✅ Workflow Completed Successfully!\n")

            # Display collected responses
            print("📊 Collected Information:")
            workflow_result = result["workflow_result"]
            for key, value in workflow_result["responses"].items():
                if not key.startswith("step"):  # Skip prefixed keys
                    print(f"   - {key}: {value}")

            # Show execution plan
            print("\n📝 Execution Plan:")
            execution_plan = result["execution_plan"]
            print(json.dumps(execution_plan, indent=2))

            break

        elif result.get("workflow_continuing"):
            # Get next step
            next_request_id = result["request_id"]
            request = elicitation_manager.pending_requests.get(next_request_id)

            if request:
                print(f"\n📋 Step {i + 2}: {request.title}")
                if request.description:
                    print(f"   {request.description}")
            else:
                print("❌ Next request not found")
                break
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            break


async def demonstrate_back_navigation():
    """Demonstrate the back navigation feature."""
    print("\n\n🔄 Demonstrating Back Navigation\n")
    print("=" * 60)

    elicitation_manager = ElicitationManager()
    workflow_manager = MultiStepElicitationManager(elicitation_manager)

    # Register workflow
    workflow = create_schema_migration_workflow()
    workflow_manager.register_workflow(workflow)

    # Start workflow
    request = await workflow_manager.start_workflow(workflow.id)
    print(f"📋 Step 1: {request.title}")

    # First response
    response1 = ElicitationResponse(
        request_id=request.id,
        values={"migration_type": "bulk_migration"},
        complete=True,
    )

    result = await workflow_manager.handle_response(response1)
    if isinstance(result, type(request)):
        print(f"📋 Step 2: {result.title}")

        # User wants to go back
        print("\n   ← User decides to go back and change migration type")

        response2 = ElicitationResponse(
            request_id=result.id,
            values={"_workflow_action": "back"},
            complete=True,
        )

        back_result = await workflow_manager.handle_response(response2)
        if isinstance(back_result, type(request)):
            print(f"📋 Back to Step 1: {back_result.title}")
            print("   ✅ Successfully navigated back!")


async def list_available_workflows():
    """List all available workflows."""
    print("\n\n📚 Available Workflows\n")
    print("=" * 60)

    from workflow_definitions import get_all_workflows

    workflows = get_all_workflows()
    for workflow in workflows:
        print(f"\n🔸 {workflow.name}")
        print(f"   ID: {workflow.id}")
        print(f"   Description: {workflow.description}")
        print(f"   Steps: {len(workflow.steps)}")
        print(f"   Metadata: {json.dumps(workflow.metadata, indent=6)}")


async def main():
    """Run all demonstrations."""
    print("Multi-Step Elicitation Demo")
    print("===========================\n")

    # Create managers
    elicitation_manager = ElicitationManager()
    workflow_manager = MultiStepElicitationManager(elicitation_manager)

    # List available workflows
    await list_available_workflows()

    # Simulate a complete workflow
    await simulate_user_responses(workflow_manager, elicitation_manager)

    # Demonstrate back navigation
    await demonstrate_back_navigation()

    print("\n\n✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
