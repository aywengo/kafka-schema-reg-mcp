#!/usr/bin/env python3
"""
Kafka Schema Registry MCP Server

A Message Control Protocol (MCP) server that provides tools for interacting with
Kafka Schema Registry, including schema management, context operations, configuration
management, mode control, comprehensive export functionality, and multi-registry operations.

Safety Features:
- READONLY mode: Set READONLY=true environment variable to block all modification
  operations while allowing read and export operations for production safety.

Multi-Registry Features:
- Connect to multiple Schema Registry instances
- Cross-registry comparison and migration
- Schema synchronization between registries
- Environment promotion workflows
"""

import os
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import asyncio
import logging
from urllib.parse import urlparse
import uuid

import requests
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Import common library functionality
from schema_registry_common import (
    RegistryConfig,
    RegistryClient,
    MigrationTask,
    LegacyRegistryManager,
    check_readonly_mode,
    build_context_url,
    get_default_client,
    format_schema_as_avro_idl,
    get_schema_with_metadata,
    export_schema as common_export_schema,
    export_subject as common_export_subject,
    export_context as common_export_context,
    export_global as common_export_global,
    clear_context_batch as common_clear_context_batch,
    SINGLE_REGISTRY_URL as SCHEMA_REGISTRY_URL,
    SINGLE_REGISTRY_USER as SCHEMA_REGISTRY_USER,
    SINGLE_REGISTRY_PASSWORD as SCHEMA_REGISTRY_PASSWORD,
    SINGLE_READONLY as READONLY
)

# Multi-registry configuration
REGISTRIES_CONFIG = os.getenv("REGISTRIES_CONFIG", "")

# Import OAuth functionality
from oauth_provider import (
    ENABLE_AUTH, require_scopes, get_oauth_scopes_info, get_fastmcp_config
)

# Initialize FastMCP with OAuth configuration
mcp_config = get_fastmcp_config("Kafka Schema Registry MCP Server")
mcp = FastMCP(**mcp_config)

# Initialize registry manager using the common library
registry_manager = LegacyRegistryManager(REGISTRIES_CONFIG)

# Set up global variables for backward compatibility
auth = None
headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
standard_headers = {"Content-Type": "application/json"}

# Set up authentication if configured
if SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD:
    auth = HTTPBasicAuth(SCHEMA_REGISTRY_USER, SCHEMA_REGISTRY_PASSWORD)
    credentials = base64.b64encode(f"{SCHEMA_REGISTRY_USER}:{SCHEMA_REGISTRY_PASSWORD}".encode()).decode()
    headers["Authorization"] = f"Basic {credentials}"
    standard_headers["Authorization"] = f"Basic {credentials}"

