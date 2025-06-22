#!/usr/bin/env python3
"""
Kafka Schema Registry Remote MCP Server

This file configures the MCP server for remote deployment with monitoring endpoints,
making it compatible with Anthropic's remote MCP server ecosystem.

✅ MCP 2025-06-18 COMPLIANT: All HTTP requests after initialization require the
   MCP-Protocol-Version header. Health, metrics, and well-known endpoints are exempt.

Remote MCP servers typically expose endpoints like:
- https://your-domain.com/mcp (for MCP protocol)
- https://your-domain.com/health (for health checks)
- https://your-domain.com/metrics (for Prometheus metrics)

Usage:
    # Local development
    python remote-mcp-server.py

    # Production deployment (via Docker/K8s)
    docker run -p 8000:8000 -e ENABLE_AUTH=true aywengo/kafka-schema-reg-mcp:stable python remote-mcp-server.py
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the unified MCP server
from kafka_schema_registry_unified_mcp import REGISTRY_MODE, mcp, registry_manager, MCP_PROTOCOL_VERSION

# Configure logging for remote deployment
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Metrics collection
class RemoteMCPMetrics:
    """Collect and expose metrics for remote MCP server."""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.response_times = defaultdict(list)
        self.oauth_token_validations = 0
        self.oauth_validation_errors = 0
        self.registry_health_checks = 0
        self.last_health_check = None

        # MCP Protocol Version tracking
        self.mcp_header_validation_attempts = 0
        self.mcp_header_validation_failures = 0
        self.mcp_header_validation_successes = 0

        # Schema Registry specific metrics
        self.schema_operations = defaultdict(int)  # operation type -> count
        self.registry_operations = defaultdict(int)  # registry -> operation count
        self.registry_errors = defaultdict(int)  # registry -> error count
        self.registry_response_times = defaultdict(list)  # registry -> [response_times]
        self.schema_registrations = defaultdict(int)  # registry -> registration count
        self.schema_compatibility_checks = defaultdict(
            int
        )  # registry -> compatibility checks
        self.schema_exports = defaultdict(int)  # registry -> export count
        self.context_operations = defaultdict(int)  # context -> operation count

        # Cache for registry stats (refreshed periodically)
        self.registry_stats_cache = {}
        self.stats_cache_timestamp = 0
        self.stats_cache_ttl = 300  # 5 minutes

    def record_request(self, method: str, duration: float, success: bool):
        """Record a request metric."""
        self.request_count[method] += 1
        self.response_times[method].append(duration)
        if not success:
            self.error_count[method] += 1

    def record_oauth_validation(self, success: bool):
        """Record OAuth validation metric."""
        self.oauth_token_validations += 1
        if not success:
            self.oauth_validation_errors += 1

    def record_mcp_header_validation(self, success: bool):
        """Record MCP-Protocol-Version header validation metric."""
        self.mcp_header_validation_attempts += 1
        if success:
            self.mcp_header_validation_successes += 1
        else:
            self.mcp_header_validation_failures += 1

    def record_health_check(self):
        """Record health check execution."""
        self.registry_health_checks += 1
        self.last_health_check = datetime.utcnow()

    def record_schema_operation(
        self,
        operation: str,
        registry: str,
        duration: float,
        success: bool,
        context: str = None,
    ):
        """Record schema registry operation metrics."""
        self.schema_operations[operation] += 1
        self.registry_operations[registry] += 1
        self.registry_response_times[registry].append(duration)

        if not success:
            self.registry_errors[registry] += 1

        # Track specific operations
        if operation == "register_schema":
            self.schema_registrations[registry] += 1
        elif operation == "check_compatibility":
            self.schema_compatibility_checks[registry] += 1
        elif operation in ["export_schema", "export_subject", "export_context"]:
            self.schema_exports[registry] += 1

        # Track context operations
        if context:
            self.context_operations[f"{registry}_{context}"] += 1

    def get_registry_stats(self):
        """Get current registry statistics (cached for performance)."""
        current_time = time.time()

        # Return cached data if still valid
        if (current_time - self.stats_cache_timestamp) < self.stats_cache_ttl:
            return self.registry_stats_cache

        stats = {}
        try:
            # Get registry statistics
            for registry_name in registry_manager.list_registries():
                try:
                    client = registry_manager.get_registry(registry_name)
                    if client:
                        # Get subject count
                        subjects = client.list_subjects()
                        subject_count = len(subjects) if subjects else 0

                        # Count total schemas across all subjects
                        total_schemas = 0
                        for subject in (subjects or [])[:50]:  # Limit to first 50 for performance
                            try:
                                versions = client.get_schema_versions(subject)
                                total_schemas += len(versions) if versions else 0
                            except:
                                pass  # Skip subjects that can't be queried

                        # Get contexts (if available)
                        try:
                            contexts = client.list_contexts() or ["."]
                            context_count = len(contexts)
                        except:
                            context_count = 1  # Default context

                        stats[registry_name] = {
                            "subjects": subject_count,
                            "schemas": total_schemas,
                            "contexts": context_count,
                            "status": "healthy",
                        }
                    else:
                        stats[registry_name] = {
                            "subjects": 0,
                            "schemas": 0,
                            "contexts": 0,
                            "status": "error",
                        }
                except Exception as e:
                    stats[registry_name] = {
                        "subjects": 0,
                        "schemas": 0,
                        "contexts": 0,
                        "status": "error",
                        "error": str(e),
                    }
        except Exception as e:
            logger.warning(f"Failed to collect registry stats: {e}")

        # Update cache
        self.registry_stats_cache = stats
        self.stats_cache_timestamp = current_time

        return stats

    def get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-format metrics."""
        uptime = self.get_uptime()

        metrics = [
            "# HELP mcp_server_uptime_seconds Time since server started",
            "# TYPE mcp_server_uptime_seconds counter",
            f"mcp_server_uptime_seconds {uptime}",
            "",
            "# HELP mcp_requests_total Total number of MCP requests",
            "# TYPE mcp_requests_total counter",
        ]

        for method, count in self.request_count.items():
            metrics.append(f'mcp_requests_total{{method="{method}"}} {count}')

        metrics.extend(
            [
                "",
                "# HELP mcp_request_errors_total Total number of MCP request errors",
                "# TYPE mcp_request_errors_total counter",
            ]
        )

        for method, count in self.error_count.items():
            metrics.append(f'mcp_request_errors_total{{method="{method}"}} {count}')

        metrics.extend(
            [
                "",
                "# HELP mcp_request_duration_seconds Request duration in seconds",
                "# TYPE mcp_request_duration_seconds histogram",
            ]
        )

        for method, times in self.response_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                metrics.append(
                    f'mcp_request_duration_seconds_avg{{method="{method}"}} {avg_time:.6f}'
                )
                metrics.append(
                    f'mcp_request_duration_seconds_max{{method="{method}"}} {max_time:.6f}'
                )
                metrics.append(
                    f'mcp_request_duration_seconds_min{{method="{method}"}} {min_time:.6f}'
                )

        metrics.extend(
            [
                "",
                "# HELP mcp_oauth_validations_total Total OAuth token validations",
                "# TYPE mcp_oauth_validations_total counter",
                f"mcp_oauth_validations_total {self.oauth_token_validations}",
                "",
                "# HELP mcp_oauth_validation_errors_total OAuth validation errors",
                "# TYPE mcp_oauth_validation_errors_total counter",
                f"mcp_oauth_validation_errors_total {self.oauth_validation_errors}",
                "",
                "# HELP mcp_protocol_header_validations_total MCP-Protocol-Version header validation attempts",
                "# TYPE mcp_protocol_header_validations_total counter",
                f"mcp_protocol_header_validations_total {self.mcp_header_validation_attempts}",
                "",
                "# HELP mcp_protocol_header_validation_failures_total MCP-Protocol-Version header validation failures",
                "# TYPE mcp_protocol_header_validation_failures_total counter",
                f"mcp_protocol_header_validation_failures_total {self.mcp_header_validation_failures}",
                "",
                "# HELP mcp_protocol_header_validation_successes_total MCP-Protocol-Version header validation successes",
                "# TYPE mcp_protocol_header_validation_successes_total counter",
                f"mcp_protocol_header_validation_successes_total {self.mcp_header_validation_successes}",
                "",
                "# HELP mcp_registry_health_checks_total Registry health checks performed",
                "# TYPE mcp_registry_health_checks_total counter",
                f"mcp_registry_health_checks_total {self.registry_health_checks}",
                "",
                "# HELP mcp_registry_mode_info Registry mode information",
                "# TYPE mcp_registry_mode_info gauge",
                f'mcp_registry_mode_info{{mode="{REGISTRY_MODE}"}} 1',
                "",
                "# HELP mcp_protocol_version_info MCP Protocol Version information",
                "# TYPE mcp_protocol_version_info gauge",
                f'mcp_protocol_version_info{{version="{MCP_PROTOCOL_VERSION}"}} 1',
            ]
        )

        # Schema Registry specific metrics
        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_operations_total Total schema registry operations by type",
                "# TYPE mcp_schema_registry_operations_total counter",
            ]
        )

        for operation, count in self.schema_operations.items():
            metrics.append(
                f'mcp_schema_registry_operations_total{{operation="{operation}"}} {count}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_operations_by_registry_total Operations by registry",
                "# TYPE mcp_schema_registry_operations_by_registry_total counter",
            ]
        )

        for registry, count in self.registry_operations.items():
            metrics.append(
                f'mcp_schema_registry_operations_by_registry_total{{registry="{registry}"}} {count}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_errors_total Registry operation errors",
                "# TYPE mcp_schema_registry_errors_total counter",
            ]
        )

        for registry, count in self.registry_errors.items():
            metrics.append(
                f'mcp_schema_registry_errors_total{{registry="{registry}"}} {count}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_response_time_seconds Registry response times",
                "# TYPE mcp_schema_registry_response_time_seconds histogram",
            ]
        )

        for registry, times in self.registry_response_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                metrics.append(
                    f'mcp_schema_registry_response_time_seconds_avg{{registry="{registry}"}} {avg_time:.6f}'
                )
                metrics.append(
                    f'mcp_schema_registry_response_time_seconds_max{{registry="{registry}"}} {max_time:.6f}'
                )
                metrics.append(
                    f'mcp_schema_registry_response_time_seconds_min{{registry="{registry}"}} {min_time:.6f}'
                )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_registrations_total Schema registrations by registry",
                "# TYPE mcp_schema_registry_registrations_total counter",
            ]
        )

        for registry, count in self.schema_registrations.items():
            metrics.append(
                f'mcp_schema_registry_registrations_total{{registry="{registry}"}} {count}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_compatibility_checks_total Compatibility checks by registry",
                "# TYPE mcp_schema_registry_compatibility_checks_total counter",
            ]
        )

        for registry, count in self.schema_compatibility_checks.items():
            metrics.append(
                f'mcp_schema_registry_compatibility_checks_total{{registry="{registry}"}} {count}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_exports_total Schema exports by registry",
                "# TYPE mcp_schema_registry_exports_total counter",
            ]
        )

        for registry, count in self.schema_exports.items():
            metrics.append(
                f'mcp_schema_registry_exports_total{{registry="{registry}"}} {count}'
            )

        # Current registry statistics (from cache)
        registry_stats = self.get_registry_stats()

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_subjects Current number of subjects per registry",
                "# TYPE mcp_schema_registry_subjects gauge",
            ]
        )

        for registry, stats in registry_stats.items():
            metrics.append(
                f'mcp_schema_registry_subjects{{registry="{registry}"}} {stats.get("subjects", 0)}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_schemas Current number of schemas per registry",
                "# TYPE mcp_schema_registry_schemas gauge",
            ]
        )

        for registry, stats in registry_stats.items():
            metrics.append(
                f'mcp_schema_registry_schemas{{registry="{registry}"}} {stats.get("schemas", 0)}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_contexts Current number of contexts per registry",
                "# TYPE mcp_schema_registry_contexts gauge",
            ]
        )

        for registry, stats in registry_stats.items():
            metrics.append(
                f'mcp_schema_registry_contexts{{registry="{registry}"}} {stats.get("contexts", 0)}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_status Registry health status (1=healthy, 0=unhealthy)",
                "# TYPE mcp_schema_registry_status gauge",
            ]
        )

        for registry, stats in registry_stats.items():
            status_value = 1 if stats.get("status") == "healthy" else 0
            metrics.append(
                f'mcp_schema_registry_status{{registry="{registry}"}} {status_value}'
            )

        metrics.extend(
            [
                "",
                "# HELP mcp_schema_registry_context_operations_total Operations by context",
                "# TYPE mcp_schema_registry_context_operations_total counter",
            ]
        )

        for context_key, count in self.context_operations.items():
            if "_" in context_key:
                registry, context = context_key.split("_", 1)
                metrics.append(
                    f'mcp_schema_registry_context_operations_total{{registry="{registry}",context="{context}"}} {count}'
                )

        return "\n".join(metrics)


