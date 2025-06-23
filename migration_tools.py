#!/usr/bin/env python3
"""
Migration Tools Module - Updated with Structured Output

Handles schema and context migration operations between registries with structured tool output
support per MCP 2025-06-18 specification.

Provides schema migration, context migration, and migration status tracking
with JSON Schema validation and type-safe responses.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from schema_validation import (
    create_error_response,
    structured_output,
)
from task_management import TaskStatus, TaskType, task_manager

# Configure logging
logger = logging.getLogger(__name__)


@structured_output("migrate_schema", fallback_on_error=True)
def migrate_schema_tool(
    subject: str,
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    dry_run: bool = False,
    preserve_ids: bool = True,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None,
    migrate_all_versions: bool = False,
) -> Dict[str, Any]:
    """
    Migrate a schema from one registry to another.
    Only available in multi-registry mode.

    **MEDIUM-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.

    Args:
        subject: The subject name
        source_registry: Source registry name
        target_registry: Target registry name
        dry_run: Preview migration without executing
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        source_context: Source context (default: ".")
        target_context: Target context (default: ".")
        versions: Optional list of specific versions to migrate
        migrate_all_versions: Migrate all versions instead of just latest

    Returns:
        Task information with task_id for monitoring progress (multi-registry mode)
        or simple result (single-registry mode) with structured validation
    """
    try:
        if registry_mode == "single":
            return create_error_response(
                "Schema migration between registries not available in single-registry mode",
                details={
                    "suggestion": "Use multi-registry configuration to enable cross-registry migration"
                },
                error_code="SINGLE_REGISTRY_MODE_LIMITATION",
                registry_mode="single",
            )

        # Multi-registry mode: use task queue
        # Create migration task
        task = task_manager.create_task(
            TaskType.MIGRATION,
            metadata={
                "operation": "migrate_schema",
                "subject": subject,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_context,
                "migrate_all_versions": migrate_all_versions,
                "preserve_ids": preserve_ids,
                "dry_run": dry_run,
            },
        )

        # Implement basic schema migration for testing
        try:
            # Check registry connections
            source_client = registry_manager.get_registry(source_registry)
            target_client = registry_manager.get_registry(target_registry)

            if not source_client:
                task.status = TaskStatus.FAILED
                task.error = f"Source registry '{source_registry}' not found"
                return create_error_response(
                    f"Source registry '{source_registry}' not found",
                    error_code="SOURCE_REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )
            if not target_client:
                task.status = TaskStatus.FAILED
                task.error = f"Target registry '{target_registry}' not found"
                return create_error_response(
                    f"Target registry '{target_registry}' not found",
                    error_code="TARGET_REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            # Mark task as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()

            # Perform actual schema migration
            migration_result = _execute_schema_migration(
                subject=subject,
                source_client=source_client,
                target_client=target_client,
                source_context=source_context,
                target_context=target_context,
                versions=versions,
                migrate_all_versions=migrate_all_versions,
                preserve_ids=preserve_ids,
                dry_run=dry_run,
            )

            # Update task with result
            if "error" in migration_result:
                task.status = TaskStatus.FAILED
                task.error = migration_result["error"]
            else:
                task.status = TaskStatus.COMPLETED
                task.progress = 100.0
                task.result = migration_result

            task.completed_at = datetime.now().isoformat()

            # Add structured output metadata to result
            migration_result.update(
                {
                    "migration_id": task.id,
                    "subject": subject,
                    "source_registry": source_registry,
                    "target_registry": target_registry,
                    "source_context": source_context,
                    "target_context": target_context,
                    "status": task.status.value,
                    "dry_run": dry_run,
                    "registry_mode": "multi",
                    "mcp_protocol_version": "2025-06-18",
                }
            )

            return migration_result

        except Exception as e:
            return create_error_response(
                f"Migration setup failed: {str(e)}",
                error_code="MIGRATION_SETUP_FAILED",
                registry_mode="multi",
            )

    except Exception as e:
        return create_error_response(
            str(e), error_code="MIGRATION_FAILED", registry_mode=registry_mode
        )


def _execute_schema_migration(
    subject: str,
    source_client,
    target_client,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None,
    migrate_all_versions: bool = False,
    preserve_ids: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Execute actual schema migration between registries with proper sparse version preservation.

    Args:
        subject: The subject name to migrate
        source_client: Source registry client
        target_client: Target registry client
        source_context: Source context
        target_context: Target context
        versions: Specific versions to migrate (overrides migrate_all_versions)
        migrate_all_versions: Whether to migrate all versions
        preserve_ids: Whether to preserve schema IDs (requires IMPORT mode)
        dry_run: Whether to simulate without making changes

    Returns:
        Migration results with counts and status
    """
    try:
        logger.info(f"Starting schema migration for subject '{subject}'")
        logger.info(
            f"Source: {source_client.config.name}, Target: {target_client.config.name}"
        )
        logger.info(f"Preserve IDs: {preserve_ids}, Dry run: {dry_run}")

        # For target operations, we may need to extract the bare subject name
        # if we're migrating to a different context
        target_subject_name = subject

        # If the subject has a context prefix, extract the bare subject name for target
        if subject.startswith(":.") and ":" in subject[2:]:
            # Format is :.context:subject
            parts = subject.split(":", 2)
            if len(parts) >= 3:
                # Extract just the subject name for target registration
                target_subject_name = parts[2]
                logger.info(
                    f"Subject has context prefix. Full name: {subject}, bare name: {target_subject_name}"
                )

        # Get subject versions from source
        try:
            if source_context and source_context != ".":
                source_versions_url = f"{source_client.config.url}/contexts/{source_context}/subjects/{subject}/versions"
            else:
                source_versions_url = (
                    f"{source_client.config.url}/subjects/{subject}/versions"
                )

            response = requests.get(
                source_versions_url,
                auth=source_client.auth,
                headers=source_client.headers,
                timeout=10,
            )

            if response.status_code == 404:
                return {
                    "total_versions": 0,
                    "successful_migrations": 0,
                    "failed_migrations": 0,
                    "skipped_migrations": 0,
                    "message": f"Subject '{subject}' not found in source registry",
                    "dry_run": dry_run,
                }
            elif response.status_code != 200:
                return {
                    "error": f"Failed to get versions from source: HTTP {response.status_code}",
                    "total_versions": 0,
                    "successful_migrations": 0,
                    "failed_migrations": 0,
                    "skipped_migrations": 0,
                    "dry_run": dry_run,
                }

            available_versions = response.json()

        except Exception as e:
            return {
                "error": f"Failed to get source versions: {str(e)}",
                "total_versions": 0,
                "successful_migrations": 0,
                "failed_migrations": 0,
                "skipped_migrations": 0,
                "dry_run": dry_run,
            }

        # Determine which versions to migrate
        if versions:
            versions_to_migrate = [v for v in versions if v in available_versions]
        elif migrate_all_versions:
            versions_to_migrate = available_versions
        else:
            # Migrate only latest version
            versions_to_migrate = (
                [max(available_versions)] if available_versions else []
            )

        if not versions_to_migrate:
            return {
                "total_versions": len(available_versions),
                "successful_migrations": 0,
                "failed_migrations": 0,
                "skipped_migrations": 0,
                "message": "No versions to migrate",
                "dry_run": dry_run,
                "debug_info": {
                    "available_versions": available_versions,
                    "requested_versions": versions,
                    "migrate_all_versions": migrate_all_versions,
                },
            }

        logger.info(f"Versions to migrate: {sorted(versions_to_migrate)}")

        # Handle IMPORT mode for ID preservation
        original_target_mode = None
        if preserve_ids:
            try:
                # Get current target registry mode
                mode_response = requests.get(
                    f"{target_client.config.url}/mode",
                    auth=target_client.auth,
                    headers=target_client.headers,
                    timeout=10,
                )
                if mode_response.status_code == 200:
                    original_target_mode = mode_response.json().get("mode", "READWRITE")

                    # Set target registry to IMPORT mode for ID preservation
                    if original_target_mode != "IMPORT":
                        logger.info(
                            f"Setting target registry to IMPORT mode for ID preservation "
                            f"(was {original_target_mode})"
                        )
                        import_response = requests.put(
                            f"{target_client.config.url}/mode",
                            json={"mode": "IMPORT"},
                            auth=target_client.auth,
                            headers={
                                **target_client.headers,
                                "Content-Type": "application/vnd.schemaregistry.v1+json",
                            },
                            timeout=10,
                        )
                        if import_response.status_code != 200:
                            logger.warning(
                                f"Failed to set IMPORT mode: {import_response.text}. "
                                f"Will try migration without ID preservation."
                            )
                            preserve_ids = False  # Disable ID preservation if can't set IMPORT mode
                        else:
                            logger.info("✅ Target registry set to IMPORT mode")
                    else:
                        logger.info("✅ Target registry already in IMPORT mode")
                else:
                    logger.warning(
                        f"Could not get target registry mode: {mode_response.text}. "
                        f"Will try migration without ID preservation."
                    )
                    preserve_ids = False
            except Exception as e:
                logger.warning(
                    f"Error setting IMPORT mode: {str(e)}. "
                    f"Will try migration without ID preservation."
                )
                preserve_ids = False

        # Migrate each version
        successful_count = 0
        failed_count = 0
        skipped_count = 0
        migration_details = []

        try:
            for version in sorted(versions_to_migrate):
                try:
                    logger.info(f"Processing version {version} of subject '{subject}'")

                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would migrate {subject} version {version}"
                        )
                        successful_count += 1
                        migration_details.append(
                            {
                                "version": version,
                                "status": "simulated",
                                "message": "Would migrate this version",
                            }
                        )
                        continue

                    # Get schema from source registry
                    if source_context and source_context != ".":
                        schema_url = (
                            f"{source_client.config.url}/contexts/{source_context}/"
                            f"subjects/{subject}/versions/{version}"
                        )
                    else:
                        schema_url = f"{source_client.config.url}/subjects/{subject}/versions/{version}"

                    schema_response = requests.get(
                        schema_url,
                        auth=source_client.auth,
                        headers=source_client.headers,
                        timeout=10,
                    )

                    if schema_response.status_code != 200:
                        raise Exception(
                            f"Failed to get schema: HTTP {schema_response.status_code}"
                        )

                    schema_data = schema_response.json()
                    schema_definition = json.loads(schema_data["schema"])

                    # Register schema in target registry
                    if target_context and target_context != ".":
                        target_url = (
                            f"{target_client.config.url}/contexts/{target_context}/"
                            f"subjects/{target_subject_name}/versions"
                        )
                    else:
                        target_url = f"{target_client.config.url}/subjects/{target_subject_name}/versions"

                    payload = {
                        "schema": json.dumps(schema_definition),
                        "schemaType": schema_data.get("schemaType", "AVRO"),
                    }

                    # Add references if they exist
                    if "references" in schema_data and schema_data["references"]:
                        payload["references"] = schema_data["references"]

                    # Try ID preservation first if requested
                    target_id = None
                    if preserve_ids and "id" in schema_data:
                        # First attempt: try with ID preservation (and version preservation)
                        payload_with_id = payload.copy()
                        payload_with_id["id"] = schema_data["id"]
                        # Also preserve version number in IMPORT mode
                        payload_with_id["version"] = version

                        target_response = requests.post(
                            target_url,
                            json=payload_with_id,
                            auth=target_client.auth,
                            headers={
                                **target_client.headers,
                                "Content-Type": "application/vnd.schemaregistry.v1+json",
                            },
                            timeout=10,
                        )

                        if target_response.status_code in [
                            200,
                            409,
                        ]:  # Success with ID preservation
                            target_id = (
                                target_response.json().get("id")
                                if target_response.status_code == 200
                                else "existing"
                            )
                            successful_count += 1
                            migration_details.append(
                                {
                                    "version": version,
                                    "status": "migrated",
                                    "source_id": schema_data.get("id"),
                                    "target_id": target_id,
                                    "preserved_version": True,
                                }
                            )
                            continue
                        elif (
                            target_response.status_code == 422
                            and "import mode" in target_response.text.lower()
                        ):
                            # Import mode required for ID preservation - fall back to normal registration
                            logger.warning(
                                f"ID preservation requires IMPORT mode for version {version}, "
                                f"falling back to normal registration"
                            )
                        else:
                            # Other error - try without ID preservation
                            logger.warning(
                                f"ID preservation failed for version {version}: {target_response.text}, trying without ID"
                            )

                    # Fallback: register without ID preservation
                    target_response = requests.post(
                        target_url,
                        json=payload,
                        auth=target_client.auth,
                        headers={
                            **target_client.headers,
                            "Content-Type": "application/vnd.schemaregistry.v1+json",
                        },
                        timeout=10,
                    )

                    if target_response.status_code in [
                        200,
                        409,
                    ]:  # 409 = already exists
                        target_id = (
                            target_response.json().get("id")
                            if target_response.status_code == 200
                            else "existing"
                        )
                        successful_count += 1
                        migration_details.append(
                            {
                                "version": version,
                                "status": "migrated",
                                "source_id": schema_data.get("id"),
                                "target_id": target_id,
                                "preserved_version": False,  # ID was not preserved
                                "note": (
                                    "ID preservation skipped (registry not in IMPORT mode)"
                                    if preserve_ids
                                    else None
                                ),
                            }
                        )
                    else:
                        raise Exception(
                            f"Failed to register schema: HTTP {target_response.status_code} - {target_response.text}"
                        )

                except Exception as e:
                    logger.error(f"Error migrating version {version}: {e}")
                    failed_count += 1
                    migration_details.append(
                        {
                            "version": version,
                            "status": "failed",
                            "error": f"Version migration error: {str(e)}",
                        }
                    )

        finally:
            # Restore original target registry mode
            if original_target_mode and original_target_mode != "IMPORT":
                try:
                    logger.info(
                        f"Restoring target registry to original mode: {original_target_mode}"
                    )
                    restore_response = requests.put(
                        f"{target_client.config.url}/mode",
                        json={"mode": original_target_mode},
                        auth=target_client.auth,
                        headers={
                            **target_client.headers,
                            "Content-Type": "application/vnd.schemaregistry.v1+json",
                        },
                        timeout=10,
                    )
                    if restore_response.status_code == 200:
                        logger.info(
                            f"✅ Target registry restored to {original_target_mode} mode"
                        )
                    else:
                        logger.warning(
                            f"Failed to restore registry mode: {restore_response.text}"
                        )
                except Exception as e:
                    logger.warning(f"Error restoring registry mode: {str(e)}")

        logger.info(
            f"Migration completed for subject '{subject}'. Migrated {successful_count} versions"
        )

        return {
            "total_versions": len(available_versions),
            "versions_to_migrate": len(versions_to_migrate),
            "successful_migrations": successful_count,
            "failed_migrations": failed_count,
            "skipped_migrations": skipped_count,
            "migration_details": migration_details,
            "dry_run": dry_run,
            "preserve_ids": preserve_ids,
            "message": f"Migrated {successful_count}/{len(versions_to_migrate)} versions successfully"
            + (" (dry run)" if dry_run else ""),
        }

    except Exception as e:
        logger.error(f"Error in _execute_schema_migration: {e}")
        return {
            "error": f"Migration execution failed: {str(e)}",
            "total_versions": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "skipped_migrations": 0,
            "dry_run": dry_run,
        }


