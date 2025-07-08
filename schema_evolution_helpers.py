#!/usr/bin/env python3
"""
Schema Evolution Helper Functions

This module provides helper functions to integrate schema evolution workflows
with existing schema registry operations and compatibility checking.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core_registry_tools import (
    check_compatibility_tool,
    get_schema_tool,
    register_schema_tool,
    update_global_config_tool,
    update_subject_config_tool,
)
from elicitation import ElicitationManager
from multi_step_elicitation import MultiStepElicitationManager
from schema_registry_common import BaseRegistryManager, RegistryClient
from workflow_mcp_integration import _is_nullable_type, analyze_schema_changes

logger = logging.getLogger(__name__)


async def evolve_schema_with_workflow(
    subject: str,
    proposed_schema: Dict[str, Any],
    registry_manager: BaseRegistryManager,
    registry_mode: str,
    elicitation_manager: ElicitationManager,
    multi_step_manager: MultiStepElicitationManager,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    current_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evolve a schema using the multi-step workflow.

    This integrates the existing compatibility checking with the
    multi-step workflow for comprehensive schema evolution.

    Args:
        subject: Schema subject name
        proposed_schema: Proposed new schema
        registry_manager: Registry manager instance
        registry_mode: Registry mode (single/multi)
        elicitation_manager: Elicitation manager instance
        multi_step_manager: Multi-step workflow manager
        context: Optional schema context
        registry: Optional registry name (for multi-registry mode)
        current_schema: Optional current schema (if not provided, will fetch from registry)

    Returns:
        Dictionary with workflow initiation details
    """
    # If current schema not provided, fetch it from registry
    if current_schema is None:
        logger.info(f"Fetching current schema for subject '{subject}'")
        schema_result = get_schema_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            version="latest",
            context=context,
            registry=registry,
        )

        if "error" in schema_result:
            # No existing schema, this is a new registration
            logger.info(f"No existing schema found for '{subject}', treating as new registration")
            current_schema = {}
            changes = []
            compatibility_result = {"is_compatible": True, "messages": []}
        else:
            # Extract schema from result
            if isinstance(schema_result.get("schema"), str):
                try:
                    current_schema = json.loads(schema_result["schema"])
                except json.JSONDecodeError:
                    logger.error("Failed to parse current schema")
                    current_schema = {}
            else:
                current_schema = schema_result.get("schema", {})

            # Analyze the changes
            changes = analyze_schema_changes(current_schema, proposed_schema)

            # Check compatibility
            logger.info(f"Checking compatibility for schema evolution of '{subject}'")
            compatibility_result = check_compatibility_tool(
                subject=subject,
                schema_definition=proposed_schema,
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )
    else:
        # Use provided current schema
        changes = analyze_schema_changes(current_schema, proposed_schema)

        # Check compatibility
        logger.info(f"Checking compatibility for schema evolution of '{subject}'")
        compatibility_result = check_compatibility_tool(
            subject=subject,
            schema_definition=proposed_schema,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            context=context,
            registry=registry,
        )

    # Extract compatibility status
    is_compatible = compatibility_result.get("is_compatible", False)
    compatibility_messages = compatibility_result.get("messages", [])

    # Start the workflow with pre-populated context
    initial_context = {
        "subject": subject,
        "current_schema": current_schema,
        "proposed_schema": proposed_schema,
        "changes": changes,
        "compatibility_result": compatibility_result,
        "has_breaking_changes": not is_compatible,
        "registry_mode": registry_mode,
        "registry": registry,
        "context": context,
    }

    # Start the multi-step workflow
    try:
        workflow_request = await multi_step_manager.start_workflow(
            workflow_id="schema_evolution_assistant", initial_context=initial_context
        )

        if workflow_request:
            return {
                "workflow_started": True,
                "request_id": workflow_request.id,
                "changes_detected": len(changes),
                "has_breaking_changes": not is_compatible,
                "compatibility_messages": compatibility_messages,
            }
        else:
            return {
                "workflow_started": False,
                "error": "Failed to start workflow",
                "changes_detected": len(changes),
                "has_breaking_changes": not is_compatible,
            }
    except Exception as e:
        logger.error(f"Error starting schema evolution workflow: {str(e)}")
        return {
            "workflow_started": False,
            "error": str(e),
            "changes_detected": len(changes),
            "has_breaking_changes": not is_compatible,
        }


