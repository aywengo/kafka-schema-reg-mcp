#!/usr/bin/env python3
"""
Kafka Schema Registry MCP Server

A Message Control Protocol (MCP) server that provides tools for interacting with
Kafka Schema Registry, including schema management, context operations, configuration
management, mode control, and comprehensive export functionality.
"""

import os
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import asyncio
import logging

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import base64

from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configuration
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")

# Setup authentication
auth = None
headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
standard_headers = {"Content-Type": "application/json"}

if SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD:
    auth = HTTPBasicAuth(SCHEMA_REGISTRY_USER, SCHEMA_REGISTRY_PASSWORD)
    credentials = base64.b64encode(f"{SCHEMA_REGISTRY_USER}:{SCHEMA_REGISTRY_PASSWORD}".encode()).decode()
    headers["Authorization"] = f"Basic {credentials}"
    standard_headers["Authorization"] = f"Basic {credentials}"

# Create the MCP server
mcp = FastMCP("Kafka Schema Registry MCP Server")

def build_context_url(base_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support."""
    if context:
        return f"{SCHEMA_REGISTRY_URL}/contexts/{context}{base_url}"
    return f"{SCHEMA_REGISTRY_URL}{base_url}"

# ===== SCHEMA MANAGEMENT TOOLS =====

@mcp.tool()
def register_schema(
    subject: str,
    schema_definition: Dict[str, Any],
    schema_type: str = "AVRO",
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Register a new schema version under the specified subject.
    
    Args:
        subject: The subject name for the schema
        schema_definition: The schema definition as a dictionary
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
    
    Returns:
        Dictionary containing the schema ID
    """
    try:
        payload = {
            "schema": json.dumps(schema_definition),
            "schemaType": schema_type
        }
        
        url = build_context_url(f"/subjects/{subject}/versions", context)
        
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

@mcp.tool()
def get_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a specific version of a schema.
    
    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
    
    Returns:
        Dictionary containing schema information
    """
    try:
        url = build_context_url(f"/subjects/{subject}/versions/{version}", context)
        
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

# ===== EXPORT FUNCTIONALITY =====

def format_schema_as_avro_idl(schema_str: str, subject: str) -> str:
    """Convert Avro JSON schema to Avro IDL format."""
    try:
        schema_obj = json.loads(schema_str)
        
        def format_field(field):
            field_type = field["type"]
            field_name = field["name"]
            default = field.get("default", None)
            doc = field.get("doc", "")
            
            if isinstance(field_type, list) and "null" in field_type:
                # Union type with null (optional field)
                non_null_types = [t for t in field_type if t != "null"]
                if len(non_null_types) == 1:
                    field_type_str = f"{non_null_types[0]}?"
                else:
                    field_type_str = f"union {{ {', '.join(field_type)} }}"
            elif isinstance(field_type, dict):
                # Complex type
                if field_type.get("type") == "array":
                    field_type_str = f"array<{field_type['items']}>"
                elif field_type.get("type") == "map":
                    field_type_str = f"map<{field_type['values']}>"
                else:
                    field_type_str = str(field_type)
            else:
                field_type_str = str(field_type)
            
            field_line = f"  {field_type_str} {field_name}"
            if default is not None:
                field_line += f" = {json.dumps(default)}"
            field_line += ";"
            
            if doc:
                field_line = f"  /** {doc} */\n{field_line}"
            
            return field_line
        
        if schema_obj.get("type") == "record":
            record_name = schema_obj.get("name", subject)
            namespace = schema_obj.get("namespace", "")
            doc = schema_obj.get("doc", "")
            
            idl_lines = []
            
            if namespace:
                idl_lines.append(f"@namespace(\"{namespace}\")")
            
            if doc:
                idl_lines.append(f"/** {doc} */")
            
            idl_lines.append(f"record {record_name} {{")
            
            fields = schema_obj.get("fields", [])
            for field in fields:
                idl_lines.append(format_field(field))
            
            idl_lines.append("}")
            
            return "\n".join(idl_lines)
        else:
            return f"// Non-record schema for {subject}\n{json.dumps(schema_obj, indent=2)}"
    
    except Exception as e:
        return f"// Error converting schema to IDL: {str(e)}\n{schema_str}"

def get_schema_with_metadata(subject: str, version: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Get schema with additional metadata."""
    try:
        schema_data = get_schema(subject, version, context)
        if "error" in schema_data:
            return schema_data
            
        # Add export metadata
        schema_data["metadata"] = {
            "exported_at": datetime.now().isoformat(),
            "registry_url": SCHEMA_REGISTRY_URL,
            "context": context,
            "export_version": "1.3.0"
        }
        
        return schema_data
    except Exception as e:
        return {"error": str(e)}

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
        schema_data = get_schema_with_metadata(subject, version, context)
        if "error" in schema_data:
            return schema_data
        
        if format == "avro_idl":
            schema_str = schema_data.get("schema", "")
            return format_schema_as_avro_idl(schema_str, subject)
        else:
            return schema_data
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
                "export_version": "1.3.0"
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
                "export_version": "1.3.0"
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
                "export_version": "1.3.0"
            }
        
        return result
    except Exception as e:
        return {"error": str(e)}

# ===== RESOURCES =====

@mcp.resource("registry://status")
def get_registry_status():
    """Get the current status of the Schema Registry connection."""
    try:
        response = requests.get(f"{SCHEMA_REGISTRY_URL}", timeout=5)
        if response.status_code == 200:
            return f"✅ Connected to Schema Registry at {SCHEMA_REGISTRY_URL}"
        else:
            return f"⚠️ Schema Registry responded with status {response.status_code}"
    except Exception as e:
        return f"❌ Cannot connect to Schema Registry: {str(e)}"

@mcp.resource("registry://info")
def get_registry_info():
    """Get detailed information about the Schema Registry configuration."""
    info = {
        "registry_url": SCHEMA_REGISTRY_URL,
        "authentication_enabled": bool(SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD),
        "server_version": "1.3.0",
        "features": [
            "Schema Registration",
            "Context Management", 
            "Configuration Management",
            "Mode Control",
            "Schema Export (JSON, Avro IDL)"
        ]
    }
    return json.dumps(info, indent=2)

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    mcp.run() 