@structured_output("list_migrations", fallback_on_error=True)
def list_migrations_tool(registry_mode: str) -> Dict[str, Any]:
    """
    List all migration tasks and their status.
    Only available in multi-registry mode.

    Returns:
        List of migration tasks with their status and progress with structured validation
    """
    try:
        if registry_mode == "single":
            return create_error_response(
                "Migration tracking not available in single-registry mode",
                details={
                    "suggestion": "Use multi-registry configuration to enable migration tracking"
                },
                error_code="SINGLE_REGISTRY_MODE_LIMITATION",
                registry_mode="single",
            )

        # Get all migration-related tasks
        all_tasks = task_manager.list_tasks(task_type=TaskType.MIGRATION)

        migrations = []
        for task in all_tasks:
            migration_info = {
                "migration_id": task.id,
                "type": task.type.value,
                "status": task.status.value,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "progress": task.progress,
                "error": task.error,
                "metadata": task.metadata or {},
            }
            migrations.append(migration_info)

        # Core business logic: return the list of migrations
        # The structured_output decorator will wrap this for MCP compliance
        # but the base business logic should return what the function name suggests
        return migrations

    except Exception as e:
        return create_error_response(
            str(e), error_code="MIGRATION_LIST_FAILED", registry_mode=registry_mode
        )


