# Multi-Step Elicitation for Complex Workflows

## Overview

This feature implements multi-step elicitation flows that enable complex workflows and conditional logic based on user responses, as described in issue #73. It allows the MCP server to guide users through sophisticated operations using interactive, wizard-like experiences.

## Key Features

- **Conditional Questions**: Dynamic flow based on previous answers
- **Progressive Disclosure**: Show relevant options as users progress
- **Complex Workflow Orchestration**: Manage multi-stage operations
- **State Management**: Maintain context across multiple elicitation steps
- **Navigation Support**: Users can go back and modify previous choices

## Architecture

### Core Components

1. **WorkflowStep**: Represents a single step in a workflow
2. **WorkflowState**: Maintains the state across workflow execution
3. **MultiStepWorkflow**: Defines a complete workflow with multiple steps
4. **MultiStepElicitationManager**: Manages workflow execution and state

### Workflow Structure

```python
workflow = MultiStepWorkflow(
    id="unique_workflow_id",
    name="Human-Readable Name",
    description="What this workflow does",
    steps={
        "step_id": WorkflowStep(...),
        # More steps...
    },
    initial_step_id="first_step"
)
```

## Pre-Defined Workflows

### 1. Schema Migration Wizard

Guides users through schema migration with different strategies:

- **Single Schema**: Migrate one specific schema
- **Bulk Migration**: Migrate multiple schemas using patterns
- **Context Migration**: Migrate entire contexts

**Example Flow**:
1. Select migration type
2. Choose source schemas
3. Configure migration options
4. Review and confirm

### 2. Context Reorganization

Helps reorganize schemas across contexts:

- **Merge**: Combine multiple contexts
- **Split**: Divide a context into multiple
- **Rename**: Change context names
- **Restructure**: Complete reorganization

**Example Flow**:
1. Select reorganization strategy
2. Define new structure
3. Map schemas to new contexts
4. Execute plan

### 3. Disaster Recovery Setup

Configure disaster recovery strategies:

- **Active-Passive**: Primary with standby
- **Active-Active**: Multiple active registries
- **Backup & Restore**: Periodic backups
- **Multi-Region**: Geographic distribution

**Example Flow**:
1. Choose DR strategy
2. Select registries
3. Configure sync options
4. Test and validate

## Usage

### Starting a Workflow

```python
# Using MCP tools
result = await start_workflow(
    workflow_id="schema_migration_wizard",
    initial_context={"environment": "production"}
)
```

### Workflow Response Structure

```json
{
    "status": "started",
    "workflow_id": "schema_migration_wizard",
    "workflow_name": "Schema Migration Wizard",
    "request_id": "abc123",
    "first_step": "Schema Migration Wizard - Migration Type",
    "description": "What type of migration would you like to perform?"
}
```

### Handling Workflow Steps

Each step presents an elicitation request. Users respond through the standard elicitation mechanism, and the workflow automatically progresses to the next appropriate step based on the response.

### Navigation

Users can navigate back to previous steps by including `_workflow_action: "back"` in their response:

```json
{
    "request_id": "current_step_id",
    "values": {
        "_workflow_action": "back"
    }
}
```

## Creating Custom Workflows

### Step Definition

```python
step = WorkflowStep(
    id="unique_step_id",
    title="Step Title",
    description="What this step does",
    elicitation_type=ElicitationType.FORM,
    fields=[
        ElicitationField(
            name="field_name",
            type="text",
            description="Field description",
            required=True
        )
    ],
    next_steps={
        "field_name": {
            "value1": "next_step_1",
            "value2": "next_step_2"
        },
        "default": "default_next_step"
    }
)
```

### Conditional Transitions

```python
def custom_condition(state: Dict[str, Any]) -> Optional[str]:
    if state.get("total_schemas") > 100:
        return "bulk_processing_step"
    return "normal_processing_step"

step = WorkflowStep(
    # ... other properties
    conditions={"check_volume": custom_condition}
)
```

### Complete Example

