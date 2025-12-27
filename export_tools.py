#!/usr/bin/env python3
"""
Export Tools Module - Updated with Resource Linking

Handles schema export operations in various formats with structured tool output
support per MCP 2025-06-18 specification including resource linking.

Provides schema, subject, context, and global export functionality
with JSON Schema validation, type-safe responses, and HATEOAS navigation links.
"""

import json
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from resource_linking import add_links_to_response
from schema_registry_common import export_context as common_export_context
from schema_registry_common import export_global as common_export_global
from schema_registry_common import export_schema as common_export_schema
from schema_registry_common import export_subject as common_export_subject
from schema_registry_common import get_default_client
from schema_validation import (
    create_error_response,
    structured_output,
)

if TYPE_CHECKING:
    from fastmcp.server.context import Context


def _get_registry_name_for_linking(registry_mode: str, client=None, registry: Optional[str] = None) -> str:
    """Helper function to get registry name for linking."""
    if registry_mode == "single":
        return "default"
    elif client and hasattr(client, "config"):
        return client.config.name
    elif registry:
        return registry
    else:
        return "unknown"


@structured_output("export_schema", fallback_on_error=True)
def export_schema_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    version: str = "latest",
    context: Optional[str] = None,
    format: str = "json",
    registry: Optional[str] = None,
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
        Exported schema data with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)

        if client is None:
            return create_error_response(
                "No registry configured or registry not found",
                error_code="REGISTRY_NOT_CONFIGURED",
                registry_mode=registry_mode,
            )

        result = common_export_schema(client, subject, version, context, format)

        if isinstance(result, dict):
            # Add structured output metadata
            result["registry_mode"] = registry_mode
            result["mcp_protocol_version"] = "2025-11-25"

            # Ensure required fields for export schema
            if "subject" not in result:
                result["subject"] = subject
            if "version" not in result:
                result["version"] = version if version != "latest" else 1
            if "format" not in result:
                result["format"] = format

            # Ensure content field is present - this is required by the schema
            if "content" not in result:
                # Generate content from schema field
                if "schema" in result:
                    if format == "json":
                        result["content"] = json.dumps(result["schema"], indent=2)
                    else:
                        result["content"] = str(result["schema"])
                else:
                    result["content"] = ""

            # Add resource links for dictionary results
            registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
            result = add_links_to_response(
                result,
                "schema",
                registry_name,
                subject=subject,
                version=version,
                context=context,
            )

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_EXPORT_FAILED", registry_mode=registry_mode)


@structured_output("export_subject", fallback_on_error=True)
def export_subject_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    registry: Optional[str] = None,
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
        Dictionary containing subject export data with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)

        if client is None:
            return create_error_response(
                "No registry configured or registry not found",
                error_code="REGISTRY_NOT_CONFIGURED",
                registry_mode=registry_mode,
            )

        result = common_export_subject(client, subject, context, include_metadata, include_config, include_versions)

        # Add structured output metadata
        result["registry_mode"] = registry_mode
        result["mcp_protocol_version"] = "2025-11-25"

        # Ensure required fields for export subject
        if "subject" not in result:
            result["subject"] = subject
        if "versions" not in result:
            result["versions"] = []

        # Add resource links
        registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
        result = add_links_to_response(result, "subject", registry_name, subject=subject, context=context)

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_EXPORT_FAILED", registry_mode=registry_mode)


