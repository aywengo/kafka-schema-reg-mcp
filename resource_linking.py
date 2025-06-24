#!/usr/bin/env python3
"""
Resource Linking Module for Kafka Schema Registry MCP

Implements the MCP 2025-06-18 specification for resource linking in tool responses.
Provides URI scheme design, URI builder utilities, and navigation helpers.

This module adds _links sections to tool responses with actionable URIs that help
users navigate between related resources in the Schema Registry ecosystem.
"""

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote


class RegistryURI:
    """
    URI scheme implementation for Schema Registry resources.
    
    Supports the following URI patterns:
    - registry://{registry-name}/contexts/{context}/subjects/{subject}/versions/{version}
    - registry://{registry-name}/contexts/{context}/subjects/{subject}/config
    - registry://{registry-name}/contexts/{context}/subjects/{subject}/compatibility
    - registry://{registry-name}/contexts/{context}/config
    - registry://{registry-name}/contexts/{context}/mode
    - registry://{registry-name}/migrations/{migration-id}
    - registry://{registry-name}/tasks/{task-id}
    """
    
    SCHEME = "registry"
    
    def __init__(self, registry_name: str):
        """Initialize URI builder for a specific registry."""
        self.registry_name = self._sanitize_name(registry_name)
        
    def _sanitize_name(self, name: str) -> str:
        """Sanitize names for safe URI usage."""
        if not name:
            return "unknown"
        # Replace unsafe characters with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '-', name)
        return sanitized.strip('-')
    
    def _encode_component(self, component: str) -> str:
        """URL encode a URI component safely."""
        return quote(str(component), safe='')
    
    def _build_base_uri(self, path: str) -> str:
        """Build the base URI with registry name."""
        return f"{self.SCHEME}://{self.registry_name}{path}"
    
    # ===== CONTEXT URIS =====
    
    def context_uri(self, context: Optional[str] = None) -> str:
        """Build URI for a context resource."""
        if context and context != ".":
            encoded_context = self._encode_component(context)
            return self._build_base_uri(f"/contexts/{encoded_context}")
        return self._build_base_uri("/contexts/default")
    
    def contexts_list_uri(self) -> str:
        """Build URI for the contexts collection."""
        return self._build_base_uri("/contexts")
    
    def context_config_uri(self, context: Optional[str] = None) -> str:
        """Build URI for context configuration."""
        base = self.context_uri(context)
        return f"{base}/config"
    
    def context_mode_uri(self, context: Optional[str] = None) -> str:
        """Build URI for context mode."""
        base = self.context_uri(context)
        return f"{base}/mode"
    
    # ===== SUBJECT URIS =====
    
    def subject_uri(self, subject: str, context: Optional[str] = None) -> str:
        """Build URI for a subject resource."""
        context_base = self.context_uri(context)
        encoded_subject = self._encode_component(subject)
        return f"{context_base}/subjects/{encoded_subject}"
    
    def subjects_list_uri(self, context: Optional[str] = None) -> str:
        """Build URI for the subjects collection in a context."""
        context_base = self.context_uri(context)
        return f"{context_base}/subjects"
    
    def subject_config_uri(self, subject: str, context: Optional[str] = None) -> str:
        """Build URI for subject configuration."""
        base = self.subject_uri(subject, context)
        return f"{base}/config"
    
    def subject_mode_uri(self, subject: str, context: Optional[str] = None) -> str:
        """Build URI for subject mode."""
        base = self.subject_uri(subject, context)
        return f"{base}/mode"
    
    def subject_compatibility_uri(self, subject: str, context: Optional[str] = None) -> str:
        """Build URI for subject compatibility checking."""
        base = self.subject_uri(subject, context)
        return f"{base}/compatibility"
    
    # ===== SCHEMA VERSION URIS =====
    
    def schema_versions_uri(self, subject: str, context: Optional[str] = None) -> str:
        """Build URI for all versions of a schema."""
        base = self.subject_uri(subject, context)
        return f"{base}/versions"
    
    def schema_version_uri(self, subject: str, version: Union[str, int], 
                          context: Optional[str] = None) -> str:
        """Build URI for a specific schema version."""
        versions_base = self.schema_versions_uri(subject, context)
        return f"{versions_base}/{version}"
    
    # ===== MIGRATION URIS =====
    
    def migration_uri(self, migration_id: str) -> str:
        """Build URI for a migration task."""
        encoded_id = self._encode_component(migration_id)
        return self._build_base_uri(f"/migrations/{encoded_id}")
    
    def migrations_list_uri(self) -> str:
        """Build URI for the migrations collection."""
        return self._build_base_uri("/migrations")
    
    # ===== TASK URIS =====
    
    def task_uri(self, task_id: str) -> str:
        """Build URI for a task."""
        encoded_id = self._encode_component(task_id)
        return self._build_base_uri(f"/tasks/{encoded_id}")
    
    def tasks_list_uri(self) -> str:
        """Build URI for the tasks collection."""
        return self._build_base_uri("/tasks")
    
    # ===== REGISTRY ROOT URIS =====
    
    def registry_uri(self) -> str:
        """Build URI for the registry root."""
        return self._build_base_uri("")
    
    def registry_info_uri(self) -> str:
        """Build URI for registry information."""
        return self._build_base_uri("/info")


