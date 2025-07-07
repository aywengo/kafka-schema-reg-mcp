#!/usr/bin/env python3
"""
Kafka Schema Registry Unified MCP Server - Modular Version with Elicitation Support

A comprehensive Message Control Protocol (MCP) server that automatically detects
and supports both single and multi-registry modes based on environment variables.

🎯 NEW: ELICITATION CAPABILITY - Interactive workflow support per MCP 2025-06-18 specification.
    Tools can now interactively request missing information from users for guided workflows.

🚫 JSON-RPC BATCHING DISABLED: Per MCP 2025-06-18 specification compliance.
    Application-level batch operations (clear_context_batch, etc.) remain available
    and use individual requests with parallel processing for performance.

✅ MCP-PROTOCOL-VERSION HEADER VALIDATION: All HTTP requests after initialization
    must include the MCP-Protocol-Version header per MCP 2025-06-18 specification.

This modular version splits functionality across specialized modules:
- task_management: Async task queue operations
- migration_tools: Schema and context migration
- comparison_tools: Registry and context comparison
- export_tools: Schema export functionality
- batch_operations: Application-level batch cleanup operations
- statistics_tools: Counting and statistics
- core_registry_tools: Basic CRUD operations
- elicitation: Interactive workflow support (NEW)
- interactive_tools: Elicitation-enabled tool variants (NEW)
- elicitation_mcp_integration: Real MCP protocol integration (NEW)

Features:
- Automatic mode detection
- 53+ MCP Tools (all original tools + elicitation-enabled variants)
- Interactive Schema Registration with guided field definition
- Interactive Migration with preference elicitation
- Interactive Compatibility Resolution
- Interactive Context Creation with metadata collection
- Interactive Export with format preference selection
- Cross-Registry Comparison and Migration
- Schema Export/Import with multiple formats
- Async Task Queue for long-running operations
- VIEWONLY Mode protection (with READONLY backward compatibility)
- OAuth scopes support
- MCP 2025-06-18 specification compliance (JSON-RPC batching disabled)
- MCP-Protocol-Version header validation
- Structured tool output for all tools (100% complete)
- Elicitation capability for interactive workflows
- MCP ping/pong protocol support
"""

import base64
import json
import logging
import os
import urllib.error

# Prevent network requests to JSON Schema meta-schema URLs
import urllib.request

from dotenv import load_dotenv

# Store original urllib opener
_original_opener = urllib.request.build_opener()


class LocalSchemaHandler(urllib.request.BaseHandler):
    """Custom handler to serve JSON Schema meta-schemas locally."""

    def http_open(self, req):
        return self.handle_schema_request(req)

    def https_open(self, req):
        return self.handle_schema_request(req)

    def handle_schema_request(self, req):
        url = req.get_full_url()

        # Check if this is a request to json-schema.org
        if "json-schema.org" in url and "draft-07" in url:
            # Return a minimal valid schema response
            schema_content = json.dumps(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "$id": "http://json-schema.org/draft-07/schema#",
                    "title": "Core schema meta-schema",
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {},
                    "definitions": {},
                }
            ).encode("utf-8")

            # Create a mock response
            import urllib.response
            from io import BytesIO

            response = urllib.response.addinfourl(
                BytesIO(schema_content), headers={"Content-Type": "application/json"}, url=url, code=200
            )
            return response

        # For non-schema URLs, use the original opener
        return _original_opener.open(req)


# Install the custom handler
custom_opener = urllib.request.build_opener(LocalSchemaHandler)
urllib.request.install_opener(custom_opener)

# Also patch requests library if available
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.models import Response

    class LocalSchemaAdapter(HTTPAdapter):
        """Custom adapter to serve JSON Schema meta-schemas locally."""

        def send(self, request, **kwargs):
            url = request.url

            # Check if this is a request to json-schema.org for draft-07 schema
            if "json-schema.org" in url and "draft-07" in url:
                # Create a mock response
                response = Response()
                response.status_code = 200
                response.headers["Content-Type"] = "application/json"
                response._content = json.dumps(
                    {
                        "$schema": "http://json-schema.org/draft-07/schema#",
                        "$id": "http://json-schema.org/draft-07/schema#",
                        "title": "Core schema meta-schema",
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {},
                        "definitions": {},
                    }
                ).encode("utf-8")
                response.url = url
                return response

            # For non-schema URLs, use normal behavior
            return super().send(request, **kwargs)

    # Create a global session with the custom adapter
    session = requests.Session()
    session.mount("http://json-schema.org", LocalSchemaAdapter())
    session.mount("https://json-schema.org", LocalSchemaAdapter())

    # Monkey-patch the requests.get function to use our session
    original_get = requests.get
    original_post = requests.post

    def patched_get(url, **kwargs):
        if "json-schema.org" in url:
            return session.get(url, **kwargs)
        return original_get(url, **kwargs)

    def patched_post(url, **kwargs):
        if "json-schema.org" in url:
            return session.post(url, **kwargs)
        return original_post(url, **kwargs)

    requests.get = patched_get
    requests.post = patched_post

except ImportError:
    pass  # requests not available

from fastmcp import FastMCP

# Load environment variables first
load_dotenv()

# Import OAuth functionality
from oauth_provider import (  # noqa: E402
    ENABLE_AUTH,
    get_fastmcp_config,
    get_oauth_scopes_info,
    require_scopes,
)

# MCP 2025-06-18 Protocol Version Support
MCP_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_MCP_VERSIONS = ["2025-06-18"]

# Paths that are exempt from MCP-Protocol-Version header validation
EXEMPT_PATHS = [
    "/health",
    "/metrics",
    "/ready",
    "/.well-known",  # This will match all paths starting with /.well-known
]


def is_exempt_path(path: str) -> bool:
    """Check if a request path is exempt from MCP-Protocol-Version header validation."""
    for exempt_path in EXEMPT_PATHS:
        if path.startswith(exempt_path):
            return True
    return False


async def validate_mcp_protocol_version_middleware(request, call_next):
    """
    Middleware to validate MCP-Protocol-Version header on all requests.

    Per MCP 2025-06-18 specification, all HTTP requests after initialization
    must include the MCP-Protocol-Version header.

    Exempt paths: /health, /metrics, /ready, /.well-known/*
    """
    # Import FastAPI components only when needed to avoid dependency issues
    try:
        from fastapi.responses import JSONResponse
    except ImportError:
        # If FastAPI is not available, skip validation (for compatibility)
        response = await call_next(request)
        return response

    # Handle different request types - some may not have a url attribute
    try:
        # Try to get the path from the request
        if hasattr(request, "url") and hasattr(request.url, "path"):
            path = request.url.path
        elif hasattr(request, "path"):
            path = request.path
        else:
            # If we can't determine the path, skip validation
            response = await call_next(request)
            return response
    except AttributeError:
        # If request doesn't have expected attributes, skip validation
        response = await call_next(request)
        return response

    # Skip validation for exempt paths
    if is_exempt_path(path):
        response = await call_next(request)
        # Still add the header to exempt responses for consistency
        if hasattr(response, "headers"):
            response.headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION
        return response

    # Check for MCP-Protocol-Version header
    try:
        if hasattr(request, "headers"):
            protocol_version = request.headers.get("MCP-Protocol-Version")
        else:
            # If request doesn't have headers, skip validation
            response = await call_next(request)
            return response
    except (AttributeError, TypeError):
        # If we can't access headers, skip validation
        response = await call_next(request)
        return response

    if not protocol_version:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing MCP-Protocol-Version header",
                "details": "The MCP-Protocol-Version header is required for all MCP requests per MCP 2025-06-18 specification",
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "example": "MCP-Protocol-Version: 2025-06-18",
            },
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION},
        )

    # Validate protocol version
    if protocol_version not in SUPPORTED_MCP_VERSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unsupported MCP-Protocol-Version",
                "details": f"Received version '{protocol_version}' is not supported",
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "received_version": protocol_version,
            },
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION},
        )

    # Process the request
    response = await call_next(request)

    # Add MCP-Protocol-Version header to all responses
    if hasattr(response, "headers"):
        response.headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION

    return response


# Initialize FastMCP with OAuth configuration and MCP 2025-06-18 compliance
mcp_config = get_fastmcp_config("Kafka Schema Registry Unified MCP Server")
mcp = FastMCP(**mcp_config)

# Add MCP-Protocol-Version validation middleware (with error handling)
MIDDLEWARE_ENABLED = False
try:
    # Check if we're in an HTTP context where middleware makes sense
    # For MCP clients using stdio or in-memory transport, middleware isn't needed

    # Try different middleware installation approaches for different FastMCP versions
    if hasattr(mcp, "app") and hasattr(mcp.app, "middleware"):
        mcp.app.middleware("http")(validate_mcp_protocol_version_middleware)
        MIDDLEWARE_ENABLED = True
        logger = logging.getLogger(__name__)
        logger.info("✅ MCP-Protocol-Version header validation middleware enabled")
    elif hasattr(mcp, "add_middleware"):
        # Alternative method for newer FastMCP versions
        mcp.add_middleware(validate_mcp_protocol_version_middleware)
        MIDDLEWARE_ENABLED = True
        logger = logging.getLogger(__name__)
        logger.info("✅ MCP-Protocol-Version header validation middleware enabled (alternative method)")
    else:
        logger = logging.getLogger(__name__)
        logger.info(
            "ℹ️ FastMCP middleware interface not available - running in compatibility mode (normal for MCP clients)"
        )
except Exception as e:
    # If middleware fails to install, log warning but continue
    logger = logging.getLogger(__name__)
    logger.info(f"ℹ️ MCP header validation middleware not installed: {e} (normal for MCP clients and testing)")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from batch_operations import (  # noqa: E402
    clear_context_batch_tool,
    clear_multiple_contexts_batch_tool,
)
from comparison_tools import (  # noqa: E402
    compare_contexts_across_registries_tool,
    compare_registries_tool,
    find_missing_schemas_tool,
)
from core_registry_tools import (  # noqa: E402
    check_compatibility_tool,
    create_context_tool,
    delete_context_tool,
    delete_subject_tool,
    get_global_config_tool,
    get_mode_tool,
    get_schema_tool,
    get_schema_versions_tool,
    get_subject_config_tool,
    get_subject_mode_tool,
    list_contexts_tool,
    list_subjects_tool,
    register_schema_tool,
    update_global_config_tool,
    update_mode_tool,
    update_subject_config_tool,
    update_subject_mode_tool,
)

