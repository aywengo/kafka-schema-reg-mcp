#!/usr/bin/env python3
"""
Tests for Multi-Step Elicitation Module

This module contains comprehensive tests for the multi-step elicitation functionality.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

import pytest

from elicitation import (
    ElicitationField,
    ElicitationManager,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationType,
)
from multi_step_elicitation import (
    MultiStepElicitationManager,
    MultiStepWorkflow,
    WorkflowState,
    WorkflowStep,
    WorkflowTransitionType,
    create_condition,
)
from workflow_definitions import (
    create_context_reorganization_workflow,
    create_disaster_recovery_workflow,
    create_schema_migration_workflow,
)


class TestWorkflowStep:
    """Tests for WorkflowStep class."""

    def test_simple_step_creation(self):
        """Test creating a simple workflow step."""
        step = WorkflowStep(
            id="test_step",
            title="Test Step",
            description="A test step",
            fields=[ElicitationField(name="test_field", type="text", description="Test field", required=True)],
            next_steps={"default": "next_step"},
        )

        assert step.id == "test_step"
        assert step.title == "Test Step"
        assert len(step.fields) == 1
        assert step.next_steps["default"] == "next_step"

    def test_conditional_next_step(self):
        """Test conditional transitions."""

        # Create a condition function
        def check_value(state: Dict[str, Any]) -> str:
            if state.get("choice") == "option1":
                return "step_a"
            elif state.get("choice") == "option2":
                return "step_b"
            return None

        step = WorkflowStep(
            id="conditional_step",
            title="Conditional Step",
            fields=[
                ElicitationField(name="choice", type="choice", options=["option1", "option2", "option3"], required=True)
            ],
            conditions={"check_choice": check_value},
        )

        # Test different response values
        assert step.get_next_step({"choice": "option1"}, {}) == "step_a"
        assert step.get_next_step({"choice": "option2"}, {}) == "step_b"
        assert step.get_next_step({"choice": "option3"}, {}) is None

    def test_value_based_transitions(self):
        """Test value-based transitions."""
        step = WorkflowStep(
            id="value_step",
            title="Value Step",
            fields=[
                ElicitationField(name="action", type="choice", options=["create", "update", "delete"], required=True)
            ],
            next_steps={"action": {"create": "create_step", "update": "update_step", "delete": "delete_step"}},
        )

        assert step.get_next_step({"action": "create"}, {}) == "create_step"
        assert step.get_next_step({"action": "update"}, {}) == "update_step"
        assert step.get_next_step({"action": "delete"}, {}) == "delete_step"


class TestWorkflowState:
    """Tests for WorkflowState class."""

    def test_state_creation(self):
        """Test creating workflow state."""
        state = WorkflowState(workflow_id="test_workflow", current_step_id="step1")

        assert state.workflow_id == "test_workflow"
        assert state.current_step_id == "step1"
        assert state.step_history == ["step1"]
        assert len(state.responses) == 0

    def test_add_response(self):
        """Test adding responses to state."""
        state = WorkflowState(workflow_id="test_workflow", current_step_id="step1")

        state.add_response("step1", {"field1": "value1", "field2": "value2"})

        assert "step1" in state.responses
        assert state.responses["step1"]["field1"] == "value1"
        assert state.responses["step1"]["field2"] == "value2"

    def test_get_all_responses(self):
        """Test getting all responses flattened."""
        state = WorkflowState(workflow_id="test_workflow", current_step_id="step2")

        state.add_response("step1", {"name": "test", "type": "schema"})
        state.add_response("step2", {"action": "create", "type": "context"})

        all_responses = state.get_all_responses()

        # Check prefixed keys
        assert all_responses["step1.name"] == "test"
        assert all_responses["step1.type"] == "schema"
        assert all_responses["step2.action"] == "create"
        assert all_responses["step2.type"] == "context"

        # Check unprefixed keys (last value wins)
        assert all_responses["type"] == "context"  # From step2

    def test_navigation(self):
        """Test workflow navigation."""
        state = WorkflowState(workflow_id="test_workflow", current_step_id="step1", step_history=["step1"])

        # Initially can't go back
        assert not state.can_go_back()

        # Add more steps
        state.step_history.extend(["step2", "step3"])
        state.current_step_id = "step3"

        # Now can go back
        assert state.can_go_back()

        # Go back
        previous = state.go_back()
        assert previous == "step2"
        assert state.current_step_id == "step2"
        assert len(state.step_history) == 2


class TestMultiStepWorkflow:
    """Tests for MultiStepWorkflow class."""

    def test_workflow_creation(self):
        """Test creating a workflow."""
        steps = {
            "start": WorkflowStep(id="start", title="Start", next_steps={"default": "middle"}),
            "middle": WorkflowStep(id="middle", title="Middle", next_steps={"default": "finish"}),
            "finish": WorkflowStep(id="finish", title="Finish", next_steps={}),
        }

        workflow = MultiStepWorkflow(
            id="test_workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            initial_step_id="start",
        )

        assert workflow.id == "test_workflow"
        assert len(workflow.steps) == 3
        assert workflow.initial_step_id == "start"

    def test_workflow_validation(self):
        """Test workflow validation."""
        # Test invalid initial step
        with pytest.raises(ValueError, match="Initial step"):
            MultiStepWorkflow(
                id="invalid", name="Invalid", description="Invalid workflow", steps={}, initial_step_id="nonexistent"
            )

        # Test invalid step reference
        with pytest.raises(ValueError, match="Referenced step"):
            steps = {"start": WorkflowStep(id="start", title="Start", next_steps={"default": "nonexistent"})}
            MultiStepWorkflow(
                id="invalid", name="Invalid", description="Invalid workflow", steps=steps, initial_step_id="start"
            )


class TestMultiStepElicitationManager:
    """Tests for MultiStepElicitationManager class."""

    @pytest.fixture
    def elicitation_manager(self):
        """Create an elicitation manager."""
        return ElicitationManager()

    @pytest.fixture
    def multi_step_manager(self, elicitation_manager):
        """Create a multi-step elicitation manager."""
        return MultiStepElicitationManager(elicitation_manager)

    @pytest.fixture
    def simple_workflow(self):
        """Create a simple test workflow."""
        steps = {
            "step1": WorkflowStep(
                id="step1",
                title="Step 1",
                fields=[ElicitationField(name="name", type="text", required=True)],
                next_steps={"default": "step2"},
            ),
            "step2": WorkflowStep(
                id="step2",
                title="Step 2",
                fields=[ElicitationField(name="confirm", type="confirmation", required=True)],
                next_steps={"confirm": {"true": "finish", "false": "step1"}},
            ),
        }

        return MultiStepWorkflow(
            id="simple_workflow",
            name="Simple Workflow",
            description="A simple test workflow",
            steps=steps,
            initial_step_id="step1",
        )

    @pytest.mark.asyncio
    async def test_register_workflow(self, multi_step_manager, simple_workflow):
        """Test registering a workflow."""
        multi_step_manager.register_workflow(simple_workflow)

        assert simple_workflow.id in multi_step_manager.workflows
        assert multi_step_manager.workflows[simple_workflow.id] == simple_workflow

    @pytest.mark.asyncio
    async def test_start_workflow(self, multi_step_manager, simple_workflow):
        """Test starting a workflow."""
        multi_step_manager.register_workflow(simple_workflow)

        # Start the workflow
        request = await multi_step_manager.start_workflow(simple_workflow.id)

        assert request is not None
        assert request.title == "Step 1"
        assert len(request.fields) == 1
        assert request.fields[0].name == "name"

        # Check workflow state was created
        assert len(multi_step_manager.active_states) == 1
        instance_id = request.context["workflow_instance_id"]
        state = multi_step_manager.active_states[instance_id]
        assert state.current_step_id == "step1"

    @pytest.mark.asyncio
    async def test_workflow_progression(self, multi_step_manager, simple_workflow, elicitation_manager):
        """Test progressing through a workflow."""
        multi_step_manager.register_workflow(simple_workflow)

        # Start workflow
        request1 = await multi_step_manager.start_workflow(simple_workflow.id)
        instance_id = request1.context["workflow_instance_id"]

        # Submit response for step 1
        response1 = ElicitationResponse(request_id=request1.id, values={"name": "Test Name"}, complete=True)

        # Handle response - should get next step
        result = await multi_step_manager.handle_response(response1)

        assert result is not None
        assert isinstance(result, ElicitationRequest)
        assert result.title == "Step 2"

        # Submit response for step 2 (confirm = true)
        response2 = ElicitationResponse(request_id=result.id, values={"confirm": "true"}, complete=True)

        # Handle response - should complete workflow
        final_result = await multi_step_manager.handle_response(response2)

        assert isinstance(final_result, dict)
        assert final_result["workflow_instance_id"] == instance_id
        assert final_result["responses"]["name"] == "Test Name"
        assert final_result["responses"]["confirm"] == "true"

        # Check workflow moved to completed
        assert instance_id not in multi_step_manager.active_states
        assert instance_id in multi_step_manager.completed_workflows

    @pytest.mark.asyncio
    async def test_workflow_back_navigation(self, multi_step_manager, simple_workflow, elicitation_manager):
        """Test going back in a workflow."""
        multi_step_manager.register_workflow(simple_workflow)

        # Start workflow and go to step 2
        request1 = await multi_step_manager.start_workflow(simple_workflow.id)
        response1 = ElicitationResponse(request_id=request1.id, values={"name": "Test Name"}, complete=True)
        request2 = await multi_step_manager.handle_response(response1)

        # Now request to go back
        response2 = ElicitationResponse(request_id=request2.id, values={"_workflow_action": "back"}, complete=True)

        # Should get step 1 again
        result = await multi_step_manager.handle_response(response2)

        assert isinstance(result, ElicitationRequest)
        assert result.title == "Step 1"

    @pytest.mark.asyncio
    async def test_abort_workflow(self, multi_step_manager, simple_workflow):
        """Test aborting a workflow."""
        multi_step_manager.register_workflow(simple_workflow)

        # Start workflow
        request = await multi_step_manager.start_workflow(simple_workflow.id)
        instance_id = request.context["workflow_instance_id"]

        # Abort it
        success = await multi_step_manager.abort_workflow(instance_id)

        assert success
        assert instance_id not in multi_step_manager.active_states
        assert instance_id in multi_step_manager.completed_workflows

        # Check aborted metadata
        state = multi_step_manager.completed_workflows[instance_id]
        assert state.metadata.get("aborted") is True
        assert "aborted_at" in state.metadata


class TestWorkflowDefinitions:
    """Tests for pre-defined workflows."""

    def test_schema_migration_workflow(self):
        """Test schema migration workflow creation."""
        workflow = create_schema_migration_workflow()

        assert workflow.id == "schema_migration_wizard"
        assert workflow.initial_step_id == "migration_type"
        assert len(workflow.steps) > 0

        # Test workflow flow
        first_step = workflow.get_step("migration_type")
        assert first_step is not None

        # Test transitions
        next_step_id = first_step.get_next_step({"migration_type": "single_schema"}, {})
        assert next_step_id == "single_schema_selection"

    def test_context_reorganization_workflow(self):
        """Test context reorganization workflow."""
        workflow = create_context_reorganization_workflow()

        assert workflow.id == "context_reorganization"
        assert workflow.initial_step_id == "reorg_strategy"
        assert workflow.metadata.get("requires_admin") is True

    def test_disaster_recovery_workflow(self):
        """Test disaster recovery workflow."""
        workflow = create_disaster_recovery_workflow()

        assert workflow.id == "disaster_recovery_setup"
        assert workflow.initial_step_id == "dr_strategy"
        assert workflow.metadata.get("difficulty") == "expert"


class TestConditionHelpers:
    """Tests for condition helper functions."""

    def test_create_condition_equals(self):
        """Test equals condition."""
        condition = create_condition("status", "equals", "active")

        assert condition({"status": "active"}) == "active"
        assert condition({"status": "inactive"}) is None
        assert condition({}) is None

    def test_create_condition_comparisons(self):
        """Test comparison conditions."""
        gt_condition = create_condition("value", "greater_than", 10)
        lt_condition = create_condition("value", "less_than", 10)

        assert gt_condition({"value": 15}) == 10
        assert gt_condition({"value": 5}) is None
        assert lt_condition({"value": 5}) == 10
        assert lt_condition({"value": 15}) is None

    def test_create_condition_contains(self):
        """Test contains condition."""
        condition = create_condition("text", "contains", "test")

        assert condition({"text": "this is a test string"}) == "test"
        assert condition({"text": "no match here"}) is None

    def test_create_condition_exists(self):
        """Test exists condition."""
        condition = create_condition("optional_field", "exists", "field_exists")

        assert condition({"optional_field": "any value"}) == "field_exists"
        assert condition({"other_field": "value"}) is None


# Integration test
class TestWorkflowIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_migration_workflow(self):
        """Test completing the migration workflow."""
        # Create managers
        elicitation_manager = ElicitationManager()
        multi_step_manager = MultiStepElicitationManager(elicitation_manager)

        # Register workflow
        workflow = create_schema_migration_workflow()
        multi_step_manager.register_workflow(workflow)

        # Start workflow
        request1 = await multi_step_manager.start_workflow(workflow.id)
        assert request1.title == "Schema Migration Wizard - Migration Type"

        # Select single schema migration
        response1 = ElicitationResponse(
            request_id=request1.id, values={"migration_type": "single_schema"}, complete=True
        )

        request2 = await multi_step_manager.handle_response(response1)
        assert request2.title == "Select Schema"

        # Provide schema details
        response2 = ElicitationResponse(
            request_id=request2.id,
            values={"source_registry": "development", "schema_name": "com.example.User", "version": "latest"},
            complete=True,
        )

        request3 = await multi_step_manager.handle_response(response2)
        assert request3.title == "Migration Options"

        # Configure migration
        response3 = ElicitationResponse(
            request_id=request3.id,
            values={
                "target_registry": "production",
                "target_context": "",
                "preserve_ids": "false",
                "conflict_resolution": "skip",
                "create_backup": "true",
            },
            complete=True,
        )

        request4 = await multi_step_manager.handle_response(response3)
        assert request4.title == "Review Migration Plan"

        # Confirm migration
        response4 = ElicitationResponse(
            request_id=request4.id, values={"dry_run": "true", "confirm_migration": "true"}, complete=True
        )

        # Complete workflow
        result = await multi_step_manager.handle_response(response4)

        assert isinstance(result, dict)
        assert result["responses"]["migration_type"] == "single_schema"
        assert result["responses"]["source_registry"] == "development"
        assert result["responses"]["target_registry"] == "production"
        assert result["steps_completed"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
