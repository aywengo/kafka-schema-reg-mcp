"""
MCP Integration for Bulk Operations Wizard

This module provides MCP tools for the Bulk Operations Wizard,
allowing it to be used through the Message Control Protocol.
"""

from typing import Dict, Any, List
from mcp.types import Tool
from bulk_operations_wizard import BulkOperationsWizard, BulkOperationType


def create_bulk_operations_tools(wizard: BulkOperationsWizard) -> List[Tool]:
    """Create MCP tools for bulk operations wizard"""

    tools = []

    # Tool: Start Bulk Operations Wizard
    tools.append(
        Tool(
            name="bulk_operations_wizard",
            description=(
                "Start the interactive Bulk Operations Wizard for admin tasks. "
                "Guides through safe execution of operations across multiple schemas. "
                "Supports schema updates, migrations, cleanup, and configuration changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "enum": ["schema_update", "migration", "cleanup", "configuration"],
                        "description": "Pre-select operation type (optional)",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run in preview mode without making changes",
                    },
                },
            },
        )
    )

    # Tool: Bulk Schema Update
    tools.append(
        Tool(
            name="bulk_schema_update",
            description=(
                "Update schemas in bulk with interactive guidance. "
                "Supports compatibility settings, naming conventions, and metadata updates. "
                "Pattern matching supported (e.g., test-*, deprecated-*)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Schema name pattern (e.g., 'test-*', 'prod-*')"},
                    "update_type": {
                        "type": "string",
                        "enum": ["compatibility", "naming", "metadata"],
                        "description": "Type of update to perform",
                    },
                    "dry_run": {"type": "boolean", "default": True, "description": "Preview changes without applying"},
                    "batch_size": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of schemas to process at once",
                    },
                },
                "required": ["update_type"],
            },
        )
    )

    # Tool: Bulk Schema Cleanup
    tools.append(
        Tool(
            name="bulk_schema_cleanup",
            description=(
                "Clean up schemas in bulk with safety checks. "
                "Detects active consumers and provides options for handling them. "
                "Supports test schema cleanup, deprecated schema removal, and version purging."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cleanup_type": {
                        "type": "string",
                        "enum": ["test", "deprecated", "old_versions", "pattern"],
                        "description": "Type of cleanup to perform",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Custom pattern for cleanup (if cleanup_type is 'pattern')",
                    },
                    "keep_versions": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of recent versions to keep",
                    },
                    "check_consumers": {
                        "type": "boolean",
                        "default": True,
                        "description": "Check for active consumers before cleanup",
                    },
                    "force": {
                        "type": "boolean",
                        "default": False,
                        "description": "Force cleanup even with active consumers (dangerous)",
                    },
                },
                "required": ["cleanup_type"],
            },
        )
    )

    # Tool: Bulk Schema Migration
    tools.append(
        Tool(
            name="bulk_schema_migration",
            description=(
                "Migrate schemas between contexts or registries. "
                "Supports pattern-based selection and maintains schema IDs. "
                "Includes preview and rollback capabilities."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_context": {"type": "string", "description": "Source context (default: current context)"},
                    "target_context": {"type": "string", "description": "Target context for migration"},
                    "source_registry": {
                        "type": "string",
                        "description": "Source registry (for cross-registry migration)",
                    },
                    "target_registry": {
                        "type": "string",
                        "description": "Target registry (for cross-registry migration)",
                    },
                    "schema_pattern": {"type": "string", "description": "Pattern to match schemas for migration"},
                    "preserve_ids": {
                        "type": "boolean",
                        "default": True,
                        "description": "Preserve schema IDs during migration",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "Preview migration without executing",
                    },
                },
            },
        )
    )

    # Tool: Bulk Configuration Update
    tools.append(
        Tool(
            name="bulk_configuration_update",
            description=(
                "Update configuration settings across multiple schemas or contexts. "
                "Supports security policies, retention settings, and access controls."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_type": {
                        "type": "string",
                        "enum": ["security", "retention", "mode", "compliance"],
                        "description": "Type of configuration to update",
                    },
                    "target_type": {
                        "type": "string",
                        "enum": ["schemas", "contexts", "global"],
                        "description": "What to apply configuration to",
                    },
                    "pattern": {"type": "string", "description": "Pattern to match targets (for schemas/contexts)"},
                    "settings": {"type": "object", "description": "Configuration settings to apply"},
                    "dry_run": {"type": "boolean", "default": True, "description": "Preview changes without applying"},
                },
                "required": ["config_type", "target_type"],
            },
        )
    )

    # Tool: Get Bulk Operation Status
    tools.append(
        Tool(
            name="get_bulk_operation_status",
            description=(
                "Get the status of a running bulk operation. "
                "Shows progress, estimated time remaining, and any errors."
            ),
            inputSchema={
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "Task ID returned by bulk operation"}},
                "required": ["task_id"],
            },
        )
    )

    # Tool: Cancel Bulk Operation
    tools.append(
        Tool(
            name="cancel_bulk_operation",
            description=(
                "Cancel a running bulk operation. " "Will attempt to rollback any changes made if rollback is enabled."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID of operation to cancel"},
                    "rollback": {"type": "boolean", "default": True, "description": "Attempt to rollback changes"},
                },
                "required": ["task_id"],
            },
        )
    )

    # Tool: Preview Bulk Operation
    tools.append(
        Tool(
            name="preview_bulk_operation",
            description=(
                "Preview a bulk operation without executing it. "
                "Shows affected items, warnings, consumer impact, and estimated duration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "enum": ["schema_update", "migration", "cleanup", "configuration"],
                        "description": "Type of operation to preview",
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of items to operate on",
                    },
                    "parameters": {"type": "object", "description": "Operation-specific parameters"},
                },
                "required": ["operation_type", "items"],
            },
        )
    )

    return tools


