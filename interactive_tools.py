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

import requests

from elicitation import (
    create_compatibility_resolution_elicitation,
    create_context_metadata_elicitation,
    create_export_preferences_elicitation,
    create_migrate_schema_elicitation,
    create_migration_preferences_elicitation,
    create_schema_field_elicitation,
    elicit_with_fallback,
    elicitation_manager,
)
from schema_validation import create_error_response

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
                    if not isinstance(field, dict) or not field.get("name") or not field.get("type"):
                        needs_elicitation = True
                        missing_info.append("Field definitions are incomplete")
                        break

        if needs_elicitation:
            logger.info(f"Schema registration for '{subject}' needs additional information: {missing_info}")

            # Create elicitation request for schema fields
            existing_fields = []
            if schema_definition and schema_definition.get("fields"):
                existing_fields = [f.get("name", "") for f in schema_definition["fields"] if f.get("name")]

            elicitation_request = create_schema_field_elicitation(context=context, existing_fields=existing_fields)

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
                        "elicitation_status": ("failed" if response is None else "incomplete"),
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
                result["elicited_fields"] = list(response.values.keys()) if response else []

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
                    preserve_ids = response.values.get("preserve_ids", "true").lower() == "true"
                if dry_run is None:
                    dry_run = response.values.get("dry_run", "true").lower() == "true"
                if migrate_all_versions is None:
                    migrate_all_versions = response.values.get("migrate_all_versions", "false").lower() == "true"

                logger.info(
                    f"Applied migration preferences from elicitation: preserve_ids={preserve_ids}, "
                    f"dry_run={dry_run}, migrate_all_versions={migrate_all_versions}"
                )
            else:
                return create_error_response(
                    "Unable to obtain migration preferences",
                    details={
                        "missing_preferences": missing_preferences,
                        "elicitation_status": ("failed" if response is None else "incomplete"),
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
                logger.info(f"Compatibility issues found for subject '{subject}': {compatibility_errors}")

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
                        "compatibility_level": response.values.get("compatibility_level"),
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
        needs_elicitation = any([description is None, owner is None, environment is None, tags is None])

        elicited_metadata = {}

        if needs_elicitation:
            logger.info(f"Context creation for '{context}' could benefit from metadata")

            # Create elicitation request for context metadata
            elicitation_request = create_context_metadata_elicitation(context_name=context)

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
                    "tags": (response.values.get("tags", "").split(",") if response.values.get("tags") else tags),
                }

                # Filter out empty values
                elicited_metadata = {k: v for k, v in elicited_metadata.items() if v}

                logger.info(f"Collected context metadata from elicitation: {list(elicited_metadata.keys())}")

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
            elicitation_request = create_export_preferences_elicitation(operation_type="global_export")

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Apply elicited preferences
                if include_metadata is None:
                    include_metadata = response.values.get("include_metadata", "true").lower() == "true"
                if include_config is None:
                    include_config = (
                        response.values.get("include_metadata", "true").lower() == "true"
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
                include_metadata = include_metadata if include_metadata is not None else True
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


async def migrate_schema_interactive(
    subject: str,
    source_registry: str,
    target_registry: str,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None,
    migrate_all_versions: Optional[bool] = None,
    preserve_ids: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    # Core tool dependencies injected
    migrate_schema_tool=None,
    get_schema_tool=None,
    export_schema_tool=None,
    registry_manager=None,
    registry_mode=None,
) -> Dict[str, Any]:
    """
    Interactive schema migration with elicitation for migration preferences.

    This tool checks if the schema exists in the target registry and elicits
    user preferences for:
    - Whether to replace existing schemas (and backup if needed)
    - Whether to preserve IDs
    - Whether to compare schemas after migration
    """
    try:
        # First, check if schema exists in target registry
        schema_exists_in_target = False
        existing_versions = []

        try:
            if registry_mode == "multi":
                target_client = registry_manager.get_registry(target_registry)
                if target_client:
                    # Check if subject exists in target
                    if target_context and target_context != ".":
                        versions_url = (
                            f"{target_client.config.url}/contexts/{target_context}/subjects/{subject}/versions"
                        )
                    else:
                        versions_url = f"{target_client.config.url}/subjects/{subject}/versions"

                    response = target_client.session.get(
                        versions_url,
                        auth=target_client.auth,
                        headers=target_client.headers,
                        timeout=10,
                    )

                    if response.status_code == 200:
                        schema_exists_in_target = True
                        existing_versions = response.json()
                        logger.info(f"Schema '{subject}' exists in target registry with versions: {existing_versions}")
                    elif response.status_code == 404:
                        logger.info(f"Schema '{subject}' does not exist in target registry")
                    else:
                        logger.warning(f"Could not check schema existence in target: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Error checking schema existence in target registry: {str(e)}")

        # Check if we need elicitation for any missing preferences
        needs_elicitation = (
            any(
                [
                    migrate_all_versions is None,
                    preserve_ids is None,
                    dry_run is None,
                ]
            )
            or schema_exists_in_target
        )  # Always elicit if schema exists in target

        if needs_elicitation:
            logger.info(f"Schema migration from {source_registry} to {target_registry} needs user preferences")

            # Create elicitation request for migration preferences
            elicitation_request = create_migrate_schema_elicitation(
                subject=subject,
                source_registry=source_registry,
                target_registry=target_registry,
                schema_exists_in_target=schema_exists_in_target,
                existing_versions=existing_versions,
                context=source_context,
            )

            # Store the request for processing
            await elicitation_manager.create_request(elicitation_request)

            # Attempt elicitation with fallback
            response = await elicit_with_fallback(elicitation_request)

            if response and response.complete:
                # Process elicited values
                replace_existing = response.values.get("replace_existing", "false").lower() == "true"
                backup_before_replace = response.values.get("backup_before_replace", "true").lower() == "true"
                compare_after_migration = response.values.get("compare_after_migration", "true").lower() == "true"

                # Apply migration preferences
                if preserve_ids is None:
                    preserve_ids = response.values.get("preserve_ids", "true").lower() == "true"
                if dry_run is None:
                    dry_run = response.values.get("dry_run", "true").lower() == "true"
                if migrate_all_versions is None:
                    migrate_all_versions = response.values.get("migrate_all_versions", "false").lower() == "true"

                # Check if we should proceed with replacement
                if schema_exists_in_target and not replace_existing:
                    return create_error_response(
                        f"Schema '{subject}' already exists in target registry and replacement was declined",
                        details={
                            "existing_versions": existing_versions,
                            "target_registry": target_registry,
                            "suggestion": "Choose a different target context or confirm replacement",
                        },
                        error_code="MIGRATION_DECLINED_EXISTING_SCHEMA",
                    )

                logger.info(
                    f"Applied migration preferences from elicitation: "
                    f"preserve_ids={preserve_ids}, dry_run={dry_run}, "
                    f"migrate_all_versions={migrate_all_versions}, "
                    f"replace_existing={replace_existing}, compare_after={compare_after_migration}"
                )
            else:
                return create_error_response(
                    "Unable to obtain migration preferences",
                    details={
                        "schema_exists_in_target": schema_exists_in_target,
                        "elicitation_status": ("failed" if response is None else "incomplete"),
                        "suggestion": "Please specify migration preferences or enable elicitation support",
                    },
                    error_code="INCOMPLETE_MIGRATION_PREFERENCES",
                )
        else:
            # Use defaults if no elicitation needed
            replace_existing = True  # Assume replacement is OK if not eliciting
            backup_before_replace = False
            compare_after_migration = False

        # Perform backup if requested and schema exists
        backup_result = None
        if schema_exists_in_target and backup_before_replace and export_schema_tool:
            try:
                logger.info(f"Creating backup of existing schema '{subject}' in target registry")
                backup_result = export_schema_tool(
                    subject=subject,
                    registry_manager=registry_manager,
                    registry_mode=registry_mode,
                    registry=target_registry,
                    context=target_context,
                    include_metadata=True,
                )
                if "error" not in backup_result:
                    logger.info("✅ Schema backup completed successfully")
                else:
                    logger.warning(f"⚠️ Schema backup failed: {backup_result.get('error')}")
            except Exception as e:
                logger.warning(f"⚠️ Schema backup failed: {str(e)}")
                backup_result = {"error": f"Backup failed: {str(e)}"}

        # Now proceed with the actual schema migration
        migration_result = migrate_schema_tool(
            subject=subject,
            source_registry=source_registry,
            target_registry=target_registry,
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            dry_run=dry_run,
            preserve_ids=preserve_ids,
            source_context=source_context,
            target_context=target_context,
            versions=versions,
            migrate_all_versions=migrate_all_versions,
        )

        # Perform post-migration comparison if requested and migration was successful
        comparison_result = None
        if (
            compare_after_migration
            and isinstance(migration_result, dict)
            and "error" not in migration_result
            and not dry_run
        ):
            try:
                logger.info("Performing post-migration schema verification")

                # Simple verification: check if schema exists in target and get basic info
                verification_result = {"verification_type": "basic", "checks": []}

                if registry_mode == "multi":
                    source_client = registry_manager.get_registry(source_registry)
                    target_client = registry_manager.get_registry(target_registry)

                    if source_client and target_client:
                        try:
                            # Get latest schema from source
                            source_schema = source_client.get_schema(subject, "latest", source_context)
                            # Get latest schema from target
                            target_schema = target_client.get_schema(subject, "latest", target_context)

                            # Compare basic properties
                            if isinstance(source_schema, dict) and isinstance(target_schema, dict):
                                checks = []

                                # Check if both schemas exist
                                checks.append(
                                    {
                                        "check": "schema_exists_in_target",
                                        "passed": "error" not in target_schema,
                                        "details": "Schema successfully migrated to target registry",
                                    }
                                )

                                # Check schema content (if both exist)
                                if "error" not in source_schema and "error" not in target_schema:
                                    schema_content_match = source_schema.get("schema") == target_schema.get("schema")
                                    checks.append(
                                        {
                                            "check": "schema_content_match",
                                            "passed": schema_content_match,
                                            "details": "Schema content matches between source and target",
                                        }
                                    )

                                    # Check schema type
                                    schema_type_match = source_schema.get("schemaType") == target_schema.get(
                                        "schemaType"
                                    )
                                    checks.append(
                                        {
                                            "check": "schema_type_match",
                                            "passed": schema_type_match,
                                            "details": (
                                                f"Schema type: {source_schema.get('schemaType')} -> "
                                                f"{target_schema.get('schemaType')}"
                                            ),
                                        }
                                    )

                                    # Check ID preservation if requested
                                    if preserve_ids:
                                        id_preserved = source_schema.get("id") == target_schema.get("id")
                                        checks.append(
                                            {
                                                "check": "id_preservation",
                                                "passed": id_preserved,
                                                "details": (
                                                    f"Schema ID: {source_schema.get('id')} -> "
                                                    f"{target_schema.get('id')}"
                                                ),
                                            }
                                        )

                                verification_result["checks"] = checks
                                verification_result["overall_success"] = all(check["passed"] for check in checks)

                        except Exception as e:
                            verification_result = {
                                "verification_type": "basic",
                                "error": f"Verification failed: {str(e)}",
                                "checks": [],
                            }

                comparison_result = verification_result
                if comparison_result.get("overall_success"):
                    logger.info("✅ Post-migration verification completed successfully")
                else:
                    logger.warning("⚠️ Post-migration verification found issues")

            except Exception as e:
                logger.warning(f"⚠️ Post-migration verification failed: {str(e)}")
                comparison_result = {"error": f"Verification failed: {str(e)}"}

        # Add elicitation and operation metadata to result
        if isinstance(migration_result, dict):
            migration_result["elicitation_used"] = needs_elicitation
            migration_result["schema_existed_in_target"] = schema_exists_in_target

            if needs_elicitation and response:
                migration_result["elicited_preferences"] = {
                    "preserve_ids": preserve_ids,
                    "dry_run": dry_run,
                    "migrate_all_versions": migrate_all_versions,
                    "replace_existing": replace_existing if schema_exists_in_target else None,
                    "backup_before_replace": backup_before_replace if schema_exists_in_target else None,
                    "compare_after_migration": compare_after_migration,
                }

            if backup_result:
                migration_result["backup_result"] = backup_result

            if comparison_result:
                migration_result["verification_result"] = comparison_result

        return migration_result

    except Exception as e:
        logger.error(f"Error in interactive schema migration: {str(e)}")
        return create_error_response(
            f"Interactive schema migration failed: {str(e)}",
            error_code="INTERACTIVE_MIGRATION_ERROR",
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
            logger.warning(f"Interactive tool failed, falling back to original: {str(e)}")
            # Fall back to original tool
            if asyncio.iscoroutinefunction(original_tool_func):
                return await original_tool_func(*args, **kwargs)
            else:
                return original_tool_func(*args, **kwargs)

    return wrapper
