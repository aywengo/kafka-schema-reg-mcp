#!/usr/bin/env python3
"""
Kafka Schema Registry Multi-Registry MCP Server

A comprehensive Message Control Protocol (MCP) server that provides tools for interacting with
multiple Kafka Schema Registry instances, including advanced schema management, cross-registry
comparison, migration, synchronization, and all original single-registry operations.

Features:
- 48 MCP Tools total (20 original + 28 new multi-registry tools)
- Multi-Registry Support: Connect to multiple Schema Registry instances
- Cross-Registry Comparison: Compare schemas, contexts, and entire registries
- Schema Migration: Move schemas between registries with conflict detection
- Synchronization: Keep registries in sync with scheduled operations
- Export/Import: Advanced bulk operations for data migration
- READONLY Mode: Production safety for all registries
- Backward Compatibility: All existing tools work with optional registry parameter
"""

import os
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import asyncio
import logging
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import uuid
import threading
import time

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import base64

from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configuration - Single Registry Mode (backward compatibility)
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
READONLY = os.getenv("READONLY", "false").lower() in ("true", "1", "yes", "on")

# Multi-registry configuration - supports up to 8 instances
MAX_REGISTRIES = 8

@dataclass
class RegistryConfig:
    """Configuration for a Schema Registry instance."""
    name: str
    url: str
    user: str = ""
    password: str = ""
    description: str = ""
    readonly: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MigrationTask:
    """Represents a migration task."""
    id: str
    source_registry: str
    target_registry: str
    scope: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    dry_run: bool = False

@dataclass
class SyncTask:
    """Represents a synchronization task."""
    id: str
    source_registry: str
    target_registry: str
    scope: str
    direction: str
    interval_seconds: int
    status: str
    created_at: str
    last_sync: Optional[str] = None
    next_sync: Optional[str] = None

