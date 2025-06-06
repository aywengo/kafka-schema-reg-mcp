#!/usr/bin/env python3
"""
Comparison Tools Module

Handles comparison operations between registries and contexts.
Provides registry comparison, context comparison, and missing schema detection.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any

async def compare_registries_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    include_contexts: bool = True,
    include_configs: bool = True
) -> Dict[str, Any]:
    """
    Compare two Schema Registry instances and show differences.
    Only available in multi-registry mode.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        include_contexts: Include context comparison
        include_configs: Include configuration comparison
    
    Returns:
        Comparison results or error if in single-registry mode
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Cross-registry comparison not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry mode with numbered environment variables"
            }
        
        result = await registry_manager.compare_registries_async(source_registry, target_registry)
        result["registry_mode"] = "multi"
        return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

async def compare_contexts_across_registries_tool(
    source_registry: str,
    target_registry: str,
    source_context: str,
    registry_manager,
    registry_mode: str,
    target_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare contexts across two registries (can be different contexts).
    Only available in multi-registry mode.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Context name in source registry
        target_context: Context name in target registry (defaults to source_context if not provided)
    
    Returns:
        Context comparison results
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Context comparison across registries not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable cross-registry comparison"
            }
        
        # If target_context not provided, use source_context (backward compatibility)
        if target_context is None:
            target_context = source_context
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client:
            return {"error": f"Source registry '{source_registry}' not found", "registry_mode": "multi"}
        if not target_client:
            return {"error": f"Target registry '{target_registry}' not found", "registry_mode": "multi"}
        
        # Simple synchronous implementation for now
        try:
            # Get subjects from both registries for their respective contexts
            source_subjects = source_client.get_subjects(source_context)
            target_subjects = target_client.get_subjects(target_context)
            
            # Handle error cases
            if isinstance(source_subjects, dict) and "error" in source_subjects:
                source_subjects = []
            if isinstance(target_subjects, dict) and "error" in target_subjects:
                target_subjects = []
            
            # Compare contexts
            source_only = list(set(source_subjects) - set(target_subjects))
            target_only = list(set(target_subjects) - set(source_subjects))
            common = list(set(source_subjects) & set(target_subjects))
            
            result = {
                "source_registry": source_registry,
                "target_registry": target_registry,
                "source_context": source_context,
                "target_context": target_context,
                "compared_at": datetime.now().isoformat(),
                "registry_mode": "multi",
                "summary": {
                    "source_only_subjects": len(source_only),
                    "target_only_subjects": len(target_only),
                    "common_subjects": len(common),
                    "total_source_subjects": len(source_subjects),
                    "total_target_subjects": len(target_subjects)
                },
                "subjects": {
                    "source_only": source_only,
                    "target_only": target_only,
                    "common": common,
                    "source_total": len(source_subjects),
                    "target_total": len(target_subjects)
                }
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Context comparison failed: {str(e)}", "registry_mode": "multi"}
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}

async def find_missing_schemas_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find schemas that exist in source registry but not in target registry.
    Only available in multi-registry mode.
    
    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Optional context to search within
    
    Returns:
        Dictionary containing missing schemas information
    """
    try:
        if registry_mode == "single":
            return {
                "error": "Finding missing schemas across registries not available in single-registry mode",
                "registry_mode": "single",
                "suggestion": "Use multi-registry configuration to enable cross-registry analysis"
            }
        
        # Get registry clients
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)
        
        if not source_client:
            return {"error": f"Source registry '{source_registry}' not found", "registry_mode": "multi"}
        if not target_client:
            return {"error": f"Target registry '{target_registry}' not found", "registry_mode": "multi"}
        
        try:
            # Get subjects from both registries
            source_subjects = source_client.get_subjects(context)
            target_subjects = target_client.get_subjects(context)
            
            # Handle error cases
            if isinstance(source_subjects, dict) and "error" in source_subjects:
                source_subjects = []
            if isinstance(target_subjects, dict) and "error" in target_subjects:
                target_subjects = []
            
            # Find missing schemas (in source but not in target)
            missing_schemas = list(set(source_subjects) - set(target_subjects))
            
            result = {
                "source_registry": source_registry,
                "target_registry": target_registry,
                "context": context,
                "analyzed_at": datetime.now().isoformat(),
                "registry_mode": "multi",
                "missing_schemas": missing_schemas,
                "missing_count": len(missing_schemas),
                "source_total": len(source_subjects),
                "target_total": len(target_subjects)
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Schema analysis failed: {str(e)}", "registry_mode": "multi"}
        
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode} 