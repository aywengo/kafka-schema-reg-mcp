#!/usr/bin/env python3
"""
Multi-Step Elicitation Module for Complex Workflows

This module implements multi-step elicitation flows that enable complex workflows
and conditional logic based on user responses, as described in issue #73.

Key Features:
- Conditional questions based on previous answers
- Progressive disclosure of options
- Complex workflow orchestration
- State management across multiple elicitation steps
- Ability to go back and modify previous choices

Use Cases:
1. Schema Migration Wizard
2. Context Reorganization
3. Disaster Recovery Setup
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from elicitation import (
    ElicitationField,
    ElicitationManager,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationType,
)

logger = logging.getLogger(__name__)


class WorkflowTransitionType(Enum):
    """Types of transitions between workflow steps."""

    NEXT = "next"  # Move to next step
    CONDITIONAL = "conditional"  # Move based on condition
    JUMP = "jump"  # Jump to specific step
    BACK = "back"  # Go back to previous step
    FINISH = "finish"  # Complete the workflow
    ABORT = "abort"  # Abort the workflow


@dataclass
class WorkflowStep:
    """Represents a single step in a multi-step workflow."""

    id: str
    title: str
    description: Optional[str] = None
    fields: List[ElicitationField] = field(default_factory=list)
    elicitation_type: ElicitationType = ElicitationType.FORM
    next_steps: Dict[str, str] = field(default_factory=dict)  # value -> step_id mapping
    conditions: Dict[str, Callable[[Dict[str, Any]], str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_next_step(self, response_values: Dict[str, Any], workflow_state: Dict[str, Any]) -> Optional[str]:
        """Determine the next step based on response values and workflow state."""
        # Check conditional transitions first
        for condition_name, condition_func in self.conditions.items():
            try:
                next_step_id = condition_func({**workflow_state, **response_values})
                if next_step_id:
                    return next_step_id
            except Exception as e:
                logger.error(f"Error evaluating condition '{condition_name}': {str(e)}")

        # Check simple value-based transitions
        for field_name, field_value in response_values.items():
            if field_name in self.next_steps:
                next_step_mapping = self.next_steps[field_name]
                # Handle nested dict mapping (e.g., {"confirm": {"true": "finish", "false": "step1"}})
                if isinstance(next_step_mapping, dict) and field_value in next_step_mapping:
                    return next_step_mapping[field_value]
                # Handle direct string mapping (e.g., {"confirm": "finish"})
                elif isinstance(next_step_mapping, str):
                    return next_step_mapping

        # Check if there's a default next step
        if "default" in self.next_steps:
            return self.next_steps["default"]

        return None


@dataclass
class WorkflowState:
    """Maintains the state of a multi-step workflow."""

    workflow_id: str
    current_step_id: str
    step_history: List[str] = field(default_factory=list)
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # step_id -> response values
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Initialize step_history with current_step_id if empty."""
        if not self.step_history:
            self.step_history = [self.current_step_id]

    def add_response(self, step_id: str, response_values: Dict[str, Any]):
        """Add a response for a step."""
        self.responses[step_id] = response_values
        self.updated_at = datetime.now(timezone.utc)

    def get_all_responses(self) -> Dict[str, Any]:
        """Get all responses flattened into a single dictionary."""
        all_responses = {}
        for step_id, step_responses in self.responses.items():
            # Prefix keys with step_id to avoid collisions
            for key, value in step_responses.items():
                all_responses[f"{step_id}.{key}"] = value
                # Also add without prefix for convenience (last value wins)
                all_responses[key] = value
        return all_responses

    def can_go_back(self) -> bool:
        """Check if the user can go back to a previous step."""
        return len(self.step_history) > 1

    def go_back(self) -> Optional[str]:
        """Go back to the previous step."""
        if self.can_go_back():
            # Remove current step from history
            self.step_history.pop()
            # Get previous step
            previous_step = self.step_history[-1]
            self.current_step_id = previous_step
            self.updated_at = datetime.now(timezone.utc)
            return previous_step
        return None