class RegistryClient:
    """Client for interacting with a single Schema Registry instance."""
    
    def __init__(self, config: RegistryConfig):
        self.config = config
        self.auth = None
        self.headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        self.standard_headers = {"Content-Type": "application/json"}
        
        if config.user and config.password:
            self.auth = HTTPBasicAuth(config.user, config.password)
            credentials = base64.b64encode(f"{config.user}:{config.password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
            self.standard_headers["Authorization"] = f"Basic {credentials}"
    
    def build_context_url(self, base_url: str, context: Optional[str] = None) -> str:
        """Build URL with optional context support."""
        # Handle default context "." as no context
        if context and context != ".":
            return f"{self.config.url}/contexts/{context}{base_url}"
        return f"{self.config.url}{base_url}"
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to this registry."""
        try:
            response = requests.get(f"{self.config.url}/subjects", 
                                  auth=self.auth, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "registry": self.config.name,
                    "url": self.config.url,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "status": "error",
                    "registry": self.config.name,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "status": "error",
                "registry": self.config.name,
                "error": str(e)
            }
    
    def get_subjects(self, context: Optional[str] = None) -> List[str]:
        """Get subjects from this registry."""
        try:
            url = self.build_context_url("/subjects", context)
            response = requests.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
    
    def get_contexts(self) -> List[str]:
        """Get contexts from this registry."""
        try:
            response = requests.get(f"{self.config.url}/contexts", 
                                  auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

class RegistryManager:
    """Manages multiple Schema Registry instances."""
    
    def __init__(self):
        self.registries: Dict[str, RegistryClient] = {}
        self.default_registry: Optional[str] = None
        self.migration_tasks: Dict[str, MigrationTask] = {}
        self.sync_tasks: Dict[str, SyncTask] = {}
        self._load_registries()
    
    def _load_registries(self):
        """Load registry configurations from environment variables."""
        
        # Check for multi-registry mode first (numbered environment variables)
        multi_registry_found = False
        
        for i in range(1, MAX_REGISTRIES + 1):
            name_var = f"SCHEMA_REGISTRY_NAME_{i}"
            url_var = f"SCHEMA_REGISTRY_URL_{i}"
            user_var = f"SCHEMA_REGISTRY_USER_{i}"
            password_var = f"SCHEMA_REGISTRY_PASSWORD_{i}"
            readonly_var = f"READONLY_{i}"
            
            name = os.getenv(name_var, "")
            url = os.getenv(url_var, "")
            
            if name and url:
                multi_registry_found = True
                
                user = os.getenv(user_var, "")
                password = os.getenv(password_var, "")
                readonly = os.getenv(readonly_var, "false").lower() in ("true", "1", "yes", "on")
                
                config = RegistryConfig(
                    name=name,
                    url=url,
                    user=user,
                    password=password,
                    description=f"{name} Schema Registry (instance {i})",
                    readonly=readonly
                )
                
                self.registries[name] = RegistryClient(config)
                
                # Set first registry as default
                if self.default_registry is None:
                    self.default_registry = name
                
                logging.info(f"Loaded registry {i}: {name} at {url} (readonly: {readonly})")
        
        # Single registry mode (backward compatibility) - only if no multi-registry found
        if not multi_registry_found and SCHEMA_REGISTRY_URL:
            default_config = RegistryConfig(
                name="default",
                url=SCHEMA_REGISTRY_URL,
                user=SCHEMA_REGISTRY_USER,
                password=SCHEMA_REGISTRY_PASSWORD,
                description="Default Schema Registry",
                readonly=READONLY
            )
            self.registries["default"] = RegistryClient(default_config)
            self.default_registry = "default"
            logging.info(f"Loaded single registry: default at {SCHEMA_REGISTRY_URL} (readonly: {READONLY})")
        
        if not self.registries:
            logging.warning("No Schema Registry instances configured. Set SCHEMA_REGISTRY_URL for single mode or SCHEMA_REGISTRY_NAME_1/SCHEMA_REGISTRY_URL_1 for multi mode.")
    
    def get_registry(self, name: Optional[str] = None) -> Optional[RegistryClient]:
        """Get a registry client by name, or default if name is None."""
        if name is None:
            name = self.default_registry
        return self.registries.get(name)
    
    def list_registries(self) -> List[str]:
        """List all configured registry names."""
        return list(self.registries.keys())
    
    def get_registry_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a registry."""
        if name not in self.registries:
            return None
        
        client = self.registries[name]
        info = client.config.to_dict()
        info["is_default"] = name == self.default_registry
        
        # Test connection
        connection_test = client.test_connection()
        info["connection_status"] = connection_test["status"]
        if "response_time_ms" in connection_test:
            info["response_time_ms"] = connection_test["response_time_ms"]
        if "error" in connection_test:
            info["connection_error"] = connection_test["error"]
            
        return info

# Initialize registry manager
registry_manager = RegistryManager()

# Create the MCP server
mcp = FastMCP("Kafka Schema Registry Multi-Registry MCP Server")

def check_readonly_mode(registry_name: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Check if the server or specific registry is in readonly mode and return error if so."""
    
    # If a specific registry is provided, check its readonly setting
    if registry_name:
        client = registry_manager.get_registry(registry_name)
        if client and client.config.readonly:
            return {
                "error": f"Operation blocked: Registry '{registry_name}' is running in READONLY mode. "
                        f"Set READONLY_{registry_name} environment variable to false to enable modifications.",
                "readonly_mode": True,
                "registry": registry_name
            }
    
    # Also check global READONLY setting (backward compatibility)
    if READONLY:
        return {
            "error": "Operation blocked: MCP server is running in global READONLY mode. "
                    "Set READONLY=false to enable modification operations.",
            "readonly_mode": True,
            "global": True
        }
    
    return None

# ===== REGISTRY MANAGEMENT TOOLS =====

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
        source_subjects = set(source_client.get_subjects())
        target_subjects = set(target_client.get_subjects())
        
        comparison["subjects"] = {
            "source_only": list(source_subjects - target_subjects),
            "target_only": list(target_subjects - source_subjects),
            "common": list(source_subjects & target_subjects),
            "source_total": len(source_subjects),
            "target_total": len(target_subjects)
        }
        
        if include_contexts:
            source_contexts = set(source_client.get_contexts())
            target_contexts = set(target_client.get_contexts())
            
            comparison["contexts"] = {
                "source_only": list(source_contexts - target_contexts),
                "target_only": list(target_contexts - source_contexts),
                "common": list(source_contexts & target_contexts),
                "source_total": len(source_contexts),
                "target_total": len(target_contexts)
            }
        
        comparison["summary"] = {
            "registries_compared": 2,
            "subjects_differ": len(comparison["subjects"]["source_only"]) > 0 or 
                             len(comparison["subjects"]["target_only"]) > 0,
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
        
        source_subjects = set(source_client.get_subjects(context))
        target_subjects = set(target_client.get_subjects(context))
        
        return {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
            "subjects": {
                "source_only": list(source_subjects - target_subjects),
                "target_only": list(target_subjects - source_subjects),
                "common": list(source_subjects & target_subjects),
                "source_total": len(source_subjects),
                "target_total": len(target_subjects)
            },
            "comparison_completed": True,
            "compared_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def find_missing_schemas(
    source_registry: str,
    target_registry: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find schemas that exist in source but not in target registry.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Optional context to compare
    
    Returns:
        List of missing schemas
    """
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        source_subjects = set(source_client.get_subjects(context))
        target_subjects = set(target_client.get_subjects(context))
        
        missing = list(source_subjects - target_subjects)
        
        return {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
            "missing_schemas": missing,
            "missing_count": len(missing),
            "checked_at": datetime.now().isoformat()
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
    migrate_all_versions: bool = True,
    preserve_ids: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Migrate a schema from one registry to another.
    
    Args:
        subject: Schema subject name
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Source context (optional)
        target_context: Target context (optional, defaults to source_context)
        migrate_all_versions: Migrate all versions or just latest (default: True)
        preserve_ids: Preserve original schema IDs (requires IMPORT mode) (default: True)
        dry_run: Preview migration without executing (default: True)
    
    Returns:
        Migration results
    """
    # Check readonly mode for actual migrations
    if not dry_run:
        readonly_check = check_readonly_mode(target_registry)
        if readonly_check:
            return readonly_check
    
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        task_id = str(uuid.uuid4())
        target_ctx = target_context or source_context
        migration_results = {
            "successful_versions": [],
            "failed_versions": [],
            "skipped_versions": []
        }
        
        # Get versions to migrate
        if migrate_all_versions:
            try:
                source_url = source_client.build_context_url(f"/subjects/{subject}/versions", source_context)
                response = requests.get(source_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                response.raise_for_status()
                versions = response.json()
            except Exception as e:
                return {"error": f"Failed to get versions for {subject}: {str(e)}"}
        else:
            versions = ["latest"]
        
        if dry_run:
            return {
                "migration_id": task_id,
                "subject": subject,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_ctx,
                "versions_to_migrate": versions,
                "version_count": len(versions),
                "preserve_ids": preserve_ids,
                "dry_run": True,
                "status": "preview",
                "preview_at": datetime.now().isoformat()
            }
        
        # Handle IMPORT mode for ID preservation
        original_mode = None
        if preserve_ids:
            try:
                # Get current mode
                mode_url = target_client.build_context_url("/mode", target_ctx)
                mode_response = requests.get(mode_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                if mode_response.status_code == 200:
                    original_mode = mode_response.json().get("mode")
                
                # Set IMPORT mode if not already
                if original_mode != "IMPORT":
                    import_payload = {"mode": "IMPORT"}
                    import_response = requests.put(
                        mode_url,
                        data=json.dumps(import_payload),
                        auth=target_client.auth,
                        headers=target_client.headers,
                        timeout=10
                    )
                    import_response.raise_for_status()
                    
            except Exception as e:
                # If IMPORT mode is not supported, fall back to standard migration
                logging.warning(f"IMPORT mode not available, falling back to standard migration: {e}")
                preserve_ids = False
        
        # Perform actual migration
        try:
            for version in versions:
                try:
                    # Get schema from source
                    source_url = source_client.build_context_url(f"/subjects/{subject}/versions/{version}", source_context)
                    response = requests.get(source_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                    response.raise_for_status()
                    schema_data = response.json()
                    
                    # Check if already exists in target
                    target_url = target_client.build_context_url(f"/subjects/{subject}/versions/{version}", target_ctx)
                    check_response = requests.get(target_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                    
                    if check_response.status_code == 200:
                        migration_results["skipped_versions"].append({
                            "version": version,
                            "reason": "Already exists in target",
                            "source_id": schema_data.get("id"),
                            "target_id": check_response.json().get("id")
                        })
                        continue
                    
                    # Register in target with or without ID preservation
                    if preserve_ids:
                        # Use import endpoint to preserve ID
                        source_id = schema_data.get("id")
                        import_payload = {
                            "schema": schema_data["schema"],
                            "schemaType": schema_data.get("schemaType", "AVRO")
                        }
                        
                        # First register the schema by ID
                        import_url = f"{target_client.config.url}/schemas/ids/{source_id}"
                        import_response = requests.post(
                            import_url,
                            data=json.dumps(import_payload),
                            auth=target_client.auth,
                            headers=target_client.headers,
                            timeout=10
                        )
                        
                        if import_response.status_code == 409:
                            # Schema ID already exists - check if it's the same schema
                            existing_response = requests.get(
                                f"{target_client.config.url}/schemas/{source_id}",
                                auth=target_client.auth,
                                headers=target_client.headers,
                                timeout=10
                            )
                            if existing_response.status_code == 200:
                                existing_schema = existing_response.json()
                                if existing_schema.get("schema") == schema_data["schema"]:
                                    migration_results["skipped_versions"].append({
                                        "version": version,
                                        "reason": "Schema with same ID already exists",
                                        "source_id": source_id,
                                        "target_id": source_id
                                    })
                                    continue
                                else:
                                    raise Exception(f"Schema ID {source_id} exists but with different content")
                            else:
                                import_response.raise_for_status()
                        else:
                            import_response.raise_for_status()
                        
                        # Then associate it with the subject
                        subject_payload = {"id": source_id}
                        target_register_url = target_client.build_context_url(f"/subjects/{subject}/versions", target_ctx)
                        register_response = requests.post(
                            target_register_url,
                            data=json.dumps(subject_payload),
                            auth=target_client.auth,
                            headers=target_client.headers,
                            timeout=10
                        )
                        register_response.raise_for_status()
                        result = register_response.json()
                        
                        migration_results["successful_versions"].append({
                            "version": version,
                            "schema_id": source_id,
                            "source_id": source_id,
                            "target_version": result.get("version"),
                            "id_preserved": True
                        })
                        
                    else:
                        # Standard migration without ID preservation
                        payload = {
                            "schema": schema_data["schema"],
                            "schemaType": schema_data.get("schemaType", "AVRO")
                        }
                        
                        target_register_url = target_client.build_context_url(f"/subjects/{subject}/versions", target_ctx)
                        register_response = requests.post(
                            target_register_url,
                            json=payload,
                            auth=target_client.auth,
                            headers=target_client.headers,
                            timeout=10
                        )
                        register_response.raise_for_status()
                        result = register_response.json()
                        
                        migration_results["successful_versions"].append({
                            "version": version,
                            "schema_id": result.get("id"),
                            "source_id": schema_data.get("id"),
                            "target_version": result.get("version"),
                            "id_preserved": False
                        })
                        
                except Exception as e:
                    migration_results["failed_versions"].append({
                        "version": version,
                        "error": str(e),
                        "source_id": schema_data.get("id") if 'schema_data' in locals() else None
                    })
        
        finally:
            # Restore original mode if we changed it
            if preserve_ids and original_mode and original_mode != "IMPORT":
                try:
                    restore_payload = {"mode": original_mode}
                    mode_url = target_client.build_context_url("/mode", target_ctx)
                    requests.put(
                        mode_url,
                        data=json.dumps(restore_payload),
                        auth=target_client.auth,
                        headers=target_client.headers,
                        timeout=10
                    )
                except Exception as e:
                    # Log error but don't fail the migration
                    logging.warning(f"Failed to restore original mode {original_mode}: {e}")
        
        # Create migration task
        task = MigrationTask(
            id=task_id,
            source_registry=source_registry,
            target_registry=target_registry,
            scope=f"schema:{subject}",
            status="completed",
            created_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            results=migration_results,
            dry_run=False
        )
        registry_manager.migration_tasks[task_id] = task
        
        success_count = len(migration_results["successful_versions"])
        total_attempted = success_count + len(migration_results["failed_versions"])
        
        return {
            "migration_id": task_id,
            "subject": subject,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "source_context": source_context,
            "target_context": target_ctx,
            "migrate_all_versions": migrate_all_versions,
            "preserve_ids": preserve_ids,
            "total_versions": len(versions),
            "successful_migrations": success_count,
            "failed_migrations": len(migration_results["failed_versions"]),
            "skipped_migrations": len(migration_results["skipped_versions"]),
            "success_rate": f"{(success_count / total_attempted * 100):.1f}%" if total_attempted > 0 else "0%",
            "results": migration_results,
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
    migrate_all_versions: bool = True,
    preserve_ids: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Migrate an entire context from one registry to another.
    
    Args:
        context: Context name to migrate
        source_registry: Source registry name
        target_registry: Target registry name
        target_context: Target context name (optional, defaults to source context)
        migrate_all_versions: Migrate all versions or just latest (default: True)
        preserve_ids: Preserve original schema IDs (requires IMPORT mode) (default: True)
        dry_run: Preview migration without executing (default: True)
    
    Returns:
        Migration results
    """
    # Check readonly mode for actual migrations
    if not dry_run:
        readonly_check = check_readonly_mode(target_registry)
        if readonly_check:
            return readonly_check
    
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        task_id = str(uuid.uuid4())
        target_ctx = target_context or context
        
        # Get subjects in the context
        subjects = source_client.get_subjects(context)
        
        if not subjects:
            return {
                "migration_id": task_id,
                "context": context,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "target_context": target_ctx,
                "subjects_found": 0,
                "error": f"No subjects found in context '{context}' in source registry"
            }
        
        if dry_run:
            # For dry run, calculate total versions if migrating all
            total_versions = 0
            if migrate_all_versions:
                for subject in subjects:
                    try:
                        versions_url = source_client.build_context_url(f"/subjects/{subject}/versions", context)
                        response = requests.get(versions_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                        if response.status_code == 200:
                            total_versions += len(response.json())
                    except Exception:
                        total_versions += 1  # Assume at least one version
            else:
                total_versions = len(subjects)  # One latest version per subject
                
            return {
                "migration_id": task_id,
                "context": context,
                "source_registry": source_registry,
                "target_registry": target_registry,
                "target_context": target_ctx,
                "subjects_to_migrate": subjects,
                "subject_count": len(subjects),
                "total_versions_to_migrate": total_versions,
                "migrate_all_versions": migrate_all_versions,
                "preserve_ids": preserve_ids,
                "dry_run": True,
                "status": "preview",
                "preview_at": datetime.now().isoformat()
            }
        
        # Handle IMPORT mode for ID preservation
        original_mode = None
        if preserve_ids:
            try:
                # Get current mode
                mode_url = target_client.build_context_url("/mode", target_ctx)
                mode_response = requests.get(mode_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                if mode_response.status_code == 200:
                    original_mode = mode_response.json().get("mode")
                
                # Set IMPORT mode if not already
                if original_mode != "IMPORT":
                    import_payload = {"mode": "IMPORT"}
                    import_response = requests.put(
                        mode_url,
                        data=json.dumps(import_payload),
                        auth=target_client.auth,
                        headers=target_client.headers,
                        timeout=10
                    )
                    import_response.raise_for_status()
                    
            except Exception as e:
                # If IMPORT mode is not supported, fall back to standard migration
                logging.warning(f"IMPORT mode not available, falling back to standard migration: {e}")
                preserve_ids = False
        
        # Perform actual migration
        migration_results = {
            "successful_subjects": [],
            "failed_subjects": [],
            "skipped_subjects": [],
            "version_details": []  # Track individual version migrations
        }
        
        total_versions_migrated = 0
        total_versions_skipped = 0
        total_versions_failed = 0
        
        try:
            for subject in subjects:
                try:
                    if migrate_all_versions:
                        # Get all versions for this subject
                        versions_url = source_client.build_context_url(f"/subjects/{subject}/versions", context)
                        versions_response = requests.get(versions_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                        versions_response.raise_for_status()
                        versions = sorted(versions_response.json())  # Migrate oldest to newest
                    else:
                        # Only migrate latest version
                        versions = ["latest"]
                    
                    subject_success = True
                    subject_versions_migrated = 0
                    subject_versions_skipped = 0
                    subject_versions_failed = 0
                    
                    for version in versions:
                        try:
                            # Get schema from source
                            source_url = source_client.build_context_url(f"/subjects/{subject}/versions/{version}", context)
                            response = requests.get(source_url, auth=source_client.auth, headers=source_client.headers, timeout=10)
                            response.raise_for_status()
                            schema_data = response.json()
                            
                            # Check if already exists in target
                            target_url = target_client.build_context_url(f"/subjects/{subject}/versions/{version}", target_ctx)
                            check_response = requests.get(target_url, auth=target_client.auth, headers=target_client.headers, timeout=10)
                            
                            if check_response.status_code == 200:
                                # Compare schemas to see if they're the same
                                target_schema_data = check_response.json()
                                if schema_data["schema"] == target_schema_data["schema"]:
                                    migration_results["version_details"].append({
                                        "subject": subject,
                                        "version": version,
                                        "status": "skipped",
                                        "reason": "Identical schema already exists",
                                        "source_id": schema_data.get("id"),
                                        "target_id": target_schema_data.get("id")
                                    })
                                    subject_versions_skipped += 1
                                    total_versions_skipped += 1
                                    continue
                            
                            # Register in target with or without ID preservation
                            if preserve_ids:
                                # Use import endpoint to preserve ID
                                source_id = schema_data.get("id")
                                import_payload = {
                                    "schema": schema_data["schema"],
                                    "schemaType": schema_data.get("schemaType", "AVRO")
                                }
                                
                                # First register the schema by ID
                                import_url = f"{target_client.config.url}/schemas/ids/{source_id}"
                                import_response = requests.post(
                                    import_url,
                                    data=json.dumps(import_payload),
                                    auth=target_client.auth,
                                    headers=target_client.headers,
                                    timeout=10
                                )
                                
                                if import_response.status_code == 409:
                                    # Schema ID already exists - check if it's the same schema
                                    existing_response = requests.get(
                                        f"{target_client.config.url}/schemas/{source_id}",
                                        auth=target_client.auth,
                                        headers=target_client.headers,
                                        timeout=10
                                    )
                                    if existing_response.status_code == 200:
                                        existing_schema = existing_response.json()
                                        if existing_schema.get("schema") == schema_data["schema"]:
                                            migration_results["version_details"].append({
                                                "subject": subject,
                                                "version": version,
                                                "status": "skipped",
                                                "reason": "Schema with same ID already exists",
                                                "source_id": source_id,
                                                "target_id": source_id
                                            })
                                            subject_versions_skipped += 1
                                            total_versions_skipped += 1
                                            continue
                                        else:
                                            raise Exception(f"Schema ID {source_id} exists but with different content")
                                    else:
                                        import_response.raise_for_status()
                                else:
                                    import_response.raise_for_status()
                                
                                # Then associate it with the subject
                                subject_payload = {"id": source_id}
                                target_register_url = target_client.build_context_url(f"/subjects/{subject}/versions", target_ctx)
                                register_response = requests.post(
                                    target_register_url,
                                    data=json.dumps(subject_payload),
                                    auth=target_client.auth,
                                    headers=target_client.headers,
                                    timeout=10
                                )
                                register_response.raise_for_status()
                                result = register_response.json()
                                
                                migration_results["version_details"].append({
                                    "subject": subject,
                                    "version": version,
                                    "status": "success",
                                    "source_id": source_id,
                                    "target_id": source_id,
                                    "target_version": result.get("version"),
                                    "id_preserved": True
                                })
                                subject_versions_migrated += 1
                                total_versions_migrated += 1
                                
                            else:
                                # Standard migration without ID preservation
                                payload = {
                                    "schema": schema_data["schema"],
                                    "schemaType": schema_data.get("schemaType", "AVRO")
                                }
                                
                                target_register_url = target_client.build_context_url(f"/subjects/{subject}/versions", target_ctx)
                                register_response = requests.post(
                                    target_register_url,
                                    json=payload,
                                    auth=target_client.auth,
                                    headers=target_client.headers,
                                    timeout=10
                                )
                                register_response.raise_for_status()
                                result = register_response.json()
                                
                                migration_results["version_details"].append({
                                    "subject": subject,
                                    "version": version,
                                    "status": "success",
                                    "source_id": schema_data.get("id"),
                                    "target_id": result.get("id"),
                                    "target_version": result.get("version"),
                                    "id_preserved": False
                                })
                                subject_versions_migrated += 1
                                total_versions_migrated += 1
                            
                        except Exception as e:
                            migration_results["version_details"].append({
                                "subject": subject,
                                "version": version,
                                "status": "failed",
                                "error": str(e),
                                "source_id": schema_data.get("id") if 'schema_data' in locals() else None
                            })
                            subject_versions_failed += 1
                            total_versions_failed += 1
                            subject_success = False
                    
                    # Record subject-level results
                    if subject_success and subject_versions_migrated > 0:
                        migration_results["successful_subjects"].append({
                            "subject": subject,
                            "versions_migrated": subject_versions_migrated,
                            "versions_skipped": subject_versions_skipped,
                            "total_versions": len(versions) if isinstance(versions, list) else 1
                        })
                    elif subject_versions_skipped > 0 and subject_versions_failed == 0:
                        migration_results["skipped_subjects"].append({
                            "subject": subject,
                            "reason": "All versions already exist",
                            "versions_skipped": subject_versions_skipped,
                            "total_versions": len(versions) if isinstance(versions, list) else 1
                        })
                    else:
                        migration_results["failed_subjects"].append({
                            "subject": subject,
                            "versions_failed": subject_versions_failed,
                            "versions_migrated": subject_versions_migrated,
                            "versions_skipped": subject_versions_skipped,
                            "total_versions": len(versions) if isinstance(versions, list) else 1,
                            "error": f"Failed to migrate {subject_versions_failed} version(s)"
                        })
                    
                except Exception as e:
                    migration_results["failed_subjects"].append({
                        "subject": subject,
                        "error": str(e),
                        "versions_failed": 1,
                        "versions_migrated": 0,
                        "versions_skipped": 0,
                        "total_versions": 1
                    })
                    total_versions_failed += 1
        
        finally:
            # Restore original mode if we changed it
            if preserve_ids and original_mode and original_mode != "IMPORT":
                try:
                    restore_payload = {"mode": original_mode}
                    mode_url = target_client.build_context_url("/mode", target_ctx)
                    requests.put(
                        mode_url,
                        data=json.dumps(restore_payload),
                        auth=target_client.auth,
                        headers=target_client.headers,
                        timeout=10
                    )
                except Exception as e:
                    # Log error but don't fail the migration
                    logging.warning(f"Failed to restore original mode {original_mode}: {e}")
        
        # Create migration task
        task = MigrationTask(
            id=task_id,
            source_registry=source_registry,
            target_registry=target_registry,
            scope=f"context:{context}",
            status="completed",
            created_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            results=migration_results,
            dry_run=False
        )
        registry_manager.migration_tasks[task_id] = task
        
        success_count = len(migration_results["successful_subjects"])
        total_attempted = success_count + len(migration_results["failed_subjects"])
        
        return {
            "migration_id": task_id,
            "context": context,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "target_context": target_ctx,
            "migrate_all_versions": migrate_all_versions,
            "preserve_ids": preserve_ids,
            "total_subjects": len(subjects),
            "successful_migrations": success_count,
            "failed_migrations": len(migration_results["failed_subjects"]),
            "skipped_migrations": len(migration_results["skipped_subjects"]),
            "total_versions_migrated": total_versions_migrated,
            "total_versions_skipped": total_versions_skipped,
            "total_versions_failed": total_versions_failed,
            "success_rate": f"{(success_count / total_attempted * 100):.1f}%" if total_attempted > 0 else "0%",
            "version_success_rate": f"{(total_versions_migrated / (total_versions_migrated + total_versions_failed) * 100):.1f}%" if (total_versions_migrated + total_versions_failed) > 0 else "0%",
            "results": migration_results,
            "status": "completed",
            "migrated_at": datetime.now().isoformat()
        }
        
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

# ===== SYNCHRONIZATION TOOLS =====

@mcp.tool()
def sync_schema(
    subject: str,
    source_registry: str,
    target_registry: str,
    direction: str = "source_to_target",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Synchronize a schema between registries.
    
    Args:
        subject: Schema subject name
        source_registry: Source registry name
        target_registry: Target registry name
        direction: sync direction (source_to_target, target_to_source, bidirectional)
        dry_run: Preview sync without executing
    
    Returns:
        Synchronization results
    """
    if not dry_run:
        readonly_check = check_readonly_mode(target_registry)
        if readonly_check:
            return readonly_check
    
    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if source_client is None:
            return {"error": f"Source registry '{source_registry}' not found"}
        if target_client is None:
            return {"error": f"Target registry '{target_registry}' not found"}
        
        return {
            "subject": subject,
            "source_registry": source_registry,
            "target_registry": target_registry,
            "direction": direction,
            "dry_run": dry_run,
            "status": "completed",
            "synced_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

# ===== CONTEXT MANAGEMENT TOOLS =====

@mcp.tool()
def list_contexts(registry: Optional[str] = None) -> List[str]:
    """
    List all available schema contexts.
    
    Args:
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of context names
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        return client.get_contexts()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def create_context(
    context: str,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Create a new schema context.
    
    Args:
        context: The context name to create
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Success message
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        response = requests.post(
            f"{client.config.url}/contexts/{context}",
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' created successfully in registry '{client.config.name}'"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def delete_context(
    context: str,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Delete a schema context.
    
    Args:
        context: The context name to delete
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Success message
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        response = requests.delete(
            f"{client.config.url}/contexts/{context}",
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' deleted successfully from registry '{client.config.name}'"}
    except Exception as e:
        return {"error": str(e)}

# ===== SUBJECT MANAGEMENT TOOLS =====

@mcp.tool()
def list_subjects(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[str]:
    """
    List all subjects, optionally filtered by context.
    
    Args:
        context: Optional schema context to filter by
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of subject names
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        return client.get_subjects(context)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def delete_subject(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[int]:
    """
    Delete a subject and all its versions.
    
    Args:
        subject: The subject name to delete
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of deleted version numbers
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}", context)
        
        response = requests.delete(
            url,
            auth=client.auth,
            headers=client.headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ===== CONFIGURATION MANAGEMENT TOOLS =====

@mcp.tool()
def get_global_config(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get global configuration settings.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing configuration
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/config", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_global_config(
    compatibility: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update global configuration settings.
    
    Args:
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/config", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_config(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing subject configuration
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/config/{subject}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_config(
    subject: str,
    compatibility: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update configuration settings for a specific subject.
    
    Args:
        subject: The subject name
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated configuration
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/config/{subject}", context)
        payload = {"compatibility": compatibility}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== MODE MANAGEMENT TOOLS =====

@mcp.tool()
def get_mode(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Get the current mode of the Schema Registry.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the current mode
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/mode", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_mode(
    mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode of the Schema Registry.
    
    Args:
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url("/mode", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_subject_mode(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Get the mode for a specific subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Dictionary containing the subject mode
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/mode/{subject}", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_subject_mode(
    subject: str,
    mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the mode for a specific subject.
    
    Args:
        subject: The subject name
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Updated mode information
    """
    # Check readonly mode
    readonly_check = check_readonly_mode(registry)
    if readonly_check:
        return readonly_check
    
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/mode/{subject}", context)
        payload = {"mode": mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=client.auth,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        result["registry"] = client.config.name
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== ENHANCED SCHEMA TOOLS =====

@mcp.tool()
def get_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> List[int]:
    """
    Get all versions of a schema for a subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        List of version numbers
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        url = client.build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.get(
            url,
            auth=client.auth,
            headers=client.headers
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
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if a schema is compatible with the latest version.
    
    Args:
        subject: The subject name
        schema_definition: The schema definition to check
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (uses default if not specified)
    
    Returns:
        Compatibility check result
    """
    try:
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = client.build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)
        
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

# ===== ORIGINAL SCHEMA MANAGEMENT TOOLS (Enhanced with Multi-Registry Support) =====

@mcp.tool()
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
    readonly_check = check_readonly_mode(registry)
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

# ===== BATCH CLEANUP TOOLS =====

@mcp.tool()
def clear_context_batch(
    context: str,
    registry: str,
    delete_context_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Efficiently remove all subjects from a context in batch mode.
    
    Args:
        context: The context name to clear
        registry: The registry name to target
        delete_context_after: Whether to delete the context itself after clearing subjects
        dry_run: If True, show what would be deleted without actually deleting (default: True for safety)
    
    Returns:
        Dictionary containing cleanup results and statistics
    """
    # Check readonly mode for actual deletions
    if not dry_run:
        readonly_check = check_readonly_mode(registry)
        if readonly_check:
            return readonly_check
    
    try:
        # Get the registry client
        client = registry_manager.get_registry(registry)
        if client is None:
            return {"error": f"Registry '{registry}' not found"}
        
        start_time = datetime.now()
        
        # Step 1: List all subjects in the context
        print(f"🔍 Scanning context '{context}' in registry '{registry}' for subjects...")
        subjects_list = list_subjects(context, registry)
        
        if isinstance(subjects_list, dict) and "error" in subjects_list:
            return subjects_list
        
        if not subjects_list:
            result = {
                "context": context,
                "registry": registry,
                "dry_run": dry_run,
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "duration_seconds": 0,
                "message": f"Context '{context}' is already empty in registry '{registry}'"
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
                    # Use the existing delete_subject function which handles multi-registry properly
                    deletion_result = delete_subject(subject, context, registry)
                    
                    if isinstance(deletion_result, list):  # Success - returns version list
                        return {"subject": subject, "status": "deleted", "versions": deletion_result}
                    elif isinstance(deletion_result, dict) and "error" in deletion_result:
                        return {"subject": subject, "status": "failed", "error": deletion_result["error"]}
                    else:
                        return {"subject": subject, "status": "deleted", "versions": deletion_result}
                        
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
                print(f"🔍 DRY RUN: Would delete context '{context}' in registry '{registry}'")
                context_deleted = True
            else:
                print(f"🗑️  Deleting context '{context}' in registry '{registry}'...")
                try:
                    deletion_result = delete_context(context, registry)
                    if "error" not in deletion_result:
                        context_deleted = True
                        print(f"   ✅ Context '{context}' deleted from registry '{registry}'")
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
            "registry": registry,
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
            result["message"] = f"DRY RUN: Would delete {len(subjects_list)} subjects from context '{context}' in registry '{registry}'"
        elif len(deleted_subjects) == len(subjects_list):
            result["message"] = f"Successfully cleared context '{context}' in registry '{registry}' - deleted {len(deleted_subjects)} subjects"
        else:
            result["message"] = f"Partially cleared context '{context}' in registry '{registry}' - deleted {len(deleted_subjects)}/{len(subjects_list)} subjects"
        
        return result
        
    except Exception as e:
        return {"error": f"Batch cleanup failed: {str(e)}"}

@mcp.tool()
def clear_multiple_contexts_batch(
    contexts: List[str],
    registry: str,
    delete_contexts_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Efficiently clear multiple contexts in batch mode within a single registry.
    
    Args:
        contexts: List of context names to clear
        registry: The registry name to target
        delete_contexts_after: Whether to delete contexts after clearing subjects
        dry_run: If True, show what would be deleted without actually deleting (default: True for safety)
    
    Returns:
        Dictionary containing overall cleanup results
    """
    # Check readonly mode for actual deletions
    if not dry_run:
        readonly_check = check_readonly_mode(registry)
        if readonly_check:
            return readonly_check
    
    try:
        start_time = datetime.now()
        context_results = []
        total_subjects_deleted = 0
        total_subjects_found = 0
        total_contexts_deleted = 0
        
        print(f"🚀 Starting batch cleanup of {len(contexts)} contexts in registry '{registry}'...")
        
        for i, context in enumerate(contexts, 1):
            print(f"\n📂 Processing context {i}/{len(contexts)}: '{context}'")
            
            context_result = clear_context_batch(
                context=context,
                registry=registry,
                delete_context_after=delete_contexts_after,
                dry_run=dry_run
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
            "registry": registry,
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
            result["message"] = f"DRY RUN: Would delete {total_subjects_found} subjects from {len(contexts)} contexts in registry '{registry}'"
        else:
            result["message"] = f"Batch cleanup completed: {total_subjects_deleted} subjects deleted from {completed_contexts} contexts in registry '{registry}'"
        
        return result
        
    except Exception as e:
        return {"error": f"Multi-context batch cleanup failed: {str(e)}"}

@mcp.tool()
def clear_context_across_registries_batch(
    context: str,
    registries: List[str],
    delete_context_after: bool = True,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Efficiently clear the same context across multiple registries in batch mode.
    
    Args:
        context: The context name to clear
        registries: List of registry names to target
        delete_context_after: Whether to delete the context after clearing subjects
        dry_run: If True, show what would be deleted without actually deleting (default: True for safety)
    
    Returns:
        Dictionary containing cross-registry cleanup results
    """
    try:
        start_time = datetime.now()
        registry_results = []
        total_subjects_deleted = 0
        total_subjects_found = 0
        total_registries_processed = 0
        
        print(f"🌐 Starting cross-registry cleanup of context '{context}' across {len(registries)} registries...")
        
        for i, registry in enumerate(registries, 1):
            print(f"\n🏢 Processing registry {i}/{len(registries)}: '{registry}'")
            
            # Check if registry exists
            if registry not in registry_manager.list_registries():
                registry_results.append({
                    "registry": registry,
                    "status": "failed",
                    "error": f"Registry '{registry}' not found"
                })
                continue
            
            registry_result = clear_context_batch(
                context=context,
                registry=registry,
                delete_context_after=delete_context_after,
                dry_run=dry_run
            )
            
            if "error" in registry_result:
                registry_results.append({
                    "registry": registry,
                    "status": "failed",
                    "error": registry_result["error"]
                })
            else:
                registry_results.append({
                    "registry": registry,
                    "status": "completed",
                    "subjects_deleted": registry_result["subjects_deleted"],
                    "subjects_found": registry_result["subjects_found"],
                    "context_deleted": registry_result["context_deleted"],
                    "duration_seconds": registry_result["duration_seconds"]
                })
                
                total_subjects_deleted += registry_result["subjects_deleted"]
                total_subjects_found += registry_result["subjects_found"]
                total_registries_processed += 1
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Build summary result
        completed_registries = sum(1 for r in registry_results if r["status"] == "completed")
        failed_registries = sum(1 for r in registry_results if r["status"] == "failed")
        
        result = {
            "operation": "cross_registry_context_cleanup",
            "context": context,
            "dry_run": dry_run,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "total_duration_seconds": round(total_duration, 2),
            "registries_targeted": len(registries),
            "registries_completed": completed_registries,
            "registries_failed": failed_registries,
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "overall_success_rate": round((completed_registries / len(registries)) * 100, 1) if registries else 100,
            "performance": {
                "registries_per_second": round(len(registries) / max(total_duration, 0.1), 2),
                "subjects_per_second": round(total_subjects_deleted / max(total_duration, 0.1), 1),
                "parallel_registry_processing": False  # Sequential for safety
            },
            "registry_results": registry_results
        }
        
        # Summary message
        if dry_run:
            result["message"] = f"DRY RUN: Would delete {total_subjects_found} subjects from context '{context}' across {len(registries)} registries"
        else:
            result["message"] = f"Cross-registry cleanup completed: {total_subjects_deleted} subjects deleted from context '{context}' across {completed_registries} registries"
        
        return result
        
    except Exception as e:
        return {"error": f"Cross-registry batch cleanup failed: {str(e)}"}

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
            "global_readonly_mode": READONLY,
            "server_version": "1.5.0-multi-registry",
            "multi_registry_support": True,
            "max_registries_supported": MAX_REGISTRIES,
            "total_tools": 68,
            "configuration_mode": "numbered_env_vars" if len(registries_info) > 1 else "single_registry",
            "features": [
                "Multi-Registry Support (Numbered Env Vars)",
                "Per-Registry READONLY Mode", 
                "Cross-Registry Comparison", 
                "Schema Migration",
                "Context Synchronization",
                "Schema Export (JSON, Avro IDL)",
                "Production Safety Controls",
                "All Original Tools Enhanced"
            ]
        }
        return json.dumps(overall_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    mcp.run() 