#!/usr/bin/env python3
"""
Tests for Schema Evolution Assistant

This module tests the multi-step workflow for schema evolution,
including breaking change detection, strategy selection, and migration planning.
"""

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

# Add parent directory to path to import modules from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elicitation import ElicitationManager, ElicitationRequest, ElicitationResponse
from multi_step_elicitation import MultiStepElicitationManager
from schema_evolution_helpers import (
    categorize_schema_changes,
    create_migration_plan,
    evolve_schema_with_workflow,
    generate_evolution_recommendations,
    validate_evolution_plan,
)
from workflow_definitions import create_schema_evolution_workflow
from workflow_mcp_integration import analyze_schema_changes

# Test schemas for evolution scenarios
TEST_SCHEMAS = {
    "user_v1": {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            {"name": "created_at", "type": "long"},
        ],
    },
    "user_v2_backward_compatible": {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            {"name": "created_at", "type": "long"},
            {"name": "email", "type": ["null", "string"], "default": None},  # Optional field
        ],
    },
    "user_v2_breaking_removal": {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            # removed created_at - breaking change
        ],
    },
    "user_v2_breaking_type_change": {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "long"},  # Changed from int to long
            {"name": "username", "type": "string"},
            {"name": "created_at", "type": "long"},
        ],
    },
    "user_v2_multiple_changes": {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "long"},  # Type change
            {"name": "username", "type": "string"},
            {"name": "email", "type": "string"},  # New required field
            {"name": "updated_at", "type": "long"},  # New field
            # removed created_at
        ],
    },
}