# Global metrics instance
metrics = RemoteMCPMetrics()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Kubernetes and monitoring."""
    try:
        start_time = time.time()

        # Test basic server functionality
        server_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": metrics.get_uptime(),
            "registry_mode": REGISTRY_MODE,
            "oauth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true",
            "transport": os.getenv("MCP_TRANSPORT", "streamable-http"),
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            "mcp_compliance": {
                "header_validation_enabled": True,
                "jsonrpc_batching_disabled": True,
                "specification": "MCP 2025-06-18",
            },
        }

        # Test registry connectivity
        registry_health = {}
        overall_healthy = True

        try:
            if REGISTRY_MODE == "single":
                # Test single registry
                default_registry = registry_manager.get_default_registry()
                if default_registry:
                    client = registry_manager.get_registry(default_registry)
                    if client:
                        test_result = client.test_connection()
                        registry_health[default_registry] = test_result
                        if test_result.get("status") != "connected":
                            overall_healthy = False
                    else:
                        overall_healthy = False
                        registry_health["error"] = "No registry client available"
            else:
                # Test all registries in multi mode
                for registry_name in registry_manager.list_registries():
                    try:
                        client = registry_manager.get_registry(registry_name)
                        if client:
                            test_result = client.test_connection()
                            registry_health[registry_name] = test_result
                            if test_result.get("status") != "connected":
                                overall_healthy = False
                        else:
                            registry_health[registry_name] = {
                                "status": "error",
                                "error": "Client not available",
                            }
                            overall_healthy = False
                    except Exception as e:
                        registry_health[registry_name] = {
                            "status": "error",
                            "error": str(e),
                        }
                        overall_healthy = False

        except Exception as e:
            overall_healthy = False
            registry_health["error"] = str(e)

        # Update server status based on registry health
        if not overall_healthy:
            server_status["status"] = "degraded"

        server_status["registries"] = registry_health
        server_status["response_time_ms"] = (time.time() - start_time) * 1000

        # Record metrics
        metrics.record_health_check()
        metrics.record_request("health", time.time() - start_time, overall_healthy)

        # Return appropriate HTTP status
        from starlette.responses import JSONResponse

        status_code = 200 if overall_healthy else 503

        return JSONResponse(
            server_status, 
            status_code=status_code,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        metrics.record_request("health", time.time() - start_time, False)

        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            status_code=503,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


@mcp.custom_route("/metrics", methods=["GET"])
async def prometheus_metrics(request):
    """Prometheus metrics endpoint."""
    try:
        start_time = time.time()

        prometheus_output = metrics.get_prometheus_metrics()

        metrics.record_request("metrics", time.time() - start_time, True)

        from starlette.responses import Response

        return Response(
            prometheus_output, 
            media_type="text/plain; version=0.0.4; charset=utf-8",
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )

    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        metrics.record_request("metrics", time.time() - start_time, False)

        from starlette.responses import Response

        return Response(
            f"# Error generating metrics: {str(e)}\n",
            status_code=500,
            media_type="text/plain",
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes (simpler than health check)."""
    try:
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": metrics.get_uptime(),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )
    except Exception as e:
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "not_ready", 
                "error": str(e),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }, 
            status_code=503,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