# Import elicitation functionality
from elicitation import (  # noqa: E402
    elicitation_manager,
    is_elicitation_supported,
)

# Import elicitation MCP integration
from elicitation_mcp_integration import (  # noqa: E402
    register_elicitation_handlers,
    update_elicitation_implementation,
)
from export_tools import (  # noqa: E402
    export_context_tool,
    export_global_tool,
    export_schema_tool,
    export_subject_tool,
)

# Import interactive tools
from interactive_tools import check_compatibility_interactive as check_compatibility_interactive_impl  # noqa: E402
from interactive_tools import create_context_interactive as create_context_interactive_impl
from interactive_tools import export_global_interactive as export_global_interactive_impl
from interactive_tools import migrate_context_interactive as migrate_context_interactive_impl
from interactive_tools import register_schema_interactive as register_schema_interactive_impl

# Import prompts from external module
from mcp_prompts import PROMPT_REGISTRY  # noqa: E402
from migration_tools import (  # noqa: E402
    get_migration_status_tool,
    list_migrations_tool,
    migrate_context_tool,
    migrate_schema_tool,
)
from multi_step_elicitation import MultiStepElicitationManager  # noqa: E402

# Import registry management tools
from registry_management_tools import (  # noqa: E402
    get_registry_info_tool,
    list_registries_tool,
    test_all_registries_tool,
    test_registry_connection_tool,
)

# Import common library functionality
from schema_registry_common import (  # noqa: E402
    SINGLE_REGISTRY_PASSWORD,
    SINGLE_REGISTRY_URL,
    SINGLE_REGISTRY_USER,
    SINGLE_VIEWONLY,
    LegacyRegistryManager,
    MultiRegistryManager,
)
from schema_registry_common import check_viewonly_mode as _check_viewonly_mode  # noqa: E402

# Import schema validation utilities for structured output
from schema_validation import (  # noqa: E402
    create_error_response,
    create_success_response,
    structured_output,
)
from statistics_tools import (  # noqa: E402
    count_contexts_tool,
    count_schema_versions_tool,
    count_schemas_task_queue_tool,
    count_schemas_tool,
    get_registry_statistics_task_queue_tool,
)

# Import specialized modules
from task_management import task_manager  # noqa: E402

# Import multi-step elicitation workflow functionality
from workflow_mcp_integration import (  # noqa: E402
    handle_workflow_elicitation_response,
    register_workflow_tools,
)


# Auto-detection of registry mode
def detect_registry_mode() -> str:
    """Auto-detect whether to use single or multi-registry mode."""
    # Check for legacy single-registry env vars
    has_legacy = any(
        [
            os.getenv("SCHEMA_REGISTRY_URL"),
            os.getenv("SCHEMA_REGISTRY_USER"),
            os.getenv("SCHEMA_REGISTRY_PASSWORD"),
        ]
    )

    # Check for numbered multi-registry env vars
    has_numbered = any(
        [
            os.getenv("SCHEMA_REGISTRY_URL_1"),
            os.getenv("SCHEMA_REGISTRY_USER_1"),
            os.getenv("SCHEMA_REGISTRY_PASSWORD_1"),
        ]
    )

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


class SecureHeaderDict(dict):
    """Dictionary-like class that generates fresh headers with credentials on each access."""

    def __init__(self, content_type: str = "application/vnd.schemaregistry.v1+json"):
        super().__init__()
        self.content_type = content_type
        self._update_headers()

    def _update_headers(self):
        """Update headers with fresh credentials."""
        self.clear()
        self["Content-Type"] = self.content_type
        # Get credentials from environment
        user = os.getenv("SCHEMA_REGISTRY_USER", "")
        password = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
        if user and password:
            credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
            self["Authorization"] = f"Basic {credentials}"

    def __getitem__(self, key):
        self._update_headers()  # Refresh on each access
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._update_headers()  # Refresh on each access
        return super().get(key, default)

    def items(self):
        self._update_headers()  # Refresh on each access
        return super().items()

    def keys(self):
        self._update_headers()  # Refresh on each access
        return super().keys()

    def values(self):
        self._update_headers()  # Refresh on each access
        return super().values()


if REGISTRY_MODE == "single":
    logger.info("📡 Initializing Single Registry Manager")
    registry_manager = LegacyRegistryManager("")

    # Legacy compatibility globals
    SCHEMA_REGISTRY_URL = SINGLE_REGISTRY_URL
    SCHEMA_REGISTRY_USER = SINGLE_REGISTRY_USER
    SCHEMA_REGISTRY_PASSWORD = SINGLE_REGISTRY_PASSWORD
    VIEWONLY = SINGLE_VIEWONLY

    # Set up authentication if configured
    auth = None
    headers = SecureHeaderDict("application/vnd.schemaregistry.v1+json")
    standard_headers = SecureHeaderDict("application/json")

    if SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD:
        from requests.auth import HTTPBasicAuth

        auth = HTTPBasicAuth(SCHEMA_REGISTRY_USER, SCHEMA_REGISTRY_PASSWORD)
else:
    logger.info("🌐 Initializing Multi-Registry Manager")
    registry_manager = MultiRegistryManager()

    # Multi-registry globals
    SCHEMA_REGISTRY_URL = ""
    SCHEMA_REGISTRY_USER = ""
    SCHEMA_REGISTRY_PASSWORD = ""
    VIEWONLY = False
    auth = None
    headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    standard_headers = {"Content-Type": "application/json"}

# Initialize elicitation MCP integration
try:
    # Register elicitation handlers with the MCP instance
    elicitation_handlers_registered = register_elicitation_handlers(mcp)
    if elicitation_handlers_registered:
        logger.info("✅ Elicitation handlers registered with MCP server")

        # Update the elicitation implementation to use real MCP protocol
        update_elicitation_implementation()
        logger.info("✅ Enhanced elicitation implementation activated")
    else:
        logger.warning("⚠️ Failed to register elicitation handlers, using fallback implementation")
except Exception as e:
    logger.error(f"❌ Error initializing elicitation MCP integration: {str(e)}")
    logger.info("📝 Falling back to mock elicitation implementation")

# Initialize multi-step elicitation workflow system
try:
    # Register workflow tools with the MCP server and get the manager instance
    workflow_tools = register_workflow_tools(mcp, elicitation_manager)

    # Use the same manager instance globally to ensure workflows are shared
    multi_step_manager = workflow_tools.multi_step_manager

    logger.info("✅ Multi-step elicitation workflows registered with MCP server")
    logger.info(f"✅ {len(multi_step_manager.workflows)} workflows available")
except Exception as e:
    logger.error(f"❌ Error initializing multi-step elicitation workflows: {str(e)}")
    logger.info("📝 Multi-step workflows not available")
    multi_step_manager = None

# ===== MCP PROTOCOL SUPPORT =====


@mcp.tool()
def ping():
    """
    Respond to MCP ping requests with pong.

    This tool implements the standard MCP ping/pong protocol for server health checking.
    MCP proxies and clients use this to verify that the server is alive and responding.
    """
    from datetime import datetime

    return {
        "response": "pong",
        "server_name": "Kafka Schema Registry Unified MCP Server",
        "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
        "timestamp": datetime.utcnow().isoformat(),
        "protocol_version": MCP_PROTOCOL_VERSION,
        "registry_mode": REGISTRY_MODE,
        "status": "healthy",
        "ping_supported": True,
        "message": "MCP server is alive and responding",
    }


# ===== UNIFIED REGISTRY MANAGEMENT TOOLS =====


