#!/usr/bin/env python3
"""
Elicitation Module for Interactive Workflows

This module implements the MCP 2025-06-18 elicitation capability, allowing tools
to interactively request missing information from users. This enables more intelligent
schema operations where the server can guide users through complex workflows.

Key Features:
- Multiple elicitation types (text, choice, confirmation, form)
- Multi-round conversations support
- Timeout handling and validation
- Schema field definition assistance
- Migration preference collection
- Compatibility resolution guidance

MCP 2025-06-18 Compliance:
- Implements elicitation request/response protocol
- Supports structured elicitation with multiple field types
- Provides fallback mechanisms for non-supporting clients
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ElicitationType(Enum):
    """Types of elicitation requests supported."""

    TEXT = "text"
    CHOICE = "choice"
    CONFIRMATION = "confirmation"
    FORM = "form"
    MULTI_FIELD = "multi_field"


class ElicitationPriority(Enum):
    """Priority levels for elicitation requests."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ElicitationField:
    """Represents a single field in an elicitation request."""

    name: str
    type: str
    label: Optional[str] = None
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None
    placeholder: Optional[str] = None


@dataclass
class ElicitationRequest:
    """Represents an elicitation request to the user."""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: ElicitationType = ElicitationType.TEXT
    title: str = "Information Required"
    description: Optional[str] = None
    fields: List[ElicitationField] = field(default_factory=list)
    priority: ElicitationPriority = ElicitationPriority.MEDIUM
    timeout_seconds: int = 300  # 5 minutes default
    allow_multiple: bool = False
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        """Calculate expiration time if not set."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=self.timeout_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol."""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type,
                    "label": f.label or f.name.replace("_", " ").title(),
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "options": f.options,
                    "validation": f.validation,
                    "placeholder": f.placeholder,
                }
                for f in self.fields
            ],
            "priority": self.priority.value,
            "timeout_seconds": self.timeout_seconds,
            "allow_multiple": self.allow_multiple,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def is_expired(self) -> bool:
        """Check if the elicitation request has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class ElicitationResponse:
    """Represents a user's response to an elicitation request."""

    request_id: str
    values: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    complete: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "values": self.values,
            "timestamp": self.timestamp.isoformat(),
            "complete": self.complete,
            "metadata": self.metadata,
        }