@mcp.custom_route("/.well-known/oauth-authorization-server-custom", methods=["GET"])
async def oauth_authorization_server_metadata(request):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    try:
        from starlette.responses import JSONResponse

        # Only provide metadata if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            return JSONResponse(
                {"error": "OAuth not enabled"},
                status_code=404,
                headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
            )

        # Get the server's base URL
        host = request.url.hostname or os.getenv("MCP_HOST", "localhost")
        port = request.url.port or int(os.getenv("MCP_PORT", "8000"))
        scheme = (
            "https" if os.getenv("TLS_ENABLED", "false").lower() == "true" else "http"
        )
        base_url = f"{scheme}://{host}:{port}"

        # Get OAuth provider info
        auth_provider = os.getenv("AUTH_PROVIDER", "auto").lower()

        # Provider-specific metadata
        provider_configs = {
            "azure": {
                "issuer": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/v2.0",
                "authorization_endpoint": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/oauth2/v2.0/authorize",
                "token_endpoint": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/oauth2/v2.0/token",
                "jwks_uri": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/discovery/v2.0/keys",
            },
            "google": {
                "issuer": "https://accounts.google.com",
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            },
            "okta": {
                "issuer": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default",
                "authorization_endpoint": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default/v1/authorize",
                "token_endpoint": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default/v1/token",
                "jwks_uri": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default/v1/keys",
            },
            "keycloak": {
                "issuer": os.getenv(
                    "AUTH_ISSUER_URL",
                    f"https://keycloak.example.com/realms/{os.getenv('KEYCLOAK_REALM', 'master')}",
                ),
                "authorization_endpoint": f"{os.getenv('AUTH_ISSUER_URL', 'https://keycloak.example.com/realms/master')}/protocol/openid-connect/auth",
                "token_endpoint": f"{os.getenv('AUTH_ISSUER_URL', 'https://keycloak.example.com/realms/master')}/protocol/openid-connect/token",
                "jwks_uri": f"{os.getenv('AUTH_ISSUER_URL', 'https://keycloak.example.com/realms/master')}/protocol/openid-connect/certs",
            },
            "github": {
                "issuer": "https://github.com",
                "authorization_endpoint": "https://github.com/login/oauth/authorize",
                "token_endpoint": "https://github.com/login/oauth/access_token",
                "jwks_uri": "https://api.github.com/meta/public_keys/oauth",
            },
        }

        provider_config = provider_configs.get(auth_provider, {})

        metadata = {
            "issuer": provider_config.get("issuer", base_url),
            "authorization_endpoint": provider_config.get("authorization_endpoint"),
            "token_endpoint": provider_config.get("token_endpoint"),
            "jwks_uri": provider_config.get("jwks_uri"),
            "scopes_supported": [
                "read",
                "write",
                "admin",
                "openid",
                "email",
                "profile",
            ],
            "response_types_supported": ["code", "token"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            "code_challenge_methods_supported": ["S256"],
            "require_pkce": True,  # PKCE is mandatory per MCP specification
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": [
                "sub",
                "iss",
                "aud",
                "exp",
                "iat",
                "name",
                "email",
                "preferred_username",
                "groups",
            ],
            # MCP-specific extensions
            "mcp_server_version": "2.0.0",
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            "mcp_transport": os.getenv("MCP_TRANSPORT", "streamable-http"),
            "mcp_endpoints": {
                "mcp": f"{base_url}/mcp",
                "health": f"{base_url}/health",
                "metrics": f"{base_url}/metrics",
            },
            "mcp_compliance": {
                "specification": "MCP 2025-06-18",
                "header_validation_enabled": True,
                "jsonrpc_batching_disabled": True,
            },
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return JSONResponse(
            metadata,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    except Exception as e:
        logger.error(f"OAuth authorization server metadata error: {e}")
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": "Failed to generate OAuth metadata"},
            status_code=500,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource_metadata(request):
    """OAuth 2.0 Protected Resource Metadata (RFC 8692)."""
    try:
        from starlette.responses import JSONResponse

        # Only provide metadata if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            return JSONResponse(
                {"error": "OAuth not enabled"},
                status_code=404,
                headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
            )

        # Get the server's base URL
        host = request.url.hostname or os.getenv("MCP_HOST", "localhost")
        port = request.url.port or int(os.getenv("MCP_PORT", "8000"))
        scheme = (
            "https" if os.getenv("TLS_ENABLED", "false").lower() == "true" else "http"
        )
        base_url = f"{scheme}://{host}:{port}"

        auth_provider = os.getenv("AUTH_PROVIDER", "auto").lower()

        # Get authorization server URL
        auth_server_configs = {
            "azure": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/v2.0",
            "google": "https://accounts.google.com",
            "okta": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default",
            "keycloak": os.getenv(
                "AUTH_ISSUER_URL",
                f"https://keycloak.example.com/realms/{os.getenv('KEYCLOAK_REALM', 'master')}",
            ),
            "github": "https://github.com",
        }

        authorization_server = auth_server_configs.get(auth_provider, base_url)

        metadata = {
            "resource": base_url,
            "authorization_servers": [authorization_server],
            "jwks_uri": f"{base_url}/.well-known/jwks.json",
            "bearer_methods_supported": ["header"],
            "resource_documentation": f"{base_url}/docs",
            # Scopes and permissions
            "scopes_supported": ["read", "write", "admin"],
            "scope_descriptions": {
                "read": "Can view schemas, subjects, configurations",
                "write": "Can register schemas, update configs (includes read permissions)",
                "admin": "Can delete subjects, manage registries (includes write and read permissions)",
            },
            # MCP-specific resource information
            "mcp_server_info": {
                "name": "Kafka Schema Registry MCP Server",
                "version": "2.0.0",
                "protocol_version": MCP_PROTOCOL_VERSION,
                "transport": os.getenv("MCP_TRANSPORT", "streamable-http"),
                "tools_count": 48,
                "supported_registries": ["confluent", "apicurio", "hortonworks"],
                "compliance": {
                    "specification": "MCP 2025-06-18",
                    "header_validation_enabled": True,
                    "jsonrpc_batching_disabled": True,
                },
            },
            # API endpoints that require OAuth
            "protected_endpoints": {
                "mcp": f"{base_url}/mcp",
                "tools": f"{base_url}/mcp",
                "resources": f"{base_url}/mcp",
            },
            # Token validation info
            "token_introspection_endpoint": (
                f"{authorization_server}/introspect"
                if auth_provider != "github"
                else None
            ),
            "token_validation_methods": (
                ["jwt", "introspection"]
                if auth_provider != "github"
                else ["api_validation"]
            ),
            # PKCE requirements (mandatory per MCP specification)
            "require_pkce": True,
            "pkce_code_challenge_methods": ["S256"],
            "pkce_note": "PKCE (Proof Key for Code Exchange) is mandatory for all authorization flows",
            # MCP Protocol Version requirements
            "mcp_protocol_requirements": {
                "required_header": "MCP-Protocol-Version",
                "supported_versions": [MCP_PROTOCOL_VERSION],
                "header_validation": "Enforced for all MCP endpoints",
            },
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return JSONResponse(
            metadata,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    except Exception as e:
        logger.error(f"OAuth protected resource metadata error: {e}")
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": "Failed to generate protected resource metadata"},
            status_code=500,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


@mcp.custom_route("/.well-known/jwks.json", methods=["GET"])
async def jwks_endpoint(request):
    """JSON Web Key Set endpoint for token validation."""
    try:
        from starlette.responses import JSONResponse

        # Only provide JWKS if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            return JSONResponse(
                {"error": "OAuth not enabled"},
                status_code=404,
                headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
            )

        auth_provider = os.getenv("AUTH_PROVIDER", "auto").lower()

        # For most providers, redirect to their JWKS endpoint
        jwks_urls = {
            "azure": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}/discovery/v2.0/keys",
            "google": "https://www.googleapis.com/oauth2/v3/certs",
            "okta": f"https://{os.getenv('OKTA_DOMAIN', 'your-domain')}/oauth2/default/v1/keys",
            "keycloak": f"{os.getenv('AUTH_ISSUER_URL', 'https://keycloak.example.com/realms/master')}/protocol/openid-connect/certs",
            "github": "https://api.github.com/meta/public_keys/oauth",
        }

        jwks_url = jwks_urls.get(auth_provider)

        if jwks_url:
            # Proxy the request to the actual JWKS endpoint
            import aiohttp

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(jwks_url, timeout=10) as response:
                        if response.status == 200:
                            jwks_data = await response.json()
                            return JSONResponse(
                                jwks_data,
                                headers={
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "public, max-age=3600",
                                    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
                                },
                            )
            except Exception:
                pass

        # Fallback: return empty JWKS
        return JSONResponse(
            {
                "keys": [], 
                "note": f"JWKS available at provider endpoint: {jwks_url}",
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    except Exception as e:
        logger.error(f"JWKS endpoint error: {e}")
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "keys": [],
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            status_code=500,
            headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        )


def main():
    """Run MCP server with remote transport configuration and monitoring."""

    # Get transport configuration from environment
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")  # Default to modern HTTP
    host = os.getenv("MCP_HOST", "0.0.0.0")  # Bind to all interfaces for containers
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp" if transport == "streamable-http" else "/sse")

    logger.info("🚀 Starting Kafka Schema Registry Remote MCP Server")
    logger.info(f"📡 Transport: {transport}")
    logger.info(f"🌐 Host: {host}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"📍 Path: {path}")
    logger.info(f"🔐 OAuth Enabled: {os.getenv('ENABLE_AUTH', 'false')}")
    logger.info(f"🏷️  OAuth Provider: {os.getenv('AUTH_PROVIDER', 'auto')}")
    logger.info(f"✅ MCP Protocol Version: {MCP_PROTOCOL_VERSION}")
    logger.info("✅ MCP-Protocol-Version Header Validation: ENABLED")

    # Remote server URL for client connections
    server_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}{path}"
    logger.info(f"🔗 Remote MCP Server URL: {server_url}")

    # Monitoring endpoints
    health_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/health"
    metrics_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/metrics"
    logger.info(f"🏥 Health Check URL: {health_url}")
    logger.info(f"📊 Metrics URL: {metrics_url}")

    try:
        # Set uvicorn environment variables for FastMCP
        os.environ["UVICORN_HOST"] = host
        os.environ["UVICORN_PORT"] = str(port)

        if transport == "streamable-http":
            # Modern HTTP transport (recommended)
            mcp.run(transport="streamable-http")
        elif transport == "sse":
            # SSE transport (compatible with existing SSE clients)
            mcp.run(transport="sse")
        else:
            logger.error(f"Unsupported transport: {transport}")
            logger.info("Supported transports: streamable-http, sse")
            return 1

    except Exception as e:
        logger.error(f"Failed to start remote MCP server: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
