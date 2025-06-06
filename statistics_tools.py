#!/usr/bin/env python3
"""
Statistics Tools Module

Handles counting and statistics operations for Schema Registry.
Provides counting for contexts, schemas, versions, and comprehensive registry statistics.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from schema_registry_common import get_default_client

def count_contexts_tool(registry_manager, registry_mode: str, registry: Optional[str] = None) -> Dict[str, Any]:
    """
    Count the number of contexts in a registry.
    
    Args:
        registry: Optional registry name (ignored in single-registry mode)
    
    Returns:
        Dictionary containing context count and details
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts
            
        return {
            "registry": client.config.name if hasattr(client.config, 'name') else "default",
            "total_contexts": len(contexts),
            "contexts": contexts,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def count_schemas_tool(
    registry_manager, 
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Count the number of schemas in a context or registry.
    
    Args:
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)
    
    Returns:
        Dictionary containing schema count and details
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        subjects = client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            return subjects
            
        return {
            "registry": client.config.name if hasattr(client.config, 'name') else "default",
            "context": context or "default",
            "total_schemas": len(subjects),
            "schemas": subjects,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def count_schema_versions_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Count the number of versions for a specific schema.
    
    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)
    
    Returns:
        Dictionary containing version count and details
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        # Import the function here to avoid circular imports
        from kafka_schema_registry_unified_mcp import get_schema_versions
        
        versions = get_schema_versions(subject, context, registry)
        if isinstance(versions, dict) and "error" in versions:
            return versions
            
        return {
            "registry": client.config.name if hasattr(client.config, 'name') else "default",
            "context": context or "default",
            "subject": subject,
            "total_versions": len(versions),
            "versions": versions,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def get_registry_statistics_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a registry.
    
    Args:
        registry: Optional registry name (ignored in single-registry mode)
        include_context_details: Whether to include detailed context statistics
    
    Returns:
        Dictionary containing registry statistics
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        # Get all contexts
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts
            
        total_schemas = 0
        total_versions = 0
        context_stats = []
        
        # Import the function here to avoid circular imports
        from kafka_schema_registry_unified_mcp import get_schema_versions
        
        # Get statistics for each context
        for context in contexts:
            subjects = client.get_subjects(context)
            if isinstance(subjects, dict) and "error" in subjects:
                continue
                
            context_schemas = len(subjects)
            context_versions = 0
            
            # Count versions for each subject
            for subject in subjects:
                versions = get_schema_versions(subject, context, registry)
                if not isinstance(versions, dict):
                    context_versions += len(versions)
            
            total_schemas += context_schemas
            total_versions += context_versions
            
            if include_context_details:
                context_stats.append({
                    "context": context,
                    "schemas": context_schemas,
                    "versions": context_versions
                })
        
        # Get default context stats
        default_subjects = client.get_subjects()
        if not isinstance(default_subjects, dict):
            default_schemas = len(default_subjects)
            default_versions = 0
            
            for subject in default_subjects:
                versions = get_schema_versions(subject, None, registry)
                if not isinstance(versions, dict):
                    default_versions += len(versions)
            
            total_schemas += default_schemas
            total_versions += default_versions
            
            if include_context_details:
                context_stats.append({
                    "context": "default",
                    "schemas": default_schemas,
                    "versions": default_versions
                })
        
        return {
            "registry": client.config.name if hasattr(client.config, 'name') else "default",
            "total_contexts": len(contexts),
            "total_schemas": total_schemas,
            "total_versions": total_versions,
            "average_versions_per_schema": round(total_versions / max(total_schemas, 1), 2),
            "contexts": context_stats if include_context_details else None,
            "counted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)} 