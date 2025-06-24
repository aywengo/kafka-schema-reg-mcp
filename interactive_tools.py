#!/usr/bin/env python3
"""
Interactive Tools with Elicitation Support

This module provides elicitation-enabled versions of high-priority MCP tools
that can interactively request missing information from users. These tools
implement the patterns described in issue #37 for interactive workflows.

Priority Tools for Elicitation:
1. register_schema_interactive - Schema field definitions
2. migrate_context_interactive - Migration preferences
3. check_compatibility_interactive - Resolution options
4. create_context_interactive - Context metadata
5. export_global_interactive - Export format preferences

Each tool follows the pattern:
- Check for missing/incomplete information
- Create appropriate elicitation request
- Wait for user response with timeout
- Process response and continue with operation
- Provide graceful fallback for non-supporting clients
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from elicitation import (
    ElicitationRequest,
    ElicitationResponse,
    create_compatibility_resolution_elicitation,
    create_context_metadata_elicitation,
    create_export_preferences_elicitation,
    create_migration_preferences_elicitation,
    create_schema_field_elicitation,
    elicit_with_fallback,
    elicitation_manager,
)
from schema_validation import create_error_response, create_success_response

logger = logging.getLogger(__name__)


async def register_schema_interactive(
    subject: str,
    schema_definition: Optional[Dict] = None,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
    # Core tool dependencies injected
    register_schema_tool=None,
    registry_manager=None,
    registry_mode=None,
    auth=None,
    headers=None,
    schema_registry_url=None,
) -> Dict[str, Any]:
    """
    Interactive schema registration with elicitation for missing field definitions.

    When schema_definition is incomplete or missing fields, this tool will
    elicit the required information from the user interactively.
    """
    try:
        # Check if schema definition is complete
        needs_elicitation = False
        missing_info = []

        if not schema_definition:
            needs_elicitation = True
            missing_info.append("Complete schema definition required")
        elif schema_type == "AVRO":
            # Check for missing Avro schema fields
            if not schema_definition.get("fields"):
                needs_elicitation = True
                missing_info.append("Schema fields definition required")
            elif len(schema_definition.get("fields", [])) == 0:
                needs_elicitation = True
                missing_info.append("At least one field must be defined")
            else:
                # Check if fields are properly defined
                for field in schema_definition.get("fields", []):
                    if (
                        not isinstance(field, dict)
                        or not field.get("name")
                        or not field.get("type")
                    ):
                        needs_elicitation = True
                        missing_info.append("Field definitions are incomplete")
                        break

        if needs_elicitation:
            logger.info(
                f"Schema registration for '{subject}' needs additional information: {missing_info}"
            )

            # Create elicitation request for schema fields
            existing_fields = []
            if schema_definition and schema_definition.get("fields"):
                existing_fields = [
                    f.get("name", "")
                    for f in schema_definition["fields"]
                    if f.get("name")
                ]

            elicitation_request = create_schema_field_elicitation(
                context=context, existing_fields=existing_fields
            )

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Build schema from elicited information
                schema_definition = await _build_schema_from_elicitation(
                    response.values, schema_definition, schema_type
                )

                logger.info(
                    f"Built schema definition from elicitation: {len(schema_definition.get('fields', []))} fields"
                )
            else:
                return create_error_response(
                    "Unable to obtain complete schema definition",
                    details={
                        "missing_info": missing_info,
                        "elicitation_status": (
                            "failed" if response is None else "incomplete"
                        ),
                        "suggestion": "Please provide a complete schema definition with field specifications",
                    },
                    error_code="INCOMPLETE_SCHEMA_DEFINITION",
                )

        # Now proceed with the actual schema registration
        result = register_schema_tool(
            subject=subject,
            schema_definition=schema_definition,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            schema_type=schema_type,
            context=context,
            registry=registry,
            auth=auth,
            headers=headers,
            schema_registry_url=schema_registry_url,
        )

        # Add elicitation metadata to successful result
        if isinstance(result, dict) and "error" not in result:
            result["elicitation_used"] = needs_elicitation
            if needs_elicitation:
                result["elicited_fields"] = (
                    list(response.values.keys()) if response else []
                )

        return result

    except Exception as e:
        logger.error(f"Error in interactive schema registration: {str(e)}")
        return create_error_response(
            f"Interactive schema registration failed: {str(e)}",
            error_code="INTERACTIVE_REGISTRATION_ERROR",
        )


async def migrate_context_interactive(
    source_registry: str,
    target_registry: str,
    context: Optional[str] = None,
    target_context: Optional[str] = None,
    preserve_ids: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    migrate_all_versions: Optional[bool] = None,
    # Core tool dependencies injected
    migrate_context_tool=None,
    registry_manager=None,
    registry_mode=None,
) -> Dict[str, Any]:
    """
    Interactive context migration with elicitation for missing preferences.

    When migration preferences are not specified, this tool will elicit
    the required configuration from the user.
    """
    try:
        # Check if migration preferences are complete
        needs_elicitation = False
        missing_preferences = []

        if preserve_ids is None:
            needs_elicitation = True
            missing_preferences.append("preserve_ids")

        if dry_run is None:
            needs_elicitation = True
            missing_preferences.append("dry_run")

        if migrate_all_versions is None:
            needs_elicitation = True
            missing_preferences.append("migrate_all_versions")

        if needs_elicitation:
            logger.info(
                f"Context migration from {source_registry} to {target_registry} needs preferences: {missing_preferences}"
            )

            # Create elicitation request for migration preferences
            elicitation_request = create_migration_preferences_elicitation(
                source_registry=source_registry,
                target_registry=target_registry,
                context=context,
            )

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Apply elicited preferences
                if preserve_ids is None:
                    preserve_ids = (
                        response.values.get("preserve_ids", "true").lower() == "true"
                    )
                if dry_run is None:
                    dry_run = response.values.get("dry_run", "true").lower() == "true"
                if migrate_all_versions is None:
                    migrate_all_versions = (
                        response.values.get("migrate_all_versions", "false").lower()
                        == "true"
                    )

                logger.info(
                    f"Applied migration preferences from elicitation: preserve_ids={preserve_ids}, dry_run={dry_run}, migrate_all_versions={migrate_all_versions}"
                )
            else:
                return create_error_response(
                    "Unable to obtain migration preferences",
                    details={
                        "missing_preferences": missing_preferences,
                        "elicitation_status": (
                            "failed" if response is None else "incomplete"
                        ),
                        "suggestion": "Please specify migration preferences or enable elicitation support",
                    },
                    error_code="INCOMPLETE_MIGRATION_PREFERENCES",
                )

        # Now proceed with the actual context migration
        result = await migrate_context_tool(
            source_registry=source_registry,
            target_registry=target_registry,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            context=context,
            target_context=target_context,
            preserve_ids=preserve_ids,
            dry_run=dry_run,
            migrate_all_versions=migrate_all_versions,
        )

        # Add elicitation metadata to successful result
        if isinstance(result, dict) and "error" not in result:
            result["elicitation_used"] = needs_elicitation
            if needs_elicitation:
                result["elicited_preferences"] = {
                    "preserve_ids": preserve_ids,
                    "dry_run": dry_run,
                    "migrate_all_versions": migrate_all_versions,
                }

        return result

    except Exception as e:
        logger.error(f"Error in interactive context migration: {str(e)}")
        return create_error_response(
            f"Interactive context migration failed: {str(e)}",
            error_code="INTERACTIVE_MIGRATION_ERROR",
        )


async def check_compatibility_interactive(
    subject: str,
    schema_definition: Dict,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
    # Core tool dependencies injected
    check_compatibility_tool=None,
    registry_manager=None,
    registry_mode=None,
    auth=None,
    headers=None,
    schema_registry_url=None,
) -> Dict[str, Any]:
    """
    Interactive compatibility checking with elicitation for resolution options.

    When compatibility issues are found, this tool will elicit resolution
    preferences from the user.
    """
    try:
        # First, perform the standard compatibility check
        compatibility_result = check_compatibility_tool(
            subject=subject,
            schema_definition=schema_definition,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            schema_type=schema_type,
            context=context,
            registry=registry,
            auth=auth,
            headers=headers,
            schema_registry_url=schema_registry_url,
        )

        # Check if there are compatibility issues
        if isinstance(compatibility_result, dict):
            is_compatible = compatibility_result.get("compatible", False)
            compatibility_errors = compatibility_result.get("messages", [])

            if not is_compatible and compatibility_errors:
                logger.info(
                    f"Compatibility issues found for subject '{subject}': {compatibility_errors}"
                )

                # Create elicitation request for resolution strategy
                elicitation_request = create_compatibility_resolution_elicitation(
                    subject=subject, compatibility_errors=compatibility_errors
                )

                # Store the request for processing
                await elicitation_manager.create_request(elicitation_request)

                # Attempt elicitation with fallback
                response = await elicit_with_fallback(elicitation_request)

                if response and response.complete:
                    # Add resolution guidance to the result
                    compatibility_result["resolution_guidance"] = {
                        "strategy": response.values.get("resolution_strategy"),
                        "compatibility_level": response.values.get(
                            "compatibility_level"
                        ),
                        "notes": response.values.get("notes"),
                        "elicitation_used": True,
                    }

                    logger.info(
                        f"Added compatibility resolution guidance: {response.values.get('resolution_strategy')}"
                    )
                else:
                    # Add default guidance
                    compatibility_result["resolution_guidance"] = {
                        "strategy": "modify_schema",
                        "compatibility_level": "BACKWARD",
                        "notes": "Default resolution strategy (elicitation failed)",
                        "elicitation_used": False,
                    }
            else:
                # No issues, add successful indicator
                compatibility_result["resolution_guidance"] = {
                    "strategy": "none_needed",
                    "notes": "Schema is compatible, no resolution required",
                    "elicitation_used": False,
                }

        return compatibility_result

    except Exception as e:
        logger.error(f"Error in interactive compatibility check: {str(e)}")
        return create_error_response(
            f"Interactive compatibility check failed: {str(e)}",
            error_code="INTERACTIVE_COMPATIBILITY_ERROR",
        )


async def create_context_interactive(
    context: str,
    registry: Optional[str] = None,
    # Additional metadata that could be elicited
    description: Optional[str] = None,
    owner: Optional[str] = None,
    environment: Optional[str] = None,
    tags: Optional[List[str]] = None,
    # Core tool dependencies injected
    create_context_tool=None,
    registry_manager=None,
    registry_mode=None,
    auth=None,
    headers=None,
    schema_registry_url=None,
) -> Dict[str, Any]:
    """
    Interactive context creation with elicitation for metadata.

    When context metadata is not provided, this tool will elicit
    organizational information from the user.
    """
    try:
        # Check if we should elicit metadata (any metadata field is None)
        needs_elicitation = any(
            [description is None, owner is None, environment is None, tags is None]
        )

        elicited_metadata = {}

        if needs_elicitation:
            logger.info(f"Context creation for '{context}' could benefit from metadata")

            # Create elicitation request for context metadata
            elicitation_request = create_context_metadata_elicitation(
                context_name=context
            )

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Extract metadata from response
                elicited_metadata = {
                    "description": response.values.get("description") or description,
                    "owner": response.values.get("owner") or owner,
                    "environment": response.values.get("environment") or environment,
                    "tags": (
                        response.values.get("tags", "").split(",")
                        if response.values.get("tags")
                        else tags
                    ),
                }

                # Filter out empty values
                elicited_metadata = {k: v for k, v in elicited_metadata.items() if v}

                logger.info(
                    f"Collected context metadata from elicitation: {list(elicited_metadata.keys())}"
                )

        # Now proceed with the actual context creation
        result = create_context_tool(
            context=context,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            registry=registry,
            auth=auth,
            headers=headers,
            schema_registry_url=schema_registry_url,
        )

        # Add metadata to successful result
        if isinstance(result, dict) and "error" not in result:
            result["elicitation_used"] = needs_elicitation
            if elicited_metadata:
                result["metadata"] = elicited_metadata
                result["metadata_note"] = (
                    "Context created with elicited metadata. Store this information in your documentation system."
                )

        return result

    except Exception as e:
        logger.error(f"Error in interactive context creation: {str(e)}")
        return create_error_response(
            f"Interactive context creation failed: {str(e)}",
            error_code="INTERACTIVE_CONTEXT_ERROR",
        )


async def export_global_interactive(
    registry: Optional[str] = None,
    include_metadata: Optional[bool] = None,
    include_config: Optional[bool] = None,
    include_versions: Optional[str] = None,
    # Additional export preferences that could be elicited
    format: Optional[str] = None,
    compression: Optional[str] = None,
    # Core tool dependencies injected
    export_global_tool=None,
    registry_manager=None,
    registry_mode=None,
) -> Dict[str, Any]:
    """
    Interactive global export with elicitation for export preferences.

    When export preferences are not specified, this tool will elicit
    the required configuration from the user.
    """
    try:
        # Check if export preferences need elicitation
        needs_elicitation = any(
            [
                include_metadata is None,
                include_config is None,
                include_versions is None,
                format is None,
                compression is None,
            ]
        )

        if needs_elicitation:
            logger.info(f"Global export for registry '{registry}' needs preferences")

            # Create elicitation request for export preferences
            elicitation_request = create_export_preferences_elicitation(
                operation_type="global_export"
            )

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Apply elicited preferences
                if include_metadata is None:
                    include_metadata = (
                        response.values.get("include_metadata", "true").lower()
                        == "true"
                    )
                if include_config is None:
                    include_config = (
                        response.values.get("include_metadata", "true").lower()
                        == "true"
                    )  # Use same setting
                if include_versions is None:
                    include_versions = response.values.get("include_versions", "latest")
                if format is None:
                    format = response.values.get("format", "json")
                if compression is None:
                    compression = response.values.get("compression", "none")

                logger.info(
                    f"Applied export preferences from elicitation: format={format}, versions={include_versions}"
                )
            else:
                # Use safe defaults
                include_metadata = (
                    include_metadata if include_metadata is not None else True
                )
                include_config = include_config if include_config is not None else True
                include_versions = include_versions or "latest"
                format = format or "json"
                compression = compression or "none"

        # Now proceed with the actual global export
        result = export_global_tool(
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            registry=registry,
            include_metadata=include_metadata,
            include_config=include_config,
            include_versions=include_versions,
        )

        # Add elicitation and format metadata to successful result
        if isinstance(result, dict) and "error" not in result:
            result["elicitation_used"] = needs_elicitation
            result["export_preferences"] = {
                "format": format,
                "compression": compression,
                "include_metadata": include_metadata,
                "include_config": include_config,
                "include_versions": include_versions,
            }
            if compression and compression != "none":
                result["compression_note"] = (
                    f"Consider compressing the export with {compression} for storage efficiency"
                )

        return result

    except Exception as e:
        logger.error(f"Error in interactive global export: {str(e)}")
        return create_error_response(
            f"Interactive global export failed: {str(e)}",
            error_code="INTERACTIVE_EXPORT_ERROR",
        )


# Helper function to build schema from elicitation response
async def _build_schema_from_elicitation(
    elicited_values: Dict[str, Any],
    existing_schema: Optional[Dict] = None,
    schema_type: str = "AVRO",
) -> Dict[str, Any]:
    """Build a complete schema definition from elicited field information."""

    if schema_type == "AVRO":
        # Start with existing schema or create new
        schema = existing_schema or {
            "type": "record",
            "name": "ElicitedSchema",
            "fields": [],
        }

        # Add new field from elicitation
        if elicited_values.get("field_name"):
            field_def = {
                "name": elicited_values["field_name"],
                "type": elicited_values.get("field_type", "string"),
            }

            # Handle nullable fields
            if elicited_values.get("nullable", "false").lower() == "true":
                field_def["type"] = ["null", field_def["type"]]
                if elicited_values.get("default_value"):
                    field_def["default"] = None
            elif elicited_values.get("default_value"):
                # Add default value for non-nullable fields
                default_val = elicited_values["default_value"]
                # Try to convert to appropriate type
                if elicited_values.get("field_type") in ["int", "long"]:
                    try:
                        default_val = int(default_val)
                    except ValueError:
                        pass
                elif elicited_values.get("field_type") in ["float", "double"]:
                    try:
                        default_val = float(default_val)
                    except ValueError:
                        pass
                elif elicited_values.get("field_type") == "boolean":
                    default_val = default_val.lower() in ["true", "1", "yes"]

                field_def["default"] = default_val

            # Add documentation if provided
            if elicited_values.get("documentation"):
                field_def["doc"] = elicited_values["documentation"]

            # Add to fields list
            schema["fields"].append(field_def)

        return schema

    else:
        # For other schema types, return a basic structure
        return {"type": schema_type, "elicited_fields": elicited_values}


# Integration helpers for backward compatibility


def create_interactive_tool_wrapper(original_tool_func, interactive_tool_func):
    """
    Create a wrapper that tries interactive tool first, falls back to original.
    This allows gradual migration to interactive tools.
    """

    async def wrapper(*args, **kwargs):
        try:
            # Try interactive version first
            result = await interactive_tool_func(*args, **kwargs)
            return result
        except Exception as e:
            logger.warning(
                f"Interactive tool failed, falling back to original: {str(e)}"
            )
            # Fall back to original tool
            if asyncio.iscoroutinefunction(original_tool_func):
                return await original_tool_func(*args, **kwargs)
            else:
                return original_tool_func(*args, **kwargs)

    return wrapper