```python
def create_custom_workflow() -> MultiStepWorkflow:
    steps = {
        "start": WorkflowStep(
            id="start",
            title="Welcome",
            description="Let's configure your schema",
            fields=[
                ElicitationField(
                    name="operation",
                    type="choice",
                    options=["create", "update", "delete"],
                    required=True
                )
            ],
            next_steps={
                "operation": {
                    "create": "create_details",
                    "update": "select_schema",
                    "delete": "confirm_delete"
                }
            }
        ),
        "create_details": WorkflowStep(
            id="create_details",
            title="Schema Details",
            fields=[
                ElicitationField(
                    name="schema_name",
                    type="text",
                    required=True
                ),
                ElicitationField(
                    name="schema_type",
                    type="choice",
                    options=["avro", "json", "protobuf"],
                    required=True
                )
            ],
            next_steps={"default": "review"}
        ),
        # ... more steps
        "review": WorkflowStep(
            id="review",
            title="Review and Confirm",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="confirm",
                    type="confirmation",
                    required=True
                )
            ],
            next_steps={
                "confirm": {
                    "true": "finish",
                    "false": "start"
                }
            }
        )
    }
    
    return MultiStepWorkflow(
        id="custom_workflow",
        name="Custom Schema Workflow",
        description="Custom schema operations",
        steps=steps,
        initial_step_id="start"
    )
```

## Integration with MCP Tools

The multi-step elicitation system integrates seamlessly with existing MCP tools:

### Available MCP Tools

1. **start_workflow**: Begin a new workflow instance
2. **list_workflows**: Show available workflows
3. **workflow_status**: Check workflow progress
4. **abort_workflow**: Cancel an active workflow
5. **describe_workflow**: Get detailed workflow information

### Example Tool Usage

```python
# List available workflows
workflows = await list_workflows()

# Start a workflow
result = await start_workflow(
    workflow_id="disaster_recovery_setup",
    initial_context={"priority": "high"}
)

# Check status
status = await workflow_status(
    instance_id="workflow_instance_123"
)

# Abort if needed
await abort_workflow(instance_id="workflow_instance_123")
```

## Best Practices

### 1. Design Clear Flows

- Keep each step focused on a single decision or data collection
- Use descriptive titles and descriptions
- Provide helpful metadata and hints

### 2. Handle Edge Cases

- Always provide a default next step or explicit finish
- Consider what happens if users go back multiple times
- Validate data at each step

### 3. Optimize for User Experience

- Group related fields in the same step
- Use progressive disclosure to avoid overwhelming users
- Provide clear navigation options

### 4. State Management

- Store minimal state between steps
- Use prefixed keys to avoid collisions
- Clean up completed workflows periodically

## Error Handling

The system handles various error scenarios:

- **Invalid Step References**: Validated at workflow creation
- **Missing Required Fields**: Caught during response validation
- **Navigation Errors**: Prevented by checking step history
- **Timeout Handling**: Workflows can be resumed or aborted

## Performance Considerations

- Workflows are kept in memory during execution
- Completed workflows are moved to a separate store
- Regular cleanup of old workflows is recommended
- State is optimized for quick access and updates

## Future Enhancements

Potential improvements for the multi-step elicitation system:

1. **Workflow Templates**: Reusable workflow patterns
2. **Dynamic Step Generation**: Create steps based on API responses
3. **Parallel Steps**: Support for concurrent step execution
4. **Workflow Composition**: Combine smaller workflows into larger ones
5. **Persistence**: Save and resume workflows across sessions

## Testing

The implementation includes comprehensive tests:

```bash
# Run all multi-step elicitation tests
pytest tests/test_multi_step_elicitation.py -v

# Run specific test classes
pytest tests/test_multi_step_elicitation.py::TestWorkflowStep -v
pytest tests/test_multi_step_elicitation.py::TestWorkflowDefinitions -v
```

## Migration Guide

To integrate multi-step elicitation into existing code:

1. Import the workflow components:
```python
from workflow_mcp_integration import register_workflow_tools
```

2. Register with your MCP server:
```python
workflow_tools = register_workflow_tools(mcp, elicitation_manager)
```

3. Handle workflow responses in your elicitation handler:
```python
from workflow_mcp_integration import handle_workflow_elicitation_response

result = await handle_workflow_elicitation_response(
    elicitation_manager,
    multi_step_manager,
    response
)
```

## Conclusion

The multi-step elicitation system transforms complex Schema Registry operations into guided, user-friendly workflows. It reduces errors, improves user experience, and enables sophisticated operations that would be difficult with single-step interactions.

For questions or contributions, please refer to issue #73 in the repository.
