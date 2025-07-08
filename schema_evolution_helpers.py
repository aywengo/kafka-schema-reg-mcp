#!/usr/bin/env python3
"""
Schema Evolution Helper Functions

This module provides helper functions to integrate schema evolution workflows
with existing schema registry operations and compatibility checking.
"""

import logging
from typing import Any, Dict, List, Optional

from elicitation import ElicitationManager
from multi_step_elicitation import MultiStepElicitationManager
from workflow_mcp_integration import analyze_schema_changes

logger = logging.getLogger(__name__)


async def evolve_schema_with_workflow(
    subject: str,
    current_schema: Dict[str, Any],
    proposed_schema: Dict[str, Any],
    registry_client,
    elicitation_manager: ElicitationManager,
    multi_step_manager: MultiStepElicitationManager,
) -> Dict[str, Any]:
    """
    Evolve a schema using the multi-step workflow.
    
    This integrates the existing compatibility checking with the 
    multi-step workflow for comprehensive schema evolution.
    
    Args:
        subject: Schema subject name
        current_schema: Current schema definition
        proposed_schema: Proposed new schema
        registry_client: Schema registry client
        elicitation_manager: Elicitation manager instance
        multi_step_manager: Multi-step workflow manager
        
    Returns:
        Dictionary with workflow initiation details
    """
    # First, analyze the changes
    changes = analyze_schema_changes(current_schema, proposed_schema)
    
    # Check basic compatibility
    try:
        compatibility_result = await registry_client.check_compatibility(
            subject=subject,
            schema=proposed_schema
        )
    except Exception as e:
        logger.error(f"Error checking compatibility: {str(e)}")
        compatibility_result = {
            "is_compatible": False,
            "messages": [str(e)]
        }
    
    # Start the workflow with pre-populated context
    initial_context = {
        "subject": subject,
        "current_schema": current_schema,
        "proposed_schema": proposed_schema,
        "changes": changes,
        "compatibility_result": compatibility_result,
        "has_breaking_changes": not compatibility_result.get("is_compatible", True)
    }
    
    # Start the multi-step workflow
    try:
        workflow_request = await multi_step_manager.start_workflow(
            workflow_id="schema_evolution_assistant",
            initial_context=initial_context
        )
        
        if workflow_request:
            return {
                "workflow_started": True,
                "request_id": workflow_request.id,
                "changes_detected": len(changes),
                "has_breaking_changes": initial_context["has_breaking_changes"],
                "compatibility_messages": compatibility_result.get("messages", []),
            }
        else:
            return {
                "workflow_started": False,
                "error": "Failed to start workflow",
                "changes_detected": len(changes),
                "has_breaking_changes": initial_context["has_breaking_changes"],
            }
    except Exception as e:
        logger.error(f"Error starting schema evolution workflow: {str(e)}")
        return {
            "workflow_started": False,
            "error": str(e),
            "changes_detected": len(changes),
            "has_breaking_changes": initial_context["has_breaking_changes"],
        }


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
            categorized["breaking_changes"].append(change)
        elif change_type == "modify_field":
            categorized["modifications"].append(change)
            if is_breaking:
                categorized["breaking_changes"].append(change)
        
        # Track all breaking changes
        if is_breaking:
            categorized["breaking_changes"].append(change)
    
    return categorized


