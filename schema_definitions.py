#!/usr/bin/env python3
"""
Schema Definitions for Kafka Schema Registry MCP Server

Comprehensive JSON Schema definitions for all 48 tools to support
structured tool output per MCP 2025-06-18 specification.

Categories:
- Base schemas (error/success responses, common fields)
- Schema operations (register, get, versions, compatibility)
- Registry management (info, connection, status)
- Configuration management (global/subject config)
- Mode management (registry/subject modes)
- Context operations (list, create, delete)
- Export operations (schema, subject, context, global)
- Migration operations (schema, context, status)
- Statistics operations (counts, registry stats)
- Batch operations (context clearing)
- Task management (status, progress, control)
- Elicitation management (requests, status)
"""

from typing import Any, Dict

# ===== BASE SCHEMAS =====

# Common metadata fields used across responses
METADATA_FIELDS = {
    "registry_mode": {
        "type": "string",
        "enum": ["single", "multi"],
        "description": "Operating mode of the registry system",
    },
    "mcp_protocol_version": {
        "type": "string",
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "description": "MCP protocol version",
    },
    "timestamp": {
        "type": "string",
        "format": "date-time",
        "description": "Timestamp of the response",
    },
}

# Standard error response schema
ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {
            "type": "string",
            "description": "Error message describing what went wrong",
        },
        "error_code": {"type": "string", "description": "Machine-readable error code"},
        "details": {"type": "object", "description": "Additional error details"},
        **METADATA_FIELDS,
    },
    "required": ["error"],
    "additionalProperties": True,
}

# Standard success response schema
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "Success message"},
        "data": {"type": "object", "description": "Additional response data"},
        **METADATA_FIELDS,
    },
    "required": ["message"],
    "additionalProperties": True,
}

# ===== SCHEMA OPERATION SCHEMAS =====

# Schema registration response
REGISTER_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique schema ID assigned by registry",
        },
        "subject": {"type": "string", "description": "Subject name for the schema"},
        "version": {
            "type": "integer",
            "minimum": 1,
            "description": "Version number of the registered schema",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["id"],
    "additionalProperties": True,
}

# Get schema response
GET_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Subject name"},
        "version": {"type": "integer", "minimum": 1, "description": "Schema version"},
        "id": {"type": "integer", "minimum": 1, "description": "Unique schema ID"},
        "schema": {
            "type": "object",
            "description": "The schema definition as JSON object",
        },
        "schemaType": {
            "type": "string",
            "enum": ["AVRO", "JSON", "PROTOBUF"],
            "description": "Type of schema",
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "subject": {"type": "string"},
                    "version": {"type": "integer", "minimum": 1},
                },
                "required": ["name", "subject", "version"],
            },
            "description": "Schema references to other schemas",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["subject", "version", "id", "schema"],
    "additionalProperties": True,
}

# Schema versions list response
GET_SCHEMA_VERSIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {
            "type": "string",
            "description": "Subject name for which versions are listed",
        },
        "versions": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1},
            "description": "List of available schema versions",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        "_links": {
            "type": "object",
            "description": "Navigation links to related resources",
            "additionalProperties": True,
        },
        **METADATA_FIELDS,
    },
    "required": ["subject", "versions"],
    "additionalProperties": True,
}

# Compatibility check response
CHECK_COMPATIBILITY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_compatible": {
            "type": "boolean",
            "description": "Whether the schema is compatible",
        },
        "compatibility_level": {
            "type": "string",
            "enum": [
                "BACKWARD",
                "FORWARD",
                "FULL",
                "NONE",
                "BACKWARD_TRANSITIVE",
                "FORWARD_TRANSITIVE",
                "FULL_TRANSITIVE",
            ],
            "description": "Compatibility level used for check",
        },
        "messages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Detailed compatibility messages",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["is_compatible"],
    "additionalProperties": True,
}