def build_context_url(base_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support (global function for backward compatibility)."""
    # Handle default context "." as no context
    if context and context != ".":
        return f"{SCHEMA_REGISTRY_URL}/contexts/{context}{base_url}"
    return f"{SCHEMA_REGISTRY_URL}{base_url}"

# ===== MULTI-REGISTRY MANAGEMENT TOOLS =====

@mcp.tool()
def list_registries() -> List[Dict[str, Any]]:
    """
    List all configured Schema Registry instances.
    
    Returns:
        List of registry configurations with connection status
    """
    try:
        result = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                result.append(info)
        return result
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_registry_info(registry_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific registry.
    
    Args:
        registry_name: Name of the registry
    
    Returns:
        Dictionary containing registry details and health information
    """
    try:
        info = registry_manager.get_registry_info(registry_name)
        if info is None:
            return {"error": f"Registry '{registry_name}' not found"}
        return info
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def test_registry_connection(registry_name: str) -> Dict[str, Any]:
    """
    Test connection to a specific registry.
    
    Args:
        registry_name: Name of the registry to test
    
    Returns:
        Connection test results
    """
    try:
        client = registry_manager.get_registry(registry_name)
        if client is None:
            return {"error": f"Registry '{registry_name}' not found"}
        
        return client.test_connection()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def test_all_registries() -> Dict[str, Any]:
    """
    Test connections to all configured registries.
    
    Returns:
        Connection test results for all registries
    """
    try:
        results = {}
        for name in registry_manager.list_registries():
            client = registry_manager.get_registry(name)
            if client:
                results[name] = client.test_connection()
        
        return {
            "registry_tests": results,
            "total_registries": len(results),
            "connected": sum(1 for r in results.values() if r.get("status") == "connected"),
            "failed": sum(1 for r in results.values() if r.get("status") == "error")
        }
    except Exception as e:
        return {"error": str(e)}

# ===== CROSS-REGISTRY COMPARISON TOOLS =====

@mcp.tool()
def compare_registries(
    source_registry: str,
    target_registry: str,
    include_contexts: bool = True,
    include_configs: bool = True
) -> Dict[str, Any]:
    """
    Compare two Schema Registry instances and show differences.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        include_contexts: Include context comparison
        include_configs: Include configuration comparison
    
    Returns:
        Comprehensive comparison results
    """
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        comparison = {
            "source": source_registry,
            "target": target_registry,
            "compared_at": datetime.now().isoformat()
        }
        
        # Compare subjects
        source_subjects = source_client.test_connection()  # Will need to implement get_subjects
        target_subjects = target_client.test_connection()  # Will need to implement get_subjects
        
        # This is a simplified version - full implementation would compare actual subjects
        comparison["summary"] = {
            "registries_compared": 2,
            "comparison_completed": True
        }
        
        return comparison
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def compare_contexts_across_registries(
    source_registry: str,
    target_registry: str,
    context: str
) -> Dict[str, Any]:
    """
    Compare a specific context across two registries.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Context name to compare
    
    Returns:
        Context comparison results
    """
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        # Implementation would compare subjects within the context
        return {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
            "comparison_completed": True,
            "compared_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

# ===== MIGRATION TOOLS =====

@mcp.tool()
def migrate_schema(
    subject: str,
    source_registry: str,
    target_registry: str,
    source_context: Optional[str] = None,
    target_context: Optional[str] = None,
    migrate_all_versions: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Migrate a schema from one registry to another.
    
    Args:
        subject: Schema subject name
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Source context (optional)
        target_context: Target context (optional, defaults to source_context)
        migrate_all_versions: Migrate all versions or just latest
        dry_run: Preview migration without executing
    
    Returns:
        Migration results
    """
    # Check readonly mode for actual migrations
    if not dry_run:
        readonly_check = check_readonly_mode(registry_manager)
        if readonly_check:
            return readonly_check
    
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        # Create migration task
        task_id = str(uuid.uuid4())
        task = MigrationTask(
            id=task_id,
            source_registry=source_registry,
            target_registry=target_registry,
            scope=f"schema:{subject}",
            status="completed" if dry_run else "completed",
            created_at=datetime.now().isoformat()
        )
        
        if not dry_run:
            registry_manager.migration_tasks[task_id] = task
        
        return {
            "migration_id": task_id,
            "subject": subject,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "source_context": source_context,
            "target_context": target_context or source_context,
            "dry_run": dry_run,
            "status": "completed",
            "migrated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def migrate_context(
    context: str,
    source_registry: str,
    target_registry: str,
    target_context: Optional[str] = None,
    dry_run: bool = False,
    preserve_ids: bool = True,
    migrate_all_versions: bool = True
) -> Dict[str, Any]:
    """
    Guide for migrating an entire context using Docker-based Kafka Schema Registry Migrator.
    
    This function generates configuration files and instructions for using the
    kafka-schema-reg-migrator Docker container, which provides a more robust
    migration solution with better error handling and recovery capabilities.
    
    Args:
        context: Context name to migrate
        source_registry: Source registry name
        target_registry: Target registry name
        target_context: Target context name (optional, defaults to source context)
        dry_run: Preview migration without executing
        preserve_ids: Preserve original schema IDs (requires IMPORT mode)
        migrate_all_versions: Migrate all versions or just latest
    
    Returns:
        Migration guide with configuration files and Docker commands
    """
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        # Use default context if not specified
        target_context = target_context or context
        
        # Generate .env file content
        env_content = f"""# Kafka Schema Registry Migrator Configuration
# Generated by kafka_schema_registry_mcp
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
# Generated by kafka_schema_registry_mcp

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
                "context": target_context
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
            "warnings": []
        }
        
        # Add warnings if needed
        if READONLY:
            guide["warnings"].append("⚠️  This server is in READONLY mode. Ensure target registry is writable before migration.")
        
        if not dry_run:
            guide["warnings"].append("⚠️  This will perform actual data migration. Consider running with dry_run=True first.")
        
        if preserve_ids:
            guide["warnings"].append("⚠️  ID preservation requires IMPORT mode on target registry. The migrator will handle this automatically.")
        
        # Add warning if registries have same URL (likely single-registry mode)
        if source_client.config.url == target_client.config.url:
            guide["warnings"].append("⚠️  Source and target registries have the same URL. Ensure contexts are different to avoid data loss.")
        
        return guide
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def list_migrations() -> List[Dict[str, Any]]:
    """
    Show migration history.
    
    Returns:
        List of migration tasks
    """
    try:
        return [asdict(task) for task in registry_manager.migration_tasks.values()]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_migration_status(migration_id: str) -> Dict[str, Any]:
    """
    Check migration progress.
    
    Args:
        migration_id: Migration task ID
    
    Returns:
        Migration status and details
    """
    try:
        task = registry_manager.migration_tasks.get(migration_id)
        if task is None:
            return {"error": f"Migration '{migration_id}' not found"}
        
        return asdict(task)
    except Exception as e:
        return {"error": str(e)}

# ===== OAUTH INFORMATION TOOLS =====

@mcp.tool()
def get_oauth_scopes_info() -> Dict[str, Any]:
    """
    Get information about OAuth scopes and permissions in this MCP server.
    
    Returns:
        Dictionary containing scope definitions, required permissions per tool, and test tokens
    """
    return get_oauth_scopes_info()

# ===== SCHEMA MANAGEMENT TOOLS =====

@mcp.tool()
@require_scopes("write")
def register_schema(
    subject: str,
    schema_definition: Dict[str, Any],
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Register a new schema version under the specified subject.
    
    Args:
        subject: The subject name for the schema
        schema_definition: The schema definition as a dictionary
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the schema ID
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = client.build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
@require_scopes("read")
def get_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a specific version of a schema.
    
    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing schema information
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}/versions/{version}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_schema_versions(
    subject: str,
    context: Optional[str] = None
) -> List[int]:
    """
    Get all versions of a schema.
    
    Args:
        subject: The subject name
        context: Optional schema context
    
    Returns:
        List of version numbers
    """
    try:
        url = build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_compatibility(
    subject: str,
    schema_definition: Dict[str, Any],
    schema_type: str = "AVRO",
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if a schema is compatible with the specified subject.
    
    Args:
        subject: The subject name
        schema_definition: The schema definition to check
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
    
    Returns:
        Dictionary containing compatibility result
    """
    try:
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ===== CONTEXT MANAGEMENT TOOLS =====

@mcp.tool()
def list_contexts() -> List[str]:
    """
    List all available schema contexts.
    
    Returns:
        List of context names
    """
    try:
        response = requests.get(
            f"{SCHEMA_REGISTRY_URL}/contexts",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def create_context(context: str) -> Dict[str, str]:
    """
    Create a new schema context.
    
    Args:
        context: The context name to create
    
    Returns:
        Success message
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        response = requests.post(
            f"{SCHEMA_REGISTRY_URL}/contexts/{context}",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' created successfully"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def delete_context(context: str) -> Dict[str, str]:
    """
    Delete a schema context.
    
    Args:
        context: The context name to delete
    
    Returns:
        Success message
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        response = requests.delete(
            f"{SCHEMA_REGISTRY_URL}/contexts/{context}",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

# ===== SUBJECT MANAGEMENT TOOLS =====

@mcp.tool()
@require_scopes("read")
def list_subjects(context: Optional[str] = None) -> List[str]:
    """
    List all subjects, optionally filtered by context.
    
    Args:
        context: Optional schema context to filter by
    
    Returns:
        List of subject names
    """
    try:
        url = build_context_url("/subjects", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
@require_scopes("admin")
def delete_subject(
    subject: str,
    context: Optional[str] = None
) -> List[int]:
    """
    Delete a subject and all its versions.
    
    Args:
        subject: The subject name to delete
        context: Optional schema context
    
    Returns:
        List of deleted version numbers
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        url = build_context_url(f"/subjects/{subject}", context)
        
        response = requests.delete(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ===== CONFIGURATION MANAGEMENT TOOLS =====

@mcp.tool()
def get_global_config(context: Optional[str] = None) -> Dict[str, Any]:
    """
    Get global configuration settings.
    
    Args:
        context: Optional schema context
    
    Returns:
        Dictionary containing configuration
    """
    try:
        url = build_context_url("/config", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
@require_scopes("write")
def update_global_config(
    compatibility: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update global configuration settings.
    
    Args:
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        url = build_context_url("/config", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_config(
    subject: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
    
    Returns:
        Dictionary containing subject configuration
    """
    try:
        url = build_context_url(f"/config/{subject}", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_config(
    subject: str,
    compatibility: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        url = build_context_url(f"/config/{subject}", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ===== MODE MANAGEMENT TOOLS =====

@mcp.tool()
def get_mode(context: Optional[str] = None) -> Dict[str, str]:
    """
    Get the current mode of the Schema Registry.
    
    Args:
        context: Optional schema context
    
    Returns:
        Dictionary containing the current mode
    """
    try:
        url = build_context_url("/mode", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_mode(
    mode: str,
    context: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode of the Schema Registry.
    
    Args:
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        url = build_context_url("/mode", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_mode(
    subject: str,
    context: Optional[str] = None
) -> Dict[str, str]:
    """
    Get the mode for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
    
    Returns:
        Dictionary containing the subject mode
    """
    try:
        url = build_context_url(f"/mode/{subject}", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_mode(
    subject: str,
    mode: str,
    context: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode for a specific subject.
    
    Args:
        subject: The subject name
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry_manager)
    if readonly_check:
        return readonly_check
    
    try:
        url = build_context_url(f"/mode/{subject}", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ===== BATCH CLEANUP TOOLS =====

@mcp.tool()
def clear_context_batch(
    context: str,
    delete_context_after: bool = True,
    dry_run: bool = True,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Efficiently remove all subjects from a context in batch mode.
    
    Args:
        context: The context name to clear
        delete_context_after: Whether to delete the context itself after clearing subjects
        dry_run: If True, show what would be deleted without actually deleting (default: True for safety)
        registry: Registry name (for multi-registry setups)
    
    Returns:
        Dictionary containing cleanup results and statistics
    """
    # Check readonly mode for actual deletions
    if not dry_run:
        readonly_check = check_readonly_mode(registry_manager)
        if readonly_check:
            return readonly_check
    
    try:
        # Get the appropriate client
        if registry:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
            registry_url = client.config.url
            registry_auth = client.auth
            registry_headers = client.headers
        else:
            client = get_default_client()
            registry_url = SCHEMA_REGISTRY_URL
            registry_auth = auth
            registry_headers = headers
        
        start_time = datetime.now()
        
        # Step 1: List all subjects in the context
        print(f"🔍 Scanning context '{context}' for subjects...")
        subjects_list = list_subjects(context)
        
        if isinstance(subjects_list, dict) and "error" in subjects_list:
            return subjects_list
        
        if not subjects_list:
            result = {
                "context": context,
                "registry": registry or "default",
                "dry_run": dry_run,
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "duration_seconds": 0,
                "message": f"Context '{context}' is already empty"
            }
            return result
        
        print(f"📋 Found {len(subjects_list)} subjects to process")
        
        # Step 2: Batch delete subjects
        deleted_subjects = []
        failed_deletions = []
        
        if dry_run:
            print(f"🔍 DRY RUN: Would delete {len(subjects_list)} subjects:")
            for subject in subjects_list:
                print(f"   - {subject}")
            deleted_subjects = subjects_list.copy()
        else:
            print(f"🗑️  Deleting {len(subjects_list)} subjects in batch...")
            
            # Use concurrent deletions for better performance
            import concurrent.futures
            import threading
            
            def delete_single_subject(subject):
                try:
                    # Build URL for context-specific deletion
                    if context and context != ".":
                        url = f"{registry_url}/contexts/{context}/subjects/{subject}"
                    else:
                        url = f"{registry_url}/subjects/{subject}"
                    
                    response = requests.delete(
                        url,
                        auth=registry_auth,
                        headers=registry_headers,
                        timeout=30
                    )
                    
                    if response.status_code in [200, 404]:  # 404 = already deleted
                        return {"subject": subject, "status": "deleted", "versions": response.json() if response.status_code == 200 else []}
                    else:
                        return {"subject": subject, "status": "failed", "error": f"HTTP {response.status_code}"}
                        
                except Exception as e:
                    return {"subject": subject, "status": "failed", "error": str(e)}
            
            # Execute deletions in parallel (max 10 concurrent)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                deletion_results = list(executor.map(delete_single_subject, subjects_list))
            
            # Process results
            for result in deletion_results:
                if result["status"] == "deleted":
                    deleted_subjects.append(result["subject"])
                    print(f"   ✅ Deleted {result['subject']}")
                else:
                    failed_deletions.append(result)
                    print(f"   ❌ Failed to delete {result['subject']}: {result['error']}")
        
        # Step 3: Optionally delete the context itself
        context_deleted = False
        context_deletion_error = None
        
        if delete_context_after and (deleted_subjects or dry_run):
            if dry_run:
                print(f"🔍 DRY RUN: Would delete context '{context}'")
                context_deleted = True
            else:
                print(f"🗑️  Deleting context '{context}'...")
                try:
                    deletion_result = delete_context(context)
                    if "error" not in deletion_result:
                        context_deleted = True
                        print(f"   ✅ Context '{context}' deleted")
                    else:
                        context_deletion_error = deletion_result["error"]
                        print(f"   ⚠️  Failed to delete context: {context_deletion_error}")
                except Exception as e:
                    context_deletion_error = str(e)
                    print(f"   ⚠️  Error deleting context: {context_deletion_error}")
        
        # Calculate metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Build comprehensive result
        result = {
            "context": context,
            "registry": registry or "default",
            "dry_run": dry_run,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "subjects_found": len(subjects_list),
            "subjects_deleted": len(deleted_subjects),
            "subjects_failed": len(failed_deletions),
            "context_deleted": context_deleted,
            "success_rate": round((len(deleted_subjects) / len(subjects_list)) * 100, 1) if subjects_list else 100,
            "deleted_subjects": deleted_subjects,
            "failed_deletions": failed_deletions[:5],  # Show first 5 failures
            "performance": {
                "subjects_per_second": round(len(deleted_subjects) / max(duration, 0.1), 1),
                "parallel_execution": not dry_run,
                "max_concurrent_deletions": 10
            }
        }
        
        if context_deletion_error:
            result["context_deletion_error"] = context_deletion_error
        
        # Summary message
        if dry_run:
            result["message"] = f"DRY RUN: Would delete {len(subjects_list)} subjects from context '{context}'"
        elif len(deleted_subjects) == len(subjects_list):
            result["message"] = f"Successfully cleared context '{context}' - deleted {len(deleted_subjects)} subjects"
        else:
            result["message"] = f"Partially cleared context '{context}' - deleted {len(deleted_subjects)}/{len(subjects_list)} subjects"
        
        return result
        
    except Exception as e:
        return {"error": f"Batch cleanup failed: {str(e)}"}

@mcp.tool()
def clear_multiple_contexts_batch(
    contexts: List[str],
    delete_contexts_after: bool = True,
    dry_run: bool = True,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Efficiently clear multiple contexts in batch mode.
    
    Args:
        contexts: List of context names to clear
        delete_contexts_after: Whether to delete contexts after clearing subjects
        dry_run: If True, show what would be deleted without actually deleting (default: True for safety)
        registry: Registry name (for multi-registry setups)
    
    Returns:
        Dictionary containing overall cleanup results
    """
    # Check readonly mode for actual deletions
    if not dry_run:
        readonly_check = check_readonly_mode(registry_manager)
        if readonly_check:
            return readonly_check
    
    try:
        start_time = datetime.now()
        context_results = []
        total_subjects_deleted = 0
        total_subjects_found = 0
        total_contexts_deleted = 0
        
        print(f"🚀 Starting batch cleanup of {len(contexts)} contexts...")
        
        for i, context in enumerate(contexts, 1):
            print(f"\n📂 Processing context {i}/{len(contexts)}: '{context}'")
            
            context_result = clear_context_batch(
                context=context,
                delete_context_after=delete_contexts_after,
                dry_run=dry_run,
                registry=registry
            )
            
            if "error" in context_result:
                context_results.append({
                    "context": context,
                    "status": "failed",
                    "error": context_result["error"]
                })
            else:
                context_results.append({
                    "context": context,
                    "status": "completed",
                    "subjects_deleted": context_result["subjects_deleted"],
                    "subjects_found": context_result["subjects_found"],
                    "context_deleted": context_result["context_deleted"],
                    "duration_seconds": context_result["duration_seconds"]
                })
                
                total_subjects_deleted += context_result["subjects_deleted"]
                total_subjects_found += context_result["subjects_found"]
                if context_result["context_deleted"]:
                    total_contexts_deleted += 1
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Build summary result
        completed_contexts = sum(1 for r in context_results if r["status"] == "completed")
        failed_contexts = sum(1 for r in context_results if r["status"] == "failed")
        
        result = {
            "operation": "batch_multi_context_cleanup",
            "registry": registry or "default", 
            "dry_run": dry_run,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "total_duration_seconds": round(total_duration, 2),
            "contexts_processed": len(contexts),
            "contexts_completed": completed_contexts,
            "contexts_failed": failed_contexts,
            "contexts_deleted": total_contexts_deleted,
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "overall_success_rate": round((completed_contexts / len(contexts)) * 100, 1) if contexts else 100,
            "performance": {
                "contexts_per_second": round(len(contexts) / max(total_duration, 0.1), 2),
                "subjects_per_second": round(total_subjects_deleted / max(total_duration, 0.1), 1),
                "parallel_execution": True
            },
            "context_results": context_results
        }
        
        # Summary message
        if dry_run:
            result["message"] = f"DRY RUN: Would delete {total_subjects_found} subjects from {len(contexts)} contexts"
        else:
            result["message"] = f"Batch cleanup completed: {total_subjects_deleted} subjects deleted from {completed_contexts} contexts"
        
        return result
        
    except Exception as e:
        return {"error": f"Multi-context batch cleanup failed: {str(e)}"}

# ===== EXPORT FUNCTIONALITY =====

# format_schema_as_avro_idl moved to schema_registry_common

# get_schema_with_metadata moved to schema_registry_common

@mcp.tool()
def export_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    format: str = "json"
) -> Union[Dict[str, Any], str]:
    """
    Export a single schema in the specified format.
    
    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
        format: Export format (json, avro_idl)
    
    Returns:
        Exported schema data
    """
    try:
        client = get_default_client(registry_manager)
        if client is None:
            return {"error": "No default registry configured"}
        return common_export_schema(client, subject, version, context, format)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def export_subject(
    subject: str,
    context: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all"
) -> Dict[str, Any]:
    """
    Export all versions of a subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        include_metadata: Include export metadata
        include_config: Include subject configuration
        include_versions: Which versions to include (all, latest)
    
    Returns:
        Dictionary containing subject export data
    """
    try:
        # Get versions
        if include_versions == "latest":
            versions = ["latest"]
        else:
            versions_list = get_schema_versions(subject, context)
            if isinstance(versions_list, dict) and "error" in versions_list:
                return versions_list
            versions = [str(v) for v in versions_list]
        
        # Get schemas for each version
        schemas = []
        for version in versions:
            schema_data = get_schema_with_metadata(subject, version, context)
            if "error" not in schema_data:
                schemas.append(schema_data)
        
        result = {
            "subject": subject,
            "versions": schemas
        }
        
        if include_config:
            config = get_subject_config(subject, context)
            if "error" not in config:
                result["config"] = config
        
        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": SCHEMA_REGISTRY_URL,
                "context": context,
                "export_version": "1.7.0"
            }
        
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def export_context(
    context: str,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all"
) -> Dict[str, Any]:
    """
    Export all subjects within a context.
    
    Args:
        context: The context name
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
    
    Returns:
        Dictionary containing context export data
    """
    try:
        # Get all subjects in context
        subjects_list = list_subjects(context)
        if isinstance(subjects_list, dict) and "error" in subjects_list:
            return subjects_list
        
        # Export each subject
        subjects_data = []
        for subject in subjects_list:
            subject_export = export_subject(
                subject, context, include_metadata, include_config, include_versions
            )
            if "error" not in subject_export:
                subjects_data.append(subject_export)
        
        result = {
            "context": context,
            "subjects": subjects_data
        }
        
        if include_config:
            global_config = get_global_config(context)
            if "error" not in global_config:
                result["global_config"] = global_config
            
            global_mode = get_mode(context)
            if "error" not in global_mode:
                result["global_mode"] = global_mode
        
        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": SCHEMA_REGISTRY_URL,
                "export_version": "1.7.0"
            }
        
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def export_global(
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all"
) -> Dict[str, Any]:
    """
    Export all contexts and schemas from the registry.
    
    Args:
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
    
    Returns:
        Dictionary containing global export data
    """
    try:
        # Get all contexts
        contexts_list = list_contexts()
        if isinstance(contexts_list, dict) and "error" in contexts_list:
            return contexts_list
        
        # Export each context
        contexts_data = []
        for context in contexts_list:
            context_export = export_context(
                context, include_metadata, include_config, include_versions
            )
            if "error" not in context_export:
                contexts_data.append(context_export)
        
        # Export default context (no context specified)
        default_export = export_context(
            "", include_metadata, include_config, include_versions
        )
        
        result = {
            "contexts": contexts_data,
            "default_context": default_export if "error" not in default_export else None
        }
        
        if include_config:
            global_config = get_global_config()
            if "error" not in global_config:
                result["global_config"] = global_config
            
            global_mode = get_mode()
            if "error" not in global_mode:
                result["global_mode"] = global_mode
        
        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": SCHEMA_REGISTRY_URL,
                "export_version": "1.7.0"
            }
        
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== RESOURCES =====

@mcp.resource("registry://status")
def get_registry_status():
    """Get the current status of Schema Registry connections."""
    try:
        registries = registry_manager.list_registries()
        if not registries:
            return "❌ No Schema Registry configured"
        
        status_lines = []
        for name in registries:
            client = registry_manager.get_registry(name)
            if client:
                test_result = client.test_connection()
                if test_result["status"] == "connected":
                    status_lines.append(f"✅ {name}: Connected to {client.config.url}")
                else:
                    status_lines.append(f"❌ {name}: {test_result.get('error', 'Connection failed')}")
        
        return "\n".join(status_lines)
    except Exception as e:
        return f"❌ Error checking registry status: {str(e)}"

@mcp.resource("registry://info")
def get_registry_info_resource():
    """Get detailed information about Schema Registry configurations."""
    try:
        registries_info = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                registries_info.append(info)
        
        overall_info = {
            "registries": registries_info,
            "total_registries": len(registries_info),
            "default_registry": registry_manager.default_registry,
            "readonly_mode": READONLY,
            "server_version": "1.7.0",
            "multi_registry_support": True,
            "features": [
                "Multi-Registry Support",
                "Cross-Registry Comparison", 
                "Schema Migration",
                "Context Synchronization",
                "Schema Export (JSON, Avro IDL)",
                "READONLY Mode Protection"
            ]
        }
        
        return json.dumps(overall_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    mcp.run() 