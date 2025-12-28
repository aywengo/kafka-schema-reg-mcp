#!/usr/bin/env python3
"""
Kafka Schema Registry Unified MCP Server - Modular Version with Elicitation Support and SLIM MODE

A comprehensive Message Control Protocol (MCP) server that automatically detects
and supports both single and multi-registry modes based on environment variables.

🚀 NEW: SLIM_MODE - Reduce exposed tools for lower LLM overhead
    When SLIM_MODE=true, only essential read-only tools are exposed.
    This reduces the number of tools from 70+ to ~20 essential ones.

🎯 NEW: ELICITATION CAPABILITY - Interactive workflow support per MCP 2025-06-18 specification.
    Tools can now interactively request missing information from users for guided workflows.

🚫 JSON-RPC BATCHING DISABLED: Per MCP 2025-06-18 specification compliance.
    Application-level batch operations (clear_context_batch, etc.) remain available
    and use individual requests with parallel processing for performance.

✅ MCP-PROTOCOL-VERSION HEADER VALIDATION: All HTTP requests after initialization
    must include the MCP-Protocol-Version header per MCP 2025-06-18 specification.

This modular version splits functionality across specialized modules:
- migration_tools: Schema and context migration
- comparison_tools: Registry and context comparison
- export_tools: Schema export functionality
- batch_operations: Application-level batch cleanup operations
- bulk_operations_wizard: Interactive admin task automation (NEW)
- statistics_tools: Counting and statistics
- core_registry_tools: Basic CRUD operations
- elicitation: Interactive workflow support (NEW)
- interactive_tools: Elicitation-enabled tool variants (NEW)
- elicitation_mcp_integration: Real MCP protocol integration (NEW)

Features:
- Automatic mode detection
- SLIM_MODE for reduced tool exposure
- 70+ MCP Tools (all original tools + elicitation-enabled variants) - reduced to ~20 in SLIM_MODE
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

# Standard library imports
import base64
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional, Union

# Third-party imports
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.dependencies import Progress
from fastmcp.server.context import Context

# Local imports
from batch_operations import (
    clear_context_batch_tool,
    clear_multiple_contexts_batch_tool,
)
from bulk_operations_mcp_integration import (
    create_bulk_operations_tools,
    handle_bulk_operations_tool,
)
from bulk_operations_wizard import BulkOperationsWizard
from comparison_tools import (
    compare_contexts_across_registries_tool,
    compare_registries_tool,
    find_missing_schemas_tool,
)
from core_registry_tools import list_subjects_tool  # Still needed for resource handlers
from core_registry_tools import (
    add_subject_alias_tool,
    check_compatibility_tool,
    create_context_tool,
    delete_context_tool,
    delete_subject_alias_tool,
    delete_subject_tool,
    get_global_config_tool,
    get_mode_tool,
    get_schema_by_id_tool,
    get_schema_tool,
    get_schema_versions_tool,
    get_subject_config_tool,
    get_subject_mode_tool,
    get_subjects_by_schema_id_tool,
    list_contexts_tool,
    register_schema_tool,
    update_global_config_tool,
    update_mode_tool,
    update_subject_config_tool,
    update_subject_mode_tool,
)
from elicitation import (
    elicitation_manager,
    is_elicitation_supported,
)
from elicitation_mcp_integration import (
    register_elicitation_handlers,
    update_elicitation_implementation,
)
from export_tools import (
    export_context_tool,
    export_global_tool,
    export_schema_tool,
    export_subject_tool,
)
from interactive_tools import check_compatibility_interactive as check_compatibility_interactive_impl
from interactive_tools import create_context_interactive as create_context_interactive_impl
from interactive_tools import export_global_interactive as export_global_interactive_impl
from interactive_tools import migrate_context_interactive as migrate_context_interactive_impl
from interactive_tools import register_schema_interactive as register_schema_interactive_impl
from migration_tools import (
    migrate_context_tool,
    migrate_schema_tool,
)
from oauth_provider import (
    ENABLE_AUTH,
    get_fastmcp_config,
    get_oauth_scopes_info,
    require_scopes,
)
from registry_management_tools import list_registries_tool  # Still needed for resource handlers
from registry_management_tools import (
    get_registry_info_tool,
    test_all_registries_tool,
    test_registry_connection_tool,
)
from schema_registry_common import (
    SINGLE_REGISTRY_PASSWORD,
    SINGLE_REGISTRY_URL,
    SINGLE_REGISTRY_USER,
    SINGLE_VIEWONLY,
    LegacyRegistryManager,
    MultiRegistryManager,
)
from schema_registry_common import check_viewonly_mode as _check_viewonly_mode
from schema_validation import (
    create_error_response,
    create_success_response,
    structured_output,
)
from statistics_tools import (
    count_contexts_tool,
    count_schema_versions_tool,
    count_schemas_task_queue_tool,
    count_schemas_tool,
    get_registry_statistics_task_queue_tool,
)
from workflow_mcp_integration import (
    handle_workflow_elicitation_response,
    register_workflow_tools,
)

# Load environment variables first
load_dotenv()

# SLIM MODE Configuration
SLIM_MODE = os.getenv("SLIM_MODE", "false").lower() == "true"

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

    requests.get = patched_get  # type: ignore
    requests.post = patched_post  # type: ignore

except ImportError:
    pass  # requests not available

# MCP 2025-06-18 Protocol Version Support
MCP_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_MCP_VERSIONS = ["2025-11-25"]

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
                "details": "The MCP-Protocol-Version header is required for all MCP requests per MCP 2025-11-25 spec",
                "supported_versions": SUPPORTED_MCP_VERSIONS,
                "example": "MCP-Protocol-Version: 2025-11-25",
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
mcp: FastMCP = FastMCP(**mcp_config)

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
    registry_manager: Union[LegacyRegistryManager, MultiRegistryManager] = LegacyRegistryManager("")

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
    headers = SecureHeaderDict("application/vnd.schemaregistry.v1+json")
    standard_headers = SecureHeaderDict("application/json")

# Initialize elicitation MCP integration (only if not in SLIM_MODE)
if not SLIM_MODE:
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
        multi_step_manager: Any = workflow_tools.multi_step_manager

        logger.info("✅ Multi-step elicitation workflows registered with MCP server")
        logger.info(f"✅ {len(multi_step_manager.workflows)} workflows available")
    except Exception as e:
        logger.error(f"❌ Error initializing multi-step elicitation workflows: {str(e)}")
        logger.info("📝 Multi-step workflows not available")
        multi_step_manager = None
else:
    logger.info("🚀 SLIM_MODE enabled - Elicitation and workflow features disabled")
    multi_step_manager = None

# ===== MCP PROTOCOL SUPPORT =====


@mcp.tool()
def ping():
    """
    Respond to MCP ping requests with pong.

    This tool implements the standard MCP ping/pong protocol for server health checking.
    MCP proxies and clients use this to verify that the server is alive and responding.
    """
    return {
        "response": "pong",
        "server_name": "Kafka Schema Registry Unified MCP Server",
        "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "protocol_version": MCP_PROTOCOL_VERSION,
        "registry_mode": REGISTRY_MODE,
        "slim_mode": SLIM_MODE,
        "status": "healthy",
        "ping_supported": True,
        "message": "MCP server is alive and responding",
    }


# ===== UNIFIED REGISTRY MANAGEMENT TOOLS =====


# ===== COMPARISON TOOLS (Hidden in SLIM_MODE) =====

if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("read")
    async def compare_registries(
        source_registry: str,
        target_registry: str,
        include_contexts: bool = True,
        include_configs: bool = True,
        *,
        context: Context,
    ):
        """Compare two Schema Registry instances and show differences."""
        return await compare_registries_tool(
            source_registry,
            target_registry,
            registry_manager,
            REGISTRY_MODE,
            include_contexts,
            include_configs,
            context,
        )

    @mcp.tool()
    @require_scopes("read")
    async def compare_contexts_across_registries(
        source_registry: str,
        target_registry: str,
        source_context: str,
        target_context: Optional[str] = None,
        *,
        context: Context,
    ):
        """Compare contexts across two registries."""
        return await compare_contexts_across_registries_tool(
            source_registry,
            target_registry,
            source_context,
            registry_manager,
            REGISTRY_MODE,
            target_context,
            context,
        )

    @mcp.tool()
    @require_scopes("read")
    async def find_missing_schemas(source_registry: str, target_registry: str, context: Optional[str] = None):
        """Find schemas that exist in source registry but not in target registry."""
        return await find_missing_schemas_tool(
            source_registry, target_registry, registry_manager, REGISTRY_MODE, context
        )


# ===== RESOURCE DISCOVERY TOOLS =====


@mcp.tool()
@require_scopes("read")
def list_available_resources():
    """List all available MCP resources and their usage patterns."""
    resources = {
        "registry_resources": {
            "registry://names": {
                "description": "List all configured registry names",
                "replaces_tool": "list_registries",
                "example": "registry://names",
                "data_type": "registry_names_list",
            },
            "registry://info": {
                "description": "Get global registry information",
                "replaces_tool": "get_registry_info (global)",
                "example": "registry://info",
                "data_type": "registry_info",
            },
            "registry://status": {
                "description": "Get status of all registries",
                "replaces_tool": "test_all_registries",
                "example": "registry://status",
                "data_type": "connection_status",
            },
            "registry://mode": {
                "description": "Get global registry mode information",
                "replaces_tool": "get_mode (global)",
                "example": "registry://mode",
                "data_type": "mode_info",
            },
            "registry://{name}/subjects": {
                "description": "List subjects for a specific registry",
                "replaces_tool": "list_subjects",
                "example": "registry://production/subjects",
                "data_type": "subjects_list",
            },
            "registry://{name}/contexts": {
                "description": "List contexts for a specific registry",
                "replaces_tool": "list_contexts",
                "example": "registry://production/contexts",
                "data_type": "contexts_list",
            },
            "registry://{name}/config": {
                "description": "Get global config for a specific registry",
                "replaces_tool": "get_global_config",
                "example": "registry://production/config",
                "data_type": "config_info",
            },
        },
        "schema_resources": {
            "schema://{name}/{context}/{subject}": {
                "description": "Get schema content for a specific subject",
                "replaces_tool": "get_schema",
                "example": "schema://production/users/user-events",
                "data_type": "schema_content",
            },
            "schema://{name}/{subject}": {
                "description": "Get schema content (default context)",
                "replaces_tool": "get_schema",
                "example": "schema://production/user-events",
                "data_type": "schema_content",
            },
            "schema://{name}/{context}/{subject}/versions": {
                "description": "Get schema versions for a specific subject",
                "replaces_tool": "get_schema_versions",
                "example": "schema://production/users/user-events/versions",
                "data_type": "versions_list",
            },
        },
        "subject_resources": {
            "subject://{name}/{context}/{subject}/config": {
                "description": "Get subject configuration",
                "replaces_tool": "get_subject_config",
                "example": "subject://production/users/user-events/config",
                "data_type": "subject_config",
            },
            "subject://{name}/{context}/{subject}/mode": {
                "description": "Get subject mode",
                "replaces_tool": "get_subject_mode",
                "example": "subject://production/users/user-events/mode",
                "data_type": "subject_mode",
            },
        },
        "usage_notes": {
            "registry_name_mapping": {
                "single_registry": "Use 'default' as registry name",
                "multi_registry": "Use configured registry names from environment",
            },
            "migration_benefits": [
                "Better performance through caching",
                "Reduced token usage in LLM interactions",
                "Real-time data updates",
                "More predictable response format",
            ],
            "response_format": {"tools": "result.content[0].text", "resources": "result.contents[0].text"},
        },
    }

    return {
        "available_resources": resources,
        "total_resources": sum(
            len(category)
            for category in [
                resources["registry_resources"],
                resources["schema_resources"],
                resources["subject_resources"],
            ]
        ),
        "registry_mode": REGISTRY_MODE,
        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
    }


@mcp.tool()
@require_scopes("read")
def suggest_resource_for_tool(tool_name: str):
    """Suggest the appropriate resource to use instead of a removed tool."""
    tool_to_resource_mapping = {
        "list_subjects": {
            "resource": "registry://{name}/subjects",
            "example": "registry://production/subjects",
            "migration_code": """# OLD (removed)