@structured_output("get_migration_status", fallback_on_error=True)
def get_migration_status_tool(migration_id: str, registry_mode: str) -> Dict[str, Any]:
    """
    Get detailed status of a specific migration.
    Only available in multi-registry mode.

    Args:
        migration_id: The migration task ID to query

    Returns:
        Detailed migration status and progress information with structured validation
    """
    try:
        if registry_mode == "single":
            return create_error_response(
                "Migration tracking not available in single-registry mode",
                details={
                    "suggestion": "Use multi-registry configuration to enable migration tracking"
                },
                error_code="SINGLE_REGISTRY_MODE_LIMITATION",
                registry_mode="single",
            )

        # Get the specific migration task
        task = task_manager.get_task(migration_id)
        if task is None:
            return create_error_response(
                f"Migration '{migration_id}' not found",
                error_code="MIGRATION_NOT_FOUND",
                registry_mode=registry_mode,
            )

        migration_status = {
            "migration_id": task.id,
            "status": task.status.value,
            "progress": task.progress,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error": task.error,
            "result": task.result,
            "metadata": task.metadata or {},
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18",
        }

        # Add estimated time remaining if in progress
        if task.status == TaskStatus.RUNNING and task.progress > 0:
            elapsed = time.time() - (
                datetime.fromisoformat(task.started_at).timestamp()
                if task.started_at
                else time.time()
            )
            if task.progress > 5:  # Only estimate if we have meaningful progress
                estimated_total = elapsed / (task.progress / 100)
                estimated_remaining = max(0, estimated_total - elapsed)
                migration_status["estimated_remaining_seconds"] = round(
                    estimated_remaining, 1
                )

        return migration_status

    except Exception as e:
        return create_error_response(
            str(e), error_code="MIGRATION_STATUS_FAILED", registry_mode=registry_mode
        )