# Subject list response
LIST_SUBJECTS_SCHEMA = {
    "type": "object",
    "properties": {
        "subjects": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of subject names",
        },
        "context": {
            "type": ["string", "null"],
            "description": "Schema context filter used",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        "_links": {
            "type": "object",
            "description": "Navigation links to related resources",
            "additionalProperties": True,
        },
        **METADATA_FIELDS,
    },
    "required": ["subjects"],
    "additionalProperties": True,
}

# ===== REGISTRY MANAGEMENT SCHEMAS =====

# Registry information schema
REGISTRY_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Registry name"},
        "url": {"type": "string", "format": "uri", "description": "Registry URL"},
        "status": {
            "type": "string",
            "enum": ["connected", "disconnected", "error", "unknown"],
            "description": "Connection status",
        },
        "auth_type": {
            "type": "string",
            "enum": ["none", "basic", "oauth", "ssl"],
            "description": "Authentication type",
        },
        "readonly": {
            "type": "boolean",
            "description": "Whether registry is in readonly mode",
        },
        "version": {"type": "string", "description": "Schema Registry server version"},
        "capabilities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Server capabilities",
        },
        **METADATA_FIELDS,
    },
    "required": ["name", "url"],
    "additionalProperties": True,
}

# List registries response
LIST_REGISTRIES_SCHEMA = {
    "type": "array",
    "items": REGISTRY_INFO_SCHEMA,
    "description": "List of registry configurations",
}

# Test connection response
TEST_CONNECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["connected", "disconnected", "error"],
            "description": "Connection test result",
        },
        "response_time_ms": {
            "type": "number",
            "minimum": 0,
            "description": "Response time in milliseconds",
        },
        "server_version": {
            "type": "string",
            "description": "Schema Registry server version",
        },
        "error": {
            "type": "string",
            "description": "Error message if connection failed",
        },
        "metadata": {"type": "object", "description": "Additional server metadata"},
        **METADATA_FIELDS,
    },
    "required": ["status"],
    "additionalProperties": True,
}

# Test all registries response
TEST_ALL_REGISTRIES_SCHEMA = {
    "type": "object",
    "properties": {
        "registry_tests": {
            "type": "object",
            "patternProperties": {".*": TEST_CONNECTION_SCHEMA},
            "description": "Test results for each registry",
        },
        "total_registries": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of registries tested",
        },
        "connected": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of successful connections",
        },
        "failed": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of failed connections",
        },
        **METADATA_FIELDS,
    },
    "required": ["registry_tests", "total_registries", "connected", "failed"],
    "additionalProperties": True,
}

# ===== CONFIGURATION SCHEMAS =====

# Configuration response (global and subject)
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "compatibility": {
            "type": "string",
            "enum": [
                "BACKWARD",
                "FORWARD",
                "FULL",
                "NONE",
                "BACKWARD_TRANSITIVE",
                "FORWARD_TRANSITIVE",
                "FULL_TRANSITIVE",
            ],
            "description": "Compatibility level",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["compatibility"],
    "additionalProperties": True,
}

# ===== MODE MANAGEMENT SCHEMAS =====

# Mode response (global and subject)
MODE_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["IMPORT", "READONLY", "READWRITE"],
            "description": "Current mode",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["mode"],
    "additionalProperties": True,
}

# ===== CONTEXT SCHEMAS =====

# Context list response
LIST_CONTEXTS_SCHEMA = {
    "type": "object",
    "properties": {
        "contexts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of context names",
        },
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        "_links": {
            "type": "object",
            "description": "Navigation links to related resources",
            "additionalProperties": True,
        },
        **METADATA_FIELDS,
    },
    "required": ["contexts"],
    "additionalProperties": True,
}

# Context operation response (create/delete)
CONTEXT_OPERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "Operation result message"},
        "context": {"type": "string", "description": "Context name"},
        "registry": {
            "type": "string",
            "description": "Registry name (multi-registry mode)",
        },
        **METADATA_FIELDS,
    },
    "required": ["message"],
    "additionalProperties": True,
}

# ===== EXPORT SCHEMAS =====