def generate_evolution_recommendations(
    changes: List[Dict[str, Any]],
    compatibility_mode: str = "BACKWARD"
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
        recommendations.append({
            "priority": "high",
            "type": "breaking_change_strategy",
            "title": "Breaking Changes Detected",
            "description": f"Found {len(categorized['breaking_changes'])} breaking changes",
            "options": [
                {
                    "strategy": "multi_version",
                    "description": "Create intermediate versions to allow gradual migration",
                    "suitable_for": "Large number of consumers, critical systems"
                },
                {
                    "strategy": "dual_support",
                    "description": "Support both old and new schema formats temporarily",
                    "suitable_for": "When consumers need time to adapt"
                },
                {
                    "strategy": "coordinated_update",
                    "description": "Coordinate simultaneous updates with all consumers",
                    "suitable_for": "Small number of consumers, controlled environment"
                }
            ]
        })
    
    # Handle field additions
    if categorized["additions"]:
        recommendations.append({
            "priority": "medium",
            "type": "field_addition",
            "title": "New Fields Added",
            "description": f"Adding {len(categorized['additions'])} new fields",
            "suggestions": [
                "Ensure new fields have default values for backward compatibility",
                "Document the purpose and format of new fields",
                "Consider if fields should be optional vs required"
            ]
        })
    
    # Handle field deletions
    if categorized["deletions"]:
        recommendations.append({
            "priority": "high",
            "type": "field_deletion",
            "title": "Fields Removed",
            "description": f"Removing {len(categorized['deletions'])} fields",
            "warnings": [
                "Field removal breaks backward compatibility",
                "Existing consumers may fail when reading new messages",
                "Consider deprecating fields instead of removing them"
            ],
            "alternatives": [
                "Mark fields as deprecated but keep them",
                "Use a new subject for the incompatible schema",
                "Implement a multi-phase migration"
            ]
        })
    
    # Compatibility mode specific recommendations
    if compatibility_mode == "BACKWARD" and categorized["breaking_changes"]:
        recommendations.append({
            "priority": "high",
            "type": "compatibility_violation",
            "title": "Backward Compatibility Violation",
            "description": "Changes violate BACKWARD compatibility mode",
            "actions": [
                "Temporarily switch to NONE compatibility for this change",
                "Create a new subject for the incompatible version",
                "Modify changes to maintain backward compatibility"
            ]
        })
    
    return recommendations


def create_migration_plan(
    subject: str,
    changes: List[Dict[str, Any]],
    evolution_strategy: str,
    timeline_days: int = 30
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
        "success_criteria": []
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
                    "Monitor for errors"
                ],
                "rollback_trigger": "Error rate > 1%"
            },
            {
                "phase": 2,
                "name": "Consumer Migration",
                "duration_days": timeline_days // 2,
                "actions": [
                    "Gradually update consumers to handle new format",
                    "Monitor consumer lag and errors",
                    "Provide migration guides to teams"
                ],
                "rollback_trigger": "Consumer failures > 5%"
            },
            {
                "phase": 3,
                "name": "Cleanup",
                "duration_days": timeline_days // 4,
                "actions": [
                    "Stop writing old format",
                    "Deploy final schema version",
                    "Remove compatibility shims"
                ],
                "rollback_trigger": "Any production issues"
            }
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
                    "Implement format detection in consumers"
                ]
            },
            {
                "phase": 2,
                "name": "Migration Window",
                "duration_days": timeline_days // 3,
                "actions": [
                    "Monitor format usage",
                    "Assist teams with consumer updates",
                    "Track migration progress"
                ]
            },
            {
                "phase": 3,
                "name": "Deprecation",
                "duration_days": timeline_days // 3,
                "actions": [
                    "Stop producing old format",
                    "Final consumer updates",
                    "Remove old format support"
                ]
            }
        ]
    
    # Add rollback points
    for i, phase in enumerate(plan["phases"]):
        plan["rollback_points"].append({
            "after_phase": i + 1,
            "checkpoint_name": f"Phase {i + 1} completion",
            "validation": f"Verify {phase['name']} success metrics"
        })
    
    # Define success criteria
    plan["success_criteria"] = [
        "All consumers successfully processing new format",
        "No increase in error rates",
        "Schema registry showing new version as active",
        "No data loss or corruption",
        "Performance metrics within acceptable range"
    ]
    
    return plan


def validate_evolution_plan(
    plan: Dict[str, Any],
    current_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a schema evolution plan against current state.
    
    Args:
        plan: Evolution plan to validate
        current_state: Current system state (consumers, versions, etc.)
        
    Returns:
        Validation results with any warnings or errors
    """
    validation = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "suggestions": []
    }
    
    # Check timeline feasibility
    if plan.get("timeline_days", 0) < 7:
        validation["warnings"].append({
            "type": "short_timeline",
            "message": "Timeline less than 7 days may be too aggressive",
            "suggestion": "Consider extending timeline for safer migration"
        })
    
    # Check consumer readiness
    consumer_count = current_state.get("active_consumers", 0)
    if consumer_count > 10 and plan.get("strategy") == "direct_update":
        validation["errors"].append({
            "type": "risky_strategy",
            "message": f"Direct update strategy risky with {consumer_count} consumers",
            "suggestion": "Use gradual migration strategy instead"
        })
        validation["is_valid"] = False
    
    # Validate phases
    phases = plan.get("phases", [])
    if not phases:
        validation["errors"].append({
            "type": "missing_phases",
            "message": "Evolution plan missing migration phases",
            "suggestion": "Define clear migration phases"
        })
        validation["is_valid"] = False
    
    # Check rollback provisions
    if not plan.get("rollback_points"):
        validation["warnings"].append({
            "type": "no_rollback_plan",
            "message": "No rollback points defined",
            "suggestion": "Add rollback checkpoints after each phase"
        })
    
    return validation