result = await client.call_tool("list_subjects", {"context": "production"})

# NEW (use resource)
result = await client.read_resource("registry://production/subjects")
data = json.loads(result.contents[0].text)""",
        },
        "list_registries": {
            "resource": "registry://names",
            "example": "registry://names",
            "migration_code": """# OLD (removed)
result = await client.call_tool("list_registries", {})

# NEW (use resource)
result = await client.read_resource("registry://names")
data = json.loads(result.contents[0].text)""",
        },
        "list_contexts": {
            "resource": "registry://{name}/contexts",
            "example": "registry://production/contexts",
            "migration_code": """# OLD (removed)
result = await client.call_tool("list_contexts", {})

# NEW (use resource)
result = await client.read_resource("registry://production/contexts")
data = json.loads(result.contents[0].text)""",
        },
        "get_schema": {
            "resource": "schema://{name}/{context}/{subject}",
            "example": "schema://production/users/user-events",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_schema", {
    "subject": "user-events",
    "context": "users"
})

# NEW (use resource)
result = await client.read_resource("schema://production/users/user-events")
data = json.loads(result.contents[0].text)""",
        },
        "get_schema_versions": {
            "resource": "schema://{name}/{context}/{subject}/versions",
            "example": "schema://production/users/user-events/versions",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_schema_versions", {
    "subject": "user-events",
    "context": "users"
})

# NEW (use resource)
result = await client.read_resource("schema://production/users/user-events/versions")
data = json.loads(result.contents[0].text)""",
        },
        "get_global_config": {
            "resource": "registry://{name}/config",
            "example": "registry://production/config",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_global_config", {})

# NEW (use resource)
result = await client.read_resource("registry://production/config")
data = json.loads(result.contents[0].text)""",
        },
        "get_subject_config": {
            "resource": "subject://{name}/{context}/{subject}/config",
            "example": "subject://production/users/user-events/config",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_subject_config", {
    "subject": "user-events",
    "context": "users"
})