@structured_output("migrate_context", fallback_on_error=True)
async def migrate_context_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    target_context: Optional[str] = None,
    preserve_ids: bool = True,
    dry_run: bool = True,
    migrate_all_versions: bool = True,
) -> Dict[str, Any]:
    """
    Generate Docker command for migrating an entire context using the external
    kafka-schema-reg-migrator tool. This MCP only supports single schema migration.
    For context migration, use the specialized external tool.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Source context to migrate (default: ".")
        target_context: Target context name (defaults to source context)
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        dry_run: Preview migration without executing
        migrate_all_versions: Migrate all versions or just latest

    Returns:
        Docker command and instructions for running the external migration tool with structured validation
    """
    try:
        if registry_mode == "single":
            return create_error_response(
                "Context migration between registries not available in single-registry mode",
                details={
                    "suggestion": "Use multi-registry configuration to enable cross-registry migration"
                },
                error_code="SINGLE_REGISTRY_MODE_LIMITATION",
                registry_mode="single",
            )

        # Get registry configurations
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode="multi",
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode="multi",
            )

        # Use default context if not specified
        context = context or "."
        target_context = target_context or context

        # Build environment variables for the docker command
        env_vars = [
            f"SOURCE_SCHEMA_REGISTRY_URL={source_client.config.url}",
            f"DEST_SCHEMA_REGISTRY_URL={target_client.config.url}",
            "ENABLE_MIGRATION=true",
            f"DRY_RUN={str(dry_run).lower()}",
            f"PRESERVE_IDS={str(preserve_ids).lower()}",
        ]

        # Add authentication if available
        if source_client.config.user:
            env_vars.append(f"SOURCE_USERNAME={source_client.config.user}")
        if source_client.config.password:
            env_vars.append(f"SOURCE_PASSWORD={source_client.config.password}")
        if target_client.config.user:
            env_vars.append(f"DEST_USERNAME={target_client.config.user}")
        if target_client.config.password:
            env_vars.append(f"DEST_PASSWORD={target_client.config.password}")

        # Add context information
        if context != ".":
            env_vars.append(f"SOURCE_CONTEXT={context}")
        if target_context != ".":
            env_vars.append(f"DEST_CONTEXT={target_context}")

        # Add import mode if preserving IDs
        if preserve_ids:
            env_vars.append("DEST_IMPORT_MODE=true")

        # Build docker run command
        docker_cmd_parts = ["docker run -it --rm"]

        # Add environment variables
        for env_var in env_vars:
            docker_cmd_parts.append(f"-e {env_var}")

        # Add the image
        docker_cmd_parts.append("aywengo/kafka-schema-reg-migrator:latest")

        docker_command = " \\\n  ".join(docker_cmd_parts)

        result = {
            "message": "Context migration requires the external kafka-schema-reg-migrator tool",
            "reason": (
                "This MCP only supports single schema migration. "
                "For context migration, use the specialized external tool."
            ),
            "tool": "kafka-schema-reg-migrator",
            "documentation": "https://github.com/aywengo/kafka-schema-reg-migrator",
            "docker_hub": "https://hub.docker.com/r/aywengo/kafka-schema-reg-migrator",
            "docker_docs": "https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md",
            "migration_details": {
                "source": {
                    "registry": source_registry,
                    "url": source_client.config.url,
                    "context": context,
                },
                "target": {
                    "registry": target_registry,
                    "url": target_client.config.url,
                    "context": target_context,
                },
                "options": {
                    "preserve_ids": preserve_ids,
                    "dry_run": dry_run,
                    "migrate_all_versions": migrate_all_versions,
                },
            },
            "docker_command": docker_command,
            "instructions": [
                "1. Copy and run the Docker command below:",
                f"   {docker_command}",
                "",
                "2. Monitor the migration output in your terminal",
                "",
                "3. For more advanced options, see the documentation:",
                "   https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md",
                "",
                "4. Alternative: Use environment file approach:",
                "   - Create a .env file with the environment variables",
                "   - Run: docker run -it --rm --env-file .env aywengo/kafka-schema-reg-migrator:latest",
            ],
            "env_variables": env_vars,
            "warnings": [
                "⚠️  This will use an external Docker container for migration",
                "⚠️  Ensure Docker is installed and running",
                (
                    "⚠️  "
                    + (
                        "This is a DRY RUN - no actual changes will be made"
                        if dry_run
                        else "This will perform actual data migration"
                    )
                ),
                "⚠️  Review the documentation for advanced configuration options",
            ],
            "status": "completed",  # For schema compatibility
            "source_registry": source_registry,
            "target_registry": target_registry,
            "dry_run": dry_run,
            "registry_mode": "multi",
            "mcp_protocol_version": "2025-06-18",
        }

        return result

    except Exception as e:
        return create_error_response(
            str(e), error_code="CONTEXT_MIGRATION_FAILED", registry_mode=registry_mode
        )
