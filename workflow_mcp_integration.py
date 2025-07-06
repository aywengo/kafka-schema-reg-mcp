#!/usr/bin/env python3
"""
MCP Tools Integration for Multi-Step Workflows

This module integrates the multi-step elicitation workflows with the existing
MCP tools in the kafka-schema-reg-mcp project.

It provides MCP tool wrappers that can initiate and manage multi-step workflows.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from functools import wraps

from fastmcp import FastMCP
from fastmcp.types import Tool

from elicitation import ElicitationManager, ElicitationResponse
from multi_step_elicitation import MultiStepElicitationManager, MultiStepWorkflow
from workflow_definitions import get_all_workflows, get_workflow_by_id

logger = logging.getLogger(__name__)


class WorkflowMCPTools:
    """MCP tools for managing multi-step workflows."""
    
    def __init__(self, mcp: FastMCP, elicitation_manager: ElicitationManager):
        self.mcp = mcp
        self.elicitation_manager = elicitation_manager
        self.multi_step_manager = MultiStepElicitationManager(elicitation_manager)
        
        # Register all workflows
        for workflow in get_all_workflows():
            self.multi_step_manager.register_workflow(workflow)
            
        self._register_tools()
        
    def _register_tools(self):
        """Register MCP tools for workflow management."""
        
        @self.mcp.tool(
            description="Start a multi-step workflow for complex Schema Registry operations",
            parameters={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of the workflow to start",
                        "enum": [
                            "schema_migration_wizard",
                            "context_reorganization",
                            "disaster_recovery_setup"
                        ]
                    },
                    "initial_context": {
                        "type": "object",
                        "description": "Optional initial context for the workflow",
                        "additionalProperties": True
                    }
                },
                "required": ["workflow_id"]
            }
        )
        async def start_workflow(workflow_id: str, initial_context: Optional[Dict[str, Any]] = None) -> str:
            """Start a multi-step workflow."""
            try:
                # Get workflow definition
                workflow = get_workflow_by_id(workflow_id)
                if not workflow:
                    return json.dumps({
                        "error": f"Workflow '{workflow_id}' not found"
                    })
                
                # Start the workflow
                request = await self.multi_step_manager.start_workflow(
                    workflow_id=workflow_id,
                    initial_context=initial_context
                )
                
                if request:
                    return json.dumps({
                        "status": "started",
                        "workflow_id": workflow_id,
                        "workflow_name": workflow.name,
                        "request_id": request.id,
                        "first_step": request.title,
                        "description": request.description,
                        "message": "Workflow started. Please respond to the elicitation request."
                    })
                else:
                    return json.dumps({
                        "error": "Failed to start workflow"
                    })
                    
            except Exception as e:
                logger.error(f"Error starting workflow: {str(e)}")
                return json.dumps({
                    "error": f"Failed to start workflow: {str(e)}"
                })
        
        @self.mcp.tool(
            description="List available multi-step workflows",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        async def list_workflows() -> str:
            """List all available workflows."""
            workflows = get_all_workflows()
            
            workflow_list = []
            for workflow in workflows:
                workflow_list.append({
                    "id": workflow.id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "steps": len(workflow.steps),
                    "metadata": workflow.metadata
                })
            
            return json.dumps({
                "workflows": workflow_list,
                "total": len(workflow_list)
            })
        
        @self.mcp.tool(
            description="Get the status of active workflows",
            parameters={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Optional workflow instance ID to get specific status"
                    }
                },
                "required": []
            }
        )
        async def workflow_status(instance_id: Optional[str] = None) -> str:
            """Get workflow status."""
            if instance_id:
                # Get specific workflow status
                state = self.multi_step_manager.active_states.get(instance_id)
                if state:
                    workflow = get_workflow_by_id(state.metadata.get("workflow_definition_id"))
                    return json.dumps({
                        "instance_id": instance_id,
                        "workflow_name": workflow.name if workflow else "Unknown",
                        "current_step": state.current_step_id,
                        "steps_completed": len(state.step_history) - 1,
                        "total_steps": len(workflow.steps) if workflow else 0,
                        "responses": state.get_all_responses(),
                        "created_at": state.created_at.isoformat(),
                        "updated_at": state.updated_at.isoformat()
                    })
                else:
                    # Check completed workflows
                    completed_state = self.multi_step_manager.completed_workflows.get(instance_id)
                    if completed_state:
                        return json.dumps({
                            "instance_id": instance_id,
                            "status": "completed",
                            "workflow_name": completed_state.metadata.get("workflow_name"),
                            "steps_completed": len(completed_state.step_history),
                            "responses": completed_state.get_all_responses(),
                            "completed": True
                        })
                    else:
                        return json.dumps({
                            "error": f"Workflow instance '{instance_id}' not found"
                        })
            else:
                # Get all active workflows
                active = self.multi_step_manager.get_active_workflows()
                return json.dumps({
                    "active_workflows": active,
                    "total_active": len(active)
                })
        
        @self.mcp.tool(
            description="Abort an active workflow",
            parameters={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Workflow instance ID to abort"
                    }
                },
                "required": ["instance_id"]
            }
        )
        async def abort_workflow(instance_id: str) -> str:
            """Abort an active workflow."""
            success = await self.multi_step_manager.abort_workflow(instance_id)
            
            if success:
                return json.dumps({
                    "status": "aborted",
                    "instance_id": instance_id,
                    "message": "Workflow aborted successfully"
                })
            else:
                return json.dumps({
                    "error": f"Failed to abort workflow '{instance_id}'. It may not exist or already be completed."
                })
        
        @self.mcp.tool(
            description="Get detailed information about a workflow definition",
            parameters={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "Workflow definition ID",
                        "enum": [
                            "schema_migration_wizard",
                            "context_reorganization",
                            "disaster_recovery_setup"
                        ]
                    }
                },
                "required": ["workflow_id"]
            }
        )
        async def describe_workflow(workflow_id: str) -> str:
            """Get detailed workflow information."""
            workflow = get_workflow_by_id(workflow_id)
            
            if not workflow:
                return json.dumps({
                    "error": f"Workflow '{workflow_id}' not found"
                })
            
            # Build step graph
            step_graph = {}
            for step_id, step in workflow.steps.items():
                step_info = {
                    "id": step.id,
                    "title": step.title,
                    "description": step.description,
                    "type": step.elicitation_type.value,
                    "fields": [
                        {
                            "name": field.name,
                            "type": field.type,
                            "description": field.description,
                            "required": field.required,
                            "options": field.options if field.type == "choice" else None
                        }
                        for field in step.fields
                    ],
                    "next_steps": step.next_steps
                }
                step_graph[step_id] = step_info
            
            return json.dumps({
                "workflow_id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "initial_step": workflow.initial_step_id,
                "total_steps": len(workflow.steps),
                "steps": step_graph,
                "metadata": workflow.metadata
            })


def create_workflow_executor(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the actions based on completed workflow results.
    
    This function takes the results from a completed workflow and executes
    the appropriate Schema Registry operations.
    """
    workflow_name = workflow_result.get("metadata", {}).get("workflow_name")
    responses = workflow_result.get("responses", {})
    
    if workflow_name == "Schema Migration Wizard":
        return execute_schema_migration(responses)
    elif workflow_name == "Context Reorganization":
        return execute_context_reorganization(responses)
    elif workflow_name == "Disaster Recovery Setup":
        return execute_disaster_recovery_setup(responses)
    else:
        return {
            "error": f"Unknown workflow: {workflow_name}"
        }


