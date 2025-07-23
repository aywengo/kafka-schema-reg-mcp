#!/usr/bin/env python3
"""
MCP Tools Integration for Multi-Step Workflows

This module integrates the multi-step elicitation workflows with the existing
MCP tools in the kafka-schema-reg-mcp project.

It provides MCP tool wrappers that can initiate and manage multi-step workflows.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from elicitation import ElicitationManager, ElicitationResponse
from multi_step_elicitation import MultiStepElicitationManager
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

        @self.mcp.tool(description="Start a multi-step workflow for complex Schema Registry operations")
        async def start_workflow(workflow_id: str, initial_context: Optional[Dict[str, Any]] = None) -> str:
            """Start a multi-step workflow."""
            try:
                # Get workflow definition
                workflow = get_workflow_by_id(workflow_id)
                if not workflow:
                    return json.dumps({"error": f"Workflow '{workflow_id}' not found"})

                # Start the workflow
                request = await self.multi_step_manager.start_workflow(
                    workflow_id=workflow_id, initial_context=initial_context
                )

                if request:
                    return json.dumps(
                        {
                            "status": "started",
                            "workflow_id": workflow_id,
                            "workflow_name": workflow.name,
                            "request_id": request.id,
                            "first_step": request.title,
                            "description": request.description,
                            "message": "Workflow started. Please respond to the elicitation request.",
                        }
                    )
                else:
                    return json.dumps({"error": "Failed to start workflow"})

            except Exception as e:
                logger.error(f"Error starting workflow: {str(e)}")
                return json.dumps({"error": f"Failed to start workflow: {str(e)}"})

        @self.mcp.tool(description="List available multi-step workflows")
        async def list_workflows() -> str:
            """List all available workflows."""
            workflows = get_all_workflows()

            workflow_list = []
            for workflow in workflows:
                workflow_list.append(
                    {
                        "id": workflow.id,
                        "name": workflow.name,
                        "description": workflow.description,
                        "steps": len(workflow.steps),
                        "metadata": workflow.metadata,
                    }
                )

            return json.dumps({"workflows": workflow_list, "total": len(workflow_list)})

        @self.mcp.tool(description="Get the status of active workflows")
        async def workflow_status(instance_id: Optional[str] = None) -> str:
            """Get workflow status."""
            if instance_id:
                # Get specific workflow status
                state = self.multi_step_manager.active_states.get(instance_id)
                if state:
                    workflow_id = state.metadata.get("workflow_definition_id")
                    workflow = get_workflow_by_id(workflow_id) if workflow_id else None
                    return json.dumps(
                        {
                            "instance_id": instance_id,
                            "workflow_name": workflow.name if workflow else "Unknown",
                            "current_step": state.current_step_id,
                            "steps_completed": len(state.step_history) - 1,
                            "total_steps": len(workflow.steps) if workflow else 0,
                            "responses": state.get_all_responses(),
                            "created_at": state.created_at.isoformat(),
                            "updated_at": state.updated_at.isoformat(),
                        }
                    )
                else:
                    # Check completed workflows
                    completed_state = self.multi_step_manager.completed_workflows.get(instance_id)
                    if completed_state:
                        return json.dumps(
                            {
                                "instance_id": instance_id,
                                "status": "completed",
                                "workflow_name": completed_state.metadata.get("workflow_name"),
                                "steps_completed": len(completed_state.step_history),
                                "responses": completed_state.get_all_responses(),
                                "completed": True,
                            }
                        )
                    else:
                        return json.dumps({"error": f"Workflow instance '{instance_id}' not found"})
            else:
                # Get all active workflows
                active = self.multi_step_manager.get_active_workflows()
                return json.dumps({"active_workflows": active, "total_active": len(active)})

        @self.mcp.tool(description="Abort an active workflow")
        async def abort_workflow(instance_id: str) -> str:
            """Abort an active workflow."""
            success = await self.multi_step_manager.abort_workflow(instance_id)

            if success:
                return json.dumps(
                    {"status": "aborted", "instance_id": instance_id, "message": "Workflow aborted successfully"}
                )
            else:
                return json.dumps(
                    {"error": f"Failed to abort workflow '{instance_id}'. It may not exist or already be completed."}
                )

        @self.mcp.tool(description="Get detailed information about a workflow definition")
        async def describe_workflow(workflow_id: str) -> str:
            """Get detailed workflow information."""
            workflow = get_workflow_by_id(workflow_id)

            if not workflow:
                return json.dumps({"error": f"Workflow '{workflow_id}' not found"})

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
                            "options": field.options if field.type == "choice" else None,
                        }
                        for field in step.fields
                    ],
                    "next_steps": step.next_steps,
                }
                step_graph[step_id] = step_info

            return json.dumps(
                {
                    "workflow_id": workflow.id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "initial_step_id": workflow.initial_step_id,
                    "total_steps": len(workflow.steps),
                    "steps": step_graph,
                    "metadata": workflow.metadata,
                }
            )

        @self.mcp.tool(
            description=(
                "Start the Schema Evolution Assistant workflow. "
                "This guided workflow helps you safely evolve schemas by analyzing changes, "
                "suggesting strategies, and coordinating consumer updates."
            ),
        )
        async def guided_schema_evolution(
            subject: Optional[str] = None,
            current_schema: Optional[str] = None,
        ) -> str:
            """Start the Schema Evolution Assistant workflow."""
            initial_context = {}
            if subject:
                initial_context["subject"] = subject
            if current_schema:
                try:
                    initial_context["current_schema"] = json.loads(current_schema)
                except json.JSONDecodeError:
                    initial_context["current_schema"] = current_schema

            workflow_id = "schema_evolution_assistant"

            try:
                request = await self.multi_step_manager.start_workflow(
                    workflow_id=workflow_id, initial_context=initial_context
                )

                if request:
                    return json.dumps(
                        {
                            "status": "started",
                            "workflow_id": workflow_id,
                            "workflow_name": "Schema Evolution Assistant",
                            "request_id": request.id,
                            "first_step": request.title,
                            "description": request.description,
                            "message": (
                                "Schema Evolution Assistant started. This workflow will guide you through:\n"
                                "1. Analyzing schema changes\n"
                                "2. Detecting breaking changes\n"
                                "3. Selecting evolution strategy\n"
                                "4. Planning consumer coordination\n"
                                "5. Setting up rollback procedures"
                            ),
                        }
                    )
                else:
                    return json.dumps({"error": "Failed to start Schema Evolution workflow"})
            except Exception as e:
                logger.error(f"Error starting Schema Evolution workflow: {str(e)}")
                return json.dumps({"error": f"Failed to start workflow: {str(e)}"})

        @self.mcp.tool(description="Start the Schema Migration Wizard workflow for guided schema migration")
        async def guided_schema_migration() -> str:
            """Convenience method to start Schema Migration workflow."""
            workflow_id = "schema_migration_wizard"

            try:
                request = await self.multi_step_manager.start_workflow(workflow_id=workflow_id, initial_context={})

                if request:
                    return json.dumps(
                        {
                            "status": "started",
                            "workflow_id": workflow_id,
                            "workflow_name": "Schema Migration Wizard",
                            "request_id": request.id,
                            "first_step": request.title,
                            "description": request.description,
                            "message": (
                                "Schema Migration Wizard started. This workflow will guide you through:\n"
                                "1. Source and target registry selection\n"
                                "2. Schema selection and validation\n"
                                "3. Migration planning and execution\n"
                                "4. Verification and rollback procedures"
                            ),
                        }
                    )
                else:
                    return json.dumps({"error": "Failed to start Schema Migration workflow"})
            except Exception as e:
                logger.error(f"Error starting Schema Migration workflow: {str(e)}")
                return json.dumps({"error": f"Failed to start workflow: {str(e)}"})

        @self.mcp.tool(description="Start the Context Reorganization workflow for reorganizing schemas across contexts")
        async def guided_context_reorganization() -> str:
            """Convenience method to start Context Reorganization workflow."""
            workflow_id = "context_reorganization"

            try:
                request = await self.multi_step_manager.start_workflow(workflow_id=workflow_id, initial_context={})

                if request:
                    return json.dumps(
                        {
                            "status": "started",
                            "workflow_id": workflow_id,
                            "workflow_name": "Context Reorganization",
                            "request_id": request.id,
                            "first_step": request.title,
                            "description": request.description,
                            "message": (
                                "Context Reorganization workflow started. This workflow will guide you through:\n"
                                "1. Current context analysis\n"
                                "2. Target context design\n"
                                "3. Schema migration planning\n"
                                "4. Context restructuring execution"
                            ),
                        }
                    )
                else:
                    return json.dumps({"error": "Failed to start Context Reorganization workflow"})
            except Exception as e:
                logger.error(f"Error starting Context Reorganization workflow: {str(e)}")
                return json.dumps({"error": f"Failed to start workflow: {str(e)}"})

        @self.mcp.tool(description="Start the Disaster Recovery Setup workflow for configuring DR strategies")
        async def guided_disaster_recovery() -> str:
            """Convenience method to start Disaster Recovery workflow."""
            workflow_id = "disaster_recovery_setup"

            try:
                request = await self.multi_step_manager.start_workflow(workflow_id=workflow_id, initial_context={})

                if request:
                    return json.dumps(
                        {
                            "status": "started",
                            "workflow_id": workflow_id,
                            "workflow_name": "Disaster Recovery Setup",
                            "request_id": request.id,
                            "first_step": request.title,
                            "description": request.description,
                            "message": (
                                "Disaster Recovery Setup workflow started. This workflow will guide you through:\n"
                                "1. Current infrastructure assessment\n"
                                "2. Backup strategy configuration\n"
                                "3. Recovery procedures planning\n"
                                "4. Testing and validation setup"
                            ),
                        }
                    )
                else:
                    return json.dumps({"error": "Failed to start Disaster Recovery workflow"})
            except Exception as e:
                logger.error(f"Error starting Disaster Recovery workflow: {str(e)}")
                return json.dumps({"error": f"Failed to start workflow: {str(e)}"})


def create_workflow_executor(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the actions based on completed workflow results.

    This function takes the results from a completed workflow and executes
    the appropriate Schema Registry operations.
    """
    workflow_name = workflow_result.get("metadata", {}).get("workflow_name")
    responses = workflow_result.get("responses", {})
    if not isinstance(responses, dict):
        responses = {}

    if workflow_name == "Schema Migration Wizard":
        return execute_schema_migration(responses)
    elif workflow_name == "Context Reorganization":
        return execute_context_reorganization(responses)
    elif workflow_name == "Disaster Recovery Setup":
        return execute_disaster_recovery_setup(responses)
    elif workflow_name == "Schema Evolution Assistant":
        return execute_schema_evolution(responses)
    else:
        return {"error": f"Unknown workflow: {workflow_name}"}


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
        "status": "pending",
    }

    # Add specific migration parameters
    if migration_type == "single_schema":
        result["schema_name"] = responses.get("schema_name")
        result["version"] = responses.get("version", "latest")
    elif migration_type == "bulk_migration":
        result["pattern"] = responses.get("schema_pattern")
        result["include_all_versions"] = responses.get("include_all_versions")
        result["context_filter"] = responses.get("context_filter")
    elif migration_type == "context_migration":
        result["source_context"] = responses.get("source_context")
        result["include_dependencies"] = responses.get("include_dependencies")

    # Add migration options
    result["options"] = {
        "preserve_ids": responses.get("preserve_ids") == "true",
        "conflict_resolution": responses.get("conflict_resolution"),
        "create_backup": responses.get("create_backup") == "true",
        "dry_run": responses.get("dry_run") == "true",
    }

    return result