async def execute_evolution_plan(
    evolution_plan: Dict[str, Any],
    registry_manager: BaseRegistryManager,
    registry_mode: str,
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a schema evolution plan.

    This function takes the evolution plan created by the workflow and
    executes it step by step.

    Args:
        evolution_plan: The evolution plan from the workflow
        registry_manager: Registry manager instance
        registry_mode: Registry mode (single/multi)
        subject: Schema subject name
        context: Optional schema context
        registry: Optional registry name

    Returns:
        Dictionary with execution results
    """
    results = {
        "subject": subject,
        "status": "executing",
        "steps_completed": [],
        "errors": [],
    }

    try:
        # Handle compatibility override if needed
        if evolution_plan.get("compatibility_resolution", {}).get("override_compatibility"):
            logger.info(f"Temporarily overriding compatibility mode for '{subject}'")

            # Import the correct function
            from core_registry_tools import get_subject_config_tool

            # Get current compatibility
            current_config = get_subject_config_tool(
                subject=subject,
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )

            # Store current compatibility for rollback
            results["original_compatibility"] = current_config.get("compatibility", "BACKWARD")

            # Update to NONE temporarily
            update_result = update_subject_config_tool(
                subject=subject,
                compatibility="NONE",
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )

            if "error" not in update_result:
                results["steps_completed"].append("compatibility_override")
            else:
                results["errors"].append(f"Failed to override compatibility: {update_result['error']}")
                return results

        # Execute based on evolution strategy
        strategy = evolution_plan.get("evolution_strategy")

        if strategy == "direct_update":
            # Direct schema update
            register_result = register_schema_tool(
                subject=subject,
                schema_definition=evolution_plan["proposed_schema"],
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )

            if "error" not in register_result:
                results["steps_completed"].append("schema_registered")
                results["schema_id"] = register_result.get("id")
                results["version"] = register_result.get("version")
            else:
                results["errors"].append(f"Failed to register schema: {register_result['error']}")

        elif strategy == "multi_version_migration":
            # Multi-version migration with intermediate schemas
            migration_config = evolution_plan.get("migration_config", {})
            intermediate_versions = migration_config.get("intermediate_versions", 1)
            version_timeline = migration_config.get("version_timeline", "7,14,30")
            deprecation_strategy = migration_config.get("deprecation_strategy", "mark_deprecated")

            # Parse timeline
            timelines = [int(t.strip()) for t in version_timeline.split(",")]

            # Create intermediate schemas
            intermediate_schemas = _create_intermediate_schemas(
                evolution_plan.get("current_schema", {}),
                evolution_plan["proposed_schema"],
                intermediate_versions,
                deprecation_strategy,
            )

            # Register intermediate schemas
            for i, intermediate_schema in enumerate(intermediate_schemas):
                logger.info(f"Registering intermediate schema version {i + 1}")

                register_result = register_schema_tool(
                    subject=subject,
                    schema_definition=intermediate_schema,
                    registry_manager=registry_manager,
                    registry_mode=registry_mode,
                    context=context,
                    registry=registry,
                )

                if "error" not in register_result:
                    results["steps_completed"].append(f"intermediate_schema_{i + 1}_registered")
                    if i < len(timelines):
                        results[f"intermediate_{i + 1}_timeline"] = f"{timelines[i]} days"
                else:
                    results["errors"].append(
                        f"Failed to register intermediate schema {i + 1}: {register_result['error']}"
                    )
                    break

            # Register final schema if no errors
            if not results["errors"]:
                register_result = register_schema_tool(
                    subject=subject,
                    schema_definition=evolution_plan["proposed_schema"],
                    registry_manager=registry_manager,
                    registry_mode=registry_mode,
                    context=context,
                    registry=registry,
                )

                if "error" not in register_result:
                    results["steps_completed"].append("final_schema_registered")
                    results["schema_id"] = register_result.get("id")
                    results["version"] = register_result.get("version")
                else:
                    results["errors"].append(f"Failed to register final schema: {register_result['error']}")

        elif strategy == "dual_support":
            # Dual support implementation
            dual_config = evolution_plan.get("dual_support_config", {})
            field_mapping = dual_config.get("field_mapping", "")

            # Create a dual-support schema that can handle both old and new formats
            dual_schema = _create_dual_support_schema(
                evolution_plan.get("current_schema", {}), evolution_plan["proposed_schema"], field_mapping
            )

            register_result = register_schema_tool(
                subject=subject,
                schema_definition=dual_schema,
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )

            if "error" not in register_result:
                results["steps_completed"].append("dual_support_schema_registered")
                results["schema_id"] = register_result.get("id")
                results["version"] = register_result.get("version")
                results["dual_support_note"] = (
                    "Schema registered with dual format support. "
                    "Consumers and producers must be updated to handle both formats."
                )
            else:
                results["errors"].append(f"Failed to register dual support schema: {register_result['error']}")

        elif strategy == "gradual_migration":
            # Gradual migration phases
            migration_phases = evolution_plan.get("migration_phases", {})
            phase_count = int(migration_phases.get("phase_count", "3"))

            results["steps_completed"].append("gradual_migration_plan_created")
            results["migration_phases"] = []

            for phase in range(1, phase_count + 1):
                phase_info = {
                    "phase": phase,
                    "description": f"Phase {phase} of {phase_count}",
                    "actions": _get_phase_actions(phase, phase_count, evolution_plan),
                }
                results["migration_phases"].append(phase_info)

            results["note"] = (
                f"Gradual migration plan created with {phase_count} phases. "
                "Execute each phase according to the defined criteria."
            )

        # Restore original compatibility if it was overridden
        if "original_compatibility" in results:
            restore_result = update_subject_config_tool(
                subject=subject,
                compatibility=results["original_compatibility"],
                registry_manager=registry_manager,
                registry_mode=registry_mode,
                context=context,
                registry=registry,
            )

            if "error" not in restore_result:
                results["steps_completed"].append("compatibility_restored")
            else:
                results["errors"].append(f"Failed to restore compatibility: {restore_result['error']}")

        # Set final status
        if results["errors"]:
            results["status"] = "completed_with_errors"
        else:
            results["status"] = "completed"

    except Exception as e:
        logger.error(f"Error executing evolution plan: {str(e)}")
        results["status"] = "failed"
        results["errors"].append(str(e))

    return results


def categorize_schema_changes(changes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize schema changes by type and breaking status.

    Args:
        changes: List of detected changes

    Returns:
        Dictionary with categorized changes
    """
    categorized = {
        "breaking_changes": [],
        "backward_compatible": [],
        "forward_compatible": [],
        "additions": [],
        "deletions": [],
        "modifications": [],
    }

    for change in changes:
        change_type = change.get("type", "unknown")
        is_breaking = change.get("breaking", False)

        # Categorize by type
        if change_type == "add_field":
            categorized["additions"].append(change)
            if not is_breaking:
                categorized["backward_compatible"].append(change)
        elif change_type == "remove_field":
            categorized["deletions"].append(change)
            if is_breaking:
                categorized["breaking_changes"].append(change)
        elif change_type.startswith("modify_field"):
            categorized["modifications"].append(change)
            if is_breaking:
                categorized["breaking_changes"].append(change)
            else:
                categorized["backward_compatible"].append(change)

        # Track all breaking changes
        if is_breaking and change not in categorized["breaking_changes"]:
            categorized["breaking_changes"].append(change)

    return categorized


def generate_evolution_recommendations(
    changes: List[Dict[str, Any]], compatibility_mode: str = "BACKWARD"
) -> List[Dict[str, Any]]:
    """
    Generate recommendations for schema evolution based on detected changes.

    Args:
        changes: List of detected changes
        compatibility_mode: Current compatibility mode

    Returns:
        List of recommendations
    """
    recommendations = []
    categorized = categorize_schema_changes(changes)

    # Handle breaking changes
    if categorized["breaking_changes"]:
        recommendations.append(
            {
                "priority": "high",
                "type": "breaking_change_strategy",
                "title": "Breaking Changes Detected",
                "description": f"Found {len(categorized['breaking_changes'])} breaking changes",
                "options": [
                    {
                        "strategy": "multi_version",
                        "description": "Create intermediate versions to allow gradual migration",
                        "suitable_for": "Large number of consumers, critical systems",
                    },
                    {
                        "strategy": "dual_support",
                        "description": "Support both old and new schema formats temporarily",
                        "suitable_for": "When consumers need time to adapt",
                    },
                    {
                        "strategy": "coordinated_update",
                        "description": "Coordinate simultaneous updates with all consumers",
                        "suitable_for": "Small number of consumers, controlled environment",
                    },
                ],
            }
        )

    # Handle field additions
    if categorized["additions"]:
        recommendations.append(
            {
                "priority": "medium",
                "type": "field_addition",
                "title": "New Fields Added",
                "description": f"Adding {len(categorized['additions'])} new fields",
                "suggestions": [
                    "Ensure new fields have default values for backward compatibility",
                    "Document the purpose and format of new fields",
                    "Consider if fields should be optional vs required",
                ],
            }
        )

    # Handle field deletions
    if categorized["deletions"]:
        recommendations.append(
            {
                "priority": "high",
                "type": "field_deletion",
                "title": "Fields Removed",
                "description": f"Removing {len(categorized['deletions'])} fields",
                "warnings": [
                    "Field removal breaks backward compatibility",
                    "Existing consumers may fail when reading new messages",
                    "Consider deprecating fields instead of removing them",
                ],
                "alternatives": [
                    "Mark fields as deprecated but keep them",
                    "Use a new subject for the incompatible schema",
                    "Implement a multi-phase migration",
                ],
            }
        )

    # Compatibility mode specific recommendations
    if compatibility_mode == "BACKWARD" and categorized["breaking_changes"]:
        recommendations.append(
            {
                "priority": "high",
                "type": "compatibility_violation",
                "title": "Backward Compatibility Violation",
                "description": "Changes violate BACKWARD compatibility mode",
                "actions": [
                    "Temporarily switch to NONE compatibility for this change",
                    "Create a new subject for the incompatible version",
                    "Modify changes to maintain backward compatibility",
                ],
            }
        )

    return recommendations


def create_migration_plan(
    subject: str, changes: List[Dict[str, Any]], evolution_strategy: str, timeline_days: int = 30
) -> Dict[str, Any]:
    """
    Create a detailed migration plan based on the evolution strategy.

    Args:
        subject: Schema subject name
        changes: List of detected changes
        evolution_strategy: Selected evolution strategy
        timeline_days: Total days for migration

    Returns:
        Detailed migration plan
    """
    plan = {
        "subject": subject,
        "strategy": evolution_strategy,
        "timeline_days": timeline_days,
        "phases": [],
        "rollback_points": [],
        "success_criteria": [],
    }

    if evolution_strategy == "multi_version_migration":
        # Create phases for gradual migration
        phases = [
            {
                "phase": 1,
                "name": "Preparation",
                "duration_days": timeline_days // 4,
                "actions": [
                    "Deploy intermediate schema version with both old and new fields",
                    "Update producers to write both formats",
                    "Monitor for errors",
                ],
                "rollback_trigger": "Error rate > 1%",
            },
            {
                "phase": 2,
                "name": "Consumer Migration",
                "duration_days": timeline_days // 2,
                "actions": [
                    "Gradually update consumers to handle new format",
                    "Monitor consumer lag and errors",
                    "Provide migration guides to teams",
                ],
                "rollback_trigger": "Consumer failures > 5%",
            },
            {
                "phase": 3,
                "name": "Cleanup",
                "duration_days": timeline_days // 4,
                "actions": ["Stop writing old format", "Deploy final schema version", "Remove compatibility shims"],
                "rollback_trigger": "Any production issues",
            },
        ]
        plan["phases"] = phases

    elif evolution_strategy == "dual_support":
        plan["phases"] = [
            {
                "phase": 1,
                "name": "Dual Write",
                "duration_days": timeline_days // 3,
                "actions": [
                    "Deploy schema that supports both formats",
                    "Update producers to write both formats",
                    "Implement format detection in consumers",
                ],
            },
            {
                "phase": 2,
                "name": "Migration Window",
                "duration_days": timeline_days // 3,
                "actions": ["Monitor format usage", "Assist teams with consumer updates", "Track migration progress"],
            },
            {
                "phase": 3,
                "name": "Deprecation",
                "duration_days": timeline_days // 3,
                "actions": ["Stop producing old format", "Final consumer updates", "Remove old format support"],
            },
        ]

    # Add rollback points
    for i, phase in enumerate(plan["phases"]):
        plan["rollback_points"].append(
            {
                "after_phase": i + 1,
                "checkpoint_name": f"Phase {i + 1} completion",
                "validation": f"Verify {phase['name']} success metrics",
            }
        )

    # Define success criteria
    plan["success_criteria"] = [
        "All consumers successfully processing new format",
        "No increase in error rates",
        "Schema registry showing new version as active",
        "No data loss or corruption",
        "Performance metrics within acceptable range",
    ]

    return plan


def validate_evolution_plan(plan: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a schema evolution plan against current state.

    Args:
        plan: Evolution plan to validate
        current_state: Current system state (consumers, versions, etc.)

    Returns:
        Validation results with any warnings or errors
    """
    validation = {"is_valid": True, "warnings": [], "errors": [], "suggestions": []}

    # Check timeline feasibility
    if plan.get("timeline_days", 0) < 7:
        validation["warnings"].append(
            {
                "type": "short_timeline",
                "message": "Timeline less than 7 days may be too aggressive",
                "suggestion": "Consider extending timeline for safer migration",
            }
        )

    # Check consumer readiness
    consumer_count = current_state.get("active_consumers", 0)
    if consumer_count > 10 and plan.get("strategy") == "direct_update":
        validation["errors"].append(
            {
                "type": "risky_strategy",
                "message": f"Direct update strategy risky with {consumer_count} consumers",
                "suggestion": "Use gradual migration strategy instead",
            }
        )
        validation["is_valid"] = False

    # Validate phases
    phases = plan.get("phases", [])
    if not phases:
        validation["errors"].append(
            {
                "type": "missing_phases",
                "message": "Evolution plan missing migration phases",
                "suggestion": "Define clear migration phases",
            }
        )
        validation["is_valid"] = False

    # Check rollback provisions
    if not plan.get("rollback_points"):
        validation["warnings"].append(
            {
                "type": "no_rollback_plan",
                "message": "No rollback points defined",
                "suggestion": "Add rollback checkpoints after each phase",
            }
        )

    return validation


def _create_intermediate_schemas(
    current_schema: Dict[str, Any], proposed_schema: Dict[str, Any], num_versions: int, deprecation_strategy: str
) -> List[Dict[str, Any]]:
    """
    Create intermediate schema versions for gradual migration.

    This function generates schemas that bridge between current and proposed versions.
    """
    if num_versions <= 0:
        return []

    intermediate_schemas = []

    # Analyze what needs to change
    changes = analyze_schema_changes(current_schema, proposed_schema)

    # Group changes by type
    field_additions = [c for c in changes if c["type"] == "add_field"]
    field_removals = [c for c in changes if c["type"] == "remove_field"]
    field_modifications = [c for c in changes if c["type"].startswith("modify_field")]

    # For single intermediate version
    if num_versions == 1:
        # Create a schema that supports both old and new
        intermediate = json.loads(json.dumps(current_schema))  # Deep copy

        # Add new fields with defaults
        for addition in field_additions:
            new_field = next((f for f in proposed_schema.get("fields", []) if f["name"] == addition["field"]), None)
            if new_field:
                # Ensure the field has a default or is nullable
                if "default" not in new_field and not _is_nullable_type(new_field.get("type")):
                    new_field = json.loads(json.dumps(new_field))  # Copy
                    new_field["type"] = ["null", new_field["type"]]
                    new_field["default"] = None
                intermediate["fields"].append(new_field)

        # Mark fields for removal as deprecated
        if deprecation_strategy == "mark_deprecated":
            for removal in field_removals:
                for field in intermediate["fields"]:
                    if field["name"] == removal["field"]:
                        field["doc"] = field.get("doc", "") + " [DEPRECATED: Will be removed in next version]"

        intermediate_schemas.append(intermediate)

    else:
        # Multiple intermediate versions - distribute changes across versions
        changes_per_version = max(1, len(changes) // num_versions)

        current_working_schema = json.loads(json.dumps(current_schema))  # Deep copy

        for version in range(num_versions):
            intermediate = json.loads(json.dumps(current_working_schema))  # Deep copy

            # Apply a subset of changes
            start_idx = version * changes_per_version
            end_idx = start_idx + changes_per_version
            if version == num_versions - 1:  # Last version gets all remaining
                end_idx = len(changes)

            version_changes = changes[start_idx:end_idx]

            for change in version_changes:
                if change["type"] == "add_field":
                    # Add the field
                    new_field = next(
                        (f for f in proposed_schema.get("fields", []) if f["name"] == change["field"]), None
                    )
                    if new_field and not any(f["name"] == new_field["name"] for f in intermediate["fields"]):
                        field_copy = json.loads(json.dumps(new_field))
                        # Make nullable if not already
                        if "default" not in field_copy and not _is_nullable_type(field_copy.get("type")):
                            field_copy["type"] = ["null", field_copy["type"]]
                            field_copy["default"] = None
                        intermediate["fields"].append(field_copy)

                elif change["type"] == "remove_field" and version == num_versions - 1:
                    # Only remove in the last intermediate version
                    intermediate["fields"] = [f for f in intermediate["fields"] if f["name"] != change["field"]]

            intermediate_schemas.append(intermediate)
            current_working_schema = intermediate

    return intermediate_schemas


def _create_dual_support_schema(
    current_schema: Dict[str, Any], proposed_schema: Dict[str, Any], field_mapping: str
) -> Dict[str, Any]:
    """
    Create a schema that supports both old and new field structures.

    This allows consumers to read both formats during migration.
    """
    dual_schema = json.loads(json.dumps(current_schema))  # Deep copy

    # Parse field mappings (format: "old:new,old2:new2")
    mappings = {}
    if field_mapping:
        for mapping in field_mapping.split(","):
            if ":" in mapping:
                old, new = mapping.split(":", 1)
                mappings[old.strip()] = new.strip()

    # Add all fields from proposed schema
    proposed_fields = {f["name"]: f for f in proposed_schema.get("fields", [])}
    current_fields = {f["name"]: f for f in dual_schema.get("fields", [])}

    # Add new fields that don't exist
    for field_name, field_def in proposed_fields.items():
        if field_name not in current_fields:
            # Make the field nullable for compatibility
            field_copy = json.loads(json.dumps(field_def))
            if "default" not in field_copy and not _is_nullable_type(field_copy.get("type")):
                field_copy["type"] = ["null", field_copy["type"]]
                field_copy["default"] = None
            dual_schema["fields"].append(field_copy)

    # Add aliases for mapped fields
    for old_name, new_name in mappings.items():
        # Find the new field and add the old name as an alias
        for field in dual_schema["fields"]:
            if field["name"] == new_name:
                aliases = field.get("aliases", [])
                if old_name not in aliases:
                    aliases.append(old_name)
                field["aliases"] = aliases

    return dual_schema


def _get_phase_actions(phase: int, total_phases: int, evolution_plan: Dict[str, Any]) -> List[str]:
    """Generate actions for a specific migration phase."""
    actions = []

    if phase == 1:
        actions.extend(
            [
                "Deploy schema changes to non-production environment",
                "Run compatibility tests with sample data",
                "Update consumer documentation",
                "Notify teams about upcoming changes",
            ]
        )
    elif phase == total_phases:
        actions.extend(
            [
                "Complete final schema deployment",
                "Remove backward compatibility code",
                "Archive old schema versions",
                "Update monitoring dashboards",
            ]
        )
    else:
        percentage = int((phase / total_phases) * 100)
        actions.extend(
            [
                f"Migrate {percentage}% of consumers to new schema",
                "Monitor error rates and consumer lag",
                "Collect feedback from migrated consumers",
                "Prepare rollback plan if issues arise",
            ]
        )

    return actions