# Schema export response
EXPORT_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Subject name"},
        "version": {"type": "integer", "minimum": 1, "description": "Schema version"},
        "format": {
            "type": "string",
            "enum": ["json", "avro-idl"],
            "description": "Export format",
        },
        "content": {"type": "string", "description": "Exported schema content"},
        "metadata": {"type": "object", "description": "Schema metadata"},
        **METADATA_FIELDS,
    },
    "required": ["subject", "version", "format", "content"],
    "additionalProperties": True,
}

# Subject export response
EXPORT_SUBJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Subject name"},
        "versions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "version": {"type": "integer", "minimum": 1},
                    "id": {"type": "integer", "minimum": 1},
                    "schema": {"type": "object"},
                    "schemaType": {"type": "string"},
                },
                "required": ["version", "id", "schema"],
            },
            "description": "All versions of the subject",
        },
        "config": {"type": "object", "description": "Subject configuration"},
        "export_metadata": {
            "type": "object",
            "properties": {
                "exported_at": {"type": "string", "format": "date-time"},
                "total_versions": {"type": "integer", "minimum": 0},
                "include_config": {"type": "boolean"},
            },
        },
        **METADATA_FIELDS,
    },
    "required": ["subject", "versions"],
    "additionalProperties": True,
}

# ===== MIGRATION SCHEMAS =====

# Migration response
MIGRATE_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "migration_id": {
            "type": "string",
            "description": "Unique migration identifier",
        },
        "status": {
            "type": "string",
            "enum": ["pending", "running", "completed", "failed"],
            "description": "Migration status",
        },
        "source_registry": {"type": "string", "description": "Source registry name"},
        "target_registry": {"type": "string", "description": "Target registry name"},
        "subject": {"type": "string", "description": "Subject being migrated"},
        "dry_run": {"type": "boolean", "description": "Whether this was a dry run"},
        "results": {
            "type": "object",
            "properties": {
                "migrated_versions": {"type": "array", "items": {"type": "integer"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        },
        **METADATA_FIELDS,
    },
    "required": ["status", "source_registry", "target_registry"],
    "additionalProperties": True,
}

# ===== STATISTICS SCHEMAS =====

# Count response
COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer", "minimum": 0, "description": "Count result"},
        "scope": {
            "type": "string",
            "description": "What was counted (contexts, schemas, versions)",
        },
        "context": {
            "type": "string",
            "description": "Context name if scoped to context",
        },
        "registry": {"type": "string", "description": "Registry name"},
        **METADATA_FIELDS,
    },
    "required": ["count", "scope"],
    "additionalProperties": True,
}

# Registry statistics response
REGISTRY_STATISTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "registry": {"type": "string", "description": "Registry name"},
        "total_contexts": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of contexts",
        },
        "total_subjects": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of subjects",
        },
        "total_schemas": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of schema versions",
        },
        "contexts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "subject_count": {"type": "integer", "minimum": 0},
                    "schema_count": {"type": "integer", "minimum": 0},
                },
                "required": ["name", "subject_count", "schema_count"],
            },
            "description": "Per-context statistics",
        },
        "generated_at": {
            "type": "string",
            "format": "date-time",
            "description": "When statistics were generated",
        },
        **METADATA_FIELDS,
    },
    "required": ["total_contexts", "total_subjects", "total_schemas"],
    "additionalProperties": True,
}

# ===== TASK MANAGEMENT SCHEMAS =====

# Task status response
TASK_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string", "description": "Unique task identifier"},
        "status": {
            "type": "string",
            "enum": ["pending", "running", "completed", "failed", "cancelled"],
            "description": "Current task status",
        },
        "progress": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Task progress percentage",
        },
        "started_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Task start timestamp",
        },
        "completed_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Task completion timestamp",
        },
        "error": {
            "type": ["string", "null"],
            "description": "Error message if task failed",
        },
        "result": {"type": ["object", "null"], "description": "Task result data"},
        "metadata": {
            "type": ["object", "null"],
            "description": "Additional task metadata",
        },
    },
    "required": ["task_id", "status", "progress"],
    "additionalProperties": True,
}