def execute_schema_migration(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute schema migration based on workflow responses."""
    migration_type = responses.get("migration_type")
    source_registry = responses.get("source_registry")
    target_registry = responses.get("target_registry")
    
    result = {
        "operation": "schema_migration",
        "migration_type": migration_type,
        "source": source_registry,
        "target": target_registry,
        "status": "pending"
    }
    
    # Add specific migration parameters
    if migration_type == "single_schema":
        result["schema_name"] = responses.get("schema_name")
        result["version"] = responses.get("version", "latest")
    elif migration_type == "bulk_migration":
        result["pattern"] = responses.get("schema_pattern")
        result["include_all_versions"] = responses.get("include_all_versions")
    elif migration_type == "context_migration":
        result["source_context"] = responses.get("source_context")
        result["include_dependencies"] = responses.get("include_dependencies")
    
    # Add migration options
    result["options"] = {
        "preserve_ids": responses.get("preserve_ids") == "true",
        "conflict_resolution": responses.get("conflict_resolution"),
        "create_backup": responses.get("create_backup") == "true",
        "dry_run": responses.get("dry_run") == "true"
    }
    
    return result


def execute_context_reorganization(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute context reorganization based on workflow responses."""
    strategy = responses.get("strategy")
    
    result = {
        "operation": "context_reorganization",
        "strategy": strategy,
        "status": "pending"
    }
    
    # Add strategy-specific parameters
    if strategy == "merge":
        result["source_contexts"] = responses.get("source_contexts", "").split(",")
        result["target_context"] = responses.get("target_context")
        result["handle_duplicates"] = responses.get("handle_duplicates")
    elif strategy == "split":
        result["source_context"] = responses.get("source_context")
        result["split_criteria"] = responses.get("split_criteria")
        result["target_contexts"] = responses.get("target_contexts", "").split(",")
        result["split_rules"] = responses.get("split_rules")
    elif strategy == "rename":
        result["rename_mappings"] = {}
        mappings = responses.get("rename_mappings", "").split(",")
        for mapping in mappings:
            if ":" in mapping:
                old, new = mapping.split(":", 1)
                result["rename_mappings"][old.strip()] = new.strip()
    
    # Add common options
    result["options"] = {
        "backup_first": responses.get("backup_first") == "true",
        "test_mode": responses.get("test_mode") == "true",
        "generate_report": responses.get("generate_report") == "true"
    }
    
    return result


def execute_disaster_recovery_setup(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute disaster recovery setup based on workflow responses."""
    dr_strategy = responses.get("dr_strategy")
    
    result = {
        "operation": "disaster_recovery_setup",
        "strategy": dr_strategy,
        "status": "pending"
    }
    
    # Add strategy-specific configuration
    if dr_strategy == "active_passive":
        result["config"] = {
            "primary_registry": responses.get("primary_registry"),
            "standby_registry": responses.get("standby_registry"),
            "replication_interval": responses.get("replication_interval"),
            "failover_mode": responses.get("failover_mode")
        }
    elif dr_strategy == "active_active":
        result["config"] = {
            "active_registries": responses.get("active_registries", "").split(","),
            "conflict_resolution": responses.get("conflict_resolution"),
            "sync_topology": responses.get("sync_topology")
        }
    elif dr_strategy == "backup_restore":
        result["config"] = {
            "backup_schedule": responses.get("backup_schedule"),
            "backup_location": responses.get("backup_location"),
            "retention_policy": responses.get("retention_policy"),
            "encryption": responses.get("encryption") == "true"
        }
    elif dr_strategy == "multi_region":
        result["config"] = {
            "regions": responses.get("regions", "").split(","),
            "primary_region": responses.get("primary_region"),
            "data_residency": responses.get("data_residency") == "true",
            "cross_region_replication": responses.get("cross_region_replication")
        }
    
    # Add common DR options
    result["options"] = {
        "enable_monitoring": responses.get("enable_monitoring") == "true",
        "run_dr_drill": responses.get("run_dr_drill") == "true",
        "generate_runbook": responses.get("generate_runbook") == "true",
        "initial_sync": responses.get("initial_sync") == "true"
    }
    
    return result


# Integration with existing elicitation response handler
async def handle_workflow_elicitation_response(
    elicitation_manager: ElicitationManager,
    multi_step_manager: MultiStepElicitationManager,
    response: ElicitationResponse
) -> Optional[Dict[str, Any]]:
    """
    Handle elicitation responses that may be part of a workflow.
    
    Returns the workflow result if completed, or None if more steps are needed.
    """
    # Check if this response is part of a workflow
    request = elicitation_manager.pending_requests.get(response.request_id)
    if not request or "workflow_instance_id" not in request.metadata:
        # Not a workflow response, handle normally
        return None
    
    # Handle workflow response
    result = await multi_step_manager.handle_response(response)
    
    if isinstance(result, dict):
        # Workflow completed, execute the actions
        execution_result = create_workflow_executor(result)
        return {
            "workflow_completed": True,
            "workflow_result": result,
            "execution_plan": execution_result
        }
    elif result is None:
        # Error occurred
        return {
            "error": "Failed to process workflow response"
        }
    else:
        # More steps needed (result is the next ElicitationRequest)
        return {
            "workflow_continuing": True,
            "next_step": result.title,
            "request_id": result.id
        }


# Convenience function to integrate with existing MCP server
def register_workflow_tools(mcp: FastMCP, elicitation_manager: ElicitationManager) -> WorkflowMCPTools:
    """Register workflow tools with an MCP server."""
    return WorkflowMCPTools(mcp, elicitation_manager)