@dataclass
class MultiStepWorkflow:
    """Defines a complete multi-step workflow."""

    id: str
    name: str
    description: str
    steps: Dict[str, WorkflowStep]
    initial_step_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate workflow structure
        if self.initial_step_id not in self.steps:
            raise ValueError(f"Initial step '{self.initial_step_id}' not found in workflow steps")

        # Validate all referenced steps exist
        for step in self.steps.values():
            for next_step_refs in step.next_steps.values():
                # Handle both direct string mappings and nested dict mappings
                if isinstance(next_step_refs, dict):
                    # Nested dict mapping (e.g., {"confirm": {"true": "finish", "false": "step1"}})
                    for next_step_id in next_step_refs.values():
                        if next_step_id and next_step_id not in self.steps and next_step_id != "finish":
                            raise ValueError(f"Referenced step '{next_step_id}' not found in workflow")
                elif isinstance(next_step_refs, str):
                    # Direct string mapping (e.g., {"default": "finish"})
                    if next_step_refs and next_step_refs not in self.steps and next_step_refs != "finish":
                        raise ValueError(f"Referenced step '{next_step_refs}' not found in workflow")

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self.steps.get(step_id)


class MultiStepElicitationManager:
    """Manages multi-step elicitation workflows."""

    def __init__(self, elicitation_manager: ElicitationManager):
        self.elicitation_manager = elicitation_manager
        self.workflows: Dict[str, MultiStepWorkflow] = {}
        self.active_states: Dict[str, WorkflowState] = {}  # workflow_instance_id -> state
        self.completed_workflows: Dict[str, WorkflowState] = {}

    def register_workflow(self, workflow: MultiStepWorkflow):
        """Register a workflow definition."""
        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow '{workflow.name}' with {len(workflow.steps)} steps")

    async def start_workflow(
        self, workflow_id: str, initial_context: Optional[Dict[str, Any]] = None
    ) -> Optional[ElicitationRequest]:
        """Start a new workflow instance."""
        if workflow_id not in self.workflows:
            logger.error(f"Workflow '{workflow_id}' not found")
            return None

        workflow = self.workflows[workflow_id]
        workflow_instance_id = str(uuid4())

        # Create workflow state
        state = WorkflowState(
            workflow_id=workflow_instance_id,
            current_step_id=workflow.initial_step_id,
            metadata={
                "workflow_definition_id": workflow_id,
                "workflow_name": workflow.name,
                "initial_context": initial_context or {},
            },
        )

        self.active_states[workflow_instance_id] = state

        # Create elicitation request for the first step
        first_step = workflow.get_step(workflow.initial_step_id)
        if not first_step:
            logger.error(f"Initial step '{workflow.initial_step_id}' not found")
            return None

        return await self._create_step_request(workflow_instance_id, first_step, state)

    async def _create_step_request(
        self, workflow_instance_id: str, step: WorkflowStep, state: WorkflowState
    ) -> ElicitationRequest:
        """Create an elicitation request for a workflow step."""
        # Add navigation fields if applicable
        fields = step.fields.copy()

        # Add back button if user can go back
        if state.can_go_back():
            fields.append(
                ElicitationField(
                    name="_workflow_action",
                    type="choice",
                    description="Navigation options",
                    options=["continue", "back"],
                    default="continue",
                    required=False,
                )
            )

        # Create request with workflow context
        request = ElicitationRequest(
            type=step.elicitation_type,
            title=step.title,
            description=step.description,
            fields=fields,
            context={
                "workflow_instance_id": workflow_instance_id,
                "step_id": step.id,
                "step_number": len(state.step_history),
                "total_steps_estimate": len(self.workflows[state.metadata["workflow_definition_id"]].steps),
                **step.metadata,
            },
        )

        # Submit to elicitation manager
        await self.elicitation_manager.create_request(request)

        return request

    async def handle_response(
        self, response: ElicitationResponse
    ) -> Optional[Union[ElicitationRequest, Dict[str, Any]]]:
        """
        Handle a response for a workflow step.

        Returns:
            - ElicitationRequest for the next step
            - Dict with final results if workflow is complete
            - None if there's an error
        """
        # Extract workflow instance ID from response context
        request = self.elicitation_manager.pending_requests.get(response.request_id)
        if not request or "workflow_instance_id" not in request.context:
            logger.error("Response not associated with a workflow")
            return None

        workflow_instance_id = request.context["workflow_instance_id"]
        state = self.active_states.get(workflow_instance_id)
        if not state:
            logger.error(f"No active state found for workflow instance '{workflow_instance_id}'")
            return None

        workflow = self.workflows.get(state.metadata["workflow_definition_id"])
        if not workflow:
            logger.error("Workflow definition not found")
            return None

        # Check if user wants to go back
        if "_workflow_action" in response.values and response.values["_workflow_action"] == "back":
            previous_step_id = state.go_back()
            if previous_step_id:
                previous_step = workflow.get_step(previous_step_id)
                if previous_step:
                    return await self._create_step_request(workflow_instance_id, previous_step, state)

        # Store response (excluding navigation fields)
        step_responses = {k: v for k, v in response.values.items() if not k.startswith("_workflow_")}
        state.add_response(state.current_step_id, step_responses)

        # Determine next step
        current_step = workflow.get_step(state.current_step_id)
        if not current_step:
            logger.error(f"Current step '{state.current_step_id}' not found")
            return None

        next_step_id = current_step.get_next_step(step_responses, state.get_all_responses())

        # Handle workflow completion
        if not next_step_id or next_step_id == "finish":
            return await self._complete_workflow(workflow_instance_id, state)

        # Move to next step
        next_step = workflow.get_step(next_step_id)
        if not next_step:
            logger.error(f"Next step '{next_step_id}' not found")
            return None

        state.current_step_id = next_step_id
        state.step_history.append(next_step_id)

        return await self._create_step_request(workflow_instance_id, next_step, state)

    async def _complete_workflow(self, workflow_instance_id: str, state: WorkflowState) -> Dict[str, Any]:
        """Complete a workflow and return the final results."""
        # Move to completed workflows
        self.completed_workflows[workflow_instance_id] = state
        del self.active_states[workflow_instance_id]

        # Return all collected responses
        return {
            "workflow_instance_id": workflow_instance_id,
            "workflow_name": state.metadata.get("workflow_name"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "steps_completed": len(state.step_history),
            "responses": state.get_all_responses(),
            "metadata": state.metadata,
        }

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get information about all active workflows."""
        active = []
        for instance_id, state in self.active_states.items():
            workflow = self.workflows.get(state.metadata.get("workflow_definition_id"))
            if workflow:
                active.append(
                    {
                        "instance_id": instance_id,
                        "workflow_name": workflow.name,
                        "current_step": state.current_step_id,
                        "steps_completed": len(state.step_history) - 1,
                        "created_at": state.created_at.isoformat(),
                        "updated_at": state.updated_at.isoformat(),
                    }
                )
        return active

    async def abort_workflow(self, workflow_instance_id: str) -> bool:
        """Abort an active workflow."""
        if workflow_instance_id in self.active_states:
            state = self.active_states[workflow_instance_id]
            state.metadata["aborted"] = True
            state.metadata["aborted_at"] = datetime.now(timezone.utc).isoformat()
            self.completed_workflows[workflow_instance_id] = state
            del self.active_states[workflow_instance_id]
            logger.info(f"Aborted workflow instance '{workflow_instance_id}'")
            return True
        return False


# Helper function to create condition functions
def create_condition(
    field_name: str, operator: str, match_value: Any, next_step_id: str
) -> Callable[[Dict[str, Any]], Optional[str]]:
    """Create a condition function for workflow transitions."""

    def condition(state: Dict[str, Any]) -> Optional[str]:
        field_value = state.get(field_name)

        if operator == "equals":
            return next_step_id if field_value == match_value else None
        elif operator == "not_equals":
            return next_step_id if field_value != match_value else None
        elif operator == "greater_than":
            return next_step_id if field_value > match_value else None
        elif operator == "less_than":
            return next_step_id if field_value < match_value else None
        elif operator == "contains":
            return next_step_id if match_value in str(field_value) else None
        elif operator == "exists":
            return next_step_id if field_name in state else None

        return None

    return condition