# Task list response
TASK_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": TASK_STATUS_SCHEMA,
            "description": "List of tasks",
        },
        "total_tasks": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of tasks",
        },
        "active_tasks": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of active tasks",
        },
        "filter": {"type": "string", "description": "Filter applied to task list"},
    },
    "required": ["tasks", "total_tasks", "active_tasks"],
    "additionalProperties": True,
}

# ===== BATCH OPERATION SCHEMAS =====

# Batch operation response
BATCH_OPERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "description": "Type of batch operation"},
        "dry_run": {"type": "boolean", "description": "Whether this was a dry run"},
        "total_items": {
            "type": "integer",
            "minimum": 0,
            "description": "Total items processed",
        },
        "successful": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of successful operations",
        },
        "failed": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of failed operations",
        },
        "errors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Error messages from failed operations",
        },
        "details": {"type": "object", "description": "Detailed operation results"},
        **METADATA_FIELDS,
    },
    "required": ["operation", "dry_run", "total_items", "successful", "failed"],
    "additionalProperties": True,
}

# ===== ELICITATION MANAGEMENT SCHEMAS =====

# Elicitation request list response
ELICITATION_REQUESTS_SCHEMA = {
    "type": "object",
    "properties": {
        "pending_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Request ID"},
                    "title": {"type": "string", "description": "Request title"},
                    "type": {"type": "string", "description": "Request type"},
                    "priority": {"type": "string", "description": "Request priority"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "expires_at": {"type": ["string", "null"], "format": "date-time"},
                    "expired": {"type": "boolean"},
                },
                "required": ["id", "title", "type", "priority", "created_at", "expired"],
            },
        },
        "total_pending": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of pending requests",
        },
        "elicitation_supported": {
            "type": "boolean",
            "description": "Whether elicitation is supported",
        },
        **METADATA_FIELDS,
    },
    "required": ["pending_requests", "total_pending", "elicitation_supported"],
    "additionalProperties": True,
}

# Elicitation status response
ELICITATION_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "elicitation_supported": {
            "type": "boolean",
            "description": "Whether elicitation is supported",
        },
        "total_pending_requests": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of pending requests",
        },
        "request_details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Request ID"},
                    "title": {"type": "string", "description": "Request title"},
                    "type": {"type": "string", "description": "Request type"},
                    "priority": {"type": "string", "description": "Request priority"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "expires_at": {"type": ["string", "null"], "format": "date-time"},
                    "expired": {"type": "boolean"},
                },
                "required": ["id", "title", "type", "priority", "created_at", "expired"],
            },
        },
        **METADATA_FIELDS,
    },
    "required": ["elicitation_supported", "total_pending_requests", "request_details"],
    "additionalProperties": True,
}

# ===== SCHEMA REGISTRY =====

