#!/usr/bin/env python3
"""
Migration Tools Module

Handles schema and context migration operations between registries.
Provides schema migration, context migration, and migration status tracking.
"""

import json
import time
import logging
import requests
import asyncio
import threading
import inspect
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from task_management import task_manager, TaskType, TaskStatus, get_operation_info

# Configure logging
logger = logging.getLogger(__name__)

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
    migrate_all_versions: bool = False
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
        or simple result (single-registry mode)
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Schema migration between registries not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable cross-registry migration"
            }
        
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
                "dry_run": dry_run
            }
        )
        
        # Implement basic schema migration for testing
        try:
            # Check registry connections
            source_client = registry_manager.get_registry(source_registry)
            target_client = registry_manager.get_registry(target_registry)
            
            if not source_client:
                task.status = TaskStatus.FAILED
                task.error = f"Source registry '{source_registry}' not found"
                return {"error": f"Source registry '{source_registry}' not found", "registry_mode": "multi"}
            if not target_client:
                task.status = TaskStatus.FAILED
                task.error = f"Target registry '{target_registry}' not found"
                return {"error": f"Target registry '{target_registry}' not found", "registry_mode": "multi"}
            
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
                dry_run=dry_run
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
            
            # Add metadata to result
            migration_result.update({
                "migration_id": task.id,
                "subject": subject,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_context,
                "registry_mode": "multi"
            })
            
            return migration_result
            
        except Exception as e:
            return {"error": f"Migration setup failed: {str(e)}", "registry_mode": "multi"}
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