async def handle_bulk_operations_tool(
    wizard: BulkOperationsWizard, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle bulk operations tool calls"""

    if tool_name == "bulk_operations_wizard":
        # Start the main wizard
        operation_type = arguments.get("operation_type")
        if operation_type:
            operation_type = BulkOperationType(operation_type)

        return await wizard.start_wizard(operation_type)

    elif tool_name == "bulk_schema_update":
        # Direct schema update with parameters
        # In real implementation, would pass parameters to wizard
        return await wizard.start_wizard(BulkOperationType.SCHEMA_UPDATE)

    elif tool_name == "bulk_schema_cleanup":
        # Direct cleanup with parameters
        return await wizard.start_wizard(BulkOperationType.CLEANUP)

    elif tool_name == "bulk_schema_migration":
        # Direct migration with parameters
        return await wizard.start_wizard(BulkOperationType.MIGRATION)

    elif tool_name == "bulk_configuration_update":
        # Direct configuration update
        return await wizard.start_wizard(BulkOperationType.CONFIGURATION)

    elif tool_name == "get_bulk_operation_status":
        # Get task status
        task_id = arguments["task_id"]
        return await wizard.task_manager.get_task_status(task_id)

    elif tool_name == "cancel_bulk_operation":
        # Cancel operation
        task_id = arguments["task_id"]
        rollback = arguments.get("rollback", True)

        # In real implementation, would cancel the task
        return {"status": "cancelled", "task_id": task_id, "rollback": rollback}

    elif tool_name == "preview_bulk_operation":
        # Preview operation
        operation_type = BulkOperationType(arguments["operation_type"])
        items = arguments["items"]
        params = arguments.get("parameters", {})

        preview = await wizard._generate_preview(operation_type, items, params)

        return {
            "preview": {
                "affected_items": preview.affected_items,
                "total_count": preview.total_count,
                "changes_summary": preview.changes_summary,
                "estimated_duration": preview.estimated_duration,
                "warnings": preview.warnings,
                "consumer_impact": preview.consumer_impact,
            }
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# Export functions
__all__ = ["create_bulk_operations_tools", "handle_bulk_operations_tool"]