class MockRegistryClient:
    """Mock schema registry client for testing."""

    def __init__(self):
        self.schemas = {}
        self.compatibility_mode = "BACKWARD"

    async def get_schema(self, subject: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """Get schema by subject and version."""
        if subject in self.schemas:
            return self.schemas[subject]
        return None

    async def register_schema(self, subject: str, schema: Dict[str, Any]) -> int:
        """Register a new schema."""
        self.schemas[subject] = schema
        return 1

    async def check_compatibility(self, subject: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Check compatibility of new schema."""
        current = await self.get_schema(subject)
        if not current:
            return {"is_compatible": True, "messages": []}

        # Enhanced compatibility check for testing
        current_fields = {f["name"]: f for f in current.get("fields", [])}
        new_fields = {f["name"]: f for f in schema.get("fields", [])}

        messages = []
        is_compatible = True

        # Check for removed fields (breaking)
        removed_fields = set(current_fields.keys()) - set(new_fields.keys())
        if removed_fields:
            messages.append(f"Removed fields: {', '.join(removed_fields)}")
            is_compatible = False

        # Check for type changes (potentially breaking)
        for field_name in set(current_fields.keys()) & set(new_fields.keys()):
            current_type = current_fields[field_name].get("type")
            new_type = new_fields[field_name].get("type")
            if current_type != new_type:
                # Simple type change detection
                if current_type == "int" and new_type == "long":
                    messages.append(f"Field '{field_name}': int promoted to long (compatible)")
                else:
                    messages.append(f"Field '{field_name}': type changed from {current_type} to {new_type}")
                    is_compatible = False

        # Check for added required fields (breaking)
        added_fields = set(new_fields.keys()) - set(current_fields.keys())
        for field_name in added_fields:
            field_def = new_fields[field_name]
            field_type = field_def.get("type")
            has_default = "default" in field_def
            is_nullable = isinstance(field_type, list) and "null" in field_type

            if not has_default and not is_nullable:
                messages.append(f"Added required field '{field_name}' without default")
                is_compatible = False
            else:
                messages.append(f"Added optional field '{field_name}' (compatible)")

        return {"is_compatible": is_compatible, "messages": messages}


class MockRegistryManager:
    """Mock registry manager for testing."""

    def __init__(self, registry_client: MockRegistryClient):
        self.client = registry_client
        self.default_registry = "test"

    def get_registry(self, name: Optional[str] = None) -> MockRegistryClient:
        """Get registry by name."""
        return self.client

    def get_default_registry(self) -> MockRegistryClient:
        """Get default registry."""
        return self.client


class MockElicitationManager(ElicitationManager):
    """Mock elicitation manager for testing."""

    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        super().__init__()  # Don't pass mock_elicit
        self.responses = responses or {}
        self.requests: List[ElicitationRequest] = []
        self.mock_elicit = True  # Set as attribute instead

    async def elicit(self, request: ElicitationRequest) -> ElicitationResponse:
        """Mock elicitation that returns predefined responses."""
        self.requests.append(request)
        return ElicitationResponse(request_id=request.id, values=self.responses)


@pytest.mark.asyncio
async def test_analyze_schema_changes():
    """Test schema change analysis."""
    # Test field addition
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_backward_compatible"])
    assert len(changes) == 1
    assert changes[0]["type"] == "add_field"
    assert changes[0]["field"] == "email"
    assert not changes[0]["breaking"]  # Optional field is not breaking

    # Test field removal
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_breaking_removal"])
    assert len(changes) == 1
    assert changes[0]["type"] == "remove_field"
    assert changes[0]["field"] == "created_at"
    assert changes[0]["breaking"]  # Removal is breaking

    # Test type change
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_breaking_type_change"])
    assert len(changes) == 1
    assert changes[0]["type"] == "modify_field_type_promotion"  # int to long is a promotion
    assert changes[0]["field"] == "id"
    assert not changes[0]["breaking"]  # int to long promotion is not breaking

    # Test multiple changes
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_multiple_changes"])
    assert len(changes) == 4
    change_types = {c["type"] for c in changes}
    assert "add_field" in change_types
    assert "remove_field" in change_types
    assert "modify_field_type_promotion" in change_types


@pytest.mark.asyncio
async def test_categorize_schema_changes():
    """Test schema change categorization."""
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_multiple_changes"])
    categorized = categorize_schema_changes(changes)

    assert len(categorized["breaking_changes"]) > 0
    assert len(categorized["additions"]) == 2  # email and updated_at
    assert len(categorized["deletions"]) == 1  # created_at
    assert len(categorized["modifications"]) == 1  # id type change (promotion)


@pytest.mark.asyncio
async def test_generate_evolution_recommendations():
    """Test evolution recommendation generation."""
    # Test breaking changes recommendations
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_breaking_removal"])
    recommendations = generate_evolution_recommendations(changes, "BACKWARD")

    assert len(recommendations) > 0

    # Should have breaking change strategy recommendation
    breaking_rec = next((r for r in recommendations if r["type"] == "breaking_change_strategy"), None)
    assert breaking_rec is not None
    assert breaking_rec["priority"] == "high"
    assert len(breaking_rec["options"]) > 0

    # Should have field deletion recommendation
    deletion_rec = next((r for r in recommendations if r["type"] == "field_deletion"), None)
    assert deletion_rec is not None
    assert deletion_rec["priority"] == "high"
    assert len(deletion_rec["warnings"]) > 0


@pytest.mark.asyncio
async def test_create_migration_plan():
    """Test migration plan creation."""
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_multiple_changes"])

    # Test multi-version migration plan
    plan = create_migration_plan(
        subject="user-events",
        changes=changes,
        evolution_strategy="multi_version_migration",
        timeline_days=30,
    )

    assert plan["subject"] == "user-events"
    assert plan["strategy"] == "multi_version_migration"
    assert plan["timeline_days"] == 30
    assert len(plan["phases"]) == 3
    assert len(plan["rollback_points"]) == 3
    assert len(plan["success_criteria"]) > 0

    # Verify phase structure
    phase1 = plan["phases"][0]
    assert phase1["phase"] == 1
    assert phase1["name"] == "Preparation"
    assert len(phase1["actions"]) > 0
    assert "rollback_trigger" in phase1


@pytest.mark.asyncio
async def test_validate_evolution_plan():
    """Test evolution plan validation."""
    changes = analyze_schema_changes(TEST_SCHEMAS["user_v1"], TEST_SCHEMAS["user_v2_multiple_changes"])

    # Create a plan with short timeline
    plan = create_migration_plan(
        subject="user-events",
        changes=changes,
        evolution_strategy="direct_update",
        timeline_days=3,  # Too short
    )

    current_state = {"active_consumers": 20}  # Many consumers

    validation = validate_evolution_plan(plan, current_state)

    assert not validation["is_valid"]  # Should fail due to risky strategy
    assert len(validation["warnings"]) > 0
    assert len(validation["errors"]) > 0

    # Find timeline warning
    timeline_warning = next((w for w in validation["warnings"] if w["type"] == "short_timeline"), None)
    assert timeline_warning is not None


@pytest.mark.asyncio
async def test_schema_evolution_workflow():
    """Test the complete schema evolution workflow."""
    # Create managers
    elicitation_responses = {
        "subject": "user-events",
        "change_type": "multiple_changes",
        "change_description": "Adding email, changing id type, removing created_at",
        "current_consumers": "10-50",
        "production_impact": "yes_critical",
        "has_breaking_changes": "true",
        "current_compatibility": "BACKWARD",
        "risk_tolerance": "low",
        "resolution_approach": "multi_version_migration",
        "compatibility_override": "true",
        "evolution_strategy": "multi_version_migration",
        "intermediate_versions": "2",
        "version_timeline": "7,14",
        "deprecation_strategy": "mark_deprecated",
        "notification_method": "multi_channel",
        "consumer_testing": "sandbox_environment",
        "support_period": "1_month",
        "rollback_trigger": "error_rate_threshold",
        "rollback_time": "4_hours",
        "data_handling": "preserve_all",
        "rollback_testing": "true",
        "generate_migration_guide": "true",
        "create_runbook": "true",
        "schedule_dry_run": "true",
        "final_confirmation": "true",
        "monitor_execution": "true",
    }

    elicitation_manager = MockElicitationManager(elicitation_responses)
    multi_step_manager = MultiStepElicitationManager(elicitation_manager)

    # Register the workflow
    workflow = create_schema_evolution_workflow()
    multi_step_manager.register_workflow(workflow)

    # Create mock registry client and manager
    registry_client = MockRegistryClient()
    await registry_client.register_schema("user-events", TEST_SCHEMAS["user_v1"])
    registry_manager = MockRegistryManager(registry_client)

    # Mock the check_compatibility_tool function
    from unittest.mock import patch

    mock_compatibility_result = {
        "is_compatible": False,
        "messages": [
            "Removed fields: created_at",
            "Added required field 'email' without default",
            "Field 'id': int promoted to long (compatible)",
        ],
    }

    with patch("schema_evolution_helpers.check_compatibility_tool", return_value=mock_compatibility_result):
        # Start the evolution workflow
        result = await evolve_schema_with_workflow(
            subject="user-events",
            current_schema=TEST_SCHEMAS["user_v1"],
            proposed_schema=TEST_SCHEMAS["user_v2_multiple_changes"],
            registry_manager=registry_manager,
            registry_mode="single",
            elicitation_manager=elicitation_manager,
            multi_step_manager=multi_step_manager,
        )

    assert result["workflow_started"]
    assert result["changes_detected"] == 4
    assert result["has_breaking_changes"]
    assert len(result["compatibility_messages"]) > 0


@pytest.mark.asyncio
async def test_workflow_with_backward_compatible_changes():
    """Test workflow with backward compatible changes only."""
    elicitation_responses = {
        "subject": "user-events",
        "change_type": "add_fields",
        "change_description": "Adding optional email field",
        "current_consumers": "5-10",
        "production_impact": "yes_non_critical",
        "has_breaking_changes": "false",
        "current_compatibility": "BACKWARD",
        "risk_tolerance": "medium",
        "evolution_strategy": "direct_update",
        "deployment_window": "2024-01-15 02:00 UTC",
        "validation_approach": "strict_validation",
        "notification_method": "documentation_only",
        "consumer_testing": "consumer_managed",
        "support_period": "1_week",
        "rollback_trigger": "manual_decision",
        "rollback_time": "1_hour",
        "data_handling": "preserve_all",
        "rollback_testing": "false",
        "generate_migration_guide": "false",
        "create_runbook": "false",
        "schedule_dry_run": "false",
        "final_confirmation": "true",
        "monitor_execution": "true",
    }

    elicitation_manager = MockElicitationManager(elicitation_responses)
    multi_step_manager = MultiStepElicitationManager(elicitation_manager)

    workflow = create_schema_evolution_workflow()
    multi_step_manager.register_workflow(workflow)

    registry_client = MockRegistryClient()
    await registry_client.register_schema("user-events", TEST_SCHEMAS["user_v1"])
    registry_manager = MockRegistryManager(registry_client)

    # Mock the check_compatibility_tool function for backward compatible changes
    from unittest.mock import patch

    mock_compatibility_result = {"is_compatible": True, "messages": ["Added optional field 'email' (compatible)"]}

    with patch("schema_evolution_helpers.check_compatibility_tool", return_value=mock_compatibility_result):
        result = await evolve_schema_with_workflow(
            subject="user-events",
            current_schema=TEST_SCHEMAS["user_v1"],
            proposed_schema=TEST_SCHEMAS["user_v2_backward_compatible"],
            registry_manager=registry_manager,
            registry_mode="single",
            elicitation_manager=elicitation_manager,
            multi_step_manager=multi_step_manager,
        )

    assert result["workflow_started"]
    assert result["changes_detected"] == 1
    assert not result["has_breaking_changes"]


@pytest.mark.asyncio
async def test_workflow_navigation():
    """Test workflow back navigation and state management."""
    # This would test the ability to go back in the workflow
    # and modify previous choices
    pass  # Implementation depends on multi-step workflow navigation features


@pytest.mark.asyncio
async def test_workflow_cancellation():
    """Test workflow cancellation and cleanup."""
    # This would test proper cleanup when a workflow is cancelled
    pass  # Implementation depends on workflow cancellation features


if __name__ == "__main__":
    import sys

    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)