class ElicitationManager:
    """Manages elicitation requests and responses."""

    def __init__(self):
        self.pending_requests: Dict[str, ElicitationRequest] = {}
        self.responses: Dict[str, ElicitationResponse] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}

    async def create_request(self, request: ElicitationRequest) -> str:
        """Create a new elicitation request."""
        self.pending_requests[request.id] = request

        # Set up timeout handling
        if request.timeout_seconds > 0:
            self.timeout_tasks[request.id] = asyncio.create_task(
                self._handle_timeout(request.id, request.timeout_seconds)
            )

        logger.info(f"Created elicitation request {request.id}: {request.title}")
        return request.id

    async def submit_response(self, response: ElicitationResponse) -> bool:
        """Submit a response to an elicitation request."""
        if response.request_id not in self.pending_requests:
            logger.warning(f"No pending request found for ID {response.request_id}")
            return False

        request = self.pending_requests[response.request_id]
        if request.is_expired():
            logger.warning(f"Request {response.request_id} has expired")
            return False

        # Validate response
        if not self._validate_response(request, response):
            logger.warning(f"Invalid response for request {response.request_id}")
            return False

        # Store response and clean up
        self.responses[response.request_id] = response
        self._cleanup_request(response.request_id)

        logger.info(f"Received response for elicitation request {response.request_id}")
        return True

    async def wait_for_response(
        self, request_id: str, timeout: Optional[float] = None
    ) -> Optional[ElicitationResponse]:
        """Wait for a response to an elicitation request."""
        if request_id not in self.pending_requests:
            return None

        request = self.pending_requests[request_id]
        effective_timeout = timeout or request.timeout_seconds

        start_time = datetime.utcnow()
        while datetime.utcnow() - start_time < timedelta(seconds=effective_timeout):
            if request_id in self.responses:
                return self.responses[request_id]

            if request.is_expired():
                logger.warning(f"Request {request_id} expired while waiting")
                break

            await asyncio.sleep(0.1)  # Check every 100ms

        return None

    def get_request(self, request_id: str) -> Optional[ElicitationRequest]:
        """Get an elicitation request by ID."""
        return self.pending_requests.get(request_id)

    def get_response(self, request_id: str) -> Optional[ElicitationResponse]:
        """Get a response by request ID."""
        return self.responses.get(request_id)

    def list_pending_requests(self) -> List[ElicitationRequest]:
        """List all pending elicitation requests."""
        return list(self.pending_requests.values())

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending elicitation request."""
        if request_id in self.pending_requests:
            self._cleanup_request(request_id)
            logger.info(f"Cancelled elicitation request {request_id}")
            return True
        return False

    async def _handle_timeout(self, request_id: str, timeout_seconds: int):
        """Handle request timeout."""
        await asyncio.sleep(timeout_seconds)
        if request_id in self.pending_requests:
            logger.warning(f"Elicitation request {request_id} timed out")
            self._cleanup_request(request_id)

    def _cleanup_request(self, request_id: str):
        """Clean up a completed or cancelled request."""
        self.pending_requests.pop(request_id, None)
        if request_id in self.timeout_tasks:
            self.timeout_tasks[request_id].cancel()
            del self.timeout_tasks[request_id]

    def _validate_response(self, request: ElicitationRequest, response: ElicitationResponse) -> bool:
        """Validate a response against the request requirements."""
        # Check required fields
        for req_field in request.fields:
            if req_field.required and req_field.name not in response.values:
                logger.warning(f"Missing required field: {req_field.name}")
                return False

            # Validate field types and constraints
            if req_field.name in response.values:
                value = response.values[req_field.name]
                if req_field.options and value not in req_field.options:
                    logger.warning(f"Invalid option for field {req_field.name}: {value}")
                    return False

                # Additional validation based on field type
                if req_field.type == "email" and "@" not in str(value):
                    logger.warning(f"Invalid email format for field {req_field.name}: {value}")
                    return False

        return True


# Global elicitation manager instance
elicitation_manager = ElicitationManager()


# Helper functions for common elicitation patterns


def create_schema_field_elicitation(
    context: Optional[str] = None, existing_fields: Optional[List[str]] = None
) -> ElicitationRequest:
    """Create an elicitation request for schema field definitions."""
    fields = [
        ElicitationField(
            name="field_name",
            type="text",
            label="Field Name",
            description="Name of the schema field",
            required=True,
            placeholder="e.g., user_id, email, timestamp",
        ),
        ElicitationField(
            name="field_type",
            type="choice",
            label="Field Type",
            description="Data type for the field",
            required=True,
            options=[
                "string",
                "int",
                "long",
                "float",
                "double",
                "boolean",
                "bytes",
                "array",
                "record",
            ],
            default="string",
        ),
        ElicitationField(
            name="nullable",
            type="choice",
            label="Nullable",
            description="Can this field be null?",
            required=True,
            options=["true", "false"],
            default="false",
        ),
        ElicitationField(
            name="default_value",
            type="text",
            label="Default Value",
            description="Default value for the field (optional)",
            required=False,
            placeholder="Leave empty for no default",
        ),
        ElicitationField(
            name="documentation",
            type="text",
            label="Documentation",
            description="Description of what this field represents",
            required=False,
            placeholder="Brief description of the field purpose",
        ),
    ]

    context_info = {"existing_fields": existing_fields or []}
    if context:
        context_info["schema_context"] = context

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Define Schema Field",
        description="Please provide details for the new schema field",
        fields=fields,
        allow_multiple=True,
        context=context_info,
        timeout_seconds=600,  # 10 minutes for schema design
    )


def create_migration_preferences_elicitation(
    source_registry: str, target_registry: str, context: Optional[str] = None
) -> ElicitationRequest:
    """Create an elicitation request for migration preferences."""
    fields = [
        ElicitationField(
            name="preserve_ids",
            type="choice",
            label="Preserve Schema IDs",
            description="Should schema IDs be preserved during migration?",
            required=True,
            options=["true", "false"],
            default="true",
        ),
        ElicitationField(
            name="migrate_all_versions",
            type="choice",
            label="Migrate All Versions",
            description="Migrate all schema versions or just the latest?",
            required=True,
            options=["true", "false"],
            default="false",
        ),
        ElicitationField(
            name="conflict_resolution",
            type="choice",
            label="Conflict Resolution",
            description="How to handle conflicts if schema already exists in target?",
            required=True,
            options=["skip", "overwrite", "merge", "prompt"],
            default="prompt",
        ),
        ElicitationField(
            name="batch_size",
            type="text",
            label="Batch Size",
            description="Number of schemas to migrate in each batch",
            required=False,
            default="10",
            validation={"min": 1, "max": 100},
        ),
        ElicitationField(
            name="dry_run",
            type="choice",
            label="Dry Run",
            description="Perform a dry run first to preview changes?",
            required=True,
            options=["true", "false"],
            default="true",
        ),
    ]

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Migration Preferences",
        description=f"Configure migration from {source_registry} to {target_registry}",
        fields=fields,
        context={
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
        },
        timeout_seconds=300,
    )


def create_compatibility_resolution_elicitation(subject: str, compatibility_errors: List[str]) -> ElicitationRequest:
    """Create an elicitation request for compatibility issue resolution."""
    fields = [
        ElicitationField(
            name="resolution_strategy",
            type="choice",
            label="Resolution Strategy",
            description="How would you like to resolve the compatibility issues?",
            required=True,
            options=[
                "modify_schema",
                "change_compatibility_level",
                "add_default_values",
                "make_fields_optional",
                "skip_registration",
            ],
        ),
        ElicitationField(
            name="compatibility_level",
            type="choice",
            label="New Compatibility Level",
            description="Set a different compatibility level for this subject",
            required=False,
            options=["BACKWARD", "FORWARD", "FULL", "NONE"],
            default="BACKWARD",
        ),
        ElicitationField(
            name="notes",
            type="text",
            label="Notes",
            description="Additional notes about this compatibility decision",
            required=False,
            placeholder="Explain the reasoning for this change",
        ),
    ]

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Resolve Compatibility Issues",
        description=f"Schema for subject '{subject}' has compatibility issues that need resolution",
        fields=fields,
        context={"subject": subject, "compatibility_errors": compatibility_errors},
        timeout_seconds=300,
    )


def create_context_metadata_elicitation(context_name: str) -> ElicitationRequest:
    """Create an elicitation request for context metadata."""
    fields = [
        ElicitationField(
            name="description",
            type="text",
            label="Context Description",
            description="What is this context used for?",
            required=False,
            placeholder="e.g., User service schemas, Payment processing events",
        ),
        ElicitationField(
            name="owner",
            type="text",
            label="Owner",
            description="Team or person responsible for this context",
            required=False,
            placeholder="e.g., data-platform-team",
        ),
        ElicitationField(
            name="environment",
            type="choice",
            label="Environment",
            description="What environment is this context for?",
            required=False,
            options=["development", "staging", "production", "testing"],
            default="development",
        ),
        ElicitationField(
            name="tags",
            type="text",
            label="Tags",
            description="Comma-separated tags for organization",
            required=False,
            placeholder="e.g., microservice, events, user-data",
        ),
    ]

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Context Metadata",
        description=f"Please provide metadata for the new context '{context_name}'",
        fields=fields,
        context={"context_name": context_name},
        timeout_seconds=300,
    )


def create_export_preferences_elicitation(operation_type: str) -> ElicitationRequest:
    """Create an elicitation request for export preferences."""
    fields = [
        ElicitationField(
            name="format",
            type="choice",
            label="Export Format",
            description="Which format would you like for the export?",
            required=True,
            options=["json", "avro_idl", "yaml", "csv"],
            default="json",
        ),
        ElicitationField(
            name="include_metadata",
            type="choice",
            label="Include Metadata",
            description="Include schema metadata in the export?",
            required=True,
            options=["true", "false"],
            default="true",
        ),
        ElicitationField(
            name="include_versions",
            type="choice",
            label="Version Inclusion",
            description="Which schema versions to include?",
            required=True,
            options=["latest", "all", "specific"],
            default="latest",
        ),
        ElicitationField(
            name="compression",
            type="choice",
            label="Compression",
            description="Compress the export file?",
            required=False,
            options=["none", "gzip", "zip"],
            default="none",
        ),
    ]

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Export Preferences",
        description=f"Configure {operation_type} export settings",
        fields=fields,
        context={"operation": operation_type},
        timeout_seconds=300,
    )


def create_migrate_schema_elicitation(
    subject: str,
    source_registry: str,
    target_registry: str,
    schema_exists_in_target: bool = False,
    existing_versions: Optional[List[int]] = None,
    context: Optional[str] = None,
) -> ElicitationRequest:
    """Create an elicitation request for migrate schema preferences."""

    fields = []

    # If schema exists in target, ask about replacement and backup
    if schema_exists_in_target:
        fields.extend(
            [
                ElicitationField(
                    name="replace_existing",
                    type="choice",
                    label="Replace Existing Schema",
                    description=(
                        f"Schema '{subject}' already exists in target registry '{target_registry}'. "
                        "Should it be replaced?"
                    ),
                    required=True,
                    options=["true", "false"],
                    default="false",
                ),
                ElicitationField(
                    name="backup_before_replace",
                    type="choice",
                    label="Backup Before Replace",
                    description="Should existing schema be backed up (exported) before replacement?",
                    required=False,
                    options=["true", "false"],
                    default="true",
                ),
            ]
        )

    # Always ask about ID preservation
    fields.append(
        ElicitationField(
            name="preserve_ids",
            type="choice",
            label="Preserve Schema IDs",
            description="Should schema IDs be preserved during migration? (Requires IMPORT mode on target registry)",
            required=True,
            options=["true", "false"],
            default="true",
        )
    )

    # Always ask about post-migration comparison
    fields.append(
        ElicitationField(
            name="compare_after_migration",
            type="choice",
            label="Compare After Migration",
            description="Should schemas be compared after migration to verify successful transfer?",
            required=True,
            options=["true", "false"],
            default="true",
        )
    )

    # Additional migration preferences
    fields.extend(
        [
            ElicitationField(
                name="migrate_all_versions",
                type="choice",
                label="Migrate All Versions",
                description="Migrate all schema versions or just the latest?",
                required=True,
                options=["true", "false"],
                default="false",
            ),
            ElicitationField(
                name="dry_run",
                type="choice",
                label="Dry Run First",
                description="Perform a dry run to preview changes before actual migration?",
                required=True,
                options=["true", "false"],
                default="true",
            ),
        ]
    )

    # Build description based on whether schema exists
    if schema_exists_in_target:
        description = (
            f"Schema '{subject}' already exists in target registry '{target_registry}' "
            f"with versions {existing_versions}. Configure migration preferences."
        )
    else:
        description = f"Configure migration of schema '{subject}' from '{source_registry}' to '{target_registry}'"

    return ElicitationRequest(
        type=ElicitationType.FORM,
        title="Schema Migration Preferences",
        description=description,
        fields=fields,
        context={
            "subject": subject,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "schema_exists_in_target": schema_exists_in_target,
            "existing_versions": existing_versions,
            "context": context,
        },
        timeout_seconds=300,
    )


# Mock elicitation function for non-supporting clients
async def mock_elicit(request: ElicitationRequest) -> Optional[ElicitationResponse]:
    """
    Mock elicitation function that provides default responses for non-supporting clients.
    This ensures graceful degradation when elicitation is not available.
    """
    logger.info(f"Mock elicitation for request: {request.title}")

    # Generate reasonable defaults based on request type and context
    values = {}

    for req_field in request.fields:
        if req_field.default is not None:
            values[req_field.name] = req_field.default
        elif req_field.type == "choice" and req_field.options:
            values[req_field.name] = req_field.options[0]  # Use first option as default
        elif req_field.type == "text":
            values[req_field.name] = req_field.placeholder or ""
        elif req_field.type == "confirmation":
            values[req_field.name] = "false"  # Conservative default
        else:
            values[req_field.name] = None

    # Override with context-specific intelligent defaults
    if request.context:
        if "schema_context" in request.context:
            # For schema fields, provide sensible defaults
            if "field_type" in values:
                values["field_type"] = "string"
            if "nullable" in values:
                values["nullable"] = "false"

        elif "migration" in request.context:
            # For migration, use safe defaults
            if "preserve_ids" in values:
                values["preserve_ids"] = "true"
            if "dry_run" in values:
                values["dry_run"] = "true"

    return ElicitationResponse(
        request_id=request.id,
        values=values,
        complete=True,
        metadata={"source": "mock_fallback", "auto_generated": True},
    )


# Integration function to check if elicitation is supported
def is_elicitation_supported() -> bool:
    """
    Check if the current MCP client supports elicitation.
    This can be extended to check client capabilities.
    """
    # For now, assume elicitation is supported
    # In a real implementation, this would check the client's declared capabilities
    return True


async def elicit_with_fallback(
    request: ElicitationRequest,
) -> Optional[ElicitationResponse]:
    """
    Attempt elicitation with fallback to defaults if not supported.
    """
    if is_elicitation_supported():
        # In a real implementation, this would use the MCP elicitation protocol
        # For now, we'll simulate with the mock function
        logger.info(f"Elicitation not yet implemented, using fallback for: {request.title}")
        return await mock_elicit(request)
    else:
        logger.info(f"Client doesn't support elicitation, using defaults for: {request.title}")
        return await mock_elicit(request)
