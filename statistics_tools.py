#!/usr/bin/env python3
"""
Statistics Tools Module

Handles counting and statistics operations for Schema Registry.
Provides counting for contexts, schemas, versions, and comprehensive registry statistics.
"""

import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from schema_registry_common import get_default_client
from task_management import task_manager, TaskType, TaskStatus

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

# ===== OPTIMIZED ASYNC STATISTICS FUNCTIONS =====

async def _count_schemas_async(
    registry_manager, 
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async version of count_schemas_tool with better performance.
    Uses parallel API calls when counting multiple contexts.
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        if context:
            # Single context - direct call
            subjects = client.get_subjects(context)
            if isinstance(subjects, dict) and "error" in subjects:
                return subjects
                
            return {
                "registry": client.config.name if hasattr(client.config, 'name') else "default",
                "context": context,
                "total_schemas": len(subjects),
                "schemas": subjects,
                "counted_at": datetime.now().isoformat()
            }
        else:
            # All contexts - parallel execution
            contexts = client.get_contexts()
            if isinstance(contexts, dict) and "error" in contexts:
                return contexts
            
            total_schemas = 0
            all_schemas = {}
            
            # Parallel execution for better performance
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_context = {
                    executor.submit(client.get_subjects, ctx): ctx 
                    for ctx in contexts
                }
                
                # Add default context
                future_to_context[executor.submit(client.get_subjects, None)] = "default"
                
                for future in as_completed(future_to_context):
                    ctx = future_to_context[future]
                    try:
                        subjects = future.result()
                        if not isinstance(subjects, dict):
                            all_schemas[ctx] = subjects
                            total_schemas += len(subjects)
                    except Exception as e:
                        all_schemas[ctx] = {"error": str(e)}
            
            return {
                "registry": client.config.name if hasattr(client.config, 'name') else "default",
                "total_schemas": total_schemas,
                "schemas_by_context": all_schemas,
                "contexts_analyzed": len(all_schemas),
                "counted_at": datetime.now().isoformat()
            }
    except Exception as e:
        return {"error": str(e)}

def count_schemas_task_queue_tool(
    registry_manager, 
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Task queue version of count_schemas for better performance on large registries.
    Returns task_id immediately for async execution.
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.STATISTICS,
            metadata={
                "operation": "count_schemas",
                "context": context,
                "registry": registry
            }
        )
        
        # Start async execution
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _count_schemas_async,
                    registry_manager=registry_manager,
                    registry_mode=registry_mode,
                    context=context,
                    registry=registry
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _count_schemas_async,
                        registry_manager=registry_manager,
                        registry_mode=registry_mode,
                        context=context,
                        registry=registry
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
        return {
            "message": "Schema counting started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": {
                "operation": "count_schemas",
                "expected_duration": "medium",
                "async_pattern": "task_queue",
                "guidance": "Long-running operation. Returns task_id immediately. Use get_task_status() to monitor progress.",
                "registry_mode": registry_mode
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _get_registry_statistics_async(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async version of get_registry_statistics_tool with parallel execution.
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}
        
        # Update progress
        if task_id:
            task_manager.update_progress(task_id, 10.0)
        
        # Get all contexts
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts
        
        if task_id:
            task_manager.update_progress(task_id, 20.0)
            
        total_schemas = 0
        total_versions = 0
        context_stats = []
        
        # Parallel execution for better performance
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all context analysis tasks
            future_to_context = {}
            
            # Add all contexts
            for context in contexts:
                future = executor.submit(_analyze_context_parallel, client, context, registry)
                future_to_context[future] = context
            
            # Add default context
            future = executor.submit(_analyze_context_parallel, client, None, registry)
            future_to_context[future] = "default"
            
            # Collect results
            completed = 0
            total_contexts = len(future_to_context)
            
            for future in as_completed(future_to_context):
                context = future_to_context[future]
                try:
                    context_result = future.result()
                    
                    if not isinstance(context_result, dict) or "error" not in context_result:
                        total_schemas += context_result.get("schemas", 0)
                        total_versions += context_result.get("versions", 0)
                        
                        if include_context_details:
                            context_stats.append({
                                "context": context,
                                "schemas": context_result.get("schemas", 0),
                                "versions": context_result.get("versions", 0)
                            })
                    
                    # Update progress
                    completed += 1
                    if task_id:
                        # Progress from 20% to 90% based on context completion
                        progress = 20.0 + (completed / total_contexts) * 70.0
                        task_manager.update_progress(task_id, progress)
                        
                except Exception as e:
                    if include_context_details:
                        context_stats.append({
                            "context": context,
                            "error": str(e)
                        })
        
        if task_id:
            task_manager.update_progress(task_id, 95.0)
        
        result = {
            "registry": client.config.name if hasattr(client.config, 'name') else "default",
            "total_contexts": len(contexts),
            "total_schemas": total_schemas,
            "total_versions": total_versions,
            "average_versions_per_schema": round(total_versions / max(total_schemas, 1), 2),
            "contexts": context_stats if include_context_details else None,
            "counted_at": datetime.now().isoformat()
        }
        
        if task_id:
            task_manager.update_progress(task_id, 100.0)
            
        return result
        
    except Exception as e:
        return {"error": str(e)}

def _analyze_context_parallel(client, context: Optional[str], registry: Optional[str]) -> Dict[str, Any]:
    """
    Analyze a single context in parallel execution.
    Returns schema and version counts for the context.
    """
    try:
        subjects = client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            return {"error": subjects["error"]}
        
        schema_count = len(subjects)
        version_count = 0
        
        # Use ThreadPoolExecutor for version counting too
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Import here to avoid circular imports
            from kafka_schema_registry_unified_mcp import get_schema_versions
            
            futures = [
                executor.submit(get_schema_versions, subject, context, registry)
                for subject in subjects
            ]
            
            for future in as_completed(futures):
                try:
                    versions = future.result()
                    if not isinstance(versions, dict):
                        version_count += len(versions)
                except Exception:
                    # Skip failed version counts
                    pass
        
        return {
            "schemas": schema_count,
            "versions": version_count
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_registry_statistics_task_queue_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True
) -> Dict[str, Any]:
    """
    Task queue version of get_registry_statistics for better performance.
    Returns task_id immediately for async execution with progress tracking.
    """
    try:
        # Create async task
        task = task_manager.create_task(
            TaskType.STATISTICS,
            metadata={
                "operation": "get_registry_statistics",
                "registry": registry,
                "include_context_details": include_context_details
            }
        )
        
        # Start async execution
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _get_registry_statistics_async,
                    registry_manager=registry_manager,
                    registry_mode=registry_mode,
                    registry=registry,
                    include_context_details=include_context_details,
                    task_id=task.id
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _get_registry_statistics_async,
                        registry_manager=registry_manager,
                        registry_mode=registry_mode,
                        registry=registry,
                        include_context_details=include_context_details,
                        task_id=task.id
                    )
                )
            thread = threading.Thread(target=run_task)
            thread.start()
        
        return {
            "message": "Registry statistics analysis started as async task",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": {
                "operation": "get_registry_statistics",
                "expected_duration": "long",
                "async_pattern": "task_queue",
                "guidance": "Long-running operation. Returns task_id immediately. Use get_task_status() to monitor progress.",
                "registry_mode": registry_mode
            }
        }
        
    except Exception as e:
        return {"error": str(e)} 