@structured_output("export_context", fallback_on_error=True)
async def export_context_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    mcp_context: Optional["Context"] = None,
) -> Dict[str, Any]:
    """
    Export all subjects within a context.

    Args:
        context: The context name
        registry: Optional registry name (ignored in single-registry mode)
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
        mcp_context: MCP Context for progress reporting

    Returns:
        Dictionary containing context export data with structured validation and resource links
    """
    try:
        # Initial setup (0-10%)
        if mcp_context:
            await mcp_context.info(f"Starting context export: {context}")
            await mcp_context.report_progress(0.0, 100.0, "Initializing context export")

        if registry_mode == "single":
            # Single-registry mode: use common function
            client = get_default_client(registry_manager)
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_CONFIGURED",
                    registry_mode="single",
                )

            if mcp_context:
                await mcp_context.report_progress(5.0, 100.0, "Using default registry client")

            result = common_export_context(client, context, include_metadata, include_config, include_versions)
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
            result = add_links_to_response(result, "context", registry_name, context=context)

            if mcp_context:
                await mcp_context.info("Context export completed successfully")
                await mcp_context.report_progress(100.0, 100.0, "Context export completed")

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            if mcp_context:
                await mcp_context.report_progress(10.0, 100.0, f"Registry client '{registry}' initialized")

            # Get all subjects in context (10-25%)
            if mcp_context:
                await mcp_context.info(f"Fetching subjects from context: {context}")
                await mcp_context.report_progress(15.0, 100.0, f"Fetching subjects from context '{context}'")

            subjects_list = client.get_subjects(context)
            if isinstance(subjects_list, dict) and "error" in subjects_list:
                return create_error_response(
                    f"Failed to get subjects for context '{context}': {subjects_list.get('error')}",
                    error_code="CONTEXT_SUBJECTS_RETRIEVAL_FAILED",
                    registry_mode=registry_mode,
                )

            if mcp_context:
                await mcp_context.report_progress(25.0, 100.0, f"Found {len(subjects_list)} subjects in context")

            # Export each subject (25-70%)
            subjects_data = []
            if mcp_context:
                await mcp_context.info(f"Exporting {len(subjects_list)} subjects")
                await mcp_context.report_progress(30.0, 100.0, f"Starting export of {len(subjects_list)} subjects")

            for i, subject in enumerate(subjects_list):
                # Report progress for subject export
                if mcp_context and len(subjects_list) > 0:
                    progress = 30.0 + (i / len(subjects_list)) * 40.0  # 30% to 70%
                    await mcp_context.report_progress(
                        progress, 100.0, f"Exporting subject {i+1}/{len(subjects_list)}: {subject}"
                    )

                subject_export = export_subject_tool(
                    subject,
                    registry_manager,
                    registry_mode,
                    context,
                    include_metadata,
                    include_config,
                    include_versions,
                    registry,
                )
                if "error" not in subject_export:
                    subjects_data.append(subject_export)

            if mcp_context:
                await mcp_context.report_progress(70.0, 100.0, f"Exported {len(subjects_data)} subjects successfully")

            # Build result structure (70-80%)
            if mcp_context:
                await mcp_context.report_progress(75.0, 100.0, "Building export result structure")

            result = {
                "context": context,
                "subjects": subjects_data,
                "subject_count": len(subjects_data),
                "registry": client.config.name,
                "registry_mode": registry_mode,
                "mcp_protocol_version": "2025-11-25",
            }

            # Add configuration data if requested (80-90%)
            if include_config:
                if mcp_context:
                    await mcp_context.report_progress(80.0, 100.0, "Fetching context configuration")

                global_config = client.get_global_config(context)
                if "error" not in global_config:
                    result["global_config"] = global_config

                global_mode = client.get_mode(context)
                if "error" not in global_mode:
                    result["global_mode"] = global_mode

                if mcp_context:
                    await mcp_context.report_progress(85.0, 100.0, "Context configuration added")
            else:
                if mcp_context:
                    await mcp_context.report_progress(85.0, 100.0, "Skipping context configuration")

            # Add metadata if requested (90-95%)
            if include_metadata:
                if mcp_context:
                    await mcp_context.report_progress(90.0, 100.0, "Adding export metadata")

                from datetime import datetime

                result["metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "registry_url": client.config.url,
                    "registry_name": client.config.name,
                    "export_version": "2.0.0",
                    "registry_mode": "multi",
                }

            # Add resource links (95-100%)
            if mcp_context:
                await mcp_context.report_progress(95.0, 100.0, "Adding resource links")

            registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
            result = add_links_to_response(result, "context", registry_name, context=context)

            if mcp_context:
                await mcp_context.info("Context export completed successfully")
                await mcp_context.report_progress(100.0, 100.0, "Context export completed")

            return result
    except Exception as e:
        if mcp_context:
            await mcp_context.error(f"Context export failed: {str(e)}")
        return create_error_response(str(e), error_code="CONTEXT_EXPORT_FAILED", registry_mode=registry_mode)


