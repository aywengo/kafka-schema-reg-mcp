#!/usr/bin/env python3
"""
Integration Patch for kafka_schema_registry_unified_mcp.py

This shows how to integrate the multi-step elicitation feature into the main MCP server.
Add these modifications to your existing kafka_schema_registry_unified_mcp.py file.
"""

# Add these imports at the top of kafka_schema_registry_unified_mcp.py:
"""
from workflow_mcp_integration import (
    register_workflow_tools,
    handle_workflow_elicitation_response
)
from multi_step_elicitation import MultiStepElicitationManager
"""

# In the main server initialization, after creating the elicitation manager:
"""
# Create elicitation managers
elicitation_manager = EnhancedElicitationManager()

# NEW: Create multi-step workflow manager
multi_step_manager = MultiStepElicitationManager(elicitation_manager)

# NEW: Register workflow tools
workflow_tools = register_workflow_tools(server, elicitation_manager)
"""

# Modify the elicitation response handler to support workflows:
"""
@server.tool(
    description="Submit a response to an elicitation request",
    elicitation_handler=True  # Mark as elicitation handler
)
async def submit_elicitation_response(
    request_id: str,
    values: Dict[str, Any],
    complete: bool = True
) -> str:
    '''Submit response to an elicitation request.'''
    try:
        response = ElicitationResponse(
            request_id=request_id,
            values=values,
            complete=complete
        )
        
        # NEW: Check if this is a workflow response
        workflow_result = await handle_workflow_elicitation_response(
            elicitation_manager,
            multi_step_manager,
            response
        )
        
        if workflow_result:
            if workflow_result.get("workflow_completed"):
                # Workflow completed - execute the plan
                execution_plan = workflow_result.get("execution_plan", {})
                return json.dumps({
                    "status": "workflow_completed",
                    "message": "Workflow completed successfully",
                    "execution_plan": execution_plan,
                    "next_action": "Execute the generated plan using appropriate tools"
                })
            elif workflow_result.get("workflow_continuing"):
                # More steps needed
                return json.dumps({
                    "status": "workflow_continuing",
                    "message": f"Proceeding to: {workflow_result.get('next_step')}",
                    "request_id": workflow_result.get("request_id")
                })
            else:
                # Error in workflow
                return json.dumps({
                    "status": "error",
                    "error": workflow_result.get("error", "Unknown workflow error")
                })
        
        # Original elicitation handling (non-workflow)
        success = await elicitation_manager.submit_response(response)
        
        if success:
            result = elicitation_manager.get_response(request_id)
            if result:
                return json.dumps({
                    "status": "success",
                    "message": "Response submitted successfully",
                    "values": result.values
                })
        
        return json.dumps({
            "status": "error",
            "error": "Failed to submit response"
        })
        
    except Exception as e:
        logger.error(f"Error submitting elicitation response: {e}")
        return json.dumps({
            "status": "error", 
            "error": str(e)
        })
"""

# Add a new tool to list available workflows:
"""
@server.tool(
    description="List available multi-step workflows for complex operations"
)
async def list_available_workflows() -> str:
    '''List all available multi-step workflows.'''
    from workflow_definitions import get_all_workflows
    
    workflows = get_all_workflows()
    workflow_list = []
    
    for workflow in workflows:
        workflow_list.append({
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "steps": len(workflow.steps),
            "difficulty": workflow.metadata.get("difficulty", "intermediate"),
            "estimated_duration": workflow.metadata.get("estimated_duration", "5-10 minutes"),
            "requires_admin": workflow.metadata.get("requires_admin", False)
        })
    
    return json.dumps({
        "workflows": workflow_list,
        "total": len(workflow_list),
        "message": "Use 'start_workflow' tool to begin any workflow"
    })
"""

# Optional: Add workflow status to the main status tool:
"""
# In the existing registry_status or get_status tool, add:

# Get active workflows
active_workflows = multi_step_manager.get_active_workflows()
status_info["active_workflows"] = {
    "count": len(active_workflows),
    "workflows": active_workflows
}
"""

# Example of how to trigger a workflow from another tool:
"""
@server.tool(
    description="Migrate schemas between registries with guided workflow"
)
async def guided_schema_migration() -> str:
    '''Start the schema migration wizard for guided migration.'''
    # Start the workflow
    request = await multi_step_manager.start_workflow(
        workflow_id="schema_migration_wizard",
        initial_context={
            "triggered_by": "guided_schema_migration",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    if request:
        return json.dumps({
            "status": "workflow_started",
            "workflow": "Schema Migration Wizard",
            "message": "Migration wizard started. Please respond to the elicitation request.",
            "first_step": request.title,
            "request_id": request.id
        })
    else:
        return json.dumps({
            "status": "error",
            "error": "Failed to start migration wizard"
        })
"""