def _execute_schema_migration(
    subject: str,
    source_client,
    target_client,
    source_context: str = ".",
    target_context: str = ".",
    versions: Optional[List[int]] = None,
    migrate_all_versions: bool = False,
    preserve_ids: bool = True,
    dry_run: bool = False
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
        logger.info(f"Source: {source_client.config.name}, Target: {target_client.config.name}")
        logger.info(f"Preserve IDs: {preserve_ids}, Dry run: {dry_run}")
        
        # For source operations, use the subject as-is
        source_subject = subject
        
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
                logger.info(f"Subject has context prefix. Full name: {subject}, bare name: {target_subject_name}")
        
        # Get subject versions from source
        try:
            if source_context and source_context != ".":
                source_versions_url = f"{source_client.config.url}/contexts/{source_context}/subjects/{subject}/versions"
            else:
                source_versions_url = f"{source_client.config.url}/subjects/{subject}/versions"
            
            response = requests.get(source_versions_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
            
            if response.status_code == 404:
                return {
                    "total_versions": 0,
                    "successful_migrations": 0,
                    "failed_migrations": 0,
                    "skipped_migrations": 0,
                    "message": f"Subject '{subject}' not found in source registry",
                    "dry_run": dry_run
                }
            elif response.status_code != 200:
                return {
                    "error": f"Failed to get versions from source: HTTP {response.status_code}",
                    "total_versions": 0,
                    "successful_migrations": 0,
                    "failed_migrations": 0,
                    "skipped_migrations": 0,
                    "dry_run": dry_run
                }
            
            available_versions = response.json()
            
        except Exception as e:
            return {
                "error": f"Failed to get source versions: {str(e)}",
                "total_versions": 0,
                "successful_migrations": 0,
                "failed_migrations": 0,
                "skipped_migrations": 0,
                "dry_run": dry_run
            }
        
        # Determine which versions to migrate
        if versions:
            versions_to_migrate = [v for v in versions if v in available_versions]
        elif migrate_all_versions:
            versions_to_migrate = available_versions
        else:
            # Migrate only latest version
            versions_to_migrate = [max(available_versions)] if available_versions else []
        
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
                    "migrate_all_versions": migrate_all_versions
                }
            }
        
        logger.info(f"Versions to migrate: {sorted(versions_to_migrate)}")
        
        # Check if target subject exists and delete it if preserve_ids is enabled
        target_subject_exists = False
        if preserve_ids and not dry_run:
            try:
                if target_context and target_context != ".":
                    target_versions_url = f"{target_client.config.url}/contexts/{target_context}/subjects/{target_subject_name}/versions"
                else:
                    target_versions_url = f"{target_client.config.url}/subjects/{target_subject_name}/versions"
                
                target_versions_response = requests.get(target_versions_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                if target_versions_response.status_code == 200:
                    target_subject_exists = True
                    logger.info(f"Subject '{target_subject_name}' exists in target registry. Will delete before migration.")
                    
                    # Delete the subject
                    if target_context and target_context != ".":
                        delete_url = f"{target_client.config.url}/contexts/{target_context}/subjects/{target_subject_name}"
                    else:
                        delete_url = f"{target_client.config.url}/subjects/{target_subject_name}"
                    
                    delete_response = requests.delete(delete_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                    if delete_response.status_code == 200:
                        logger.info(f"Successfully deleted existing subject '{target_subject_name}' from target registry")
                        target_subject_exists = False
                    else:
                        logger.warning(f"Failed to delete existing subject: {delete_response.status_code} - {delete_response.text}")
                        
            except Exception as e:
                logger.warning(f"Error checking/deleting existing subject: {e}")
        
        # Set target subject to IMPORT mode if preserving IDs and create placeholder schemas
        if preserve_ids and not dry_run:
            try:
                if target_context and target_context != ".":
                    mode_url = f"{target_client.config.url}/contexts/{target_context}/mode/{target_subject_name}"
                else:
                    mode_url = f"{target_client.config.url}/mode/{target_subject_name}"
                
                logger.info(f"Setting IMPORT mode on target subject '{target_subject_name}'")
                mode_response = requests.put(
                    mode_url,
                    auth=target_client.auth,
                    headers=target_client.headers,
                    json={"mode": "IMPORT"},
                    timeout=10
                )
                
                if mode_response.status_code in [200, 404]:
                    logger.info("Successfully set target subject to IMPORT mode")
                    
                    # Create placeholder schemas for missing versions to preserve sparse version numbers
                    min_version = min(versions_to_migrate)
                    if min_version > 1:
                        logger.info(f"Creating placeholder schemas for versions 1 to {min_version-1}")
                        for placeholder_version in range(1, min_version):
                            try:
                                placeholder_schema = {
                                    "type": "record",
                                    "name": "PlaceholderSchema",
                                    "fields": [
                                        {"name": "placeholder_field", "type": "string", "default": "placeholder"}
                                    ]
                                }
                                
                                placeholder_payload = {
                                    "schema": json.dumps(placeholder_schema),
                                    "schemaType": "AVRO",
                                    "id": placeholder_version,
                                    "version": placeholder_version
                                }
                                
                                if target_context and target_context != ".":
                                    placeholder_url = f"{target_client.config.url}/contexts/{target_context}/subjects/{target_subject_name}/versions"
                                else:
                                    placeholder_url = f"{target_client.config.url}/subjects/{target_subject_name}/versions"
                                
                                placeholder_response = requests.post(
                                    placeholder_url,
                                    auth=target_client.auth,
                                    headers=target_client.headers,
                                    json=placeholder_payload,
                                    timeout=10
                                )
                                
                                if placeholder_response.status_code == 200:
                                    logger.info(f"Created placeholder schema for version {placeholder_version}")
                                else:
                                    logger.warning(f"Failed to create placeholder for version {placeholder_version}: {placeholder_response.status_code}")
                                    
                            except Exception as e:
                                logger.warning(f"Error creating placeholder for version {placeholder_version}: {e}")
                    
                elif mode_response.status_code == 405:
                    logger.warning("IMPORT mode not supported by target registry, will proceed without ID preservation")
                    preserve_ids = False
                else:
                    logger.warning(f"Failed to set IMPORT mode: {mode_response.status_code} - {mode_response.text}")
                    preserve_ids = False
                    
            except Exception as e:
                logger.warning(f"Error setting IMPORT mode: {e}")
                preserve_ids = False
        
        # Migrate each version
        successful_count = 0
        failed_count = 0
        skipped_count = 0
        migration_details = []
        
        for version in sorted(versions_to_migrate):
            try:
                logger.info(f"Processing version {version} of subject '{subject}'")
                
                # Get schema from source
                if source_context and source_context != ".":
                    source_schema_url = f"{source_client.config.url}/contexts/{source_context}/subjects/{subject}/versions/{version}"
                else:
                    source_schema_url = f"{source_client.config.url}/subjects/{subject}/versions/{version}"
                
                schema_response = requests.get(source_schema_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                
                if schema_response.status_code != 200:
                    failed_count += 1
                    migration_details.append({
                        "version": version,
                        "status": "failed",
                        "error": f"Failed to get schema: HTTP {schema_response.status_code}"
                    })
                    continue
                
                schema_data = schema_response.json()
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate {subject} version {version}")
                    successful_count += 1
                    migration_details.append({
                        "version": version,
                        "status": "simulated",
                        "schema_id": schema_data.get("id"),
                        "schema": schema_data.get("schema"),
                        "message": "Would migrate this version"
                    })
                    continue
                
                # Prepare registration payload
                register_payload = {
                    "schema": schema_data.get("schema"),
                    "schemaType": schema_data.get("schemaType", "AVRO")
                }
                
                # Add references if present
                if "references" in schema_data:
                    register_payload["references"] = schema_data["references"]
                
                # CRITICAL: Add ID and version if preserving IDs to maintain sparse version numbers
                if preserve_ids and schema_data.get("id"):
                    register_payload["id"] = schema_data.get("id")
                    register_payload["version"] = version  # CRITICAL: Include version to preserve sparse numbering
                    logger.info(f"Preserving schema ID {schema_data.get('id')} and version {version}")
                else:
                    logger.info(f"Not preserving IDs - version {version} will be auto-assigned sequential number in target")
                
                # Register schema in target
                if target_context and target_context != ".":
                    target_register_url = f"{target_client.config.url}/contexts/{target_context}/subjects/{target_subject_name}/versions"
                else:
                    target_register_url = f"{target_client.config.url}/subjects/{target_subject_name}/versions"
                
                logger.info(f"Registering schema version {version} in target registry")
                register_response = requests.post(
                    target_register_url,
                    auth=target_client.auth,
                    headers=target_client.headers,
                    json=register_payload,
                    timeout=10
                )
                
                if register_response.status_code in [200, 409]:  # 409 = already exists
                    result = register_response.json()
                    actual_version = result.get("version", version)
                    logger.info(f"Successfully registered version {actual_version} with ID {result.get('id')}")
                    successful_count += 1
                    migration_details.append({
                        "version": actual_version,
                        "status": "migrated",
                        "source_id": schema_data.get("id"),
                        "target_id": result.get("id"),
                        "preserved_version": preserve_ids and actual_version == version
                    })
                else:
                    error_text = register_response.text
                    logger.error(f"Error migrating version {version}: {error_text}")
                    failed_count += 1
                    migration_details.append({
                        "version": version,
                        "status": "failed",
                        "error": f"Registration failed: HTTP {register_response.status_code}: {error_text}"
                    })
                        
            except Exception as e:
                logger.error(f"Error migrating version {version}: {e}")
                failed_count += 1
                migration_details.append({
                    "version": version,
                    "status": "failed",
                    "error": f"Version migration error: {str(e)}"
                })
        
        # Restore original mode if we changed it (optional - many registries auto-restore)
        if preserve_ids and not dry_run:
            try:
                if target_context and target_context != ".":
                    mode_url = f"{target_client.config.url}/contexts/{target_context}/mode/{target_subject_name}"
                else:
                    mode_url = f"{target_client.config.url}/mode/{target_subject_name}"
                
                logger.info("Restoring original subject mode")
                restore_response = requests.put(
                    mode_url,
                    auth=target_client.auth,
                    headers=target_client.headers,
                    json={"mode": "READWRITE"},
                    timeout=10
                )
                
                if restore_response.status_code == 200:
                    logger.info("Restored original subject mode")
                else:
                    logger.warning(f"Failed to restore original mode: {restore_response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Error restoring original mode: {e}")
        
        logger.info(f"Migration completed for subject '{subject}'. Migrated {successful_count} versions")
        
        return {
            "total_versions": len(available_versions),
            "versions_to_migrate": len(versions_to_migrate),
            "successful_migrations": successful_count,
            "failed_migrations": failed_count,
            "skipped_migrations": skipped_count,
            "migration_details": migration_details,
            "dry_run": dry_run,
            "subject_existed_in_target": target_subject_exists,
            "preserve_ids": preserve_ids,
            "message": f"Migrated {successful_count}/{len(versions_to_migrate)} versions successfully" + (f" (dry run)" if dry_run else ""),
            "debug_info": {
                "available_versions": available_versions,
                "requested_versions": versions,
                "versions_to_migrate_list": versions_to_migrate,
                "preserve_ids": preserve_ids
            }
        }
        
    except Exception as e:
        logger.error(f"Error in _execute_schema_migration: {e}")
        return {
            "error": f"Migration execution failed: {str(e)}",
            "total_versions": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "skipped_migrations": 0,
            "dry_run": dry_run
        }

def list_migrations_tool(registry_mode: str) -> Dict[str, Any]:
    """
    List all migration tasks and their status.
    Only available in multi-registry mode.
    
    Returns:
        List of migration tasks with their status and progress
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Migration tracking not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable migration tracking"
            }
        
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
                "metadata": task.metadata or {}
            }
            migrations.append(migration_info)
        
        # Return list format for API compatibility with tests
        # Tests expect len(list_migrations()) to work
        return migrations
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

def get_migration_status_tool(migration_id: str, registry_mode: str) -> Dict[str, Any]:
    """
    Get detailed status of a specific migration.
    Only available in multi-registry mode.
    
    Args:
        migration_id: The migration task ID to query
    
    Returns:
        Detailed migration status and progress information
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Migration tracking not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable migration tracking"
            }
        
        # Get the specific migration task
        task = task_manager.get_task(migration_id)
        if task is None:
            return {"error": f"Migration '{migration_id}' not found"}
        
        migration_status = {
            "migration_id": task.id,
            "type": task.type.value,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "progress": task.progress,
            "error": task.error,
            "result": task.result,
            "metadata": task.metadata or {},
            "registry_mode": "multi"
        }
        
        # Add estimated time remaining if in progress
        if task.status == TaskStatus.RUNNING and task.progress > 0:
            elapsed = time.time() - (datetime.fromisoformat(task.started_at).timestamp() if task.started_at else time.time())
            if task.progress > 5:  # Only estimate if we have meaningful progress
                estimated_total = elapsed / (task.progress / 100)
                estimated_remaining = max(0, estimated_total - elapsed)
                migration_status["estimated_remaining_seconds"] = round(estimated_remaining, 1)
        
        return migration_status
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

async def migrate_context_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    target_context: Optional[str] = None,
    preserve_ids: bool = True,
    dry_run: bool = True,
    migrate_all_versions: bool = True
) -> Dict[str, Any]:
    """
    Guide for migrating an entire context using Docker-based Kafka Schema Registry Migrator.
    Only available in multi-registry mode.
    
    This function generates configuration files and instructions for using the
    kafka-schema-reg-migrator Docker container, which provides a more robust
    migration solution with better error handling and recovery capabilities.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Source context to migrate (default: ".")
        target_context: Target context name (defaults to source context)
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        dry_run: Preview migration without executing
        migrate_all_versions: Migrate all versions or just latest
    
    Returns:
        Migration guide with configuration files and Docker commands
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Context migration between registries not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable cross-registry migration"
            }
        
        # Get registry configurations
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client:
            return {"error": f"Source registry '{source_registry}' not found", "registry_mode": "multi"}
        if not target_client:
            return {"error": f"Target registry '{target_registry}' not found", "registry_mode": "multi"}
        
        # Use default context if not specified
        context = context or "."
        target_context = target_context or context
        
        # Generate .env file content
        env_content = f"""# Kafka Schema Registry Migrator Configuration
# Generated by kafka_schema_registry_unified_mcp
# Documentation: https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md

# Source Registry Configuration
SCHEMA_REGISTRY_URL={source_client.config.url}
{f'SCHEMA_REGISTRY_USERNAME={source_client.config.user}' if source_client.config.user else '# SCHEMA_REGISTRY_USERNAME='}
{f'SCHEMA_REGISTRY_PASSWORD={source_client.config.password}' if source_client.config.password else '# SCHEMA_REGISTRY_PASSWORD='}

# Target Registry Configuration
TARGET_SCHEMA_REGISTRY_URL={target_client.config.url}
{f'TARGET_SCHEMA_REGISTRY_USERNAME={target_client.config.user}' if target_client.config.user else '# TARGET_SCHEMA_REGISTRY_USERNAME='}
{f'TARGET_SCHEMA_REGISTRY_PASSWORD={target_client.config.password}' if target_client.config.password else '# TARGET_SCHEMA_REGISTRY_PASSWORD='}

# Migration Options
SOURCE_CONTEXT={context}
TARGET_CONTEXT={target_context}
PRESERVE_SCHEMA_IDS={str(preserve_ids).lower()}
MIGRATE_ALL_VERSIONS={str(migrate_all_versions).lower()}
DRY_RUN={str(dry_run).lower()}

# Additional Options (customize as needed)
# BATCH_SIZE=50
# CONCURRENT_REQUESTS=5
# RETRY_ATTEMPTS=3
# LOG_LEVEL=INFO
"""

        # Generate docker-compose.yml content
        docker_compose_content = f"""version: '3.8'

services:
  schema-registry-migrator:
    image: aywengo/kafka-schema-reg-migrator:latest
    env_file:
      - .env
    environment:
      - MODE=migrate-context
    volumes:
      - ./logs:/app/logs
      - ./backups:/app/backups
    command: ["--source-context", "{context}", "--target-context", "{target_context}"]
"""

        # Generate shell script for easy execution
        shell_script_content = f"""#!/bin/bash
# Kafka Schema Registry Context Migration Script
# Generated by kafka_schema_registry_unified_mcp

echo "🚀 Starting Kafka Schema Registry Context Migration"
echo "Source: {source_registry} (context: {context})"
echo "Target: {target_registry} (context: {target_context})"
echo ""

# Run the migration using Docker
docker run -it --rm \\
  --env-file .env \\
  -v "$(pwd)/logs:/app/logs" \\
  -v "$(pwd)/backups:/app/backups" \\
  aywengo/kafka-schema-reg-migrator:latest \\
  migrate-context \\
  --source-context "{context}" \\
  --target-context "{target_context}" \\
  {'--dry-run' if dry_run else ''} \\
  {'--preserve-ids' if preserve_ids else ''} \\
  {'--all-versions' if migrate_all_versions else '--latest-only'}

echo ""
echo "✅ Migration process completed. Check logs directory for details."
"""

        # Generate migration guide
        guide = {
            "migration_type": "Docker-based Context Migration",
            "tool": "kafka-schema-reg-migrator",
            "documentation": "https://github.com/aywengo/kafka-schema-reg-migrator/blob/main/docs/run-in-docker.md",
            "source": {
                "registry": source_registry,
                "url": source_client.config.url,
                "context": context
            },
            "target": {
                "registry": target_registry,
                "url": target_client.config.url,
                "context": target_context,
                "readonly": getattr(target_client.config, 'readonly', False)
            },
            "options": {
                "preserve_ids": preserve_ids,
                "dry_run": dry_run,
                "migrate_all_versions": migrate_all_versions
            },
            "files_to_create": {
                ".env": {
                    "description": "Environment configuration file",
                    "content": env_content
                },
                "docker-compose.yml": {
                    "description": "Docker Compose configuration",
                    "content": docker_compose_content
                },
                "migrate-context.sh": {
                    "description": "Migration execution script",
                    "content": shell_script_content,
                    "make_executable": True
                }
            },
            "instructions": [
                "1. Create a new directory for the migration:",
                f"   mkdir schema-migration-{context.replace('.', 'default')}-to-{target_context.replace('.', 'default')}",
                f"   cd schema-migration-{context.replace('.', 'default')}-to-{target_context.replace('.', 'default')}",
                "",
                "2. Create the configuration files:",
                "   - Save the .env content to a file named '.env'",
                "   - Save the docker-compose.yml content to 'docker-compose.yml'",
                "   - Save the shell script to 'migrate-context.sh' and make it executable:",
                "     chmod +x migrate-context.sh",
                "",
                "3. Review and adjust the .env file as needed",
                "",
                "4. Run the migration:",
                "   Option A: Using Docker Compose:",
                "     docker-compose up",
                "   Option B: Using the shell script:",
                "     ./migrate-context.sh",
                "   Option C: Direct Docker command:",
                "     docker run -it --rm --env-file .env aywengo/kafka-schema-reg-migrator:latest",
                "",
                "5. Monitor the migration:",
                "   - Logs will be saved in the ./logs directory",
                "   - Backups (if enabled) will be in ./backups",
                "",
                "6. Verify the migration:",
                "   - Use compare_contexts_across_registries to verify the migration"
            ],
            "warnings": [],
            "registry_mode": "multi"
        }
        
        # Add warnings if needed
        if getattr(target_client.config, 'readonly', False):
            guide["warnings"].append(f"⚠️  Target registry '{target_registry}' is marked as READONLY. Ensure it's writable before migration.")
        
        if not dry_run:
            guide["warnings"].append("⚠️  This will perform actual data migration. Consider running with dry_run=True first.")
        
        if preserve_ids:
            guide["warnings"].append("⚠️  ID preservation requires IMPORT mode on target registry. The migrator will handle this automatically.")
        
        return guide
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode} 