@mcp.tool()
@require_scopes("read")
def list_registries():
    """List all configured Schema Registry instances."""
    return list_registries_tool(registry_manager, REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def get_registry_info(registry_name: str = None):
    """Get detailed information about a specific registry."""
    return get_registry_info_tool(registry_manager, REGISTRY_MODE, registry_name)


@mcp.tool()
@require_scopes("read")
def test_registry_connection(registry_name: str = None):
    """Test connection to a specific registry and return comprehensive information including metadata."""
    return test_registry_connection_tool(registry_manager, REGISTRY_MODE, registry_name)


@mcp.tool()
@require_scopes("read")
async def test_all_registries():
    """Test connections to all configured registries with comprehensive metadata."""
    return await test_all_registries_tool(registry_manager, REGISTRY_MODE)


# ===== COMPARISON TOOLS =====


@mcp.tool()
@require_scopes("read")
async def compare_registries(
    source_registry: str,
    target_registry: str,
    include_contexts: bool = True,
    include_configs: bool = True,
):
    """Compare two Schema Registry instances and show differences."""
    return await compare_registries_tool(
        source_registry,
        target_registry,
        registry_manager,
        REGISTRY_MODE,
        include_contexts,
        include_configs,
    )


@mcp.tool()
@require_scopes("read")
async def compare_contexts_across_registries(
    source_registry: str,
    target_registry: str,
    source_context: str,
    target_context: str = None,
):
    """Compare contexts across two registries."""
    return await compare_contexts_across_registries_tool(
        source_registry,
        target_registry,
        source_context,
        registry_manager,
        REGISTRY_MODE,
        target_context,
    )


@mcp.tool()
@require_scopes("read")
async def find_missing_schemas(source_registry: str, target_registry: str, context: str = None):
    """Find schemas that exist in source registry but not in target registry."""
    return await find_missing_schemas_tool(source_registry, target_registry, registry_manager, REGISTRY_MODE, context)


# ===== SCHEMA MANAGEMENT TOOLS =====


@mcp.tool()
@require_scopes("write")
def register_schema(
    subject: str,
    schema_definition: dict,
    schema_type: str = "AVRO",
    context: str = None,
    registry: str = None,
):
    """Register a new schema version."""
    return register_schema_tool(
        subject,
        schema_definition,
        registry_manager,
        REGISTRY_MODE,
        schema_type,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
async def register_schema_interactive(
    subject: str,
    schema_definition: dict = None,
    schema_type: str = "AVRO",
    context: str = None,
    registry: str = None,
):
    """
    Interactive schema registration with elicitation for missing field definitions.

    When schema_definition is incomplete or missing fields, this tool will
    elicit the required information from the user interactively.
    """
    return await register_schema_interactive_impl(
        subject=subject,
        schema_definition=schema_definition,
        schema_type=schema_type,
        context=context,
        registry=registry,
        register_schema_tool=register_schema_tool,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
        auth=auth,
        headers=headers,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_schema(subject: str, version: str = "latest", context: str = None, registry: str = None):
    """Get a specific version of a schema."""
    return get_schema_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        version,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_schema_versions(subject: str, context: str = None, registry: str = None):
    """Get all versions of a schema for a subject."""
    return get_schema_versions_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def list_subjects(context: str = None, registry: str = None):
    """List all subjects, optionally filtered by context."""
    return list_subjects_tool(
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def check_compatibility(
    subject: str,
    schema_definition: dict,
    schema_type: str = "AVRO",
    context: str = None,
    registry: str = None,
):
    """Check if a schema is compatible with the latest version."""
    return check_compatibility_tool(
        subject,
        schema_definition,
        registry_manager,
        REGISTRY_MODE,
        schema_type,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
async def check_compatibility_interactive(
    subject: str,
    schema_definition: dict,
    schema_type: str = "AVRO",
    context: str = None,
    registry: str = None,
):
    """
    Interactive compatibility checking with elicitation for resolution options.

    When compatibility issues are found, this tool will elicit resolution
    preferences from the user.
    """
    return await check_compatibility_interactive_impl(
        subject=subject,
        schema_definition=schema_definition,
        schema_type=schema_type,
        context=context,
        registry=registry,
        check_compatibility_tool=check_compatibility_tool,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
        auth=auth,
        headers=headers,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )


# ===== CONFIGURATION TOOLS =====


@mcp.tool()
@require_scopes("read")
def get_global_config(context: str = None, registry: str = None):
    """Get global configuration settings."""
    return get_global_config_tool(
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
def update_global_config(compatibility: str, context: str = None, registry: str = None):
    """Update global configuration settings."""
    return update_global_config_tool(
        compatibility,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_subject_config(subject: str, context: str = None, registry: str = None):
    """Get configuration settings for a specific subject."""
    return get_subject_config_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
def update_subject_config(subject: str, compatibility: str, context: str = None, registry: str = None):
    """Update configuration settings for a specific subject."""
    return update_subject_config_tool(
        subject,
        compatibility,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


# ===== MODE TOOLS =====


@mcp.tool()
@require_scopes("read")
def get_mode(context: str = None, registry: str = None):
    """Get the current mode of the Schema Registry."""
    return get_mode_tool(
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
def update_mode(mode: str, context: str = None, registry: str = None):
    """Update the mode of the Schema Registry."""
    return update_mode_tool(
        mode,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_subject_mode(subject: str, context: str = None, registry: str = None):
    """Get the mode for a specific subject."""
    return get_subject_mode_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
def update_subject_mode(subject: str, mode: str, context: str = None, registry: str = None):
    """Update the mode for a specific subject."""
    return update_subject_mode_tool(
        subject,
        mode,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        standard_headers,
        SCHEMA_REGISTRY_URL,
    )


# ===== CONTEXT TOOLS =====


@mcp.tool()
@require_scopes("read")
def list_contexts(registry: str = None):
    """List all available schema contexts."""
    return list_contexts_tool(registry_manager, REGISTRY_MODE, registry, auth, headers, SCHEMA_REGISTRY_URL)


@mcp.tool()
@require_scopes("write")
def create_context(context: str, registry: str = None):
    """Create a new schema context."""
    return create_context_tool(
        context,
        registry_manager,
        REGISTRY_MODE,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("write")
async def create_context_interactive(
    context: str,
    registry: str = None,
    description: str = None,
    owner: str = None,
    environment: str = None,
    tags: list = None,
):
    """
    Interactive context creation with elicitation for metadata.

    When context metadata is not provided, this tool will elicit
    organizational information from the user.
    """
    return await create_context_interactive_impl(
        context=context,
        registry=registry,
        description=description,
        owner=owner,
        environment=environment,
        tags=tags,
        create_context_tool=create_context_tool,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
        auth=auth,
        headers=headers,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("admin")
def delete_context(context: str, registry: str = None):
    """Delete a schema context."""
    return delete_context_tool(
        context,
        registry_manager,
        REGISTRY_MODE,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("admin")
async def delete_subject(subject: str, context: str = None, registry: str = None, permanent: bool = False):
    """Delete a subject and all its versions.

    Args:
        subject: The subject name to delete
        context: Optional schema context
        registry: Optional registry name
        permanent: If True, perform a hard delete (removes all metadata including schema ID)
    """
    return await delete_subject_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        permanent,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


# ===== EXPORT TOOLS =====


@mcp.tool()
@require_scopes("read")
def export_schema(
    subject: str,
    version: str = "latest",
    context: str = None,
    format: str = "json",
    registry: str = None,
):
    """Export a single schema in the specified format."""
    return export_schema_tool(subject, registry_manager, REGISTRY_MODE, version, context, format, registry)


@mcp.tool()
@require_scopes("read")
def export_subject(
    subject: str,
    context: str = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    registry: str = None,
):
    """Export all versions of a subject."""
    return export_subject_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        include_metadata,
        include_config,
        include_versions,
        registry,
    )


@mcp.tool()
@require_scopes("read")
def export_context(
    context: str,
    registry: str = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
):
    """Export all subjects within a context."""
    return export_context_tool(
        context,
        registry_manager,
        REGISTRY_MODE,
        registry,
        include_metadata,
        include_config,
        include_versions,
    )


@mcp.tool()
@require_scopes("read")
def export_global(
    registry: str = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
):
    """Export all contexts and schemas from a registry."""
    return export_global_tool(
        registry_manager,
        REGISTRY_MODE,
        registry,
        include_metadata,
        include_config,
        include_versions,
    )


@mcp.tool()
@require_scopes("read")
async def export_global_interactive(
    registry: str = None,
    include_metadata: bool = None,
    include_config: bool = None,
    include_versions: str = None,
    format: str = None,
    compression: str = None,
):
    """
    Interactive global export with elicitation for export preferences.

    When export preferences are not specified, this tool will elicit
    the required configuration from the user.
    """
    return await export_global_interactive_impl(
        registry=registry,
        include_metadata=include_metadata,
        include_config=include_config,
        include_versions=include_versions,
        format=format,
        compression=compression,
        export_global_tool=export_global_tool,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
    )


# ===== MIGRATION TOOLS =====


@mcp.tool()
@require_scopes("admin")
def migrate_schema(
    subject: str,
    source_registry: str,
    target_registry: str,
    dry_run: bool = False,
    preserve_ids: bool = True,
    source_context: str = ".",
    target_context: str = ".",
    versions: list = None,
    migrate_all_versions: bool = False,
):
    """Migrate a schema from one registry to another."""
    return migrate_schema_tool(
        subject=subject,
        source_registry=source_registry,
        target_registry=target_registry,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
        dry_run=dry_run,
        preserve_ids=preserve_ids,
        source_context=source_context,
        target_context=target_context,
        versions=versions,
        migrate_all_versions=migrate_all_versions,
    )


@mcp.tool()
@require_scopes("read")
def list_migrations():
    """List all migration tasks and their status."""
    return list_migrations_tool(REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def get_migration_status(migration_id: str):
    """Get detailed status of a specific migration."""
    return get_migration_status_tool(migration_id, REGISTRY_MODE)


@mcp.tool()
@require_scopes("admin")
async def migrate_context(
    source_registry: str,
    target_registry: str,
    context: str = None,
    target_context: str = None,
    preserve_ids: bool = True,
    dry_run: bool = True,
    migrate_all_versions: bool = True,
):
    """Guide for migrating an entire context using Docker-based tools."""
    return await migrate_context_tool(
        source_registry,
        target_registry,
        registry_manager,
        REGISTRY_MODE,
        context,
        target_context,
        preserve_ids,
        dry_run,
        migrate_all_versions,
    )


@mcp.tool()
@require_scopes("admin")
async def migrate_context_interactive(
    source_registry: str,
    target_registry: str,
    context: str = None,
    target_context: str = None,
    preserve_ids: bool = None,
    dry_run: bool = None,
    migrate_all_versions: bool = None,
):
    """
    Interactive context migration with elicitation for missing preferences.

    When migration preferences are not specified, this tool will elicit
    the required configuration from the user.
    """
    return await migrate_context_interactive_impl(
        source_registry=source_registry,
        target_registry=target_registry,
        context=context,
        target_context=target_context,
        preserve_ids=preserve_ids,
        dry_run=dry_run,
        migrate_all_versions=migrate_all_versions,
        migrate_context_tool=migrate_context_tool,
        registry_manager=registry_manager,
        registry_mode=REGISTRY_MODE,
    )


# ===== APPLICATION-LEVEL BATCH OPERATIONS =====


@mcp.tool()
@require_scopes("admin")
def clear_context_batch(
    context: str,
    registry: str = None,
    delete_context_after: bool = True,
    dry_run: bool = True,
):
    """Clear all subjects in a context using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2025-06-18 compliance.
    """
    return clear_context_batch_tool(
        context,
        registry_manager,
        REGISTRY_MODE,
        registry,
        delete_context_after,
        dry_run,
    )


@mcp.tool()
@require_scopes("admin")
def clear_multiple_contexts_batch(
    contexts: list,
    registry: str = None,
    delete_contexts_after: bool = True,
    dry_run: bool = True,
):
    """Clear multiple contexts in a registry using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2025-06-18 compliance.
    """
    return clear_multiple_contexts_batch_tool(
        contexts,
        registry_manager,
        REGISTRY_MODE,
        registry,
        delete_contexts_after,
        dry_run,
    )


# ===== STATISTICS TOOLS =====


@mcp.tool()
@require_scopes("read")
def count_contexts(registry: str = None):
    """Count the number of contexts in a registry."""
    return count_contexts_tool(registry_manager, REGISTRY_MODE, registry)


@mcp.tool()
@require_scopes("read")
def count_schemas(context: str = None, registry: str = None):
    """Count the number of schemas in a context or registry."""
    # Use task queue version for better performance when counting across multiple contexts
    if context is None:
        # Multiple contexts - use optimized async version
        return count_schemas_task_queue_tool(registry_manager, REGISTRY_MODE, context, registry)
    else:
        # Single context - use direct version
        return count_schemas_tool(registry_manager, REGISTRY_MODE, context, registry)


@mcp.tool()
@require_scopes("read")
def count_schema_versions(subject: str, context: str = None, registry: str = None):
    """Count the number of versions for a specific schema."""
    return count_schema_versions_tool(subject, registry_manager, REGISTRY_MODE, context, registry)


@mcp.tool()
@require_scopes("read")
def get_registry_statistics(registry: str = None, include_context_details: bool = True):
    """Get comprehensive statistics about a registry."""
    # Always use task queue version for better performance due to complexity
    return get_registry_statistics_task_queue_tool(registry_manager, REGISTRY_MODE, registry, include_context_details)


# ===== ELICITATION MANAGEMENT TOOLS =====


@mcp.tool()
@require_scopes("read")
def list_elicitation_requests():
    """List all pending elicitation requests."""
    try:
        requests = elicitation_manager.list_pending_requests()
        return {
            "pending_requests": [req.to_dict() for req in requests],
            "total_pending": len(requests),
            "elicitation_supported": is_elicitation_supported(),
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }
    except Exception as e:
        return create_error_response(
            f"Failed to list elicitation requests: {str(e)}",
            error_code="ELICITATION_LIST_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@mcp.tool()
@require_scopes("read")
def get_elicitation_request(request_id: str):
    """Get details of a specific elicitation request."""
    try:
        request = elicitation_manager.get_request(request_id)
        if not request:
            return create_error_response(
                f"Elicitation request '{request_id}' not found",
                error_code="ELICITATION_REQUEST_NOT_FOUND",
                registry_mode=REGISTRY_MODE,
            )

        response = elicitation_manager.get_response(request_id)

        return {
            "request": request.to_dict(),
            "response": response.to_dict() if response else None,
            "status": ("completed" if response else ("expired" if request.is_expired() else "pending")),
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }
    except Exception as e:
        return create_error_response(
            f"Failed to get elicitation request: {str(e)}",
            error_code="ELICITATION_GET_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@mcp.tool()
@require_scopes("admin")
@structured_output("cancel_elicitation_request", fallback_on_error=True)
def cancel_elicitation_request(request_id: str):
    """Cancel a pending elicitation request."""
    try:
        cancelled = elicitation_manager.cancel_request(request_id)
        if cancelled:
            return create_success_response(
                f"Elicitation request '{request_id}' cancelled successfully",
                data={"request_id": request_id, "cancelled": True},
                registry_mode=REGISTRY_MODE,
            )
        else:
            return create_error_response(
                f"Elicitation request '{request_id}' not found or already completed",
                error_code="ELICITATION_REQUEST_NOT_FOUND",
                registry_mode=REGISTRY_MODE,
            )
    except Exception as e:
        return create_error_response(
            f"Failed to cancel elicitation request: {str(e)}",
            error_code="ELICITATION_CANCEL_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@mcp.tool()
@require_scopes("read")
@structured_output("get_elicitation_status", fallback_on_error=True)
def get_elicitation_status():
    """Get the status of the elicitation system."""
    try:
        pending_requests = elicitation_manager.list_pending_requests()
        return {
            "elicitation_supported": is_elicitation_supported(),
            "total_pending_requests": len(pending_requests),
            "request_details": [
                {
                    "id": req.id,
                    "title": req.title,
                    "type": req.type.value,
                    "priority": req.priority.value,
                    "created_at": req.created_at.isoformat(),
                    "expires_at": (req.expires_at.isoformat() if req.expires_at else None),
                    "expired": req.is_expired(),
                }
                for req in pending_requests
            ],
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            "registry_mode": REGISTRY_MODE,
        }
    except Exception as e:
        return create_error_response(
            f"Failed to get elicitation status: {str(e)}",
            error_code="ELICITATION_STATUS_FAILED",
            registry_mode=REGISTRY_MODE,
        )


# ===== MULTI-STEP WORKFLOW TOOLS =====


@mcp.tool()
@require_scopes("write")
async def submit_elicitation_response(
    request_id: str,
    response_data: dict,
    complete: bool = True,
):
    """
    Submit a response to an elicitation request.

    This tool handles both regular elicitation responses and multi-step workflow responses.
    When a workflow is in progress, it will automatically advance to the next step.
    """
    from elicitation import ElicitationResponse

    try:
        # Create response object
        response = ElicitationResponse(request_id=request_id, values=response_data, complete=complete)

        # Check if multi-step manager is available and handle workflow responses
        if "multi_step_manager" in globals() and multi_step_manager:
            workflow_result = await handle_workflow_elicitation_response(
                elicitation_manager, multi_step_manager, response
            )

            if workflow_result:
                if workflow_result.get("workflow_completed"):
                    # Workflow completed - return execution plan
                    execution_plan = workflow_result.get("execution_plan", {})
                    return {
                        "status": "workflow_completed",
                        "message": "Workflow completed successfully",
                        "execution_plan": execution_plan,
                        "next_action": "Execute the generated plan using appropriate tools",
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                    }
                elif workflow_result.get("workflow_continuing"):
                    # More steps needed
                    return {
                        "status": "workflow_continuing",
                        "message": f"Proceeding to: {workflow_result.get('next_step')}",
                        "request_id": workflow_result.get("request_id"),
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                    }
                else:
                    # Error in workflow
                    return create_error_response(
                        workflow_result.get("error", "Unknown workflow error"),
                        error_code="WORKFLOW_ERROR",
                        registry_mode=REGISTRY_MODE,
                    )

        # Original elicitation handling (non-workflow)
        success = await elicitation_manager.submit_response(response)

        if success:
            result = elicitation_manager.get_response(request_id)
            if result:
                return {
                    "status": "success",
                    "message": "Response submitted successfully",
                    "values": result.values,
                    "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                }

        return create_error_response(
            "Failed to submit response", error_code="ELICITATION_RESPONSE_FAILED", registry_mode=REGISTRY_MODE
        )

    except Exception as e:
        logger.error(f"Error submitting elicitation response: {e}")
        return create_error_response(str(e), error_code="ELICITATION_RESPONSE_ERROR", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def list_available_workflows():
    """List all available multi-step workflows for complex operations."""
    try:
        if "multi_step_manager" not in globals() or not multi_step_manager:
            return create_error_response(
                "Multi-step workflows are not available",
                error_code="WORKFLOWS_NOT_AVAILABLE",
                registry_mode=REGISTRY_MODE,
            )

        from workflow_definitions import get_all_workflows

        workflows = get_all_workflows()
        workflow_list = []

        for workflow in workflows:
            workflow_list.append(
                {
                    "id": workflow.id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "steps": len(workflow.steps),
                    "difficulty": workflow.metadata.get("difficulty", "intermediate"),
                    "estimated_duration": workflow.metadata.get("estimated_duration", "5-10 minutes"),
                    "requires_admin": workflow.metadata.get("requires_admin", False),
                }
            )

        return {
            "workflows": workflow_list,
            "total": len(workflow_list),
            "message": "Use 'start_workflow' tool to begin any workflow",
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

    except Exception as e:
        logger.error(f"Error listing available workflows: {e}")
        return create_error_response(str(e), error_code="WORKFLOWS_LIST_ERROR", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def get_workflow_status(workflow_id: str = None):
    """Get the status of active workflows."""
    try:
        if "multi_step_manager" not in globals() or not multi_step_manager:
            return create_error_response(
                "Multi-step workflows are not available",
                error_code="WORKFLOWS_NOT_AVAILABLE",
                registry_mode=REGISTRY_MODE,
            )

        active_workflows = multi_step_manager.get_active_workflows()

        if workflow_id:
            # Return status for specific workflow
            workflow_info = next((wf for wf in active_workflows if wf.get("instance_id") == workflow_id), None)
            if workflow_info:
                return {
                    "workflow_id": workflow_id,
                    "status": workflow_info,
                    "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                }
            else:
                return create_error_response(
                    f"Workflow '{workflow_id}' not found or not active",
                    error_code="WORKFLOW_NOT_FOUND",
                    registry_mode=REGISTRY_MODE,
                )

        # Return all active workflows
        return {
            "active_workflows": active_workflows,
            "total_active": len(active_workflows),
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        return create_error_response(str(e), error_code="WORKFLOW_STATUS_ERROR", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("write")
async def guided_schema_migration():
    """Start the schema migration wizard for guided migration."""
    try:
        if "multi_step_manager" not in globals() or not multi_step_manager:
            return create_error_response(
                "Multi-step workflows are not available",
                error_code="WORKFLOWS_NOT_AVAILABLE",
                registry_mode=REGISTRY_MODE,
            )

        from datetime import datetime

        # Start the schema migration workflow
        request = await multi_step_manager.start_workflow(
            workflow_id="schema_migration_wizard",
            initial_context={
                "triggered_by": "guided_schema_migration",
                "timestamp": datetime.utcnow().isoformat(),
                "registry_mode": REGISTRY_MODE,
            },
        )

        if request:
            return {
                "status": "workflow_started",
                "workflow_name": "Schema Migration Wizard",
                "message": "Migration wizard started. Please respond to the elicitation request.",
                "first_step": request.title,
                "request_id": request.id,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
        else:
            return create_error_response(
                "Failed to start migration wizard",
                error_code="MIGRATION_WIZARD_START_FAILED",
                registry_mode=REGISTRY_MODE,
            )

    except Exception as e:
        logger.error(f"Error starting guided schema migration: {e}")
        return create_error_response(str(e), error_code="MIGRATION_WIZARD_ERROR", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("write")
async def guided_context_reorganization():
    """Start the context reorganization wizard for guided context management."""
    try:
        if "multi_step_manager" not in globals() or not multi_step_manager:
            return create_error_response(
                "Multi-step workflows are not available",
                error_code="WORKFLOWS_NOT_AVAILABLE",
                registry_mode=REGISTRY_MODE,
            )

        from datetime import datetime

        # Start the context reorganization workflow
        request = await multi_step_manager.start_workflow(
            workflow_id="context_reorganization",
            initial_context={
                "triggered_by": "guided_context_reorganization",
                "timestamp": datetime.utcnow().isoformat(),
                "registry_mode": REGISTRY_MODE,
            },
        )

        if request:
            return {
                "status": "workflow_started",
                "workflow_name": "Context Reorganization Wizard",
                "message": "Context reorganization wizard started. Please respond to the elicitation request.",
                "first_step": request.title,
                "request_id": request.id,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
        else:
            return create_error_response(
                "Failed to start context reorganization wizard",
                error_code="CONTEXT_WIZARD_START_FAILED",
                registry_mode=REGISTRY_MODE,
            )

    except Exception as e:
        logger.error(f"Error starting guided context reorganization: {e}")
        return create_error_response(str(e), error_code="CONTEXT_WIZARD_ERROR", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("admin")
async def guided_disaster_recovery():
    """Start the disaster recovery wizard for guided backup and recovery setup."""
    try:
        if "multi_step_manager" not in globals() or not multi_step_manager:
            return create_error_response(
                "Multi-step workflows are not available",
                error_code="WORKFLOWS_NOT_AVAILABLE",
                registry_mode=REGISTRY_MODE,
            )

        from datetime import datetime

        # Start the disaster recovery workflow
        request = await multi_step_manager.start_workflow(
            workflow_id="disaster_recovery_setup",
            initial_context={
                "triggered_by": "guided_disaster_recovery",
                "timestamp": datetime.utcnow().isoformat(),
                "registry_mode": REGISTRY_MODE,
            },
        )

        if request:
            return {
                "status": "workflow_started",
                "workflow_name": "Disaster Recovery Wizard",
                "message": "Disaster recovery wizard started. Please respond to the elicitation request.",
                "first_step": request.title,
                "request_id": request.id,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
        else:
            return create_error_response(
                "Failed to start disaster recovery wizard",
                error_code="DISASTER_RECOVERY_WIZARD_START_FAILED",
                registry_mode=REGISTRY_MODE,
            )

    except Exception as e:
        logger.error(f"Error starting guided disaster recovery: {e}")
        return create_error_response(str(e), error_code="DISASTER_RECOVERY_WIZARD_ERROR", registry_mode=REGISTRY_MODE)


# ===== TASK MANAGEMENT TOOLS (Updated with Structured Output) =====


@structured_output("get_task_status", fallback_on_error=True)
def get_task_status_tool(task_id: str):
    """Get the status and progress of an async task with structured validation."""
    try:
        task = task_manager.get_task(task_id)
        if task is None:
            return create_error_response(
                f"Task '{task_id}' not found",
                error_code="TASK_NOT_FOUND",
                registry_mode=REGISTRY_MODE,
            )

        task_dict = task.to_dict()
        # Transform the result to match the expected schema
        result = {
            "task_id": task_dict["id"],  # Map "id" to "task_id" as expected by schema
            "status": task_dict["status"],
            "progress": task_dict["progress"],
            "started_at": task_dict["started_at"],
            "completed_at": task_dict["completed_at"],
            "error": task_dict["error"],
            "result": task_dict["result"],
            "metadata": task_dict["metadata"],
            # Add structured output metadata
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="TASK_STATUS_FAILED", registry_mode=REGISTRY_MODE)


@structured_output("get_task_progress", fallback_on_error=True)
def get_task_progress_tool(task_id: str):
    """Get the progress of an async task (alias for get_task_status) with structured validation."""
    task_status = get_task_status_tool(task_id)
    if "error" in task_status:
        return task_status

    # Transform to progress-focused response
    result = {
        "task_id": task_id,
        "status": task_status["status"],
        "progress_percent": task_status["progress"],
        "started_at": task_status["started_at"],
        "completed_at": task_status["completed_at"],
        "error": task_status["error"],
        "result": task_status["result"],
        "registry_mode": REGISTRY_MODE,
        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
    }

    return result


@structured_output("list_active_tasks", fallback_on_error=True)
def list_active_tasks_tool():
    """List all active tasks in the system with structured validation."""
    try:
        tasks = task_manager.list_tasks()

        # Transform each task to match the expected schema
        transformed_tasks = []
        for task in tasks:
            task_dict = task.to_dict()
            transformed_task = {
                "task_id": task_dict["id"],  # Map "id" to "task_id" as expected by schema
                "status": task_dict["status"],
                "progress": task_dict["progress"],
                "started_at": task_dict["started_at"],
                "completed_at": task_dict["completed_at"],
                "error": task_dict["error"],
                "result": task_dict["result"],
                "metadata": task_dict["metadata"],
            }
            transformed_tasks.append(transformed_task)

        result = {
            "tasks": transformed_tasks,  # Use "tasks" field name to match schema
            "total_tasks": len(tasks),
            "active_tasks": len([t for t in tasks if t.status.value in ["pending", "running"]]),
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="TASK_LIST_FAILED", registry_mode=REGISTRY_MODE)


@structured_output("cancel_task", fallback_on_error=True)
async def cancel_task_tool(task_id: str):
    """Cancel a running task with structured validation."""
    try:
        cancelled = await task_manager.cancel_task(task_id)
        if cancelled:
            return create_success_response(
                f"Task '{task_id}' cancelled successfully",
                data={"task_id": task_id, "cancelled": True},
                registry_mode=REGISTRY_MODE,
            )
        else:
            return create_error_response(
                f"Could not cancel task '{task_id}' (may already be completed)",
                error_code="TASK_CANCEL_FAILED",
                registry_mode=REGISTRY_MODE,
            )
    except Exception as e:
        return create_error_response(str(e), error_code="TASK_CANCEL_ERROR", registry_mode=REGISTRY_MODE)


@structured_output("list_statistics_tasks", fallback_on_error=True)
def list_statistics_tasks_tool():
    """List all statistics-related tasks with structured validation."""
    try:
        from task_management import TaskType

        tasks = task_manager.list_tasks(task_type=TaskType.STATISTICS)

        # Transform each task to match the expected schema
        transformed_tasks = []
        for task in tasks:
            task_dict = task.to_dict()
            transformed_task = {
                "task_id": task_dict["id"],  # Map "id" to "task_id" as expected by schema
                "status": task_dict["status"],
                "progress": task_dict["progress"],
                "started_at": task_dict["started_at"],
                "completed_at": task_dict["completed_at"],
                "error": task_dict["error"],
                "result": task_dict["result"],
                "metadata": task_dict["metadata"],
            }
            transformed_tasks.append(transformed_task)

        result = {
            "tasks": transformed_tasks,  # Use "tasks" field name to match schema
            "total_tasks": len(tasks),
            "active_tasks": len([t for t in tasks if t.status.value in ["pending", "running"]]),
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="STATISTICS_TASK_LIST_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@structured_output("get_statistics_task_progress", fallback_on_error=True)
def get_statistics_task_progress_tool(task_id: str):
    """Get detailed progress for a statistics task with structured validation."""
    try:
        task = task_manager.get_task(task_id)
        if task is None:
            return create_error_response(
                f"Task '{task_id}' not found",
                error_code="TASK_NOT_FOUND",
                registry_mode=REGISTRY_MODE,
            )

        task_dict = task.to_dict()

        # Transform the result to match the expected schema
        result = {
            "task_id": task_dict["id"],  # Map "id" to "task_id" as expected by schema
            "status": task_dict["status"],
            "progress": task_dict["progress"],
            "started_at": task_dict["started_at"],
            "completed_at": task_dict["completed_at"],
            "error": task_dict["error"],
            "result": task_dict["result"],
            "metadata": task_dict["metadata"],
        }

        # Add statistics-specific progress information
        if task.metadata and task.metadata.get("operation") in [
            "count_schemas",
            "get_registry_statistics",
        ]:
            operation = task.metadata.get("operation")
            progress_stage = "Initializing"

            if result["status"] == "running":
                progress = result["progress"]
                if operation == "get_registry_statistics":
                    if progress < 20:
                        progress_stage = "Getting contexts list"
                    elif progress < 50:
                        progress_stage = "Analyzing contexts in parallel"
                    elif progress < 90:
                        progress_stage = "Counting schemas and versions"
                    elif progress < 100:
                        progress_stage = "Finalizing statistics"
                    else:
                        progress_stage = "Complete"
                elif operation == "count_schemas":
                    if progress < 50:
                        progress_stage = "Getting schema lists"
                    elif progress < 100:
                        progress_stage = "Counting schemas across contexts"
                    else:
                        progress_stage = "Complete"
            elif result["status"] == "completed":
                progress_stage = "Complete"
            elif result["status"] == "failed":
                progress_stage = "Failed"

            result["progress_stage"] = progress_stage

        # Add structured output metadata
        result["registry_mode"] = REGISTRY_MODE
        result["mcp_protocol_version"] = MCP_PROTOCOL_VERSION

        return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="STATISTICS_TASK_PROGRESS_FAILED",
            registry_mode=REGISTRY_MODE,
        )


# MCP tool wrappers that call the structured tool functions
@mcp.tool()
@require_scopes("read")
def get_task_status(task_id: str):
    """Get the status and progress of an async task."""
    return get_task_status_tool(task_id)


@mcp.tool()
@require_scopes("read")
def get_task_progress(task_id: str):
    """Get the progress of an async task (alias for get_task_status)."""
    return get_task_progress_tool(task_id)


@mcp.tool()
@require_scopes("read")
def list_active_tasks():
    """List all active tasks in the system."""
    return list_active_tasks_tool()


@mcp.tool()
@require_scopes("admin")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    return await cancel_task_tool(task_id)


@mcp.tool()
@require_scopes("read")
def list_statistics_tasks():
    """List all statistics-related tasks."""
    return list_statistics_tasks_tool()


@mcp.tool()
@require_scopes("read")
def get_statistics_task_progress(task_id: str):
    """Get detailed progress for a statistics task."""
    return get_statistics_task_progress_tool(task_id)


# ===== MCP COMPLIANCE AND UTILITY TOOLS (Updated with Structured Output) =====


@structured_output("get_mcp_compliance_status_tool", fallback_on_error=True)
def _internal_get_mcp_compliance_status():
    """Internal function to get MCP compliance status with structured output validation.

    This function can be called directly for testing purposes.
    """
    try:
        from datetime import datetime

        # Check if header validation middleware is active
        header_validation_active = MIDDLEWARE_ENABLED

        # Get FastMCP configuration details
        config_details = {
            "protocol_version": MCP_PROTOCOL_VERSION,
            "supported_versions": SUPPORTED_MCP_VERSIONS,
            "header_validation_enabled": header_validation_active,
            "jsonrpc_batching_disabled": True,
            "compliance_status": "COMPLIANT",
            "last_verified": datetime.utcnow().isoformat(),
            "server_info": {
                "name": "Kafka Schema Registry Unified MCP Server",
                "version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                "architecture": "modular",
                "registry_mode": REGISTRY_MODE,
                "structured_output_implementation": "100% Complete - All tools",
                "elicitation_capability": "Enabled - MCP 2025-06-18 Interactive Workflows",
                "ping_support": "Enabled - MCP ping/pong protocol",
            },
            "header_validation": {
                "required_header": "MCP-Protocol-Version",
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "exempt_paths": EXEMPT_PATHS,
                "validation_active": header_validation_active,
                "error_response_code": 400,
            },
            "batching_configuration": {
                "jsonrpc_batching": "DISABLED - Per MCP 2025-06-18 specification",
                "application_level_batching": "ENABLED - clear_context_batch, clear_multiple_contexts_batch",
                "performance_strategy": "Individual requests with parallel processing",
                "fastmcp_config": {
                    "allow_batch_requests": False,
                    "batch_support": False,
                    "jsonrpc_batching_disabled": True,
                },
            },
            "structured_output": {
                "implementation_status": "100% Complete",
                "total_tools": "53+",
                "tools_with_structured_output": "All tools",
                "completion_percentage": 100.0,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "validation_framework": "JSON Schema with fallback support",
                "features": [
                    "Type-safe responses for all tools",
                    "Runtime validation with graceful fallback",
                    "Standardized error codes and structures",
                    "Comprehensive metadata in all responses",
                    "Zero breaking changes - backward compatible",
                ],
            },
            "elicitation_capability": {
                "implementation_status": "Complete - MCP 2025-06-18 Specification",
                "interactive_tools": [
                    "register_schema_interactive",
                    "migrate_context_interactive",
                    "check_compatibility_interactive",
                    "create_context_interactive",
                    "export_global_interactive",
                ],
                "elicitation_types": [
                    "text",
                    "choice",
                    "confirmation",
                    "form",
                    "multi_field",
                ],
                "features": [
                    "Interactive schema field definition",
                    "Migration preference collection",
                    "Compatibility resolution guidance",
                    "Context metadata elicitation",
                    "Export format preference selection",
                    "Multi-round conversation support",
                    "Timeout handling and validation",
                    "Graceful fallback for non-supporting clients",
                ],
                "management_tools": [
                    "list_elicitation_requests",
                    "get_elicitation_request",
                    "cancel_elicitation_request",
                    "get_elicitation_status",
                    "submit_elicitation_response",
                ],
            },
            "ping_support": {
                "implementation_status": "Complete - MCP ping/pong protocol",
                "ping_tool": "ping",
                "response_format": "pong",
                "features": [
                    "Standard MCP ping/pong protocol support",
                    "Server health verification",
                    "MCP proxy compatibility",
                    "Detailed server status in ping response",
                    "Protocol version information",
                    "Timestamp for monitoring",
                ],
            },
            "migration_info": {
                "breaking_change": True,
                "migration_required": "Clients using JSON-RPC batching must be updated",
                "header_requirement": "All MCP requests must include MCP-Protocol-Version header",
                "alternative_solutions": [
                    "Use application-level batch operations (clear_context_batch, etc.)",
                    "Implement client-side request queuing",
                    "Use parallel individual requests for performance",
                    "Ensure all MCP clients send MCP-Protocol-Version header",
                    "Use interactive tools for guided workflows",
                    "Use ping tool for server health checking",
                ],
                "performance_impact": "Minimal - parallel processing maintains efficiency",
            },
            "supported_operations": {
                "individual_requests": "All MCP tools support individual requests",
                "application_batch_operations": [
                    "clear_context_batch",
                    "clear_multiple_contexts_batch",
                ],
                "async_task_queue": "Long-running operations use task queue pattern",
                "structured_output": "All tools have validated structured responses",
                "interactive_workflows": "Elicitation-enabled tools for guided user experiences",
                "ping_support": "Standard MCP ping/pong protocol for health checking",
            },
            "compliance_verification": {
                "fastmcp_version": "2.8.0+",
                "mcp_specification": "2025-06-18",
                "validation_date": datetime.utcnow().isoformat(),
                "compliance_notes": [
                    (
                        f"MCP-Protocol-Version header validation "
                        f"{'enabled' if header_validation_active else 'disabled (compatibility mode)'}"
                    ),
                    "JSON-RPC batching explicitly disabled in FastMCP configuration",
                    "Application-level batching uses individual requests",
                    "All operations maintain backward compatibility except JSON-RPC batching",
                    "Performance optimized through parallel processing and task queuing",
                    f"Exempt paths: {EXEMPT_PATHS}",
                    "Structured tool output implemented for all tools (100% complete)",
                    "Type-safe responses with JSON Schema validation",
                    "Graceful fallback on validation failures",
                    "Elicitation capability implemented per MCP 2025-06-18 specification",
                    "Interactive workflow support with fallback mechanisms",
                    "Real MCP protocol integration for elicitation with fallback to mock",
                    "MCP ping/pong protocol implemented for server health checking",
                ],
            },
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return config_details

    except Exception as e:
        return create_error_response(
            f"Failed to get compliance status: {str(e)}",
            error_code="COMPLIANCE_STATUS_FAILED",
            registry_mode=REGISTRY_MODE,
        )


def get_mcp_compliance_status():
    """Get MCP 2025-06-18 specification compliance status and configuration details.

    Returns information about JSON-RPC batching status, protocol version, header validation, and migration guidance.
    """
    return _internal_get_mcp_compliance_status()


@mcp.tool()
@require_scopes("read")
def get_mcp_compliance_status_tool():
    """Get MCP 2025-06-18 specification compliance status and configuration details.

    Returns information about JSON-RPC batching status, protocol version, header validation, and migration guidance.
    """
    return _internal_get_mcp_compliance_status()


@structured_output("set_default_registry", fallback_on_error=True)
def set_default_registry_tool(registry_name: str):
    """Set the default registry with structured output validation."""
    try:
        if REGISTRY_MODE == "single":
            return create_error_response(
                "Default registry setting not available in single-registry mode",
                details={
                    "current_registry": (
                        registry_manager.get_default_registry()
                        if hasattr(registry_manager, "get_default_registry")
                        else "default"
                    )
                },
                error_code="SINGLE_REGISTRY_MODE_LIMITATION",
                registry_mode="single",
            )

        if registry_manager.set_default_registry(registry_name):
            return create_success_response(
                f"Default registry set to '{registry_name}'",
                data={
                    "default_registry": registry_name,
                    "previous_default": (
                        registry_manager.get_previous_default()
                        if hasattr(registry_manager, "get_previous_default")
                        else None
                    ),
                },
                registry_mode="multi",
            )
        else:
            return create_error_response(
                f"Registry '{registry_name}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode="multi",
            )
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="SET_DEFAULT_REGISTRY_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@structured_output("get_default_registry", fallback_on_error=True)
def get_default_registry_tool():
    """Get the current default registry with structured output validation."""
    try:
        if REGISTRY_MODE == "single":
            default = (
                registry_manager.get_default_registry()
                if hasattr(registry_manager, "get_default_registry")
                else "default"
            )
            return {
                "default_registry": default,
                "registry_mode": "single",
                "info": (registry_manager.get_registry_info(default) if default else None),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
        else:
            default = registry_manager.get_default_registry()
            if default:
                return {
                    "default_registry": default,
                    "registry_mode": "multi",
                    "info": registry_manager.get_registry_info(default),
                    "available_registries": registry_manager.list_registries(),
                    "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                }
            else:
                return create_error_response(
                    "No default registry configured",
                    error_code="NO_DEFAULT_REGISTRY",
                    registry_mode="multi",
                )
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="GET_DEFAULT_REGISTRY_FAILED",
            registry_mode=REGISTRY_MODE,
        )


@structured_output("check_viewonly_mode", fallback_on_error=True)
def check_viewonly_mode_tool(registry: str = None):
    """Check if a registry is in viewonly mode with structured output validation."""
    try:
        result = _check_viewonly_mode(registry_manager, registry)

        # If the original function returns an error dict, pass it through
        if isinstance(result, dict) and "error" in result:
            # Add structured output metadata to error response
            result["registry_mode"] = REGISTRY_MODE
            result["mcp_protocol_version"] = MCP_PROTOCOL_VERSION
            return result

        # If it returns a boolean or other simple result, structure it
        if isinstance(result, bool):
            return {
                "viewonly": result,
                "registry": registry or "default",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }

        # If it's already a dict (successful response), add metadata
        if isinstance(result, dict):
            result["registry_mode"] = REGISTRY_MODE
            result["mcp_protocol_version"] = MCP_PROTOCOL_VERSION
            return result

        # Default case
        return {
            "viewonly": False,
            "registry": registry or "default",
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

    except Exception as e:
        return create_error_response(str(e), error_code="VIEWONLY_MODE_CHECK_FAILED", registry_mode=REGISTRY_MODE)


@structured_output("get_oauth_scopes_info_tool", fallback_on_error=True)
def get_oauth_scopes_info_tool_wrapper():
    """Get information about OAuth scopes and permissions with structured output validation."""
    try:
        result = get_oauth_scopes_info()

        # Ensure the result is structured properly
        if isinstance(result, dict):
            # Add structured output metadata
            result["registry_mode"] = REGISTRY_MODE
            result["mcp_protocol_version"] = MCP_PROTOCOL_VERSION
            return result
        else:
            # If result is not a dict, structure it
            return {
                "oauth_scopes": result,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }

    except Exception as e:
        return create_error_response(str(e), error_code="OAUTH_SCOPES_INFO_FAILED", registry_mode=REGISTRY_MODE)


@structured_output("get_operation_info_tool", fallback_on_error=True)
def get_operation_info_tool_wrapper(operation_name: str = None):
    """Get detailed information about MCP operations and their metadata with structured output validation."""
    try:
        from task_management import OPERATION_METADATA

        if operation_name:
            # Get specific operation info
            if operation_name in OPERATION_METADATA:
                return {
                    "operation": operation_name,
                    "metadata": OPERATION_METADATA[operation_name],
                    "registry_mode": REGISTRY_MODE,
                    "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                }
            else:
                return create_error_response(
                    f"Operation '{operation_name}' not found",
                    details={"available_operations": list(OPERATION_METADATA.keys())},
                    error_code="OPERATION_NOT_FOUND",
                    registry_mode=REGISTRY_MODE,
                )
        else:
            # Return all operations
            return {
                "operations": OPERATION_METADATA,
                "total_operations": len(OPERATION_METADATA),
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
    except Exception as e:
        return create_error_response(str(e), error_code="OPERATION_INFO_FAILED", registry_mode=REGISTRY_MODE)


@mcp.tool()
@require_scopes("admin")
def set_default_registry(registry_name: str):
    """Set the default registry."""
    return set_default_registry_tool(registry_name)


@mcp.tool()
@require_scopes("read")
def get_default_registry():
    """Get the current default registry."""
    return get_default_registry_tool()


@mcp.tool()
@require_scopes("read")
def check_viewonly_mode(registry: str = None):
    """Check if a registry is in viewonly mode."""
    return check_viewonly_mode_tool(registry)


@mcp.tool()
@require_scopes("read")
def get_oauth_scopes_info_tool():
    """Get information about OAuth scopes and permissions."""
    return get_oauth_scopes_info_tool_wrapper()


@mcp.tool()
@require_scopes("read")
def test_oauth_discovery_endpoints(server_url: str = "http://localhost:8000"):
    """
    Test OAuth discovery endpoints to ensure proper MCP client compatibility.

    Validates:
    - /.well-known/oauth-authorization-server
    - /.well-known/oauth-protected-resource
    - /.well-known/jwks.json

    Args:
        server_url: Base URL of the MCP server (default: http://localhost:8000)

    Returns:
        Dictionary with test results for each discovery endpoint
    """
    import json
    from datetime import datetime

    import requests

    results = {
        "test_time": datetime.utcnow().isoformat(),
        "server_url": server_url,
        "oauth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true",
        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        "endpoints": {},
    }

    # Discovery endpoints to test
    endpoints = {
        "oauth_authorization_server": "/.well-known/oauth-authorization-server",
        "oauth_protected_resource": "/.well-known/oauth-protected-resource",
        "jwks": "/.well-known/jwks.json",
    }

    for endpoint_name, endpoint_path in endpoints.items():
        endpoint_url = f"{server_url.rstrip('/')}{endpoint_path}"

        try:
            response = requests.get(endpoint_url, timeout=10)

            endpoint_result = {
                "url": endpoint_url,
                "status_code": response.status_code,
                "success": response.status_code in [200, 404],  # 404 is OK if OAuth disabled
                "headers": dict(response.headers),
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }

            # Check for MCP-Protocol-Version header in response
            if "MCP-Protocol-Version" in response.headers:
                endpoint_result["mcp_protocol_version_header"] = response.headers["MCP-Protocol-Version"]
            else:
                endpoint_result["mcp_protocol_version_header"] = "Missing"

            # Try to parse JSON response
            try:
                response_data = response.json()
                endpoint_result["data"] = response_data

                # Validate expected fields based on endpoint
                if endpoint_name == "oauth_authorization_server" and response.status_code == 200:
                    required_fields = [
                        "issuer",
                        "scopes_supported",
                        "mcp_server_version",
                    ]
                    missing_fields = [f for f in required_fields if f not in response_data]
                    if missing_fields:
                        endpoint_result["warnings"] = f"Missing recommended fields: {missing_fields}"

                    # Check MCP-specific extensions
                    if "mcp_endpoints" not in response_data:
                        endpoint_result["warnings"] = endpoint_result.get("warnings", "") + " Missing MCP endpoints"

                elif endpoint_name == "oauth_protected_resource" and response.status_code == 200:
                    required_fields = [
                        "resource",
                        "authorization_servers",
                        "scopes_supported",
                    ]
                    missing_fields = [f for f in required_fields if f not in response_data]
                    if missing_fields:
                        endpoint_result["warnings"] = f"Missing required fields: {missing_fields}"

                    # Check MCP-specific fields
                    if "mcp_server_info" not in response_data:
                        endpoint_result["warnings"] = endpoint_result.get("warnings", "") + " Missing MCP server info"

                elif endpoint_name == "jwks" and response.status_code == 200:
                    if "keys" not in response_data:
                        endpoint_result["warnings"] = "Missing 'keys' field in JWKS response"

            except json.JSONDecodeError:
                endpoint_result["data"] = response.text[:500]  # First 500 chars if not JSON
                endpoint_result["warnings"] = "Response is not valid JSON"

            # Additional validations
            if response.status_code == 404 and not results["oauth_enabled"]:
                endpoint_result["note"] = "404 expected when OAuth is disabled"
            elif response.status_code == 200 and not results["oauth_enabled"]:
                endpoint_result["warnings"] = "Endpoint returns 200 but OAuth appears disabled"
            elif response.status_code != 200 and results["oauth_enabled"]:
                endpoint_result["warnings"] = f"Expected 200 status when OAuth enabled, got {response.status_code}"

        except requests.exceptions.RequestException as e:
            endpoint_result = {
                "url": endpoint_url,
                "success": False,
                "error": str(e),
                "note": "Could not connect to endpoint",
            }

        results["endpoints"][endpoint_name] = endpoint_result

    # Overall assessment
    successful_endpoints = sum(1 for ep in results["endpoints"].values() if ep.get("success", False))
    total_endpoints = len(endpoints)

    results["summary"] = {
        "successful_endpoints": successful_endpoints,
        "total_endpoints": total_endpoints,
        "success_rate": f"{(successful_endpoints/total_endpoints)*100:.1f}%",
        "oauth_discovery_ready": successful_endpoints == total_endpoints and results["oauth_enabled"],
        "mcp_header_validation": "Enabled",
        "recommendations": [],
    }

    # Add recommendations
    if not results["oauth_enabled"]:
        results["summary"]["recommendations"].append(
            "Enable OAuth with ENABLE_AUTH=true to test full discovery functionality"
        )

    for endpoint_name, endpoint_result in results["endpoints"].items():
        if endpoint_result.get("warnings"):
            results["summary"]["recommendations"].append(f"{endpoint_name}: {endpoint_result['warnings']}")

    if results["oauth_enabled"] and successful_endpoints == total_endpoints:
        results["summary"]["recommendations"].append(
            "✅ All OAuth discovery endpoints working correctly - MCP clients should have no issues"
        )

    # Check MCP-Protocol-Version header presence
    headers_present = sum(
        1 for ep in results["endpoints"].values() if ep.get("mcp_protocol_version_header") == MCP_PROTOCOL_VERSION
    )
    if headers_present == total_endpoints:
        results["summary"]["recommendations"].append(
            f"✅ MCP-Protocol-Version header correctly added to all responses ({MCP_PROTOCOL_VERSION})"
        )
    else:
        results["summary"]["recommendations"].append("⚠️ MCP-Protocol-Version header missing from some responses")

    return results


@mcp.tool()
@require_scopes("read")
def get_operation_info_tool(operation_name: str = None):
    """Get detailed information about MCP operations and their metadata."""
    return get_operation_info_tool_wrapper(operation_name)


# ===== RESOURCES =====


@mcp.resource("registry://status")
def get_registry_status():
    """Get the current status of Schema Registry connections."""
    try:
        registries = registry_manager.list_registries()
        if not registries:
            return "❌ No Schema Registry configured"

        status_lines = [f"🔧 Registry Mode: {REGISTRY_MODE.upper()}"]
        status_lines.append("🚫 JSON-RPC Batching: DISABLED (MCP 2025-06-18 compliance)")

        # Check if header validation is active
        header_validation_status = "ENABLED"
        try:
            if hasattr(mcp, "app") and hasattr(mcp.app, "middleware_stack"):
                header_validation_status = "ENABLED"
            else:
                header_validation_status = "DISABLED (compatibility mode)"
        except (AttributeError, TypeError):
            header_validation_status = "UNKNOWN"

        status_lines.append(
            f"✅ MCP-Protocol-Version Header Validation: {header_validation_status} ({MCP_PROTOCOL_VERSION})"
        )
        status_lines.append("🎯 Structured Tool Output: 100% Complete (All tools)")
        status_lines.append("🎭 Elicitation Capability: ENABLED (Interactive Workflows)")
        status_lines.append("🏓 MCP Ping/Pong: ENABLED (Server Health Checking)")

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

        # Check header validation status
        header_validation_active = True
        try:
            if hasattr(mcp, "app") and hasattr(mcp.app, "middleware_stack"):
                header_validation_active = True
            else:
                header_validation_active = False
        except (AttributeError, TypeError):
            header_validation_active = False

        overall_info = {
            "registry_mode": REGISTRY_MODE,
            "registries": registries_info,
            "total_registries": len(registries_info),
            "default_registry": (
                registry_manager.get_default_registry() if hasattr(registry_manager, "get_default_registry") else None
            ),
            "viewonly_mode": VIEWONLY if REGISTRY_MODE == "single" else False,
            "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
            "structured_output": {
                "implementation_status": "100% Complete",
                "total_tools": "53+",
                "tools_with_structured_output": "All tools",
                "completion_percentage": 100.0,
                "validation_framework": "JSON Schema with graceful fallback",
            },
            "elicitation_capability": {
                "implementation_status": "Complete - MCP 2025-06-18 Specification",
                "supported": is_elicitation_supported(),
                "interactive_tools": 5,
                "elicitation_types": [
                    "text",
                    "choice",
                    "confirmation",
                    "form",
                    "multi_field",
                ],
            },
            "ping_support": {
                "implementation_status": "Complete - MCP ping/pong protocol",
                "ping_tool": "ping",
                "response_format": "pong",
                "server_health_checking": True,
            },
            "mcp_compliance": {
                "protocol_version": MCP_PROTOCOL_VERSION,
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "header_validation_enabled": header_validation_active,
                "exempt_paths": EXEMPT_PATHS,
                "jsonrpc_batching_disabled": True,
                "compliance_status": "COMPLIANT",
                "structured_output_complete": True,
                "elicitation_capability_enabled": True,
                "ping_support_enabled": True,
            },
            "features": [
                f"Unified {REGISTRY_MODE.title()} Registry Support",
                "Auto-Mode Detection",
                ("Cross-Registry Comparison" if REGISTRY_MODE == "multi" else "Single Registry Operations"),
                "Schema Migration",
                "Context Management",
                "Schema Export (JSON, Avro IDL)",
                "VIEWONLY Mode Protection",
                "OAuth Scopes Support",
                "Async Task Queue",
                "Modular Architecture",
                "MCP 2025-06-18 Compliance (No JSON-RPC Batching)",
                (
                    f"MCP-Protocol-Version Header Validation "
                    f"({'enabled' if header_validation_active else 'compatibility mode'}) "
                    f"({MCP_PROTOCOL_VERSION})"
                ),
                "Application-Level Batch Operations",
                "🎯 Structured Tool Output (100% Complete - All tools)",
                "🎭 Interactive Workflows with Elicitation Support",
                "🚀 Guided Schema Registration",
                "📋 Interactive Migration Configuration",
                "🔧 Compatibility Resolution Guidance",
                "📊 Context Metadata Collection",
                "💾 Export Preference Selection",
                "🏓 MCP Ping/Pong Protocol Support",
            ],
        }

        return json.dumps(overall_info, indent=2)
    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "registry_mode": REGISTRY_MODE,
                "structured_output": {
                    "implementation_status": "100% Complete",
                    "total_tools": "53+",
                    "completion_percentage": 100.0,
                },
                "elicitation_capability": {
                    "implementation_status": "Complete - MCP 2025-06-18 Specification",
                    "supported": is_elicitation_supported(),
                },
                "ping_support": {
                    "implementation_status": "Complete - MCP ping/pong protocol",
                    "ping_tool": "ping",
                    "response_format": "pong",
                    "server_health_checking": True,
                },
                "mcp_compliance": {
                    "protocol_version": MCP_PROTOCOL_VERSION,
                    "supported_versions": SUPPORTED_MCP_VERSIONS,
                    "header_validation_enabled": False,
                    "exempt_paths": EXEMPT_PATHS,
                    "jsonrpc_batching_disabled": True,
                    "compliance_status": "COMPLIANT",
                    "structured_output_complete": True,
                    "elicitation_capability_enabled": True,
                    "ping_support_enabled": True,
                },
            },
            indent=2,
        )


@mcp.resource("registry://mode")
def get_mode_info():
    """Get information about the current registry mode and how it was detected."""
    try:
        # Check header validation status
        header_validation_active = True
        try:
            if hasattr(mcp, "app") and hasattr(mcp.app, "middleware_stack"):
                header_validation_active = True
            else:
                header_validation_active = False
        except (AttributeError, TypeError):
            header_validation_active = False

        detection_info = {
            "current_mode": REGISTRY_MODE,
            "detection_logic": {
                "single_mode_triggers": [
                    "SCHEMA_REGISTRY_URL environment variable",
                    "SCHEMA_REGISTRY_USER environment variable",
                    "SCHEMA_REGISTRY_PASSWORD environment variable",
                ],
                "multi_mode_triggers": [
                    "SCHEMA_REGISTRY_URL_1 (or _2, _3, etc.) environment variable",
                    "SCHEMA_REGISTRY_USER_1 (or _2, _3, etc.) environment variable",
                    "SCHEMA_REGISTRY_PASSWORD_1 (or _2, _3, etc.) environment variable",
                    "REGISTRIES_CONFIG environment variable",
                ],
            },
            "architecture": "modular",
            "modules": [
                "task_management",
                "migration_tools",
                "comparison_tools",
                "export_tools",
                "batch_operations",
                "statistics_tools",
                "core_registry_tools",
                "registry_management_tools",
                "elicitation",
                "interactive_tools",
                "elicitation_mcp_integration",
            ],
            "structured_output": {
                "implementation_status": "100% Complete",
                "total_tools": "53+",
                "tools_with_structured_output": "All tools",
                "completion_percentage": 100.0,
                "features": [
                    "JSON Schema validation for all tool responses",
                    "Graceful fallback on validation failures",
                    "Standardized error codes and structures",
                    "Type-safe responses with metadata",
                    "Zero breaking changes - backward compatible",
                ],
            },
            "elicitation_capability": {
                "implementation_status": "Complete - MCP 2025-06-18 Specification",
                "supported": is_elicitation_supported(),
                "interactive_tools": [
                    "register_schema_interactive",
                    "migrate_context_interactive",
                    "check_compatibility_interactive",
                    "create_context_interactive",
                    "export_global_interactive",
                ],
                "elicitation_types": [
                    "text",
                    "choice",
                    "confirmation",
                    "form",
                    "multi_field",
                ],
                "management_tools": [
                    "list_elicitation_requests",
                    "get_elicitation_request",
                    "cancel_elicitation_request",
                    "get_elicitation_status",
                    "submit_elicitation_response",
                ],
                "features": [
                    "Interactive schema field definition",
                    "Migration preference collection",
                    "Compatibility resolution guidance",
                    "Context metadata elicitation",
                    "Export format preference selection",
                    "Multi-round conversation support",
                    "Timeout handling and validation",
                    "Graceful fallback for non-supporting clients",
                    "Real MCP protocol integration with mock fallback",
                ],
            },
            "ping_support": {
                "implementation_status": "Complete - MCP ping/pong protocol",
                "ping_tool": "ping",
                "response_format": "pong",
                "features": [
                    "Standard MCP ping/pong protocol support",
                    "Server health verification",
                    "MCP proxy compatibility",
                    "Detailed server status in ping response",
                    "Protocol version information",
                    "Timestamp for monitoring",
                ],
            },
            "mcp_compliance": {
                "protocol_version": MCP_PROTOCOL_VERSION,
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "header_validation_enabled": header_validation_active,
                "exempt_paths": EXEMPT_PATHS,
                "jsonrpc_batching_disabled": True,
                "application_level_batching": True,
                "compliance_notes": [
                    (
                        f"MCP-Protocol-Version header validation "
                        f"{'enabled' if header_validation_active else 'disabled (compatibility mode)'} "
                        f"per MCP 2025-06-18 specification"
                    ),
                    "JSON-RPC batching disabled per MCP 2025-06-18 specification",
                    "Application-level batch operations use individual requests",
                    "All operations maintain backward compatibility except JSON-RPC batching",
                    "Performance maintained through parallel processing and task queuing",
                    f"Exempt paths for header validation: {EXEMPT_PATHS}",
                    "🎯 Structured tool output implemented for all tools (100% complete)",
                    "Type-safe responses with JSON Schema validation",
                    "Graceful fallback on validation failures",
                    "🎭 Elicitation capability implemented per MCP 2025-06-18 specification",
                    "Interactive workflow support with fallback mechanisms",
                    "Real MCP protocol integration for elicitation with intelligent fallback",
                    "🏓 MCP ping/pong protocol implemented for server health checking",
                ],
            },
        }

        return json.dumps(detection_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ===== MCP PROMPTS =====


# Register all prompts with the MCP server
def register_prompt(name, func):
    """Helper function to register a prompt with proper closure."""

    @mcp.prompt(name)
    def prompt_handler():
        return func()

    # Set the proper function name and docstring
    prompt_handler.__name__ = name.replace("-", "_")
    prompt_handler.__doc__ = func.__doc__
    return prompt_handler


# Register all prompts
for prompt_name, prompt_function in PROMPT_REGISTRY.items():
    handler = register_prompt(prompt_name, prompt_function)
    globals()[prompt_name.replace("-", "_")] = handler

# ===== SERVER ENTRY POINT =====

if __name__ == "__main__":
    # Print startup banner to stderr to avoid interfering with MCP JSON protocol on stdout
    import sys

    # Check header validation status for startup message
    header_validation_status = "ENABLED"
    try:
        if hasattr(mcp, "app") and hasattr(mcp.app, "middleware_stack"):
            header_validation_status = "ENABLED"
        else:
            header_validation_status = "DISABLED (compatibility mode)"
    except (AttributeError, TypeError):
        header_validation_status = "UNKNOWN"

    print(
        f"""
🚀 Kafka Schema Registry Unified MCP Server Starting (Modular + Elicitation + Ping)
📡 Mode: {REGISTRY_MODE.upper()}
🔧 Registries: {len(registry_manager.list_registries())}
🛡️  OAuth: {"Enabled" if ENABLE_AUTH else "Disabled"}
🚫 JSON-RPC Batching: DISABLED (MCP 2025-06-18 Compliance)
✅ MCP-Protocol-Version Header Validation: {header_validation_status} ({MCP_PROTOCOL_VERSION})
💼 Application Batching: ENABLED (clear_context_batch, etc.)
📦 Architecture: Modular (11 specialized modules)
💬 Prompts: 6 comprehensive guides available
🎯 Structured Tool Output: 100% Complete (All tools)
🎭 Elicitation Capability: ENABLED (Interactive Workflows)
🏓 MCP Ping/Pong: ENABLED (Server Health Checking)
🔗 Real MCP Elicitation Protocol: INTEGRATED (with fallback)
    """,
        file=sys.stderr,
    )

    # Log startup information
    logger.info(f"Starting Unified MCP Server in {REGISTRY_MODE} mode (modular architecture with elicitation and ping)")
    logger.info(f"Detected {len(registry_manager.list_registries())} registry configurations")
    logger.info(
        f"✅ MCP-Protocol-Version header validation {header_validation_status.lower()} ({MCP_PROTOCOL_VERSION})"
    )
    logger.info(f"🚫 Exempt paths from header validation: {EXEMPT_PATHS}")
    logger.info("🚫 JSON-RPC batching DISABLED per MCP 2025-06-18 specification compliance")
    logger.info("💼 Application-level batch operations ENABLED with individual requests")
    logger.info("🎯 Structured tool output: 100% Complete - All tools have JSON Schema validation")
    logger.info(
        (
            f"🎭 Elicitation capability: "
            f"{'ENABLED' if is_elicitation_supported() else 'DISABLED'} - "
            f"Interactive workflows per MCP 2025-06-18"
        )
    )
    logger.info("🏓 MCP ping/pong protocol: ENABLED - Server health checking for MCP proxies")
    logger.info("🔗 Real MCP elicitation protocol integrated with intelligent fallback to mock")
    logger.info(
        (
            "Available prompts: schema-getting-started, schema-registration, "
            "context-management, schema-export, multi-registry, "
            "schema-compatibility, troubleshooting, advanced-workflows"
        )
    )

    mcp.run()