def execute_context_reorganization(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute context reorganization based on workflow responses."""
    strategy = responses.get("strategy")

    result = {"operation": "context_reorganization", "strategy": strategy, "status": "pending"}

    # Add strategy-specific parameters
    if strategy == "merge":
        result["source_contexts"] = [ctx.strip() for ctx in responses.get("source_contexts", "").split(",")]
        result["target_context"] = responses.get("target_context")
        result["handle_duplicates"] = responses.get("handle_duplicates")
    elif strategy == "split":
        result["source_context"] = responses.get("source_context")
        result["split_criteria"] = responses.get("split_criteria")
        result["target_contexts"] = [ctx.strip() for ctx in responses.get("target_contexts", "").split(",")]
        result["split_rules"] = responses.get("split_rules")
    elif strategy == "rename":
        rename_mappings: Dict[str, str] = {}
        mappings_str = responses.get("rename_mappings", "")
        if mappings_str and isinstance(mappings_str, str):
            mappings = [mapping.strip() for mapping in mappings_str.split(",")]
            for mapping in mappings:
                if ":" in mapping and isinstance(mapping, str):
                    old, new = mapping.split(":", 1)
                    if old and new:
                        rename_mappings[old.strip()] = new.strip()
        result["rename_mappings"] = rename_mappings
    elif strategy == "restructure":
        result["structure_definition"] = responses.get("structure_definition")
        result["migration_strategy"] = responses.get("migration_strategy")

    # Add common options
    result["options"] = {
        "backup_first": responses.get("backup_first") == "true",
        "test_mode": responses.get("test_mode") == "true",
        "generate_report": responses.get("generate_report") == "true",
    }

    return result


def execute_disaster_recovery_setup(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute disaster recovery setup based on workflow responses."""
    dr_strategy = responses.get("dr_strategy")

    result = {"operation": "disaster_recovery_setup", "strategy": dr_strategy, "status": "pending"}

    # Add strategy-specific configuration
    if dr_strategy == "active_passive":
        result["config"] = {
            "primary_registry": responses.get("primary_registry"),
            "standby_registry": responses.get("standby_registry"),
            "replication_interval": responses.get("replication_interval"),
            "failover_mode": responses.get("failover_mode"),
        }
    elif dr_strategy == "active_active":
        result["config"] = {
            "active_registries": [reg.strip() for reg in responses.get("active_registries", "").split(",")],
            "conflict_resolution": responses.get("conflict_resolution"),
            "sync_topology": responses.get("sync_topology"),
        }
    elif dr_strategy == "backup_restore":
        result["config"] = {
            "backup_schedule": responses.get("backup_schedule"),
            "backup_location": responses.get("backup_location"),
            "retention_policy": responses.get("retention_policy"),
            "encryption": responses.get("encryption") == "true",
        }
    elif dr_strategy == "multi_region":
        result["config"] = {
            "regions": [region.strip() for region in responses.get("regions", "").split(",")],
            "primary_region": responses.get("primary_region"),
            "data_residency": responses.get("data_residency") == "true",
            "cross_region_replication": responses.get("cross_region_replication"),
        }

    # Add common DR options
    result["options"] = {
        "enable_monitoring": responses.get("enable_monitoring") == "true",
        "run_dr_drill": responses.get("run_dr_drill") == "true",
        "generate_runbook": responses.get("generate_runbook") == "true",
        "initial_sync": responses.get("initial_sync") == "true",
    }

    return result


def execute_schema_evolution(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Execute schema evolution based on workflow responses."""
    result = {
        "operation": "schema_evolution",
        "subject": responses.get("subject"),
        "status": "pending",
    }

    # Basic change information
    result["change_info"] = {
        "change_type": responses.get("change_type"),
        "description": responses.get("change_description"),
        "current_consumers": responses.get("current_consumers"),
        "production_impact": responses.get("production_impact"),
        "has_breaking_changes": responses.get("has_breaking_changes") == "true",
    }

    # Evolution strategy
    strategy = responses.get("evolution_strategy")
    result["evolution_strategy"] = strategy

    # Strategy-specific configuration
    if strategy == "multi_version_migration":
        result["migration_config"] = {
            "intermediate_versions": int(responses.get("intermediate_versions", 1)),
            "version_timeline": responses.get("version_timeline"),
            "deprecation_strategy": responses.get("deprecation_strategy"),
        }
    elif strategy == "dual_support":
        result["dual_support_config"] = {
            "support_duration": responses.get("support_duration"),
            "field_mapping": responses.get("field_mapping"),
            "conversion_logic": responses.get("conversion_logic"),
        }
    elif strategy == "gradual_migration":
        result["migration_phases"] = {
            "phase_count": responses.get("phase_count"),
            "phase_criteria": responses.get("phase_criteria"),
            "rollback_checkpoints": responses.get("rollback_checkpoints") == "true",
        }
    else:
        result["implementation"] = {
            "deployment_window": responses.get("deployment_window"),
            "validation_approach": responses.get("validation_approach"),
        }

    # Compatibility resolution (if breaking changes)
    change_info = result.get("change_info", {})
    if isinstance(change_info, dict) and change_info.get("has_breaking_changes"):
        result["compatibility_resolution"] = {
            "approach": responses.get("resolution_approach"),
            "override_compatibility": responses.get("compatibility_override") == "true",
            "notes": responses.get("compatibility_notes"),
        }

    # Consumer coordination
    result["consumer_coordination"] = {
        "notification_method": responses.get("notification_method"),
        "testing_approach": responses.get("consumer_testing"),
        "support_period": responses.get("support_period"),
    }

    # Rollback planning
    result["rollback_plan"] = {
        "trigger": responses.get("rollback_trigger"),
        "max_time": responses.get("rollback_time"),
        "data_handling": responses.get("data_handling"),
        "test_rollback": responses.get("rollback_testing") == "true",
    }

    # Final options
    result["documentation"] = {
        "generate_migration_guide": responses.get("generate_migration_guide") == "true",
        "create_runbook": responses.get("create_runbook") == "true",
        "schedule_dry_run": responses.get("schedule_dry_run") == "true",
        "evolution_notes": responses.get("evolution_notes"),
    }

    # Execution settings
    result["execution"] = {
        "confirmed": responses.get("final_confirmation") == "true",
        "enable_monitoring": responses.get("monitor_execution") == "true",
    }

    return result


def analyze_schema_changes(current_schema: Dict[str, Any], proposed_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze differences between current and proposed schemas.

    Returns a list of changes with their types and descriptions.
    """
    changes = []

    # Handle case where current schema is empty (new schema)
    if not current_schema or not current_schema.get("fields"):
        if proposed_schema.get("fields"):
            changes.append(
                {
                    "type": "new_schema",
                    "description": f"Creating new schema with {len(proposed_schema.get('fields', []))} fields",
                    "breaking": False,
                }
            )
        return changes

    current_fields = {f["name"]: f for f in current_schema.get("fields", [])}
    proposed_fields = {f["name"]: f for f in proposed_schema.get("fields", [])}

    # Check for added fields
    for field_name, field_def in proposed_fields.items():
        if field_name not in current_fields:
            # Check if field has a default value or is nullable
            has_default = "default" in field_def
            is_nullable = _is_nullable_type(field_def.get("type"))

            changes.append(
                {
                    "type": "add_field",
                    "field": field_name,
                    "field_type": field_def.get("type"),
                    "description": f"New field '{field_name}' of type {field_def.get('type')}",
                    "breaking": not (has_default or is_nullable),  # Breaking if required without default
                    "has_default": has_default,
                    "default_value": field_def.get("default") if has_default else None,
                    "is_nullable": is_nullable,
                }
            )

    # Check for removed fields
    for field_name in current_fields:
        if field_name not in proposed_fields:
            changes.append(
                {
                    "type": "remove_field",
                    "field": field_name,
                    "field_type": current_fields[field_name].get("type"),
                    "description": f"Field '{field_name}' removed",
                    "breaking": True,  # Removing fields is always breaking for readers
                }
            )

    # Check for modified fields
    for field_name in set(current_fields) & set(proposed_fields):
        current_field = current_fields[field_name]
        proposed_field = proposed_fields[field_name]

        field_changes = _analyze_field_changes(field_name, current_field, proposed_field)
        changes.extend(field_changes)

    # Check for schema-level changes
    schema_changes = _analyze_schema_level_changes(current_schema, proposed_schema)
    changes.extend(schema_changes)

    return changes


def _analyze_field_changes(
    field_name: str, current_field: Dict[str, Any], proposed_field: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze changes to a specific field."""
    changes = []

    current_type = current_field.get("type")
    proposed_type = proposed_field.get("type")

    # Type changes
    if current_type != proposed_type:
        type_change = _analyze_type_change(field_name, current_type, proposed_type)
        changes.append(type_change)

    # Default value changes
    current_default = current_field.get("default")
    proposed_default = proposed_field.get("default")
    if current_default != proposed_default:
        changes.append(
            {
                "type": "modify_field_default",
                "field": field_name,
                "description": f"Default value for '{field_name}' changed from {current_default} to {proposed_default}",
                "breaking": False,  # Default value changes are usually backward compatible
                "current_default": current_default,
                "proposed_default": proposed_default,
            }
        )

    # Alias changes
    current_aliases = current_field.get("aliases", [])
    proposed_aliases = proposed_field.get("aliases", [])
    if current_aliases != proposed_aliases:
        changes.append(
            {
                "type": "modify_field_aliases",
                "field": field_name,
                "description": f"Aliases for '{field_name}' changed",
                "breaking": False,  # Alias changes are usually backward compatible
                "added_aliases": list(set(proposed_aliases) - set(current_aliases)),
                "removed_aliases": list(set(current_aliases) - set(proposed_aliases)),
            }
        )

    # Documentation changes
    current_doc = current_field.get("doc")
    proposed_doc = proposed_field.get("doc")
    if current_doc != proposed_doc:
        changes.append(
            {
                "type": "modify_field_doc",
                "field": field_name,
                "description": f"Documentation for '{field_name}' changed",
                "breaking": False,  # Doc changes are never breaking
            }
        )

    return changes


def _analyze_type_change(field_name: str, current_type: Any, proposed_type: Any) -> Dict[str, Any]:
    """Analyze a type change and determine if it's a promotion or breaking change."""

    # Check for type promotions (compatible changes)
    type_promotions = {
        ("int", "long"): "Type promotion from int to long",
        ("float", "double"): "Type promotion from float to double",
        ("string", "bytes"): "Type change from string to bytes (may be compatible)",
    }

    # Normalize types for comparison
    current_normalized = _normalize_type(current_type)
    proposed_normalized = _normalize_type(proposed_type)

    # Check if it's a known promotion
    promotion_key = (current_normalized, proposed_normalized)
    if promotion_key in type_promotions:
        return {
            "type": "modify_field_type_promotion",
            "field": field_name,
            "description": f"{type_promotions[promotion_key]} for field '{field_name}'",
            "breaking": False,  # These specific promotions are backward compatible
            "current_type": current_type,
            "proposed_type": proposed_type,
            "is_promotion": True,
        }

    # Check for union type changes
    if _is_union_type(current_type) or _is_union_type(proposed_type):
        return _analyze_union_type_change(field_name, current_type, proposed_type)

    # Check for complex type changes (records, arrays, maps)
    if isinstance(current_type, dict) or isinstance(proposed_type, dict):
        return _analyze_complex_type_change(field_name, current_type, proposed_type)

    # Default: breaking type change
    return {
        "type": "modify_field_type",
        "field": field_name,
        "description": f"Field '{field_name}' type changed from {current_type} to {proposed_type}",
        "breaking": True,
        "current_type": current_type,
        "proposed_type": proposed_type,
    }


def _analyze_union_type_change(field_name: str, current_type: Any, proposed_type: Any) -> Dict[str, Any]:
    """Analyze changes to union types."""
    current_union = _get_union_types(current_type)
    proposed_union = _get_union_types(proposed_type)

    added_types = proposed_union - current_union
    removed_types = current_union - proposed_union

    # Adding types to a union is backward compatible
    # Removing types from a union is breaking
    is_breaking = len(removed_types) > 0

    description_parts = []
    if added_types:
        description_parts.append(f"added types: {added_types}")
    if removed_types:
        description_parts.append(f"removed types: {removed_types}")

    return {
        "type": "modify_field_union",
        "field": field_name,
        "description": f"Union type for '{field_name}' changed: {', '.join(description_parts)}",
        "breaking": is_breaking,
        "current_type": current_type,
        "proposed_type": proposed_type,
        "added_types": list(added_types),
        "removed_types": list(removed_types),
    }


def _analyze_complex_type_change(field_name: str, current_type: Any, proposed_type: Any) -> Dict[str, Any]:
    """Analyze changes to complex types (records, arrays, maps)."""
    # Handle record types
    if (
        isinstance(current_type, dict)
        and current_type.get("type") == "record"
        and isinstance(proposed_type, dict)
        and proposed_type.get("type") == "record"
    ):

        # Recursively analyze nested record changes
        nested_changes = analyze_schema_changes(current_type, proposed_type)
        has_breaking_changes = any(c.get("breaking", False) for c in nested_changes)

        return {
            "type": "modify_field_record",
            "field": field_name,
            "description": f"Nested record '{field_name}' changed with {len(nested_changes)} modifications",
            "breaking": has_breaking_changes,
            "current_type": current_type,
            "proposed_type": proposed_type,
            "nested_changes": nested_changes,
        }

    # Handle array types
    if (
        isinstance(current_type, dict)
        and current_type.get("type") == "array"
        and isinstance(proposed_type, dict)
        and proposed_type.get("type") == "array"
    ):

        current_items = current_type.get("items")
        proposed_items = proposed_type.get("items")

        if current_items != proposed_items:
            items_change = _analyze_type_change(f"{field_name}.items", current_items, proposed_items)
            return {
                "type": "modify_field_array",
                "field": field_name,
                "description": f"Array element type changed for '{field_name}'",
                "breaking": items_change.get("breaking", True),
                "current_type": current_type,
                "proposed_type": proposed_type,
                "items_change": items_change,
            }

    # Handle map types
    if (
        isinstance(current_type, dict)
        and current_type.get("type") == "map"
        and isinstance(proposed_type, dict)
        and proposed_type.get("type") == "map"
    ):

        current_values = current_type.get("values")
        proposed_values = proposed_type.get("values")

        if current_values != proposed_values:
            values_change = _analyze_type_change(f"{field_name}.values", current_values, proposed_values)
            return {
                "type": "modify_field_map",
                "field": field_name,
                "description": f"Map value type changed for '{field_name}'",
                "breaking": values_change.get("breaking", True),
                "current_type": current_type,
                "proposed_type": proposed_type,
                "values_change": values_change,
            }

    # Default complex type change
    return {
        "type": "modify_field_type",
        "field": field_name,
        "description": f"Complex type change for '{field_name}'",
        "breaking": True,
        "current_type": current_type,
        "proposed_type": proposed_type,
    }


def _analyze_schema_level_changes(
    current_schema: Dict[str, Any], proposed_schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze schema-level changes (name, namespace, aliases, etc.)."""
    changes = []

    # Schema name change
    if current_schema.get("name") != proposed_schema.get("name"):
        changes.append(
            {
                "type": "modify_schema_name",
                "description": (
                    f"Schema name changed from '{current_schema.get('name')}' " f"to '{proposed_schema.get('name')}'"
                ),
                "breaking": True,  # Name changes are typically breaking
                "current_name": current_schema.get("name"),
                "proposed_name": proposed_schema.get("name"),
            }
        )

    # Namespace change
    if current_schema.get("namespace") != proposed_schema.get("namespace"):
        changes.append(
            {
                "type": "modify_schema_namespace",
                "description": (
                    f"Schema namespace changed from '{current_schema.get('namespace')}' "
                    f"to '{proposed_schema.get('namespace')}'"
                ),
                "breaking": True,  # Namespace changes affect fully qualified names
                "current_namespace": current_schema.get("namespace"),
                "proposed_namespace": proposed_schema.get("namespace"),
            }
        )

    # Schema-level aliases
    current_aliases = current_schema.get("aliases", [])
    proposed_aliases = proposed_schema.get("aliases", [])
    if current_aliases != proposed_aliases:
        changes.append(
            {
                "type": "modify_schema_aliases",
                "description": "Schema aliases changed",
                "breaking": False,  # Alias changes are usually compatible
                "added_aliases": list(set(proposed_aliases) - set(current_aliases)),
                "removed_aliases": list(set(current_aliases) - set(proposed_aliases)),
            }
        )

    return changes


# Helper functions
def _is_nullable_type(field_type: Any) -> bool:
    """Check if a type is nullable (includes null in union)."""
    if _is_union_type(field_type):
        return bool("null" in field_type)
    return bool(field_type == "null")


def _is_union_type(field_type: Any) -> bool:
    """Check if a type is a union type."""
    return bool(isinstance(field_type, list))


def _get_union_types(field_type: Any) -> set:
    """Get the set of types in a union."""
    if _is_union_type(field_type):
        return set(field_type)
    return {field_type}


def _normalize_type(field_type: Any) -> str:
    """Normalize a type for comparison."""
    if isinstance(field_type, str):
        return field_type
    elif isinstance(field_type, dict):
        return str(field_type.get("type", "complex"))
    elif isinstance(field_type, list):
        # For unions, return a normalized representation
        return "union"
    return str(field_type)


# Integration with existing elicitation response handler
async def handle_workflow_elicitation_response(
    elicitation_manager: ElicitationManager,
    multi_step_manager: MultiStepElicitationManager,
    response: ElicitationResponse,
) -> Optional[Dict[str, Any]]:
    """
    Handle elicitation responses that may be part of a workflow.

    Returns the workflow result if completed, or None if more steps are needed.
    """
    # Check if this response is part of a workflow
    request = elicitation_manager.pending_requests.get(response.request_id)
    if not request or not request.context or "workflow_instance_id" not in request.context:
        # Not a workflow response, handle normally
        return None

    # Handle workflow response
    result = await multi_step_manager.handle_response(response)

    if isinstance(result, dict):
        # Workflow completed, execute the actions
        execution_result = create_workflow_executor(result)
        return {"workflow_completed": True, "workflow_result": result, "execution_plan": execution_result}
    elif result is None:
        # Error occurred
        return {"error": "Failed to process workflow response"}
    else:
        # More steps needed (result is the next ElicitationRequest)
        return {"workflow_continuing": True, "next_step": result.title, "request_id": result.id}


# Convenience function to integrate with existing MCP server
def register_workflow_tools(mcp: FastMCP, elicitation_manager: ElicitationManager) -> WorkflowMCPTools:
    """Register workflow tools with an MCP server."""
    return WorkflowMCPTools(mcp, elicitation_manager)