class ResourceLinker:
    """
    Helper class for adding resource links to tool responses.
    
    Provides methods to add _links sections to various tool outputs
    according to the MCP 2025-06-18 specification.
    """
    
    def __init__(self, registry_name: str):
        """Initialize the resource linker for a specific registry."""
        self.uri_builder = RegistryURI(registry_name)
    
    # ===== SCHEMA LINKS =====
    
    def add_schema_links(self, response: Dict[str, Any], subject: str, version: Union[str, int], 
                        context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to schema response."""
        links = {}
        
        # Core links
        links["self"] = self.uri_builder.schema_version_uri(subject, version, context)
        links["subject"] = self.uri_builder.subject_uri(subject, context)
        links["context"] = self.uri_builder.context_uri(context)
        links["versions"] = self.uri_builder.schema_versions_uri(subject, context)
        links["compatibility"] = self.uri_builder.subject_compatibility_uri(subject, context)
        
        # Configuration links
        links["config"] = self.uri_builder.subject_config_uri(subject, context)
        links["mode"] = self.uri_builder.subject_mode_uri(subject, context)
        
        # Add previous/next version links if applicable
        if isinstance(version, int) or (isinstance(version, str) and version.isdigit()):
            version_num = int(version)
            if version_num > 1:
                links["previous"] = self.uri_builder.schema_version_uri(subject, version_num - 1, context)
            links["next"] = self.uri_builder.schema_version_uri(subject, version_num + 1, context)
        
        response["_links"] = links
        return response
    
    def add_subject_links(self, response: Dict[str, Any], subject: str, 
                         context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to subject response."""
        links = {}
        
        links["self"] = self.uri_builder.subject_uri(subject, context)
        links["context"] = self.uri_builder.context_uri(context)
        links["versions"] = self.uri_builder.schema_versions_uri(subject, context)
        links["compatibility"] = self.uri_builder.subject_compatibility_uri(subject, context)
        links["config"] = self.uri_builder.subject_config_uri(subject, context)
        links["mode"] = self.uri_builder.subject_mode_uri(subject, context)
        
        response["_links"] = links
        return response
    
    def add_subjects_list_links(self, response: Union[List[str], Dict[str, Any]], 
                               context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to subjects list response."""
        # Convert list response to dict format if needed
        if isinstance(response, list):
            subjects_list = response
            response = {"subjects": subjects_list}
        else:
            subjects_list = response.get("subjects", [])
        
        links = {}
        links["self"] = self.uri_builder.subjects_list_uri(context)
        links["context"] = self.uri_builder.context_uri(context)
        
        # Add links to individual subjects
        subject_links = {}
        for subject in subjects_list:
            subject_links[subject] = self.uri_builder.subject_uri(subject, context)
        
        if subject_links:
            links["items"] = subject_links
        
        response["_links"] = links
        return response
    
    def add_schema_versions_links(self, response: Union[List[int], Dict[str, Any]], 
                                 subject: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to schema versions response."""
        # Convert list response to dict format if needed
        if isinstance(response, list):
            versions_list = response
            response = {"versions": versions_list, "subject": subject}
        else:
            versions_list = response.get("versions", [])
        
        links = {}
        links["self"] = self.uri_builder.schema_versions_uri(subject, context)
        links["subject"] = self.uri_builder.subject_uri(subject, context)
        links["context"] = self.uri_builder.context_uri(context)
        
        # Add links to individual versions
        version_links = {}
        for version in versions_list:
            version_links[str(version)] = self.uri_builder.schema_version_uri(subject, version, context)
        
        if version_links:
            links["items"] = version_links
        
        response["_links"] = links
        return response
    
    # ===== CONTEXT LINKS =====
    
    def add_context_links(self, response: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Add navigation links to context response."""
        links = {}
        
        links["self"] = self.uri_builder.context_uri(context)
        links["subjects"] = self.uri_builder.subjects_list_uri(context)
        links["config"] = self.uri_builder.context_config_uri(context)
        links["mode"] = self.uri_builder.context_mode_uri(context)
        links["contexts"] = self.uri_builder.contexts_list_uri()
        
        response["_links"] = links
        return response
    
    def add_contexts_list_links(self, response: Union[List[str], Dict[str, Any]]) -> Dict[str, Any]:
        """Add navigation links to contexts list response."""
        # Convert list response to dict format if needed
        if isinstance(response, list):
            contexts_list = response
            response = {"contexts": contexts_list}
        else:
            contexts_list = response.get("contexts", [])
        
        links = {}
        links["self"] = self.uri_builder.contexts_list_uri()
        
        # Add links to individual contexts
        context_links = {}
        for context in contexts_list:
            context_links[context or "default"] = self.uri_builder.context_uri(context)
        
        if context_links:
            links["items"] = context_links
        
        response["_links"] = links
        return response
    
    # ===== CONFIGURATION LINKS =====
    
    def add_config_links(self, response: Dict[str, Any], subject: Optional[str] = None,
                        context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to configuration response."""
        links = {}
        
        if subject:
            # Subject-specific configuration
            links["self"] = self.uri_builder.subject_config_uri(subject, context)
            links["subject"] = self.uri_builder.subject_uri(subject, context)
            links["context"] = self.uri_builder.context_uri(context)
            links["global_config"] = self.uri_builder.context_config_uri(context)
        else:
            # Global/context configuration
            links["self"] = self.uri_builder.context_config_uri(context)
            links["context"] = self.uri_builder.context_uri(context)
        
        response["_links"] = links
        return response
    
    def add_mode_links(self, response: Dict[str, Any], subject: Optional[str] = None,
                      context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to mode response."""
        links = {}
        
        if subject:
            # Subject-specific mode
            links["self"] = self.uri_builder.subject_mode_uri(subject, context)
            links["subject"] = self.uri_builder.subject_uri(subject, context)
            links["context"] = self.uri_builder.context_uri(context)
            links["global_mode"] = self.uri_builder.context_mode_uri(context)
        else:
            # Global/context mode
            links["self"] = self.uri_builder.context_mode_uri(context)
            links["context"] = self.uri_builder.context_uri(context)
        
        response["_links"] = links
        return response
    
    def add_compatibility_links(self, response: Dict[str, Any], subject: str,
                               context: Optional[str] = None) -> Dict[str, Any]:
        """Add navigation links to compatibility check response."""
        links = {}
        
        links["self"] = self.uri_builder.subject_compatibility_uri(subject, context)
        links["subject"] = self.uri_builder.subject_uri(subject, context)
        links["context"] = self.uri_builder.context_uri(context)
        links["versions"] = self.uri_builder.schema_versions_uri(subject, context)
        links["config"] = self.uri_builder.subject_config_uri(subject, context)
        
        response["_links"] = links
        return response
    
    # ===== MIGRATION LINKS =====
    
    def add_migration_links(self, response: Dict[str, Any], migration_id: str) -> Dict[str, Any]:
        """Add navigation links to migration response."""
        links = {}
        
        links["self"] = self.uri_builder.migration_uri(migration_id)
        links["migrations"] = self.uri_builder.migrations_list_uri()
        
        # Add source and target registry links if available
        if "source_registry" in response:
            source_uri_builder = RegistryURI(response["source_registry"])
            links["source_registry"] = source_uri_builder.registry_uri()
        
        if "target_registry" in response:
            target_uri_builder = RegistryURI(response["target_registry"])
            links["target_registry"] = target_uri_builder.registry_uri()
        
        response["_links"] = links
        return response
    
    def add_migrations_list_links(self, response: Union[List[Dict], Dict[str, Any]]) -> Dict[str, Any]:
        """Add navigation links to migrations list response."""
        # Convert list response to dict format if needed
        if isinstance(response, list):
            migrations_list = response
            response = {"migrations": migrations_list}
        else:
            migrations_list = response.get("migrations", [])
        
        links = {}
        links["self"] = self.uri_builder.migrations_list_uri()
        
        # Add links to individual migrations
        migration_links = {}
        for migration in migrations_list:
            if isinstance(migration, dict) and "id" in migration:
                migration_id = migration["id"]
                migration_links[migration_id] = self.uri_builder.migration_uri(migration_id)
        
        if migration_links:
            links["items"] = migration_links
        
        response["_links"] = links
        return response
    
    # ===== REGISTRY LINKS =====
    
    def add_registry_links(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add navigation links to registry response."""
        links = {}
        
        links["self"] = self.uri_builder.registry_uri()
        links["info"] = self.uri_builder.registry_info_uri()
        links["contexts"] = self.uri_builder.contexts_list_uri()
        links["subjects"] = self.uri_builder.subjects_list_uri()
        links["migrations"] = self.uri_builder.migrations_list_uri()
        links["tasks"] = self.uri_builder.tasks_list_uri()
        
        response["_links"] = links
        return response
    
    # ===== COMPARISON LINKS =====
    
    def add_comparison_links(self, response: Dict[str, Any], source_registry: str,
                            target_registry: str) -> Dict[str, Any]:
        """Add navigation links to registry comparison response."""
        links = {}
        
        # Links to source and target registries
        source_uri_builder = RegistryURI(source_registry)
        target_uri_builder = RegistryURI(target_registry)
        
        links["source_registry"] = source_uri_builder.registry_uri()
        links["target_registry"] = target_uri_builder.registry_uri()
        links["source_contexts"] = source_uri_builder.contexts_list_uri()
        links["target_contexts"] = target_uri_builder.contexts_list_uri()
        
        response["_links"] = links
        return response


# ===== UTILITY FUNCTIONS =====

def create_registry_linker(registry_name: str) -> ResourceLinker:
    """Create a ResourceLinker instance for a specific registry."""
    return ResourceLinker(registry_name)


def add_links_to_response(response: Dict[str, Any], link_type: str, 
                         registry_name: str, **kwargs) -> Dict[str, Any]:
    """
    Generic function to add links to any response based on type.
    
    Args:
        response: The response dictionary to enhance
        link_type: Type of links to add (schema, subject, context, etc.)
        registry_name: Name of the registry
        **kwargs: Additional parameters specific to the link type
    
    Returns:
        Enhanced response with _links section
    """
    linker = create_registry_linker(registry_name)
    
    if link_type == "schema":
        return linker.add_schema_links(response, kwargs["subject"], kwargs["version"], 
                                      kwargs.get("context"))
    elif link_type == "subject":
        return linker.add_subject_links(response, kwargs["subject"], kwargs.get("context"))
    elif link_type == "subjects_list":
        return linker.add_subjects_list_links(response, kwargs.get("context"))
    elif link_type == "schema_versions":
        return linker.add_schema_versions_links(response, kwargs["subject"], kwargs.get("context"))
    elif link_type == "context":
        return linker.add_context_links(response, kwargs["context"])
    elif link_type == "contexts_list":
        return linker.add_contexts_list_links(response)
    elif link_type == "config":
        return linker.add_config_links(response, kwargs.get("subject"), kwargs.get("context"))
    elif link_type == "mode":
        return linker.add_mode_links(response, kwargs.get("subject"), kwargs.get("context"))
    elif link_type == "compatibility":
        return linker.add_compatibility_links(response, kwargs["subject"], kwargs.get("context"))
    elif link_type == "migration":
        return linker.add_migration_links(response, kwargs["migration_id"])
    elif link_type == "migrations_list":
        return linker.add_migrations_list_links(response)
    elif link_type == "registry":
        return linker.add_registry_links(response)
    elif link_type == "comparison":
        return linker.add_comparison_links(response, kwargs["source_registry"], kwargs["target_registry"])
    else:
        # Unknown link type, return response unchanged
        return response


def validate_registry_uri(uri: str) -> bool:
    """
    Validate that a URI follows the registry URI scheme.
    
    Args:
        uri: The URI to validate
        
    Returns:
        True if the URI is valid, False otherwise
    """
    if not uri.startswith(f"{RegistryURI.SCHEME}://"):
        return False
    
    # Basic validation - could be extended with more sophisticated checks
    try:
        # Remove scheme and split into components
        path = uri[len(f"{RegistryURI.SCHEME}://"):]
        parts = path.split("/")
        
        # Should have at least registry name
        if len(parts) < 1 or not parts[0]:
            return False
        
        return True
    except Exception:
        return False


def extract_registry_from_uri(uri: str) -> Optional[str]:
    """
    Extract the registry name from a registry URI.
    
    Args:
        uri: The registry URI
        
    Returns:
        Registry name or None if invalid URI
    """
    if not validate_registry_uri(uri):
        return None
    
    try:
        path = uri[len(f"{RegistryURI.SCHEME}://"):]
        registry_name = path.split("/")[0]
        return registry_name if registry_name else None
    except Exception:
        return None


def parse_registry_uri(uri: str) -> Optional[Dict[str, str]]:
    """
    Parse a registry URI into its components.
    
    Args:
        uri: The registry URI to parse
        
    Returns:
        Dictionary with URI components or None if invalid
    """
    if not validate_registry_uri(uri):
        return None
    
    try:
        path = uri[len(f"{RegistryURI.SCHEME}://"):]
        parts = path.split("/")
        
        result = {"registry": parts[0]}
        
        # Parse different URI patterns
        if len(parts) >= 3 and parts[1] == "contexts":
            result["context"] = parts[2] if parts[2] != "default" else None
            
            if len(parts) >= 5 and parts[3] == "subjects":
                result["subject"] = parts[4]
                
                if len(parts) >= 7 and parts[5] == "versions":
                    result["version"] = parts[6]
                elif len(parts) >= 6 and parts[5] in ["config", "compatibility", "mode"]:
                    result["resource_type"] = parts[5]
            elif len(parts) >= 5 and parts[3] in ["config", "mode"]:
                result["resource_type"] = parts[3]
        elif len(parts) >= 3 and parts[1] == "migrations":
            result["migration_id"] = parts[2]
        elif len(parts) >= 3 and parts[1] == "tasks":
            result["task_id"] = parts[2]
        
        return result
    except Exception:
        return None