# NEW (use resource)
result = await client.read_resource("subject://production/users/user-events/config")
data = json.loads(result.contents[0].text)""",
        },
        "get_mode": {
            "resource": "registry://mode",
            "example": "registry://mode",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_mode", {})

# NEW (use resource)
result = await client.read_resource("registry://mode")
data = json.loads(result.contents[0].text)""",
        },
        "get_subject_mode": {
            "resource": "subject://{name}/{context}/{subject}/mode",
            "example": "subject://production/users/user-events/mode",
            "migration_code": """# OLD (removed)
result = await client.call_tool("get_subject_mode", {
    "subject": "user-events",
    "context": "users"
})

# NEW (use resource)
result = await client.read_resource("subject://production/users/user-events/mode")
data = json.loads(result.contents[0].text)""",
        },
    }

    if tool_name in tool_to_resource_mapping:
        suggestion = tool_to_resource_mapping[tool_name]
        return {
            "tool_name": tool_name,
            "status": "migrated_to_resource",
            "suggested_resource": suggestion["resource"],
            "example_uri": suggestion["example"],
            "migration_code": suggestion["migration_code"],
            "benefits": [
                "Better performance through caching",
                "Reduced token usage",
                "Real-time data updates",
                "More predictable response format",
            ],
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }
    else:
        return {
            "tool_name": tool_name,
            "status": "tool_still_available",
            "message": f"Tool '{tool_name}' is still available as an MCP tool",
            "suggestion": "Use list_available_resources() to see all available resources",
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }


@mcp.tool()
@require_scopes("read")
def generate_resource_templates(
    registry_name: Optional[str] = None, context: Optional[str] = None, subject: Optional[str] = None
):
    """Generate resource URI templates for your specific configuration."""

    # Use default registry name if not provided
    if not registry_name:
        registry_name = "default" if REGISTRY_MODE == "single" else "production"

    # Use example context if not provided
    if not context:
        context = "production"

    # Use example subject if not provided
    if not subject:
        subject = "user-events"

    templates = {
        "registry_resources": {
            "list_all_registries": "registry://names",
            "get_registry_info": "registry://info",
            "test_all_registries": "registry://status",
            "get_global_mode": "registry://mode",
            "list_subjects": f"registry://{registry_name}/subjects",
            "list_contexts": f"registry://{registry_name}/contexts",
            "get_global_config": f"registry://{registry_name}/config",
        },
        "schema_resources": {
            "get_schema_with_context": f"schema://{registry_name}/{context}/{subject}",
            "get_schema_default_context": f"schema://{registry_name}/{subject}",
            "get_schema_versions": f"schema://{registry_name}/{context}/{subject}/versions",
        },
        "subject_resources": {
            "get_subject_config": f"subject://{registry_name}/{context}/{subject}/config",
            "get_subject_mode": f"subject://{registry_name}/{context}/{subject}/mode",
        },
        "usage_examples": {
            "python_async": f"""# Example: List subjects
result = await client.read_resource("registry://{registry_name}/subjects")
data = json.loads(result.contents[0].text)
subjects = data.get("subjects", [])

# Example: Get schema
result = await client.read_resource("schema://{registry_name}/{context}/{subject}")
data = json.loads(result.contents[0].text)
schema = data.get("schema", {{}})""",
            "error_handling": f"""# Example with error handling
try:
    result = await client.read_resource("registry://{registry_name}/subjects")
    if result.contents and len(result.contents) > 0:
        data = json.loads(result.contents[0].text)
        subjects = data.get("subjects", [])
        print(f"Found {{{{len(subjects)}}}} subjects")
    else:
        print("No data returned from resource")
except Exception as e:
    print(f"Error accessing resource: {{{{e}}}}")""",
        },
        "configuration": {
            "registry_name": registry_name,
            "context": context,
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
        },
    }

    return {
        "templates": templates,
        "registry_mode": REGISTRY_MODE,
        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        "note": "Replace {registry_name}, {context}, and {subject} with your actual values",
    }


# ===== BACKWARD COMPATIBILITY WRAPPER TOOLS =====
# These tools exist to maintain compatibility with clients that expect them
# They internally use resources for better performance


