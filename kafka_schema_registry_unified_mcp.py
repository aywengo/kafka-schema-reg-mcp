#!/usr/bin/env python3
"""
Kafka Schema Registry Unified MCP Server - Modular Version

A comprehensive Message Control Protocol (MCP) server that automatically detects
and supports both single and multi-registry modes based on environment variables.

This modular version splits functionality across specialized modules:
- task_management: Async task queue operations
- migration_tools: Schema and context migration
- comparison_tools: Registry and context comparison
- export_tools: Schema export functionality
- batch_operations: Batch cleanup operations
- statistics_tools: Counting and statistics
- core_registry_tools: Basic CRUD operations

Features:
- Automatic mode detection
- 48 MCP Tools (all original tools + multi-registry extensions)
- Cross-Registry Comparison and Migration
- Schema Export/Import with multiple formats
- Async Task Queue for long-running operations
- READONLY Mode protection
- OAuth scopes support
"""

import os
import json
import logging
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

# Load environment variables first
load_dotenv()

# Import OAuth functionality
from oauth_provider import (
    ENABLE_AUTH, require_scopes, get_oauth_scopes_info, get_fastmcp_config
)

# Initialize FastMCP with OAuth configuration
mcp_config = get_fastmcp_config("Kafka Schema Registry Unified MCP Server")
mcp = FastMCP(**mcp_config)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import specialized modules
from task_management import task_manager, get_operation_info
from migration_tools import (
    migrate_schema_tool, list_migrations_tool, get_migration_status_tool, migrate_context_tool
)
from comparison_tools import (
    compare_registries_tool, compare_contexts_across_registries_tool, find_missing_schemas_tool
)
from export_tools import (
    export_schema_tool, export_subject_tool, export_context_tool, export_global_tool
)
from batch_operations import (
    clear_context_batch_tool, clear_multiple_contexts_batch_tool
)
from statistics_tools import (
    count_contexts_tool, count_schemas_tool, count_schema_versions_tool, get_registry_statistics_tool
)
from core_registry_tools import (
    register_schema_tool, get_schema_tool, get_schema_versions_tool, list_subjects_tool,
    check_compatibility_tool, get_global_config_tool, update_global_config_tool,
    get_subject_config_tool, update_subject_config_tool, get_mode_tool, update_mode_tool,
    get_subject_mode_tool, update_subject_mode_tool, list_contexts_tool, create_context_tool,
    delete_context_tool, delete_subject_tool
)

# Import common library functionality
from schema_registry_common import (
    RegistryConfig, RegistryClient, LegacyRegistryManager, MultiRegistryManager,
    check_readonly_mode as _check_readonly_mode, build_context_url, get_default_client,
    SINGLE_REGISTRY_URL, SINGLE_REGISTRY_USER, SINGLE_REGISTRY_PASSWORD, SINGLE_READONLY
)

# Auto-detection of registry mode
def detect_registry_mode() -> str:
    """Auto-detect whether to use single or multi-registry mode."""
    # Check for legacy single-registry env vars
    has_legacy = any([
        os.getenv("SCHEMA_REGISTRY_URL"),
        os.getenv("SCHEMA_REGISTRY_USER"),
        os.getenv("SCHEMA_REGISTRY_PASSWORD")
    ])
    
    # Check for numbered multi-registry env vars
    has_numbered = any([
        os.getenv("SCHEMA_REGISTRY_URL_1"),
        os.getenv("SCHEMA_REGISTRY_USER_1"),
        os.getenv("SCHEMA_REGISTRY_PASSWORD_1")
    ])
    
    # Check for REGISTRIES_CONFIG
    has_config = os.getenv("REGISTRIES_CONFIG", "").strip() != ""
    
    if has_numbered or has_config:
        return "multi"
    elif has_legacy:
        return "single" 
    else:
        # Default to multi-registry mode if no env vars detected
        return "multi"

# Detect mode and initialize appropriate manager
REGISTRY_MODE = detect_registry_mode()
logger.info(f"🔍 Auto-detected registry mode: {REGISTRY_MODE}")