@structured_output("export_global", fallback_on_error=True)
async def export_global_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    mcp_context: Optional["Context"] = None,
) -> Dict[str, Any]:
    """
    Export all contexts and schemas from a registry.

    Args:
        registry: Optional registry name (ignored in single-registry mode)
        include_metadata: Include export metadata
        include_config: Include configuration data
        include_versions: Which versions to include (all, latest)
        mcp_context: MCP Context for progress reporting

    Returns:
        Dictionary containing global export data with structured validation and resource links
    """
    try:
        # Initial setup (0-10%)
        if mcp_context:
            await mcp_context.info(f"Starting global export from registry: {registry or 'default'}")
            await mcp_context.report_progress(0.0, 100.0, "Initializing global export")

        if registry_mode == "single":
            # Single-registry mode: use common function
            client = get_default_client(registry_manager)
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_CONFIGURED",
                    registry_mode="single",
                )

            if mcp_context:
                await mcp_context.report_progress(5.0, 100.0, "Using default registry client")

            result = common_export_global(client, include_metadata, include_config, include_versions)
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
            result = add_links_to_response(result, "registry", registry_name)

            if mcp_context:
                await mcp_context.info("Global export completed successfully")
                await mcp_context.report_progress(100.0, 100.0, "Global export completed")

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            if mcp_context:
                await mcp_context.report_progress(10.0, 100.0, f"Registry client '{registry}' initialized")

            # Get all contexts (10-20%)
            if mcp_context:
                await mcp_context.info(f"Fetching contexts from registry: {registry}")
                await mcp_context.report_progress(15.0, 100.0, f"Fetching contexts from registry '{registry}'")

            contexts_list = client.get_contexts()
            if isinstance(contexts_list, dict) and "error" in contexts_list:
                return create_error_response(
                    f"Failed to get contexts: {contexts_list.get('error')}",
                    error_code="CONTEXTS_RETRIEVAL_FAILED",
                    registry_mode=registry_mode,
                )

            if mcp_context:
                await mcp_context.report_progress(20.0, 100.0, f"Found {len(contexts_list)} contexts in registry")

            # Export each context (20-70%)
            contexts_data = []
            if mcp_context:
                await mcp_context.info(f"Exporting {len(contexts_list)} contexts")
                await mcp_context.report_progress(25.0, 100.0, f"Starting export of {len(contexts_list)} contexts")

            for i, context in enumerate(contexts_list):
                # Report progress for context export
                if mcp_context and len(contexts_list) > 0:
                    progress = 25.0 + (i / len(contexts_list)) * 40.0  # 25% to 65%
                    await mcp_context.report_progress(
                        progress, 100.0, f"Exporting context {i+1}/{len(contexts_list)}: {context}"
                    )

                context_export = await export_context_tool(
                    context,
                    registry_manager,
                    registry_mode,
                    registry,
                    include_metadata,
                    include_config,
                    include_versions,
                    None,  # Don't pass mcp_context to avoid nested progress reporting
                )
                if "error" not in context_export:
                    contexts_data.append(context_export)

            if mcp_context:
                await mcp_context.report_progress(65.0, 100.0, f"Exported {len(contexts_data)} contexts successfully")

            # Export default context (65-70%)
            if mcp_context:
                await mcp_context.report_progress(68.0, 100.0, "Exporting default context")

            default_export = await export_context_tool(
                "",
                registry_manager,
                registry_mode,
                registry,
                include_metadata,
                include_config,
                include_versions,
                None,  # Don't pass mcp_context to avoid nested progress reporting
            )

            if mcp_context:
                await mcp_context.report_progress(70.0, 100.0, "Default context export completed")

            # Build result structure (70-80%)
            if mcp_context:
                await mcp_context.report_progress(75.0, 100.0, "Building global export result structure")

            result = {
                "contexts": contexts_data,
                "contexts_count": len(contexts_data),
                "default_context": (default_export if "error" not in default_export else None),
                "registry": client.config.name,
                "registry_mode": registry_mode,
                "mcp_protocol_version": "2025-11-25",
            }

            # Add configuration data if requested (80-90%)
            if include_config:
                if mcp_context:
                    await mcp_context.report_progress(80.0, 100.0, "Fetching global configuration")

                global_config = client.get_global_config()
                if "error" not in global_config:
                    result["global_config"] = global_config

                global_mode = client.get_mode()
                if "error" not in global_mode:
                    result["global_mode"] = global_mode

                if mcp_context:
                    await mcp_context.report_progress(85.0, 100.0, "Global configuration added")
            else:
                if mcp_context:
                    await mcp_context.report_progress(85.0, 100.0, "Skipping global configuration")

            # Add metadata if requested (90-95%)
            if include_metadata:
                if mcp_context:
                    await mcp_context.report_progress(90.0, 100.0, "Adding export metadata")

                from datetime import datetime

                result["metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "registry_url": client.config.url,
                    "registry_name": client.config.name,
                    "export_version": "2.0.0",
                    "registry_mode": "multi",
                    "total_contexts": len(contexts_data),
                    "total_subjects": sum(len(ctx.get("subjects", [])) for ctx in contexts_data),
                }

            # Add resource links (95-100%)
            if mcp_context:
                await mcp_context.report_progress(95.0, 100.0, "Adding resource links")

            registry_name = _get_registry_name_for_linking(registry_mode, client, registry)
            result = add_links_to_response(result, "registry", registry_name)

            if mcp_context:
                await mcp_context.info("Global export completed successfully")
                await mcp_context.report_progress(100.0, 100.0, "Global export completed")

            return result
    except Exception as e:
        if mcp_context:
            await mcp_context.error(f"Global export failed: {str(e)}")
        return create_error_response(str(e), error_code="GLOBAL_EXPORT_FAILED", registry_mode=registry_mode)
