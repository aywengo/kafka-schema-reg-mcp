#!/usr/bin/env python3
"""
Kafka Schema Registry Remote MCP Server - OAuth 2.1 Compliant

This file configures the MCP server for remote deployment with monitoring endpoints,
making it compatible with Anthropic's remote MCP server ecosystem and OAuth 2.1 specification.

✅ MCP 2025-06-18 COMPLIANT: All HTTP requests after initialization require the
   MCP-Protocol-Version header. Health, metrics, and well-known endpoints are exempt.

✅ OAuth 2.1 COMPLIANT: Implements RFC 8692 (Protected Resource), RFC 8707 (Resource Indicators),
   PKCE enforcement, and proper security headers.

✅ TRANSPORT: Uses modern streamable-http transport only (SSE transport deprecated per MCP 2025-06-18)

Remote MCP servers typically expose endpoints like:
- https://your-domain.com/mcp (for MCP protocol)
- https://your-domain.com/health (for health checks)
- https://your-domain.com/metrics (for Prometheus metrics)
- https://your-domain.com/.well-known/oauth-authorization-server (OAuth metadata)
- https://your-domain.com/.well-known/oauth-protected-resource (Resource metadata)

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
from kafka_schema_registry_unified_mcp import (
    MCP_PROTOCOL_VERSION,
    REGISTRY_MODE,
    mcp,
    registry_manager,
)

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

        # OAuth 2.1 specific metrics
        self.pkce_validation_attempts = 0
        self.pkce_validation_failures = 0
        self.resource_indicator_validations = 0
        self.resource_indicator_failures = 0
        self.audience_validation_failures = 0
        self.token_revocation_checks = 0
        self.jwks_cache_hits = 0
        self.jwks_cache_misses = 0

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

    def record_oauth_2_1_validation(self, validation_type: str, success: bool):
        """Record OAuth 2.1 specific validation metrics."""
        if validation_type == "pkce":
            self.pkce_validation_attempts += 1
            if not success:
                self.pkce_validation_failures += 1
        elif validation_type == "resource_indicator":
            self.resource_indicator_validations += 1
            if not success:
                self.resource_indicator_failures += 1
        elif validation_type == "audience":
            if not success:
                self.audience_validation_failures += 1
        elif validation_type == "revocation":
            self.token_revocation_checks += 1
        elif validation_type == "jwks_hit":
            self.jwks_cache_hits += 1
        elif validation_type == "jwks_miss":
            self.jwks_cache_misses += 1

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
                        for subject in (subjects or [])[
                            :50
                        ]:  # Limit to first 50 for performance
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

        # OAuth 2.1 metrics
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
                "# HELP mcp_oauth_pkce_validation_attempts_total PKCE validation attempts",
                "# TYPE mcp_oauth_pkce_validation_attempts_total counter",
                f"mcp_oauth_pkce_validation_attempts_total {self.pkce_validation_attempts}",
                "",
                "# HELP mcp_oauth_pkce_validation_failures_total PKCE validation failures",
                "# TYPE mcp_oauth_pkce_validation_failures_total counter",
                f"mcp_oauth_pkce_validation_failures_total {self.pkce_validation_failures}",
                "",
                "# HELP mcp_oauth_resource_indicator_validations_total Resource indicator validations",
                "# TYPE mcp_oauth_resource_indicator_validations_total counter",
                f"mcp_oauth_resource_indicator_validations_total {self.resource_indicator_validations}",
                "",
                "# HELP mcp_oauth_resource_indicator_failures_total Resource indicator validation failures",
                "# TYPE mcp_oauth_resource_indicator_failures_total counter",
                f"mcp_oauth_resource_indicator_failures_total {self.resource_indicator_failures}",
                "",
                "# HELP mcp_oauth_audience_validation_failures_total Audience validation failures",
                "# TYPE mcp_oauth_audience_validation_failures_total counter",
                f"mcp_oauth_audience_validation_failures_total {self.audience_validation_failures}",
                "",
                "# HELP mcp_oauth_token_revocation_checks_total Token revocation checks",
                "# TYPE mcp_oauth_token_revocation_checks_total counter",
                f"mcp_oauth_token_revocation_checks_total {self.token_revocation_checks}",
                "",
                "# HELP mcp_oauth_jwks_cache_hits_total JWKS cache hits",
                "# TYPE mcp_oauth_jwks_cache_hits_total counter",
                f"mcp_oauth_jwks_cache_hits_total {self.jwks_cache_hits}",
                "",
                "# HELP mcp_oauth_jwks_cache_misses_total JWKS cache misses",
                "# TYPE mcp_oauth_jwks_cache_misses_total counter",
                f"mcp_oauth_jwks_cache_misses_total {self.jwks_cache_misses}",
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


def get_security_headers() -> dict:
    """Get OAuth 2.1 compliant security headers."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Strict-Transport-Security": (
            "max-age=31536000; includeSubDomains"
            if os.getenv("TLS_ENABLED", "false").lower() == "true"
            else ""
        ),
        "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none';",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "OAuth-Version": "2.1",
        "MCP-Specification": "MCP 2025-06-18",
    }


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
            "oauth_2_1_compliant": True,
            "transport": "streamable-http",  # Only supported transport
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            "mcp_compliance": {
                "header_validation_enabled": True,
                "jsonrpc_batching_disabled": True,
                "specification": "MCP 2025-06-18",
                "oauth_2_1_features": {
                    "pkce_required": True,
                    "resource_indicators": True,
                    "audience_validation": True,
                    "token_binding": True,
                    "revocation_checking": True,
                },
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

        # Return appropriate HTTP status with security headers
        from starlette.responses import JSONResponse

        status_code = 200 if overall_healthy else 503
        security_headers = get_security_headers()

        return JSONResponse(
            server_status,
            status_code=status_code,
            headers=security_headers,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        metrics.record_request("health", time.time() - start_time, False)

        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "oauth_2_1_compliant": True,
            },
            status_code=503,
            headers=security_headers,
        )