@mcp.tool()
@require_scopes("read")
def list_registries():
    """List all configured Schema Registry instances.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://names' resource instead for better performance.
    """
    # Use the internal tool function
    return list_registries_tool(registry_manager, REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def get_registry_info(registry: Optional[str] = None):
    """Get detailed information about a specific registry.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://info/{name}' resource instead for better performance.
    """
    return get_registry_info_tool(registry_manager, REGISTRY_MODE, registry)


@mcp.tool()
@require_scopes("read")
def test_registry_connection(registry: Optional[str] = None):
    """Test connection to a specific registry.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://status/{name}' resource instead for better performance.
    """
    return test_registry_connection_tool(registry_manager, REGISTRY_MODE, registry)


@mcp.tool()
@require_scopes("read")
def test_all_registries():
    """Test connections to all configured registries.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://status' resource instead for better performance.
    """
    return test_all_registries_tool(registry_manager, REGISTRY_MODE)


@mcp.tool()
@require_scopes("read")
def list_subjects(context: Optional[str] = None, registry: Optional[str] = None):
    """List all subjects, optionally filtered by context.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://{name}/subjects' resource instead for better performance.
    """
    return list_subjects_tool(
        registry_manager,
        REGISTRY_MODE,
        context=context,
        registry=registry,
        auth=auth,
        headers=headers,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    registry: Optional[str] = None,
):
    """Get a specific version of a schema.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'schema://{name}/{context}/{subject}' resource instead for better performance.
    """
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
def get_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
):
    """Get all versions of a schema for a subject.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'schema://{name}/{context}/{subject}/versions' resource instead for better performance.
    """
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
def get_schema_by_id(
    schema_id: int,
    registry: Optional[str] = None,
):
    """Get a schema by its globally unique ID.

    Args:
        schema_id: The globally unique schema ID
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Schema information including content, type, and metadata
    """
    return get_schema_by_id_tool(
        schema_id,
        registry_manager,
        REGISTRY_MODE,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_subjects_by_schema_id(
    schema_id: int,
    registry: Optional[str] = None,
):
    """Get subjects and versions associated with a schema ID.

    Args:
        schema_id: The globally unique schema ID
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        List of subject-version pairs that use this schema ID
    """
    return get_subjects_by_schema_id_tool(
        schema_id,
        registry_manager,
        REGISTRY_MODE,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_global_config(context: Optional[str] = None, registry: Optional[str] = None):
    """Get global configuration settings.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://{name}/config' resource instead for better performance.
    """
    return get_global_config_tool(
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
def get_mode(context: Optional[str] = None, registry: Optional[str] = None):
    """Get the current mode of the Schema Registry.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://mode' resource instead for better performance.
    """
    return get_mode_tool(
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
def list_contexts(registry: Optional[str] = None):
    """List all available schema contexts.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'registry://{name}/contexts' resource instead for better performance.
    """
    return list_contexts_tool(
        registry_manager,
        REGISTRY_MODE,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


@mcp.tool()
@require_scopes("read")
def get_subject_config(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
):
    """Get configuration settings for a specific subject.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'subject://{name}/{context}/{subject}/config' resource instead for better performance.
    """
    return get_subject_config_tool(
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
def get_subject_mode(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
):
    """Get the operational mode for a specific subject.

    NOTE: This tool is maintained for backward compatibility.
    Consider using the 'subject://{name}/{context}/{subject}/mode' resource instead for better performance.
    """
    return get_subject_mode_tool(
        subject,
        registry_manager,
        REGISTRY_MODE,
        context,
        registry,
        auth,
        headers,
        SCHEMA_REGISTRY_URL,
    )


# Note: check_viewonly_mode is kept in the non-SLIM_MODE section below


# ===== SCHEMA MANAGEMENT TOOLS =====


# Basic register schema is kept even in SLIM_MODE for essential operations
@mcp.tool()
@require_scopes("write")
def register_schema(
    subject: str,
    schema_definition: dict,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
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


# Interactive schema registration (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    async def register_schema_interactive(
        subject: str,
        schema_definition: Optional[dict] = None,
        schema_type: str = "AVRO",
        context: Optional[str] = None,
        registry: Optional[str] = None,
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
            multi_step_manager=multi_step_manager,
        )


@mcp.tool()
@require_scopes("read")
def check_compatibility(
    subject: str,
    schema_definition: dict,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
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


# Interactive compatibility checking (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("read")
    async def check_compatibility_interactive(
        subject: str,
        schema_definition: dict,
        schema_type: str = "AVRO",
        context: Optional[str] = None,
        registry: Optional[str] = None,
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


# Update configuration tools (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    def update_global_config(compatibility: str, context: Optional[str] = None, registry: Optional[str] = None):
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


# Update subject config (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    def update_subject_config(
        subject: str, compatibility: str, context: Optional[str] = None, registry: Optional[str] = None
    ):
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


# Add subject alias tool (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    def add_subject_alias(
        alias: str,
        existing_subject: str,
        context: Optional[str] = None,
        registry: Optional[str] = None,
    ):
        """Create a subject alias to an existing subject (not available in SLIM/VIEWONLY)."""
        return add_subject_alias_tool(
            alias,
            existing_subject,
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
    def delete_subject_alias(
        alias: str,
        context: Optional[str] = None,
        registry: Optional[str] = None,
    ):
        """Delete a subject alias (not available in SLIM/VIEWONLY)."""
        return delete_subject_alias_tool(
            alias,
            registry_manager,
            REGISTRY_MODE,
            context,
            registry,
            auth,
            standard_headers,
            SCHEMA_REGISTRY_URL,
        )


# ===== MODE TOOLS =====


# Update mode tools (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    def update_mode(mode: str, context: Optional[str] = None, registry: Optional[str] = None):
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


# Update subject mode (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    def update_subject_mode(subject: str, mode: str, context: Optional[str] = None, registry: Optional[str] = None):
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


# Create context is kept even in SLIM_MODE for essential operations
@mcp.tool()
@require_scopes("write")
def create_context(context: str, registry: Optional[str] = None):
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


# Interactive context creation (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("write")
    async def create_context_interactive(
        context: str,
        registry: Optional[str] = None,
        description: Optional[str] = None,
        owner: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[list] = None,
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


# Delete operations (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("admin")
    def delete_context(context: str, registry: Optional[str] = None):
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
    async def delete_subject(
        subject: str, context: Optional[str] = None, registry: Optional[str] = None, permanent: bool = False
    ):
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


# Essential export tools (Available in SLIM_MODE)
@mcp.tool()
@require_scopes("read")
def export_schema(
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    format: str = "json",
    registry: Optional[str] = None,
):
    """Export a single schema in the specified format."""
    return export_schema_tool(subject, registry_manager, REGISTRY_MODE, version, context, format, registry)


@mcp.tool()
@require_scopes("read")
def export_subject(
    subject: str,
    context: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
    registry: Optional[str] = None,
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


# Advanced export tools (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool()
    @require_scopes("read")
    async def export_context(
        context: str,
        registry: Optional[str] = None,
        include_metadata: bool = True,
        include_config: bool = True,
        include_versions: str = "all",
        *,
        mcp_context: Context,
    ):
        """Export all subjects within a context."""
        return await export_context_tool(
            context,
            registry_manager,
            REGISTRY_MODE,
            registry,
            include_metadata,
            include_config,
            include_versions,
            mcp_context,
        )

    @mcp.tool()
    @require_scopes("read")
    async def export_global(
        registry: Optional[str] = None,
        include_metadata: bool = True,
        include_config: bool = True,
        include_versions: str = "all",
        *,
        mcp_context: Context,
    ):
        """Export all contexts and schemas from a registry."""
        return await export_global_tool(
            registry_manager,
            REGISTRY_MODE,
            registry,
            include_metadata,
            include_config,
            include_versions,
            mcp_context,
        )

    @mcp.tool()
    @require_scopes("read")
    async def export_global_interactive(
        registry: Optional[str] = None,
        include_metadata: Optional[bool] = None,
        include_config: Optional[bool] = None,
        include_versions: Optional[str] = None,
        format: Optional[str] = None,
        compression: Optional[str] = None,
        # Backward compatibility parameters
        output_format: Optional[str] = None,
        schemas_per_file: Optional[str] = None,
    ):
        """
        Interactive global export with elicitation for export preferences.

        When export preferences are not specified, this tool will elicit
        the required configuration from the user.
        """
        # Handle backward compatibility parameters
        if output_format is not None and format is None:
            format = output_format

        # schemas_per_file is not currently used but accepted for compatibility
        if schemas_per_file is not None:
            logger.warning(f"schemas_per_file parameter is not currently supported, ignoring value: {schemas_per_file}")

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


# ===== MIGRATION TOOLS (Hidden in SLIM_MODE) =====

if not SLIM_MODE:

    @mcp.tool(task=True)
    @require_scopes("admin")
    async def migrate_schema(
        subject: str,
        source_registry: str,
        target_registry: str,
        dry_run: bool = False,
        preserve_ids: bool = True,
        source_context: str = ".",
        target_context: str = ".",
        versions: Optional[list] = None,
        migrate_all_versions: bool = False,
        progress: Progress = Progress(),
    ):
        """Migrate a schema from one registry to another.

        Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.
        """
        return await migrate_schema_tool(
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
            progress=progress,
        )

    @mcp.tool(task=True)
    @require_scopes("admin")
    async def migrate_context(
        source_registry: str,
        target_registry: str,
        context: Optional[str] = None,
        target_context: Optional[str] = None,
        preserve_ids: bool = True,
        dry_run: bool = True,
        migrate_all_versions: bool = True,
        progress: Progress = Progress(),
    ):
        """Guide for migrating an entire context using Docker-based tools.

        Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.
        """
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
            progress=progress,
        )

    @mcp.tool()
    @require_scopes("admin")
    async def migrate_context_interactive(
        source_registry: str,
        target_registry: str,
        context: Optional[str] = None,
        target_context: Optional[str] = None,
        preserve_ids: Optional[bool] = None,
        dry_run: Optional[bool] = None,
        migrate_all_versions: Optional[bool] = None,
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


# ===== APPLICATION-LEVEL BATCH OPERATIONS (Hidden in SLIM_MODE) =====

if not SLIM_MODE:

    @mcp.tool(task=True)
    @require_scopes("admin")
    async def clear_context_batch(
        context: str,
        registry: Optional[str] = None,
        delete_context_after: bool = True,
        dry_run: bool = True,
        progress: Progress = Progress(),
    ):
        """Clear all subjects in a context using application-level batch operations.

        ⚠️  APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2025-11-25 compliance.
        Uses FastMCP background tasks API (SEP-1686) for async execution.
        """
        return await clear_context_batch_tool(
            context,
            registry_manager,
            REGISTRY_MODE,
            registry,
            delete_context_after,
            dry_run,
            progress=progress,
        )

    @mcp.tool(task=True)
    @require_scopes("admin")
    async def clear_multiple_contexts_batch(
        contexts: list,
        registry: Optional[str] = None,
        delete_contexts_after: bool = True,
        dry_run: bool = True,
        progress: Progress = Progress(),
    ):
        """Clear multiple contexts in a registry using application-level batch operations.

        ⚠️  APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2025-11-25 compliance.
        Uses FastMCP background tasks API (SEP-1686) for async execution.
        """
        return await clear_multiple_contexts_batch_tool(
            contexts,
            registry_manager,
            REGISTRY_MODE,
            registry,
            delete_contexts_after,
            dry_run,
            progress=progress,
        )


# ===== BULK OPERATIONS WIZARD (Hidden in SLIM_MODE) =====

if not SLIM_MODE:
    # Initialize bulk operations wizard
    try:
        # Create wizard instance (using None for batch_operations for now)
        # Note: task_manager removed - wizard now uses FastMCP Progress directly
        bulk_wizard = BulkOperationsWizard(registry_manager, elicitation_manager, None)  # batch_operations placeholder

        # Register bulk operations tools
        bulk_tools = create_bulk_operations_tools(bulk_wizard)

        # Add tools to MCP server
        @mcp.tool()
        @require_scopes("admin")
        async def bulk_operations_wizard(operation_type: Optional[str] = None, dry_run: bool = True):
            """
            Start the interactive Bulk Operations Wizard for admin tasks.

            Guides through safe execution of operations across multiple schemas.
            Supports schema updates, migrations, cleanup, and configuration changes.
            """
            from bulk_operations_wizard import BulkOperationType

            op_type = None
            if operation_type:
                op_type = BulkOperationType(operation_type)

            return await bulk_wizard.start_wizard(op_type)

        @mcp.tool()
        @require_scopes("admin")
        async def bulk_schema_update(
            pattern: Optional[str] = None,
            update_type: str = "compatibility",
            dry_run: bool = True,
            batch_size: int = 10,
        ):
            """
            Update schemas in bulk with interactive guidance.

            Supports compatibility settings, naming conventions, and metadata updates.
            Pattern matching supported (e.g., test-*, deprecated-*).
            """
            return await handle_bulk_operations_tool(
                bulk_wizard,
                "bulk_schema_update",
                {"pattern": pattern, "update_type": update_type, "dry_run": dry_run, "batch_size": batch_size},
            )

        @mcp.tool()
        @require_scopes("admin")
        async def bulk_schema_cleanup(
            cleanup_type: str = "test",
            pattern: Optional[str] = None,
            keep_versions: int = 3,
            check_consumers: bool = True,
            force: bool = False,
        ):
            """
            Clean up schemas in bulk with safety checks.

            Detects active consumers and provides options for handling them.
            Supports test schema cleanup, deprecated schema removal, and version purging.
            """
            return await handle_bulk_operations_tool(
                bulk_wizard,
                "bulk_schema_cleanup",
                {
                    "cleanup_type": cleanup_type,
                    "pattern": pattern,
                    "keep_versions": keep_versions,
                    "check_consumers": check_consumers,
                    "force": force,
                },
            )

        @mcp.tool()
        @require_scopes("admin")
        async def bulk_schema_migration(
            source_context: Optional[str] = None,
            target_context: Optional[str] = None,
            source_registry: Optional[str] = None,
            target_registry: Optional[str] = None,
            schema_pattern: Optional[str] = None,
            preserve_ids: bool = True,
            dry_run: bool = True,
        ):
            """
            Migrate schemas between contexts or registries.

            Supports pattern-based selection and maintains schema IDs.
            Includes preview and rollback capabilities.
            """
            return await handle_bulk_operations_tool(
                bulk_wizard,
                "bulk_schema_migration",
                {
                    "source_context": source_context,
                    "target_context": target_context,
                    "source_registry": source_registry,
                    "target_registry": target_registry,
                    "schema_pattern": schema_pattern,
                    "preserve_ids": preserve_ids,
                    "dry_run": dry_run,
                },
            )

        @mcp.tool()
        @require_scopes("admin")
        async def bulk_configuration_update(
            config_type: str = "security",
            target_type: str = "schemas",
            pattern: Optional[str] = None,
            settings: Optional[dict] = None,
            dry_run: bool = True,
        ):
            """
            Update configuration settings across multiple schemas or contexts.

            Supports security policies, retention settings, and access controls.
            """
            return await handle_bulk_operations_tool(
                bulk_wizard,
                "bulk_configuration_update",
                {
                    "config_type": config_type,
                    "target_type": target_type,
                    "pattern": pattern,
                    "settings": settings,
                    "dry_run": dry_run,
                },
            )

        logger.info("✅ Bulk Operations Wizard registered with MCP server")

    except Exception as e:
        logger.error(f"❌ Error initializing Bulk Operations Wizard: {str(e)}")
        logger.info("📝 Bulk Operations Wizard not available")


# ===== STATISTICS TOOLS =====

# Basic count tools are kept in SLIM_MODE


@mcp.tool()
@require_scopes("read")
def count_contexts(registry: Optional[str] = None):
    """Count the number of contexts in a registry."""
    return count_contexts_tool(registry_manager, REGISTRY_MODE, registry)


@mcp.tool(task=True)
@require_scopes("read")
async def count_schemas(context: Optional[str] = None, registry: Optional[str] = None, progress: Progress = Progress()):
    """Count the number of schemas in a context or registry."""
    # Use background task version for better performance when counting across multiple contexts
    if not SLIM_MODE and context is None:
        # Multiple contexts - use optimized async version with background tasks
        return await count_schemas_task_queue_tool(
            registry_manager, REGISTRY_MODE, context, registry, progress=progress
        )
    else:
        # Single context or SLIM_MODE - use direct version
        return count_schemas_tool(registry_manager, REGISTRY_MODE, context, registry)


@mcp.tool()
@require_scopes("read")
def count_schema_versions(subject: str, context: Optional[str] = None, registry: Optional[str] = None):
    """Count the number of versions for a specific schema."""
    return count_schema_versions_tool(subject, registry_manager, REGISTRY_MODE, context, registry)


# Heavy statistics tool (Hidden in SLIM_MODE)
if not SLIM_MODE:

    @mcp.tool(task=True)
    @require_scopes("read")
    async def get_registry_statistics(
        registry: Optional[str] = None, include_context_details: bool = True, progress: Progress = Progress()
    ):
        """Get comprehensive statistics about a registry."""
        # Always use background task version for better performance due to complexity
        return await get_registry_statistics_task_queue_tool(
            registry_manager, REGISTRY_MODE, registry, include_context_details, progress=progress
        )


# ===== ELICITATION MANAGEMENT TOOLS (Hidden in SLIM_MODE) =====

if not SLIM_MODE:

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


# ===== MULTI-STEP WORKFLOW TOOLS (Hidden in SLIM_MODE) =====

if not SLIM_MODE:

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
    def get_workflow_status(workflow_id: Optional[str] = None):
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

    # Guided workflow tools are now registered in workflow_mcp_integration.py
    # to avoid duplicate registrations


# ===== TASK MANAGEMENT TOOLS REMOVED =====
# These tools have been removed as FastMCP handles task status via Docket.
# Use FastMCP's built-in task tracking instead.


# ===== MCP COMPLIANCE AND UTILITY TOOLS =====


@structured_output("get_mcp_compliance_status_tool", fallback_on_error=True)
def _internal_get_mcp_compliance_status():
    """Internal function to get MCP compliance status with structured output validation.

    This function can be called directly for testing purposes.
    """
    try:
        # Check if header validation middleware is active
        header_validation_active = MIDDLEWARE_ENABLED

        # Get FastMCP configuration details
        config_details = {
            "slim_mode": SLIM_MODE,
            "protocol_version": MCP_PROTOCOL_VERSION,
            "supported_versions": SUPPORTED_MCP_VERSIONS,
            "header_validation_enabled": header_validation_active,
            "jsonrpc_batching_disabled": True,
            "compliance_status": "COMPLIANT",
            "last_verified": datetime.now(timezone.utc).isoformat(),
            "server_info": {
                "name": "Kafka Schema Registry Unified MCP Server",
                "version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                "architecture": "modular",
                "registry_mode": REGISTRY_MODE,
                "slim_mode": SLIM_MODE,
                "structured_output_implementation": "100% Complete - All tools",
                "elicitation_capability": (
                    "Enabled - MCP 2025-06-18 Interactive Workflows" if not SLIM_MODE else "Disabled in SLIM_MODE"
                ),
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
                "application_level_batching": (
                    "ENABLED - clear_context_batch, clear_multiple_contexts_batch"
                    if not SLIM_MODE
                    else "DISABLED in SLIM_MODE"
                ),
                "performance_strategy": "Individual requests with parallel processing",
                "fastmcp_config": {
                    "allow_batch_requests": False,
                    "batch_support": False,
                    "jsonrpc_batching_disabled": True,
                },
            },
            "structured_output": {
                "implementation_status": "100% Complete",
                "total_tools": "70+" if not SLIM_MODE else "~20 (SLIM_MODE)",
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
                "implementation_status": (
                    "Complete - MCP 2025-06-18 Specification" if not SLIM_MODE else "Disabled in SLIM_MODE"
                ),
                "interactive_tools": (
                    [
                        "register_schema_interactive",
                        "migrate_context_interactive",
                        "check_compatibility_interactive",
                        "create_context_interactive",
                        "export_global_interactive",
                    ]
                    if not SLIM_MODE
                    else []
                ),
                "elicitation_types": (
                    [
                        "text",
                        "choice",
                        "confirmation",
                        "form",
                        "multi_field",
                    ]
                    if not SLIM_MODE
                    else []
                ),
                "features": (
                    [
                        "Interactive schema field definition",
                        "Migration preference collection",
                        "Compatibility resolution guidance",
                        "Context metadata elicitation",
                        "Export format preference selection",
                        "Multi-round conversation support",
                        "Timeout handling and validation",
                        "Graceful fallback for non-supporting clients",
                    ]
                    if not SLIM_MODE
                    else ["Disabled in SLIM_MODE"]
                ),
                "management_tools": (
                    [
                        "list_elicitation_requests",
                        "get_elicitation_request",
                        "cancel_elicitation_request",
                        "get_elicitation_status",
                        "submit_elicitation_response",
                    ]
                    if not SLIM_MODE
                    else []
                ),
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
                    "SLIM_MODE status included",
                ],
            },
            "migration_info": {
                "breaking_change": True,
                "migration_required": "Clients using JSON-RPC batching must be updated",
                "header_requirement": "All MCP requests must include MCP-Protocol-Version header",
                "alternative_solutions": [
                    (
                        "Use application-level batch operations (clear_context_batch, etc.)"
                        if not SLIM_MODE
                        else "Use SLIM_MODE=true to reduce tool overhead"
                    ),
                    "Implement client-side request queuing",
                    "Use parallel individual requests for performance",
                    "Ensure all MCP clients send MCP-Protocol-Version header",
                    (
                        "Use interactive tools for guided workflows"
                        if not SLIM_MODE
                        else "Enable full mode for interactive tools"
                    ),
                    "Use ping tool for server health checking",
                ],
                "performance_impact": "Minimal - parallel processing maintains efficiency",
            },
            "supported_operations": {
                "individual_requests": "All MCP tools support individual requests",
                "application_batch_operations": (
                    [
                        "clear_context_batch",
                        "clear_multiple_contexts_batch",
                    ]
                    if not SLIM_MODE
                    else []
                ),
                "async_task_queue": (
                    "Long-running operations use task queue pattern" if not SLIM_MODE else "Limited in SLIM_MODE"
                ),
                "structured_output": "All tools have validated structured responses",
                "interactive_workflows": (
                    "Elicitation-enabled tools for guided user experiences"
                    if not SLIM_MODE
                    else "Disabled in SLIM_MODE"
                ),
                "ping_support": "Standard MCP ping/pong protocol for health checking",
            },
            "compliance_verification": {
                "fastmcp_version": "2.8.0+",
                "mcp_specification": "2025-06-18",
                "validation_date": datetime.now(timezone.utc).isoformat(),
                "compliance_notes": [
                    (
                        f"MCP-Protocol-Version header validation "
                        f"{'enabled' if header_validation_active else 'disabled (compatibility mode)'}"
                    ),
                    "JSON-RPC batching explicitly disabled in FastMCP configuration",
                    (
                        "Application-level batching uses individual requests"
                        if not SLIM_MODE
                        else "Batch operations disabled in SLIM_MODE"
                    ),
                    "All operations maintain backward compatibility except JSON-RPC batching",
                    (
                        "Performance optimized through parallel processing and task queuing"
                        if not SLIM_MODE
                        else "Simplified operations in SLIM_MODE"
                    ),
                    f"Exempt paths: {EXEMPT_PATHS}",
                    "Structured tool output implemented for all tools (100% complete)",
                    "Type-safe responses with JSON Schema validation",
                    "Graceful fallback on validation failures",
                    (
                        "Elicitation capability implemented per MCP 2025-06-18 specification"
                        if not SLIM_MODE
                        else "Elicitation disabled in SLIM_MODE"
                    ),
                    (
                        "Interactive workflow support with fallback mechanisms"
                        if not SLIM_MODE
                        else "Workflows disabled in SLIM_MODE"
                    ),
                    (
                        "Real MCP protocol integration for elicitation with fallback to mock"
                        if not SLIM_MODE
                        else "N/A in SLIM_MODE"
                    ),
                    "MCP ping/pong protocol implemented for server health checking",
                    f"SLIM_MODE: {'ENABLED - Reduced tool exposure (~9 tools)' if SLIM_MODE else 'DISABLED - Full feature set (70+ tools)'}",
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


# Default registry management tools (Hidden in SLIM_MODE for multi-registry)
if not SLIM_MODE or REGISTRY_MODE == "single":

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

    @mcp.tool()
    @require_scopes("admin")
    def set_default_registry(registry_name: str):
        """Set the default registry."""
        return set_default_registry_tool(registry_name)


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


@mcp.tool()
@require_scopes("read")
def get_default_registry():
    """Get the current default registry."""
    return get_default_registry_tool()


@structured_output("check_viewonly_mode", fallback_on_error=True)
def check_viewonly_mode_tool(registry: Optional[str] = None):
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


# OAuth info tools (Hidden in SLIM_MODE)
if not SLIM_MODE:

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

        import requests

        results: Dict[str, Any] = {
            "test_time": datetime.now(timezone.utc).isoformat(),
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
                            warnings = endpoint_result.get("warnings", "")
                            if isinstance(warnings, str):
                                endpoint_result["warnings"] = warnings + " Missing MCP endpoints"
                            else:
                                endpoint_result["warnings"] = "Missing MCP endpoints"

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
                            warnings = endpoint_result.get("warnings", "")
                            if isinstance(warnings, str):
                                endpoint_result["warnings"] = warnings + " Missing MCP server info"
                            else:
                                endpoint_result["warnings"] = "Missing MCP server info"

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


# Note: get_operation_info_tool removed in v2.2.0+
# FastMCP tool definitions (with task=True) automatically expose background task capability
# Clients can see task support directly in tool metadata via MCP protocol


# ===== RESOURCES =====


# Global registry resources
@mcp.resource("registry://names")
@require_scopes("read")
def registry_names_resource():
    """Get list of all configured registry names."""
    import json

    try:
        # Get all registry names
        registry_names = registry_manager.list_registries()

        result = {
            "registry_names": registry_names,
            "total_registries": len(registry_names),
            "registry_mode": REGISTRY_MODE,
            "resource_info": {
                "resource_uri": "registry://names",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "replaces_tool": "list_registries",
                "migration_hint": "This resource replaces the list_registries tool for better performance",
                "related_resources": [
                    "registry://info - Get detailed registry information",
                    "registry://status - Test registry connections",
                    "registry://{name}/subjects - List subjects for specific registry",
                ],
            },
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get registry names: {str(e)}",
            "resource_info": {
                "resource_uri": "registry://names",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://info")
@require_scopes("read")
def registry_info_resource():
    """Get detailed server configuration and capabilities."""
    import json

    try:
        # Get info for all registries
        all_registries = {}
        for name in registry_manager.list_registries():
            try:
                registry_info = get_registry_info_tool(registry_manager, REGISTRY_MODE, name)
                all_registries[name] = registry_info
            except Exception as e:
                all_registries[name] = {"error": str(e)}

        result = {
            "registries": all_registries,
            "server_info": {
                "name": "Kafka Schema Registry Unified MCP Server",
                "version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                "registry_mode": REGISTRY_MODE,
                "slim_mode": SLIM_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            "resource_info": {
                "resource_uri": "registry://info",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get registry info: {str(e)}",
            "resource_info": {
                "resource_uri": "registry://info",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://info/{name}")
@require_scopes("read")
def registry_info_specific_resource(name: str):
    """Get detailed information about a specific registry."""
    import json

    try:
        # Use the existing get_registry_info_tool implementation
        result = get_registry_info_tool(registry_manager, REGISTRY_MODE, name)

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://info/{name}",
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get info for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://info/{name}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://status")
@require_scopes("read")
def registry_status_resource():
    """Get connection status for all registries."""
    import json

    try:
        # Test all registries
        result = test_all_registries_tool(registry_manager, REGISTRY_MODE)

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": "registry://status",
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get registry status: {str(e)}",
            "resource_info": {
                "resource_uri": "registry://status",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://status/{name}")
@require_scopes("read")
def registry_status_specific_resource(name: str):
    """Get connection status for a specific registry."""
    import json

    try:
        # Use the existing test_registry_connection_tool implementation
        result = test_registry_connection_tool(registry_manager, REGISTRY_MODE, name)

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://status/{name}",
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get status for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://status/{name}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://mode")
@require_scopes("read")
def registry_mode_resource():
    """Get operational mode for all registries."""
    import json

    try:
        # Get mode for all registries
        all_modes = {}
        for name in registry_manager.list_registries():
            try:
                mode_info = get_mode_tool(
                    registry_manager,
                    REGISTRY_MODE,
                    context=None,
                    registry=name if REGISTRY_MODE == "multi" else None,
                    auth=auth,
                    standard_headers=standard_headers,
                    schema_registry_url=SCHEMA_REGISTRY_URL,
                )
                all_modes[name] = mode_info
            except Exception as e:
                all_modes[name] = {"error": str(e)}

        result = {
            "registries": all_modes,
            "resource_info": {
                "resource_uri": "registry://mode",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get registry modes: {str(e)}",
            "resource_info": {
                "resource_uri": "registry://mode",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://mode/{name}")
@require_scopes("read")
def registry_mode_specific_resource(name: str):
    """Get operational mode for a specific registry."""
    import json

    try:
        # Use the existing get_mode_tool implementation
        result = get_mode_tool(
            registry_manager,
            REGISTRY_MODE,
            context=None,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://mode/{name}",
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get mode for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://mode/{name}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


# Registry-specific resources for read-only operations
@mcp.resource("registry://{name}/subjects")
@require_scopes("read")
def registry_subjects_resource(name: str, context: Optional[str] = None):
    """Get all subjects for a specific registry, optionally filtered by context."""
    import json

    try:
        # Use the existing list_subjects_tool implementation
        result = list_subjects_tool(
            registry_manager,
            REGISTRY_MODE,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://{name}/subjects",
            "registry_name": name,
            "context": context,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get subjects for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://{name}/subjects",
                "registry_name": name,
                "context": context,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://{name}/contexts")
@require_scopes("read")
def registry_contexts_resource(name: str):
    """Get all contexts for a specific registry."""
    import json

    try:
        # Use the existing list_contexts_tool implementation
        result = list_contexts_tool(
            registry_manager,
            REGISTRY_MODE,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://{name}/contexts",
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get contexts for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://{name}/contexts",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("registry://{name}/config")
@require_scopes("read")
def registry_config_resource(name: str, context: Optional[str] = None):
    """Get global configuration for a specific registry, optionally filtered by context."""
    import json

    try:
        # Use the existing get_global_config_tool implementation
        result = get_global_config_tool(
            registry_manager,
            REGISTRY_MODE,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"registry://{name}/config",
            "registry_name": name,
            "context": context,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get config for registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"registry://{name}/config",
                "registry_name": name,
                "context": context,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


# Schema-specific resources for direct schema content access
@mcp.resource("schema://{name}/{context}/{subject}")
@require_scopes("read")
def schema_content_resource(name: str, context: str, subject: str, version: str = "latest"):
    """Get schema content for a specific subject in a specific context and registry."""
    import json

    try:
        # Use the existing get_schema_tool implementation
        result = get_schema_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            version=version,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"schema://{name}/{context}/{subject}",
            "registry_name": name,
            "context": context,
            "subject": subject,
            "version": version,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get schema '{subject}' from registry '{name}' context '{context}': {str(e)}",
            "resource_info": {
                "resource_uri": f"schema://{name}/{context}/{subject}",
                "registry_name": name,
                "context": context,
                "subject": subject,
                "version": version,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("schema://{name}/{subject}")
@require_scopes("read")
def schema_content_default_context_resource(name: str, subject: str, version: str = "latest"):
    """Get schema content for a specific subject in the default context of a registry."""
    import json

    try:
        # Use the existing get_schema_tool implementation with default context
        result = get_schema_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            version=version,
            context=None,  # Use default context
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"schema://{name}/{subject}",
            "registry_name": name,
            "context": "default",
            "subject": subject,
            "version": version,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get schema '{subject}' from registry '{name}' (default context): {str(e)}",
            "resource_info": {
                "resource_uri": f"schema://{name}/{subject}",
                "registry_name": name,
                "context": "default",
                "subject": subject,
                "version": version,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("schema://{name}/{context}/{subject}/versions")
@require_scopes("read")
def schema_versions_resource(name: str, context: str, subject: str):
    """Get all versions of a schema for a specific subject in a specific context and registry."""
    import json

    try:
        # Use the existing get_schema_versions_tool implementation
        result = get_schema_versions_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"schema://{name}/{context}/{subject}/versions",
            "registry_name": name,
            "context": context,
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get schema versions for '{subject}' from registry '{name}' context '{context}': {str(e)}",
            "resource_info": {
                "resource_uri": f"schema://{name}/{context}/{subject}/versions",
                "registry_name": name,
                "context": context,
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("schema://{name}/{subject}/versions")
@require_scopes("read")
def schema_versions_default_context_resource(name: str, subject: str):
    """Get all versions of a schema for a specific subject in the default context of a registry."""
    import json

    try:
        # Use the existing get_schema_versions_tool implementation with default context
        result = get_schema_versions_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=None,  # Use default context
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            headers=headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"schema://{name}/{subject}/versions",
            "registry_name": name,
            "context": "default",
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get schema versions for '{subject}' from registry '{name}' (default context): {str(e)}",
            "resource_info": {
                "resource_uri": f"schema://{name}/{subject}/versions",
                "registry_name": name,
                "context": "default",
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


# ===== SUBJECT RESOURCES =====


@mcp.resource("subject://{name}/{context}/{subject}/config")
@require_scopes("read")
def subject_config_resource(name: str, context: str, subject: str):
    """Get configuration settings for a specific subject with explicit context."""
    import json

    try:
        # Use the existing get_subject_config_tool implementation
        result = get_subject_config_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"subject://{name}/{context}/{subject}/config",
            "registry_name": name,
            "context": context,
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get config for subject '{subject}' in context '{context}' from registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"subject://{name}/{context}/{subject}/config",
                "registry_name": name,
                "context": context,
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("subject://{name}/{subject}/config")
@require_scopes("read")
def subject_config_default_context_resource(name: str, subject: str):
    """Get configuration settings for a specific subject in the default context."""
    import json

    try:
        # Use the existing get_subject_config_tool implementation with default context
        result = get_subject_config_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=None,  # Use default context
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"subject://{name}/{subject}/config",
            "registry_name": name,
            "context": "default",
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get config for subject '{subject}' from registry '{name}' (default context): {str(e)}",
            "resource_info": {
                "resource_uri": f"subject://{name}/{subject}/config",
                "registry_name": name,
                "context": "default",
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("subject://{name}/{context}/{subject}/mode")
@require_scopes("read")
def subject_mode_resource(name: str, context: str, subject: str):
    """Get the mode for a specific subject with explicit context."""
    import json

    try:
        # Use the existing get_subject_mode_tool implementation
        result = get_subject_mode_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=context,
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"subject://{name}/{context}/{subject}/mode",
            "registry_name": name,
            "context": context,
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get mode for subject '{subject}' in context '{context}' from registry '{name}': {str(e)}",
            "resource_info": {
                "resource_uri": f"subject://{name}/{context}/{subject}/mode",
                "registry_name": name,
                "context": context,
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.resource("subject://{name}/{subject}/mode")
@require_scopes("read")
def subject_mode_default_context_resource(name: str, subject: str):
    """Get the mode for a specific subject in the default context."""
    import json

    try:
        # Use the existing get_subject_mode_tool implementation with default context
        result = get_subject_mode_tool(
            subject=subject,
            registry_manager=registry_manager,
            registry_mode=REGISTRY_MODE,
            context=None,  # Use default context
            registry=name if REGISTRY_MODE == "multi" else None,
            auth=auth,
            standard_headers=standard_headers,
            schema_registry_url=SCHEMA_REGISTRY_URL,
        )

        # Add resource metadata
        result["resource_info"] = {
            "resource_uri": f"subject://{name}/{subject}/mode",
            "registry_name": name,
            "context": "default",
            "subject": subject,
            "registry_mode": REGISTRY_MODE,
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_response = {
            "error": f"Failed to get mode for subject '{subject}' from registry '{name}' (default context): {str(e)}",
            "resource_info": {
                "resource_uri": f"subject://{name}/{subject}/mode",
                "registry_name": name,
                "context": "default",
                "subject": subject,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
        }
        return json.dumps(error_response, indent=2)


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

    # Calculate tool count based on SLIM_MODE
    if SLIM_MODE:
        tool_count = "~9 (SLIM_MODE)"
        features_status = "Essential tools only"
    else:
        tool_count = "75+"
        features_status = "Full feature set + Bulk Operations Wizard"

    print(
        f"""
🚀 Kafka Schema Registry Unified MCP Server Starting (Modular + Elicitation + Ping)
📡 Mode: {REGISTRY_MODE.upper()}
🚦 SLIM_MODE: {"ENABLED" if SLIM_MODE else "DISABLED"} - {features_status}
🔧 Registries: {len(registry_manager.list_registries())}
🛡️  OAuth: {"Enabled" if ENABLE_AUTH else "Disabled"}
🚫 JSON-RPC Batching: DISABLED (MCP 2025-06-18 Compliance)
✅ MCP-Protocol-Version Header Validation: {header_validation_status} ({MCP_PROTOCOL_VERSION})
💼 Application Batching: {"DISABLED (SLIM_MODE)" if SLIM_MODE else "ENABLED (clear_context_batch, etc.)"}
📦 Architecture: Modular (12 specialized modules)
🔧 Tools: {tool_count}
💬 Prompts: 6 comprehensive guides available
🎯 Structured Tool Output: 100% Complete (All tools)
🎭 Elicitation Capability: {"DISABLED (SLIM_MODE)" if SLIM_MODE else "ENABLED (Interactive Workflows)"}
🏓 MCP Ping/Pong: ENABLED (Server Health Checking)
🔗 Real MCP Elicitation Protocol: {"DISABLED (SLIM_MODE)" if SLIM_MODE else "INTEGRATED (with fallback)"}
    """,
        file=sys.stderr,
    )

    # Log startup information
    logger.info(f"Starting Unified MCP Server in {REGISTRY_MODE} mode (modular architecture with elicitation and ping)")
    logger.info(f"SLIM_MODE: {'ENABLED' if SLIM_MODE else 'DISABLED'} - {features_status}")
    logger.info(f"Detected {len(registry_manager.list_registries())} registry configurations")
    logger.info(
        f"✅ MCP-Protocol-Version header validation {header_validation_status.lower()} ({MCP_PROTOCOL_VERSION})"
    )
    logger.info(f"🚫 Exempt paths from header validation: {EXEMPT_PATHS}")
    logger.info("🚫 JSON-RPC batching DISABLED per MCP 2025-06-18 specification compliance")
    if not SLIM_MODE:
        logger.info("💼 Application-level batch operations ENABLED with individual requests")
    else:
        logger.info("💼 Application-level batch operations DISABLED in SLIM_MODE")
    logger.info("🎯 Structured tool output: 100% Complete - All tools have JSON Schema validation")
    logger.info(
        (
            f"🎭 Elicitation capability: "
            f"{'DISABLED (SLIM_MODE)' if SLIM_MODE else 'ENABLED' if is_elicitation_supported() else 'DISABLED'} - "
            f"{'SLIM_MODE active' if SLIM_MODE else 'Interactive workflows per MCP 2025-06-18'}"
        )
    )
    logger.info("🏓 MCP ping/pong protocol: ENABLED - Server health checking for MCP proxies")
    if not SLIM_MODE:
        logger.info("🔗 Real MCP elicitation protocol integrated with intelligent fallback to mock")
        logger.info(
            (
                "Available prompts: schema-getting-started, schema-registration, "
                "context-management, schema-export, multi-registry, "
                "schema-compatibility, troubleshooting, advanced-workflows"
            )
        )
    else:
        logger.info("🔗 Elicitation and workflow features disabled in SLIM_MODE")
        logger.info("💡 To enable full features, set SLIM_MODE=false")

    mcp.run()