# Master registry mapping tool names to their output schemas
TOOL_OUTPUT_SCHEMAS = {
    # Schema Operations
    "register_schema": REGISTER_SCHEMA_SCHEMA,
    "get_schema": GET_SCHEMA_SCHEMA,
    "get_schema_versions": GET_SCHEMA_VERSIONS_SCHEMA,
    "check_compatibility": CHECK_COMPATIBILITY_SCHEMA,
    "list_subjects": LIST_SUBJECTS_SCHEMA,
    # Registry Management
    "list_registries": LIST_REGISTRIES_SCHEMA,
    "get_registry_info": REGISTRY_INFO_SCHEMA,
    "test_registry_connection": TEST_CONNECTION_SCHEMA,
    "test_all_registries": TEST_ALL_REGISTRIES_SCHEMA,
    # Configuration Management
    "get_global_config": CONFIG_SCHEMA,
    "update_global_config": CONFIG_SCHEMA,
    "get_subject_config": CONFIG_SCHEMA,
    "update_subject_config": CONFIG_SCHEMA,
    # Mode Management
    "get_mode": MODE_SCHEMA,
    "update_mode": MODE_SCHEMA,
    "get_subject_mode": MODE_SCHEMA,
    "update_subject_mode": MODE_SCHEMA,
    # Context Operations
    "list_contexts": LIST_CONTEXTS_SCHEMA,
    "create_context": CONTEXT_OPERATION_SCHEMA,
    "delete_context": CONTEXT_OPERATION_SCHEMA,
    "delete_subject": {
        "type": "array",
        "items": {"type": "integer"},
    },  # Returns list of deleted versions
    # Export Operations
    "export_schema": EXPORT_SCHEMA_SCHEMA,
    "export_subject": EXPORT_SUBJECT_SCHEMA,
    "export_context": {
        "type": "object",
        "additionalProperties": True,
    },  # Complex export structure
    "export_global": {
        "type": "object",
        "additionalProperties": True,
    },  # Complex export structure
    # Migration Operations
    "migrate_schema": MIGRATE_SCHEMA_SCHEMA,
    "migrate_context": MIGRATE_SCHEMA_SCHEMA,  # Similar structure
    "confirm_migration_without_ids": MIGRATE_SCHEMA_SCHEMA,  # Similar structure to migrate_schema
    "list_migrations": {
        "type": "array",
        "items": TASK_STATUS_SCHEMA,
        "description": "List of migration tasks",
    },
    "get_migration_status": MIGRATE_SCHEMA_SCHEMA,
    # Statistics Operations
    "count_contexts": COUNT_SCHEMA,
    "count_schemas": COUNT_SCHEMA,
    "count_schema_versions": COUNT_SCHEMA,
    "get_registry_statistics": REGISTRY_STATISTICS_SCHEMA,
    # Batch Operations
    "clear_context_batch": BATCH_OPERATION_SCHEMA,
    "clear_multiple_contexts_batch": BATCH_OPERATION_SCHEMA,
    # Task Management
    "get_task_status": TASK_STATUS_SCHEMA,
    "get_task_progress": TASK_STATUS_SCHEMA,
    "list_active_tasks": TASK_LIST_SCHEMA,
    "cancel_task": SUCCESS_RESPONSE_SCHEMA,
    "list_statistics_tasks": TASK_LIST_SCHEMA,
    "get_statistics_task_progress": TASK_STATUS_SCHEMA,
    # Elicitation Management
    "list_elicitation_requests": ELICITATION_REQUESTS_SCHEMA,
    "get_elicitation_request": {"type": "object", "additionalProperties": True},  # Complex structure
    "cancel_elicitation_request": SUCCESS_RESPONSE_SCHEMA,
    "get_elicitation_status": ELICITATION_STATUS_SCHEMA,
    "submit_elicitation_response": SUCCESS_RESPONSE_SCHEMA,
    # Utility Tools
    "set_default_registry": SUCCESS_RESPONSE_SCHEMA,
    "get_default_registry": REGISTRY_INFO_SCHEMA,
    "check_readonly_mode": {
        "type": "object",
        "properties": {"readonly": {"type": "boolean"}},
    },
    "get_oauth_scopes_info_tool": {"type": "object", "additionalProperties": True},
    "get_operation_info_tool": {"type": "object", "additionalProperties": True},
    "get_mcp_compliance_status_tool": {"type": "object", "additionalProperties": True},
}


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """
    Get the output schema for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        JSON Schema definition for the tool's output
    """
    return TOOL_OUTPUT_SCHEMAS.get(tool_name, {"type": "object", "additionalProperties": True})


def get_all_schemas() -> Dict[str, Any]:
    """
    Get all tool output schemas.

    Returns:
        Dictionary mapping tool names to their schemas
    """
    return TOOL_OUTPUT_SCHEMAS.copy()


# Export commonly used schemas
__all__ = [
    "TOOL_OUTPUT_SCHEMAS",
    "ERROR_RESPONSE_SCHEMA",
    "SUCCESS_RESPONSE_SCHEMA",
    "get_tool_schema",
    "get_all_schemas",
]