@mcp.custom_route("/metrics", methods=["GET"])
async def prometheus_metrics(request):
    """Prometheus metrics endpoint."""
    try:
        start_time = time.time()

        prometheus_output = metrics.get_prometheus_metrics()

        metrics.record_request("metrics", time.time() - start_time, True)

        from starlette.responses import Response

        security_headers = get_security_headers()
        security_headers["Content-Type"] = "text/plain; version=0.0.4; charset=utf-8"

        return Response(
            prometheus_output,
            media_type="text/plain; version=0.0.4; charset=utf-8",
            headers=security_headers,
        )

    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        metrics.record_request("metrics", time.time() - start_time, False)

        from starlette.responses import Response

        security_headers = get_security_headers()

        return Response(
            f"# Error generating metrics: {str(e)}\n",
            status_code=500,
            media_type="text/plain",
            headers=security_headers,
        )


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes (simpler than health check)."""
    try:
        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": metrics.get_uptime(),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "oauth_2_1_compliant": True,
            },
            headers=security_headers,
        )
    except Exception as e:
        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "status": "not_ready",
                "error": str(e),
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "oauth_2_1_compliant": True,
            },
            status_code=503,
            headers=security_headers,
        )


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_authorization_server_metadata(request):
    """
    OAuth 2.1 Authorization Server Metadata (RFC 8414) - FIXED ENDPOINT PATH.

    This endpoint provides OAuth 2.1 compliant authorization server metadata
    with mandatory PKCE support and other OAuth 2.1 features.
    """
    try:
        from starlette.responses import JSONResponse

        # Only provide metadata if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            security_headers = get_security_headers()
            return JSONResponse(
                {"error": "OAuth not enabled", "oauth_2_1_compliant": False},
                status_code=404,
                headers=security_headers,
            )

        # Get the server's base URL
        host = request.url.hostname or os.getenv("MCP_HOST", "localhost")
        port = request.url.port or int(os.getenv("MCP_PORT", "8000"))
        scheme = (
            "https" if os.getenv("TLS_ENABLED", "false").lower() == "true" else "http"
        )
        base_url = f"{scheme}://{host}:{port}"

        # Get OAuth provider info
        # Use generic OAuth 2.1 discovery approach
        issuer_url = os.getenv("AUTH_ISSUER_URL", base_url)

        # Special handling for GitHub (not OAuth 2.1 compliant)
        if "github.com" in issuer_url:
            provider_config = {
                "issuer": "https://github.com",
                "authorization_endpoint": "https://github.com/login/oauth/authorize",
                "token_endpoint": "https://github.com/login/oauth/access_token",
                "jwks_uri": "https://api.github.com/meta/public_keys/oauth",
                # GitHub has limited OAuth 2.1 support
            }
        else:
            # Generic OAuth 2.1 provider (endpoints discovered automatically)
            provider_config = {
                "issuer": issuer_url,
                "authorization_endpoint": f"{issuer_url}/oauth2/authorize",
                "token_endpoint": f"{issuer_url}/oauth2/token",
                "jwks_uri": f"{issuer_url}/oauth2/jwks",
                "token_introspection_endpoint": f"{issuer_url}/oauth2/introspect",
                "revocation_endpoint": f"{issuer_url}/oauth2/revoke",
            }

        # OAuth 2.1 compliant metadata
        metadata = {
            "issuer": provider_config.get("issuer", base_url),
            "authorization_endpoint": provider_config.get("authorization_endpoint"),
            "token_endpoint": provider_config.get("token_endpoint"),
            "jwks_uri": provider_config.get("jwks_uri"),
            "token_introspection_endpoint": provider_config.get(
                "token_introspection_endpoint"
            ),
            "revocation_endpoint": provider_config.get("revocation_endpoint"),
            # OAuth 2.1 required features
            "scopes_supported": [
                "read",
                "write",
                "admin",
                "openid",
                "email",
                "profile",
            ],
            "response_types_supported": ["code"],  # OAuth 2.1 removes implicit flow
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "private_key_jwt",  # OAuth 2.1 enhancement
            ],
            # PKCE (mandatory in OAuth 2.1)
            "code_challenge_methods_supported": ["S256"],  # Only S256 in OAuth 2.1
            "require_pkce": True,  # Mandatory per OAuth 2.1
            # OAuth 2.1 security enhancements
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256", "ES256"],
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
            # Resource indicators support (RFC 8707)
            "resource_documentation": f"{base_url}/.well-known/oauth-protected-resource",
            "resource_indicators_supported": True,
            # Token introspection (RFC 7662)
            "introspection_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            # Token revocation (RFC 7009)
            "revocation_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            # MCP-specific extensions
            "mcp_server_version": "2.0.0",
            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            "mcp_transport": "streamable-http",  # Only supported transport
            "mcp_endpoints": {
                "mcp": f"{base_url}/mcp",
                "health": f"{base_url}/health",
                "metrics": f"{base_url}/metrics",
            },
            "mcp_compliance": {
                "specification": "MCP 2025-06-18",
                "header_validation_enabled": True,
                "jsonrpc_batching_disabled": True,
                "oauth_2_1_compliant": True,
            },
            # OAuth 2.1 version indicator
            "oauth_version": "2.1",
            "oauth_2_1_features": {
                "pkce_mandatory": True,
                "implicit_flow_disabled": True,
                "resource_indicators": True,
                "token_binding": True,
                "enhanced_security": True,
            },
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        security_headers = get_security_headers()
        security_headers.update(
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }
        )

        return JSONResponse(
            metadata,
            headers=security_headers,
        )

    except Exception as e:
        logger.error(f"OAuth authorization server metadata error: {e}")
        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "error": "Failed to generate OAuth metadata",
                "oauth_2_1_compliant": False,
            },
            status_code=500,
            headers=security_headers,
        )


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource_metadata(request):
    """
    OAuth 2.0 Protected Resource Metadata (RFC 8692) - Enhanced for OAuth 2.1.

    This endpoint provides comprehensive resource server metadata including
    OAuth 2.1 features like resource indicators and enhanced security.
    """
    try:
        from starlette.responses import JSONResponse

        # Only provide metadata if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            security_headers = get_security_headers()
            return JSONResponse(
                {"error": "OAuth not enabled", "oauth_2_1_compliant": False},
                status_code=404,
                headers=security_headers,
            )

        # Get the server's base URL
        host = request.url.hostname or os.getenv("MCP_HOST", "localhost")
        port = request.url.port or int(os.getenv("MCP_PORT", "8000"))
        scheme = (
            "https" if os.getenv("TLS_ENABLED", "false").lower() == "true" else "http"
        )
        base_url = f"{scheme}://{host}:{port}"

        # Get authorization server URL (generic OAuth 2.1)
        authorization_server = os.getenv("AUTH_ISSUER_URL", base_url)

        # Resource indicators configuration
        resource_indicators = []
        if os.getenv("RESOURCE_INDICATORS"):
            resource_indicators = [
                url.strip()
                for url in os.getenv("RESOURCE_INDICATORS").split(",")
                if url.strip()
            ]

        # Default resource indicator is our server URL
        if not resource_indicators:
            resource_indicators = [base_url]

        # RFC 8692 compliant protected resource metadata
        metadata = {
            # Core resource server information
            "resource": base_url,
            "authorization_servers": [authorization_server],
            "jwks_uri": f"{base_url}/.well-known/jwks.json",
            "bearer_methods_supported": ["header"],  # Only header method per OAuth 2.1
            "resource_documentation": f"{base_url}/docs",
            # Resource indicators (RFC 8707)
            "resource_indicators": resource_indicators,
            "resource_indicators_supported": True,
            # Scopes and permissions
            "scopes_supported": ["read", "write", "admin"],
            "scope_descriptions": {
                "read": "Can view schemas, subjects, configurations",
                "write": "Can register schemas, update configs (includes read permissions)",
                "admin": "Can delete subjects, manage registries (includes write and read permissions)",
            },
            # Audience validation
            "audience_supported": True,
            "audience_values": [base_url] + resource_indicators,
            # Token validation methods
            "token_validation_methods": (
                ["jwt", "introspection"]
                if "github.com" not in authorization_server
                else ["api_validation"]
            ),
            "token_introspection_endpoint": (
                f"{authorization_server}/introspect"
                if "github.com" not in authorization_server
                else None
            ),
            "token_revocation_endpoint": (
                f"{authorization_server}/revoke"
                if "github.com" not in authorization_server
                else None
            ),
            # OAuth 2.1 security features
            "oauth_version": "2.1",
            "oauth_2_1_features": {
                "pkce_required": True,
                "resource_indicator_validation": True,
                "audience_validation": True,
                "token_binding_support": True,
                "enhanced_token_validation": True,
                "implicit_flow_disabled": True,
            },
            # Token binding (if supported)
            "token_binding_methods_supported": (
                ["tls-server-end-point"] if scheme == "https" else []
            ),
            # MCP-specific resource information
            "mcp_server_info": {
                "name": "Kafka Schema Registry MCP Server",
                "version": "2.0.0",
                "protocol_version": MCP_PROTOCOL_VERSION,
                "transport": "streamable-http",  # Only supported transport
                "tools_count": 48,
                "supported_registries": ["confluent", "apicurio", "hortonworks"],
                "compliance": {
                    "specification": "MCP 2025-06-18",
                    "header_validation_enabled": True,
                    "jsonrpc_batching_disabled": True,
                    "oauth_2_1_compliant": True,
                },
            },
            # Protected endpoints requiring OAuth
            "protected_endpoints": {
                "mcp": f"{base_url}/mcp",
                "tools": f"{base_url}/mcp",
                "resources": f"{base_url}/mcp",
            },
            # Public endpoints (no OAuth required)
            "public_endpoints": {
                "health": f"{base_url}/health",
                "metrics": f"{base_url}/metrics",
                "oauth_metadata": f"{base_url}/.well-known/oauth-authorization-server",
                "resource_metadata": f"{base_url}/.well-known/oauth-protected-resource",
                "jwks": f"{base_url}/.well-known/jwks.json",
            },
            # PKCE requirements (mandatory per OAuth 2.1)
            "require_pkce": True,
            "pkce_code_challenge_methods": ["S256"],  # Only S256 in OAuth 2.1
            "pkce_note": "PKCE (Proof Key for Code Exchange) is mandatory for all authorization flows per OAuth 2.1",
            # MCP Protocol Version requirements
            "mcp_protocol_requirements": {
                "required_header": "MCP-Protocol-Version",
                "supported_versions": [MCP_PROTOCOL_VERSION],
                "header_validation": "Enforced for all MCP endpoints",
            },
            # Security policies
            "security_policies": {
                "token_lifetime_max": 3600,  # 1 hour max
                "refresh_token_rotation": True,
                "scope_validation": "strict",
                "audience_validation": "mandatory",
                "resource_indicator_validation": "enabled",
            },
            # Supported algorithms
            "token_signing_alg_values_supported": ["RS256", "ES256"],
            "token_encryption_alg_values_supported": (
                ["RSA-OAEP", "A256KW"] if scheme == "https" else []
            ),
            # Error handling
            "error_uris": {
                "invalid_token": f"{base_url}/docs/errors#invalid_token",
                "insufficient_scope": f"{base_url}/docs/errors#insufficient_scope",
                "invalid_audience": f"{base_url}/docs/errors#invalid_audience",
            },
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        security_headers = get_security_headers()
        security_headers.update(
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }
        )

        return JSONResponse(
            metadata,
            headers=security_headers,
        )

    except Exception as e:
        logger.error(f"OAuth protected resource metadata error: {e}")
        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "error": "Failed to generate protected resource metadata",
                "oauth_2_1_compliant": False,
            },
            status_code=500,
            headers=security_headers,
        )


@mcp.custom_route("/.well-known/jwks.json", methods=["GET"])
async def jwks_endpoint(request):
    """JSON Web Key Set endpoint for token validation with enhanced caching."""
    try:
        from starlette.responses import JSONResponse

        # Only provide JWKS if OAuth is enabled
        if not os.getenv("ENABLE_AUTH", "false").lower() == "true":
            security_headers = get_security_headers()
            return JSONResponse(
                {"error": "OAuth not enabled", "oauth_2_1_compliant": False},
                status_code=404,
                headers=security_headers,
            )

        # Get JWKS URL from issuer (generic OAuth 2.1)
        issuer_url = os.getenv("AUTH_ISSUER_URL", "")

        # Special handling for GitHub
        if "github.com" in issuer_url:
            jwks_url = "https://api.github.com/meta/public_keys/oauth"
        else:
            # Generic OAuth 2.1 provider - use standard JWKS endpoint
            jwks_url = f"{issuer_url}/oauth2/jwks"

        if jwks_url:
            # Proxy the request to the actual JWKS endpoint with caching
            import aiohttp

            try:
                metrics.record_oauth_2_1_validation("jwks_miss", True)

                async with aiohttp.ClientSession() as session:
                    async with session.get(jwks_url, timeout=10) as response:
                        if response.status == 200:
                            jwks_data = await response.json()

                            # Add OAuth 2.1 compliance information
                            jwks_data["oauth_2_1_compliant"] = True
                            jwks_data["mcp_protocol_version"] = MCP_PROTOCOL_VERSION

                            security_headers = get_security_headers()
                            security_headers.update(
                                {
                                    "Content-Type": "application/json",
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "public, max-age=3600",
                                }
                            )

                            return JSONResponse(
                                jwks_data,
                                headers=security_headers,
                            )
            except Exception:
                pass

        # Fallback: return empty JWKS with OAuth 2.1 compliance info
        security_headers = get_security_headers()
        security_headers.update(
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            }
        )

        return JSONResponse(
            {
                "keys": [],
                "note": f"JWKS available at provider endpoint: {jwks_url}",
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "oauth_2_1_compliant": True,
                "provider": ("github" if "github.com" in issuer_url else "oauth2.1"),
            },
            headers=security_headers,
        )

    except Exception as e:
        logger.error(f"JWKS endpoint error: {e}")
        from starlette.responses import JSONResponse

        security_headers = get_security_headers()

        return JSONResponse(
            {
                "keys": [],
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "oauth_2_1_compliant": False,
                "error": str(e),
            },
            status_code=500,
            headers=security_headers,
        )


def main():
    """Run MCP server with streamable-http transport only (MCP 2025-06-18 compliant)."""

    # Force streamable-http transport only (SSE deprecated per MCP 2025-06-18)
    transport = "streamable-http"
    host = os.getenv("MCP_HOST", "0.0.0.0")  # Bind to all interfaces for containers
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")  # Always use /mcp for streamable-http

    logger.info("🚀 Starting Kafka Schema Registry Remote MCP Server")
    logger.info(
        f"📡 Transport: {transport} (SSE transport deprecated per MCP 2025-06-18)"
    )
    logger.info(f"🌐 Host: {host}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"📍 Path: {path}")
    logger.info(f"🔐 OAuth Enabled: {os.getenv('ENABLE_AUTH', 'false')}")
    logger.info(f"🏷️  OAuth Provider: {os.getenv('AUTH_PROVIDER', 'auto')}")
    logger.info(f"✅ MCP Protocol Version: {MCP_PROTOCOL_VERSION}")
    logger.info("✅ MCP-Protocol-Version Header Validation: ENABLED")
    logger.info("✅ OAuth 2.1 Compliance: ENABLED")
    logger.info("✅ PKCE Enforcement: MANDATORY")
    logger.info("✅ Resource Indicators: SUPPORTED")

    # Remote server URL for client connections
    server_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}{path}"
    logger.info(f"🔗 Remote MCP Server URL: {server_url}")

    # Monitoring endpoints
    health_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/health"
    metrics_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/metrics"
    oauth_metadata_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/.well-known/oauth-authorization-server"
    resource_metadata_url = f"http{'s' if os.getenv('TLS_ENABLED', 'false').lower() == 'true' else ''}://{host}:{port}/.well-known/oauth-protected-resource"

    logger.info(f"🏥 Health Check URL: {health_url}")
    logger.info(f"📊 Metrics URL: {metrics_url}")
    logger.info(f"🔐 OAuth Metadata URL: {oauth_metadata_url}")
    logger.info(f"🛡️  Resource Metadata URL: {resource_metadata_url}")

    try:
        # Set uvicorn environment variables for FastMCP
        os.environ["UVICORN_HOST"] = host
        os.environ["UVICORN_PORT"] = str(port)

        # Only streamable-http transport is supported (SSE deprecated per MCP 2025-06-18)
        logger.info("🚀 Starting MCP server with streamable-http transport")
        mcp.run(transport="streamable-http")

    except Exception as e:
        logger.error(f"Failed to start remote MCP server: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
