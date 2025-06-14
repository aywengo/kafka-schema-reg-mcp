#!/usr/bin/env python3
"""
Export Tools Module

Handles schema export operations in various formats.
Provides schema, subject, context, and global export functionality.
"""

from typing import Dict, List, Optional, Union, Any
from schema_registry_common import (
    get_default_client,
    export_schema as common_export_schema,
    export_subject as common_export_subject,
    export_context as common_export_context,
    export_global as common_export_global
)

def export_schema_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    version: str = "latest",
    context: Optional[str] = None,
    format: str = "json",
    registry: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    Export a single schema in the specified format.
    
    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
        format: Export format (json, avro_idl)
        registry: Optional registry name (ignored in single-registry mode)
    
    Returns:
        Exported schema data
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            
        if client is None:
            return {"error": "No registry configured or registry not found"}
        
        result = common_export_schema(client, subject, version, context, format)
        if isinstance(result, dict):
            result["registry_mode"] = registry_mode
        return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

def export_subject_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export all versions of a subject.
    
    Args:
        subject: The subject name
        context: Optional schema context
        include_metadata: Include export metadata
        include_config: Include subject configuration
        include_versions: Which versions to include (all, latest)
        registry: Optional registry name (ignored in single-registry mode)
    
    Returns:
        Dictionary containing subject export data
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            
        if client is None:
            return {"error": "No registry configured or registry not found", "registry_mode": registry_mode}
        
        result = common_export_subject(client, subject, context, include_metadata, include_config, include_versions)
        result["registry_mode"] = registry_mode
        return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

def export_context_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all"
) -> Dict[str, Any]:
    """
    Export all subjects within a context.
    
    Args:
        context: The context name
        registry: Optional registry name (ignored in single-registry mode)
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
    
    Returns:
        Dictionary containing context export data
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use common function
            client = get_default_client(registry_manager)
            if client is None:
                return {"error": "No default registry configured", "registry_mode": "single"}
            result = common_export_context(client, context, include_metadata, include_config, include_versions)
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found", "registry_mode": "multi"}
            
            # Get all subjects in context
            subjects_list = client.get_subjects(context)
            if isinstance(subjects_list, dict) and "error" in subjects_list:
                return subjects_list
            
            # Export each subject
            subjects_data = []
            for subject in subjects_list:
                subject_export = export_subject_tool(
                    subject, registry_manager, registry_mode, context, include_metadata, include_config, include_versions, registry
                )
                if "error" not in subject_export:
                    subjects_data.append(subject_export)
            
            result = {
                "context": context,
                "subjects": subjects_data,
                "registry": client.config.name
            }
            
            if include_config:
                global_config = client.get_global_config(context)
                if "error" not in global_config:
                    result["global_config"] = global_config
                
                global_mode = client.get_mode(context)
                if "error" not in global_mode:
                    result["global_mode"] = global_mode
            
            if include_metadata:
                from datetime import datetime
                result["metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "registry_url": client.config.url,
                    "registry_name": client.config.name,
                    "export_version": "2.0.0",
                    "registry_mode": "multi"
                }
            
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

def export_global_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all"
) -> Dict[str, Any]:
    """
    Export all contexts and schemas from a registry.
    
    Args:
        registry: Optional registry name (ignored in single-registry mode)
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
    
    Returns:
        Dictionary containing global export data
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use common function
            client = get_default_client(registry_manager)
            if client is None:
                return {"error": "No default registry configured", "registry_mode": "single"}
            result = common_export_global(client, include_metadata, include_config, include_versions)
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found", "registry_mode": "multi"}
            
            # Get all contexts
            contexts_list = client.get_contexts()
            if isinstance(contexts_list, dict) and "error" in contexts_list:
                return contexts_list
            
            # Export each context
            contexts_data = []
            for context in contexts_list:
                context_export = export_context_tool(
                    context, registry_manager, registry_mode, registry, include_metadata, include_config, include_versions
                )
                if "error" not in context_export:
                    contexts_data.append(context_export)
            
            # Export default context (no context specified)
            default_export = export_context_tool(
                "", registry_manager, registry_mode, registry, include_metadata, include_config, include_versions
            )
            
            result = {
                "contexts": contexts_data,
                "default_context": default_export if "error" not in default_export else None,
                "registry": client.config.name
            }
            
            if include_config:
                global_config = client.get_global_config()
                if "error" not in global_config:
                    result["global_config"] = global_config
                
                global_mode = client.get_mode()
                if "error" not in global_mode:
                    result["global_mode"] = global_mode
            
            if include_metadata:
                from datetime import datetime
                result["metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "registry_url": client.config.url,
                    "registry_name": client.config.name,
                    "export_version": "2.0.0",
                    "registry_mode": "multi"
                }
            
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode} 