if REGISTRY_MODE == "single":
    logger.info("📡 Initializing Single Registry Manager")
    registry_manager = LegacyRegistryManager("")
    
    # Legacy compatibility globals
    SCHEMA_REGISTRY_URL = SINGLE_REGISTRY_URL
    SCHEMA_REGISTRY_USER = SINGLE_REGISTRY_USER
    SCHEMA_REGISTRY_PASSWORD = SINGLE_REGISTRY_PASSWORD
    READONLY = SINGLE_READONLY
    
    # Set up authentication if configured
    auth = None
    headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    standard_headers = {"Content-Type": "application/json"}
    
    if SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD:
        from requests.auth import HTTPBasicAuth
        import base64
        auth = HTTPBasicAuth(SCHEMA_REGISTRY_USER, SCHEMA_REGISTRY_PASSWORD)
        credentials = base64.b64encode(f"{SCHEMA_REGISTRY_USER}:{SCHEMA_REGISTRY_PASSWORD}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
        standard_headers["Authorization"] = f"Basic {credentials}"
else:
    logger.info("🌐 Initializing Multi-Registry Manager")
    registry_manager = MultiRegistryManager()
    
    # Multi-registry globals
    SCHEMA_REGISTRY_URL = ""
    SCHEMA_REGISTRY_USER = ""
    SCHEMA_REGISTRY_PASSWORD = ""
    READONLY = False
    auth = None
    headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    standard_headers = {"Content-Type": "application/json"}

# ===== UNIFIED REGISTRY MANAGEMENT TOOLS =====

@mcp.tool()
@require_scopes("read")
def list_registries():
    """List all configured Schema Registry instances."""
    try:
        result = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                result.append(info)
        if result:
            result[0]["registry_mode"] = REGISTRY_MODE
        return result
    except Exception as e:
        return [{"error": str(e), "registry_mode": REGISTRY_MODE}]

@mcp.tool()
@require_scopes("read") 
def get_registry_info(registry_name: str = None):
    """Get detailed information about a specific registry."""
    try:
        if REGISTRY_MODE == "single" and not registry_name:
            registry_name = registry_manager.get_default_registry()
        info = registry_manager.get_registry_info(registry_name)
        if info is None:
            return {"error": f"Registry '{registry_name}' not found", "registry_mode": REGISTRY_MODE}
        info["registry_mode"] = REGISTRY_MODE
        return info
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

@mcp.tool()
@require_scopes("read")
def test_registry_connection(registry_name: str = None):
    """Test connection to a specific registry."""
    try:
        if REGISTRY_MODE == "single" and not registry_name:
            registry_name = registry_manager.get_default_registry()
        client = registry_manager.get_registry(registry_name)
        if client is None:
            return {"error": f"Registry '{registry_name}' not found", "registry_mode": REGISTRY_MODE}
        result = client.test_connection()
        result["registry_mode"] = REGISTRY_MODE
        return result
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

@mcp.tool()
@require_scopes("read")
async def test_all_registries():
    """Test connections to all configured registries."""
    try:
        if REGISTRY_MODE == "single":
            default_registry = registry_manager.get_default_registry()
            if default_registry:
                client = registry_manager.get_registry(default_registry)
                if client:
                    result = client.test_connection()
                    return {
                        "registry_tests": {default_registry: result},
                        "total_registries": 1,
                        "connected": 1 if result.get("status") == "connected" else 0,
                        "failed": 0 if result.get("status") == "connected" else 1,
                        "registry_mode": "single"
                    }
            return {"error": "No registry configured", "registry_mode": "single"}
        else:
            result = await registry_manager.test_all_registries_async()
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

# ===== COMPARISON TOOLS =====

@mcp.tool()
@require_scopes("read")
async def compare_registries(source_registry: str, target_registry: str, include_contexts: bool = True, include_configs: bool = True):
    """Compare two Schema Registry instances and show differences."""
    return await compare_registries_tool(source_registry, target_registry, registry_manager, REGISTRY_MODE, include_contexts, include_configs)

@mcp.tool()
@require_scopes("read") 
async def compare_contexts_across_registries(source_registry: str, target_registry: str, source_context: str, target_context: str = None):
    """Compare contexts across two registries."""
    return await compare_contexts_across_registries_tool(source_registry, target_registry, source_context, registry_manager, REGISTRY_MODE, target_context)

@mcp.tool()
@require_scopes("read")
async def find_missing_schemas(source_registry: str, target_registry: str, context: str = None):
    """Find schemas that exist in source registry but not in target registry."""
    return await find_missing_schemas_tool(source_registry, target_registry, registry_manager, REGISTRY_MODE, context)

# ===== SCHEMA MANAGEMENT TOOLS =====

@mcp.tool()
@require_scopes("write")
def register_schema(subject: str, schema_definition: dict, schema_type: str = "AVRO", context: str = None, registry: str = None):
    """Register a new schema version."""
    return register_schema_tool(subject, schema_definition, registry_manager, REGISTRY_MODE, schema_type, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("read")
def get_schema(subject: str, version: str = "latest", context: str = None, registry: str = None):
    """Get a specific version of a schema."""
    return get_schema_tool(subject, registry_manager, REGISTRY_MODE, version, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
def get_schema_versions(subject: str, context: str = None, registry: str = None):
    """Get all versions of a schema for a subject."""
    return get_schema_versions_tool(subject, registry_manager, REGISTRY_MODE, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("read")
def list_subjects(context: str = None, registry: str = None):
    """List all subjects, optionally filtered by context."""
    return list_subjects_tool(registry_manager, REGISTRY_MODE, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
def check_compatibility(subject: str, schema_definition: dict, schema_type: str = "AVRO", context: str = None, registry: str = None):
    """Check if a schema is compatible with the latest version."""
    return check_compatibility_tool(subject, schema_definition, registry_manager, REGISTRY_MODE, schema_type, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

# ===== CONFIGURATION TOOLS =====

@mcp.tool()
def get_global_config(context: str = None, registry: str = None):
    """Get global configuration settings."""
    return get_global_config_tool(registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("write")
def update_global_config(compatibility: str, context: str = None, registry: str = None):
    """Update global configuration settings."""
    return update_global_config_tool(compatibility, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
def get_subject_config(subject: str, context: str = None, registry: str = None):
    """Get configuration settings for a specific subject."""
    return get_subject_config_tool(subject, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("write")
def update_subject_config(subject: str, compatibility: str, context: str = None, registry: str = None):
    """Update configuration settings for a specific subject."""
    return update_subject_config_tool(subject, compatibility, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

# ===== MODE TOOLS =====

@mcp.tool()
def get_mode(context: str = None, registry: str = None):
    """Get the current mode of the Schema Registry."""
    return get_mode_tool(registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("write")
def update_mode(mode: str, context: str = None, registry: str = None):
    """Update the mode of the Schema Registry."""
    return update_mode_tool(mode, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
def get_subject_mode(subject: str, context: str = None, registry: str = None):
    """Get the mode for a specific subject."""
    return get_subject_mode_tool(subject, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("write")
def update_subject_mode(subject: str, mode: str, context: str = None, registry: str = None):
    """Update the mode for a specific subject."""
    return update_subject_mode_tool(subject, mode, registry_manager, REGISTRY_MODE, context, registry, auth, standard_headers, SCHEMA_REGISTRY_URL)

# ===== CONTEXT TOOLS =====

@mcp.tool()
def list_contexts(registry: str = None):
    """List all available schema contexts."""
    return list_contexts_tool(registry_manager, REGISTRY_MODE, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("write")
def create_context(context: str, registry: str = None):
    """Create a new schema context."""
    return create_context_tool(context, registry_manager, REGISTRY_MODE, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("admin")
def delete_context(context: str, registry: str = None):
    """Delete a schema context."""
    return delete_context_tool(context, registry_manager, REGISTRY_MODE, registry, auth, headers, SCHEMA_REGISTRY_URL)

@mcp.tool()
@require_scopes("admin")
async def delete_subject(subject: str, context: str = None, registry: str = None):
    """Delete a subject and all its versions."""
    return await delete_subject_tool(subject, registry_manager, REGISTRY_MODE, context, registry, auth, headers, SCHEMA_REGISTRY_URL)

# ===== EXPORT TOOLS =====

@mcp.tool()
def export_schema(subject: str, version: str = "latest", context: str = None, format: str = "json", registry: str = None):
    """Export a single schema in the specified format."""
    return export_schema_tool(subject, registry_manager, REGISTRY_MODE, version, context, format, registry)

@mcp.tool()
def export_subject(subject: str, context: str = None, include_metadata: bool = True, include_config: bool = True, include_versions: str = "all", registry: str = None):
    """Export all versions of a subject."""
    return export_subject_tool(subject, registry_manager, REGISTRY_MODE, context, include_metadata, include_config, include_versions, registry)

@mcp.tool()
def export_context(context: str, registry: str = None, include_metadata: bool = True, include_config: bool = True, include_versions: str = "all"):
    """Export all subjects within a context."""
    return export_context_tool(context, registry_manager, REGISTRY_MODE, registry, include_metadata, include_config, include_versions)

@mcp.tool()
def export_global(registry: str = None, include_metadata: bool = True, include_config: bool = True, include_versions: str = "all"):
    """Export all contexts and schemas from a registry."""
    return export_global_tool(registry_manager, REGISTRY_MODE, registry, include_metadata, include_config, include_versions)

# ===== MIGRATION TOOLS =====

@mcp.tool()
@require_scopes("admin")
def migrate_schema(subject: str, source_registry: str, target_registry: str, dry_run: bool = False, preserve_ids: bool = True, source_context: str = ".", target_context: str = ".", versions: list = None, migrate_all_versions: bool = False):
    """Migrate a schema from one registry to another."""
    return migrate_schema_tool(subject, source_registry, target_registry, registry_manager, REGISTRY_MODE, dry_run, preserve_ids, source_context, target_context, versions, migrate_all_versions)

@mcp.tool()
def list_migrations():
    """List all migration tasks and their status."""
    return list_migrations_tool(REGISTRY_MODE)

@mcp.tool()
def get_migration_status(migration_id: str):
    """Get detailed status of a specific migration."""
    return get_migration_status_tool(migration_id, REGISTRY_MODE)

@mcp.tool()
@require_scopes("admin")
async def migrate_context(source_registry: str, target_registry: str, context: str = None, target_context: str = None, preserve_ids: bool = True, dry_run: bool = True, migrate_all_versions: bool = True):
    """Guide for migrating an entire context using Docker-based tools."""
    return await migrate_context_tool(source_registry, target_registry, registry_manager, REGISTRY_MODE, context, target_context, preserve_ids, dry_run, migrate_all_versions)

# ===== BATCH OPERATIONS =====

@mcp.tool()
@require_scopes("admin")
def clear_context_batch(context: str, registry: str = None, delete_context_after: bool = True, dry_run: bool = True):
    """Clear all subjects in a context using batch operations."""
    return clear_context_batch_tool(context, registry_manager, REGISTRY_MODE, registry, delete_context_after, dry_run)

@mcp.tool()
@require_scopes("admin")
def clear_multiple_contexts_batch(contexts: list, registry: str = None, delete_contexts_after: bool = True, dry_run: bool = True):
    """Clear multiple contexts in a registry in batch mode."""
    return clear_multiple_contexts_batch_tool(contexts, registry_manager, REGISTRY_MODE, registry, delete_contexts_after, dry_run)

# ===== STATISTICS TOOLS =====

@mcp.tool()
def count_contexts(registry: str = None):
    """Count the number of contexts in a registry."""
    return count_contexts_tool(registry_manager, REGISTRY_MODE, registry)

@mcp.tool()
def count_schemas(context: str = None, registry: str = None):
    """Count the number of schemas in a context or registry."""
    return count_schemas_tool(registry_manager, REGISTRY_MODE, context, registry)

@mcp.tool()
def count_schema_versions(subject: str, context: str = None, registry: str = None):
    """Count the number of versions for a specific schema."""
    return count_schema_versions_tool(subject, registry_manager, REGISTRY_MODE, context, registry)

@mcp.tool()
def get_registry_statistics(registry: str = None, include_context_details: bool = True):
    """Get comprehensive statistics about a registry."""
    return get_registry_statistics_tool(registry_manager, REGISTRY_MODE, registry, include_context_details)

# ===== TASK MANAGEMENT TOOLS =====

@mcp.tool()
def get_task_status(task_id: str):
    """Get the status and progress of an async task."""
    try:
        task = task_manager.get_task(task_id)
        if task is None:
            return {"error": f"Task '{task_id}' not found"}
        return task.to_dict()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_task_progress(task_id: str):
    """Get the progress of an async task (alias for get_task_status)."""
    task_status = get_task_status(task_id)
    if "error" in task_status:
        return task_status
    return {
        "task_id": task_id,
        "status": task_status["status"],
        "progress_percent": task_status["progress"],
        "started_at": task_status["started_at"],
        "completed_at": task_status["completed_at"],
        "error": task_status["error"],
        "result": task_status["result"]
    }

@mcp.tool()
def list_active_tasks():
    """List all active tasks in the system."""
    try:
        tasks = task_manager.list_tasks()
        return {
            "tasks": [task.to_dict() for task in tasks],
            "total_tasks": len(tasks),
            "active_tasks": len([t for t in tasks if t.status.value in ["pending", "running"]])
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def cancel_task(task_id: str):
    """Cancel a running task."""
    try:
        cancelled = await task_manager.cancel_task(task_id)
        if cancelled:
            return {"message": f"Task '{task_id}' cancelled successfully"}
        else:
            return {"error": f"Could not cancel task '{task_id}' (may already be completed)"}
    except Exception as e:
        return {"error": str(e)}

# ===== UTILITY TOOLS =====

@mcp.tool()
def set_default_registry(registry_name: str):
    """Set the default registry."""
    try:
        if REGISTRY_MODE == "single":
            return {
                "error": "Default registry setting not available in single-registry mode",
                "registry_mode": "single",
                "current_registry": registry_manager.get_default_registry() if hasattr(registry_manager, 'get_default_registry') else "default"
            }
        
        if registry_manager.set_default_registry(registry_name):
            return {
                "message": f"Default registry set to '{registry_name}'",
                "default_registry": registry_name,
                "registry_mode": "multi"
            }
        else:
            return {"error": f"Registry '{registry_name}' not found", "registry_mode": "multi"}
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

@mcp.tool()
def get_default_registry():
    """Get the current default registry."""
    try:
        if REGISTRY_MODE == "single":
            default = registry_manager.get_default_registry() if hasattr(registry_manager, 'get_default_registry') else "default"
            return {
                "default_registry": default,
                "registry_mode": "single",
                "info": registry_manager.get_registry_info(default) if default else None
            }
        else:
            default = registry_manager.get_default_registry()
            if default:
                return {
                    "default_registry": default,
                    "registry_mode": "multi",
                    "info": registry_manager.get_registry_info(default)
                }
            else:
                return {"error": "No default registry configured", "registry_mode": "multi"}
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

@mcp.tool()
def check_readonly_mode(registry: str = None):
    """Check if a registry is in readonly mode."""
    return _check_readonly_mode(registry_manager, registry)

@mcp.tool()
def get_oauth_scopes_info():
    """Get information about OAuth scopes and permissions."""
    return get_oauth_scopes_info()

@mcp.tool()
def get_operation_info_tool(operation_name: str = None):
    """Get information about MCP operations."""
    try:
        if operation_name:
            return get_operation_info(operation_name, REGISTRY_MODE)
        else:
            # Return all operation metadata
            from task_management import OPERATION_METADATA
            all_ops = {}
            for op_name in OPERATION_METADATA.keys():
                all_ops[op_name] = get_operation_info(op_name, REGISTRY_MODE)
            
            # Add summary statistics
            quick_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "quick")
            medium_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "medium")
            long_ops = sum(1 for info in all_ops.values() if info["expected_duration"] == "long")
            task_queue_ops = sum(1 for info in all_ops.values() if info["async_pattern"] == "task_queue")
            
            return {
                "operations": all_ops,
                "registry_mode": REGISTRY_MODE,
                "summary": {
                    "total_operations": len(all_ops),
                    "quick_operations": quick_ops,
                    "medium_operations": medium_ops,
                    "long_operations": long_ops,
                    "task_queue_operations": task_queue_ops,
                    "direct_operations": len(all_ops) - task_queue_ops
                },
                "guidance": {
                    "task_queue_pattern": "Operations that return task_id require polling with get_task_status()",
                    "direct_pattern": "Operations that return results immediately",
                    "timeout_recommendation": "Set MCP client timeouts to at least 60 seconds for medium/long operations"
                }
            }
    except Exception as e:
        return {"error": str(e), "registry_mode": REGISTRY_MODE}

# ===== RESOURCES =====

@mcp.resource("registry://status")
def get_registry_status():
    """Get the current status of Schema Registry connections."""
    try:
        registries = registry_manager.list_registries()
        if not registries:
            return "❌ No Schema Registry configured"
        
        status_lines = [f"🔧 Registry Mode: {REGISTRY_MODE.upper()}"]
        
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
            "registry_mode": REGISTRY_MODE,
            "registries": registries_info,
            "total_registries": len(registries_info),
            "default_registry": registry_manager.get_default_registry() if hasattr(registry_manager, 'get_default_registry') else None,
            "readonly_mode": READONLY if REGISTRY_MODE == "single" else False,
            "server_version": "2.0.0-unified-modular",
            "features": [
                f"Unified {REGISTRY_MODE.title()} Registry Support",
                "Auto-Mode Detection",
                "Cross-Registry Comparison" if REGISTRY_MODE == "multi" else "Single Registry Operations",
                "Schema Migration",
                "Context Management",
                "Schema Export (JSON, Avro IDL)",
                "READONLY Mode Protection",
                "OAuth Scopes Support",
                "Async Task Queue",
                "Modular Architecture"
            ]
        }
        
        return json.dumps(overall_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "registry_mode": REGISTRY_MODE}, indent=2)

@mcp.resource("registry://mode")
def get_mode_info():
    """Get information about the current registry mode and how it was detected."""
    try:
        detection_info = {
            "current_mode": REGISTRY_MODE,
            "detection_logic": {
                "single_mode_triggers": [
                    "SCHEMA_REGISTRY_URL environment variable",
                    "SCHEMA_REGISTRY_USER environment variable", 
                    "SCHEMA_REGISTRY_PASSWORD environment variable"
                ],
                "multi_mode_triggers": [
                    "SCHEMA_REGISTRY_URL_1 (or _2, _3, etc.) environment variable",
                    "SCHEMA_REGISTRY_USER_1 (or _2, _3, etc.) environment variable",
                    "SCHEMA_REGISTRY_PASSWORD_1 (or _2, _3, etc.) environment variable",
                    "REGISTRIES_CONFIG environment variable"
                ]
            },
            "architecture": "modular",
            "modules": [
                "task_management",
                "migration_tools",
                "comparison_tools", 
                "export_tools",
                "batch_operations",
                "statistics_tools",
                "core_registry_tools"
            ]
        }
        
        return json.dumps(detection_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    print(f"""
🚀 Kafka Schema Registry Unified MCP Server Starting (Modular)
📡 Mode: {REGISTRY_MODE.upper()}
🔧 Registries: {len(registry_manager.list_registries())}
🛡️  OAuth: {"Enabled" if ENABLE_AUTH else "Disabled"}
📦 Architecture: Modular (8 specialized modules)
    """)
    
    # Log startup information
    logger.info(f"Starting Unified MCP Server in {REGISTRY_MODE} mode (modular architecture)")
    logger.info(f"Detected {len(registry_manager.list_registries())} registry configurations")
    
    mcp.run() 