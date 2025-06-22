#!/usr/bin/env python3
"""
OAuth Provider for Kafka Schema Registry MCP Server

This module provides OAuth 2.0 authentication and authorization functionality
with scope-based permissions for the Kafka Schema Registry MCP server.

Supported OAuth Providers:
- Azure AD / Entra ID
- Google OAuth 2.0
- Keycloak
- Okta
- Any OAuth 2.0 compliant provider

Scopes:
- read: Can view schemas, subjects, configurations
- write: Can register schemas, update configs (includes read permissions)
- admin: Can delete subjects, manage registries (includes write and read permissions)
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional, Set

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Try to import JWT and HTTP libraries for production validation
try:
    import aiohttp
    import jwt
    import requests
    from cryptography.hazmat.primitives import serialization
    from jwt.algorithms import RSAAlgorithm

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning(
        "JWT validation libraries not available. Install: pip install PyJWT aiohttp cryptography"
    )

# OAuth configuration from environment variables
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() in ("true", "1", "yes", "on")
AUTH_ISSUER_URL = os.getenv("AUTH_ISSUER_URL", "https://example.com")
AUTH_VALID_SCOPES = [
    s.strip()
    for s in os.getenv("AUTH_VALID_SCOPES", "read,write,admin").split(",")
    if s.strip()
]
AUTH_DEFAULT_SCOPES = [
    s.strip() for s in os.getenv("AUTH_DEFAULT_SCOPES", "read").split(",") if s.strip()
]
AUTH_REQUIRED_SCOPES = [
    s.strip() for s in os.getenv("AUTH_REQUIRED_SCOPES", "read").split(",") if s.strip()
]
AUTH_CLIENT_REG_ENABLED = os.getenv("AUTH_CLIENT_REG_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
AUTH_REVOCATION_ENABLED = os.getenv("AUTH_REVOCATION_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# Provider-specific configuration
AUTH_PROVIDER = os.getenv(
    "AUTH_PROVIDER", "auto"
).lower()  # azure, google, keycloak, okta, github, auto
AUTH_AUDIENCE = os.getenv("AUTH_AUDIENCE", "")  # Client ID or API identifier
AUTH_AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AUTH_KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "")
AUTH_OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")
AUTH_GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
AUTH_GITHUB_ORG = os.getenv(
    "GITHUB_ORG", ""
)  # Optional: restrict to organization members

# JWKS cache configuration
JWKS_CACHE_TTL = int(os.getenv("JWKS_CACHE_TTL", "3600"))  # 1 hour default
JWKS_CACHE = {}
JWKS_CACHE_TIMESTAMPS = {}

# Scope definitions and hierarchy
SCOPE_DEFINITIONS = {
    "read": {
        "description": "Can view schemas, subjects, configurations",
        "includes": [
            "list_registries",
            "get_subjects",
            "get_schema",
            "get_global_config",
            "compare_registries",
        ],
        "level": 1,
    },
    "write": {
        "description": "Can register schemas, update configs (includes read permissions)",
        "includes": [
            "register_schema",
            "update_global_config",
            "update_subject_config",
            "update_mode",
        ],
        "requires": ["read"],
        "level": 2,
    },
    "admin": {
        "description": "Can delete subjects, manage registries (includes write and read permissions)",
        "includes": [
            "delete_subject",
            "clear_context_batch",
            "migrate_schema",
            "migrate_context",
        ],
        "requires": ["write", "read"],
        "level": 3,
    },
}

if ENABLE_AUTH:
    try:
        from fastmcp.server.auth import BearerAuthProvider
        from fastmcp.server.dependencies import AccessToken, get_access_token

        class KafkaSchemaRegistryBearerAuthProvider(BearerAuthProvider):
            """
            Bearer Auth Provider for Kafka Schema Registry MCP Server using FastMCP 2.8+ architecture.

            Implements scope-based authorization with three levels:
            - read: Can view schemas, subjects, configurations
            - write: Can register schemas, update configs
            - admin: Can delete subjects, manage registries
            """

            def __init__(self, **kwargs):
                # Set up JWKS URI or public key based on provider configuration
                provider_config = self.get_provider_config(AUTH_PROVIDER)

                if provider_config and "jwks_uri" in provider_config:
                    super().__init__(
                        jwks_uri=provider_config["jwks_uri"],
                        issuer=AUTH_ISSUER_URL,
                        audience=AUTH_AUDIENCE,
                        required_scopes=AUTH_REQUIRED_SCOPES,
                        **kwargs,
                    )
                else:
                    # Fallback to basic configuration
                    super().__init__(
                        issuer=AUTH_ISSUER_URL,
                        audience=AUTH_AUDIENCE,
                        required_scopes=AUTH_REQUIRED_SCOPES,
                        **kwargs,
                    )

                self.valid_scopes = set(AUTH_VALID_SCOPES)
                self.required_scopes = set(AUTH_REQUIRED_SCOPES)
                logger.info(
                    f"Bearer Auth Provider initialized with scopes: {self.valid_scopes}"
                )
                logger.info(f"JWT validation available: {JWT_AVAILABLE}")
                if JWT_AVAILABLE:
                    logger.info(
                        f"OAuth provider: {AUTH_PROVIDER}, Issuer: {AUTH_ISSUER_URL}"
                    )

            def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
                """Get provider-specific configuration."""
                provider_configs = {
                    "azure": {
                        "jwks_uri": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/discovery/v2.0/keys",
                        "token_endpoint": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/oauth2/v2.0/token",
                        "auth_endpoint": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/oauth2/v2.0/authorize",
                        "issuer": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/v2.0",
                        "scope_claim": "scp",
                        "username_claim": "upn",
                    },
                    "google": {
                        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
                        "token_endpoint": "https://oauth2.googleapis.com/token",
                        "auth_endpoint": "https://accounts.google.com/o/oauth2/auth",
                        "issuer": "https://accounts.google.com",
                        "scope_claim": "scope",
                        "username_claim": "email",
                    },
                    "keycloak": {
                        "jwks_uri": f"{AUTH_ISSUER_URL}/protocol/openid-connect/certs",
                        "token_endpoint": f"{AUTH_ISSUER_URL}/protocol/openid-connect/token",
                        "auth_endpoint": f"{AUTH_ISSUER_URL}/protocol/openid-connect/auth",
                        "issuer": AUTH_ISSUER_URL,
                        "scope_claim": "scope",
                        "username_claim": "preferred_username",
                    },
                    "okta": {
                        "jwks_uri": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default/v1/keys",
                        "token_endpoint": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default/v1/token",
                        "auth_endpoint": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default/v1/authorize",
                        "issuer": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default",
                        "scope_claim": "scp",
                        "username_claim": "sub",
                    },
                    "github": {
                        # GitHub doesn't use standard OIDC, so this is limited
                        "token_endpoint": "https://github.com/login/oauth/access_token",
                        "auth_endpoint": "https://github.com/login/oauth/authorize",
                        "api_endpoint": "https://api.github.com/user",
                        "scope_claim": "scope",
                        "username_claim": "login",
                    },
                }

                if provider == "auto":
                    # Auto-detect based on issuer URL
                    if "microsoftonline.com" in AUTH_ISSUER_URL:
                        return provider_configs["azure"]
                    elif (
                        "googleapis.com" in AUTH_ISSUER_URL
                        or "accounts.google.com" in AUTH_ISSUER_URL
                    ):
                        return provider_configs["google"]
                    elif AUTH_OKTA_DOMAIN and AUTH_OKTA_DOMAIN in AUTH_ISSUER_URL:
                        return provider_configs["okta"]
                    elif "github.com" in AUTH_ISSUER_URL:
                        return provider_configs["github"]
                    else:
                        # Assume Keycloak or compatible OIDC provider
                        return provider_configs["keycloak"]

                return provider_configs.get(provider)

            def check_scopes(
                self, user_scopes: Set[str], required_scopes: Set[str]
            ) -> bool:
                """Check if user has required scopes, considering scope hierarchy."""
                if not required_scopes:
                    return True

                # Expand user scopes to include inherited scopes
                expanded_user_scopes = self.expand_scopes(list(user_scopes))

                # Check if all required scopes are present
                return required_scopes.issubset(expanded_user_scopes)

            def expand_scopes(self, scopes: list) -> Set[str]:
                """Expand scopes to include inherited scopes based on hierarchy."""
                expanded = set(scopes)

                for scope in scopes:
                    if scope in SCOPE_DEFINITIONS:
                        required_scopes = SCOPE_DEFINITIONS[scope].get("requires", [])
                        expanded.update(required_scopes)

                return expanded

            def has_read_access(self, user_scopes: Set[str]) -> bool:
                return self.check_scopes(user_scopes, {"read"})

            def has_write_access(self, user_scopes: Set[str]) -> bool:
                return self.check_scopes(user_scopes, {"write"})

            def has_admin_access(self, user_scopes: Set[str]) -> bool:
                return self.check_scopes(user_scopes, {"admin"})

        # Create global instance for easy access
        if JWT_AVAILABLE:
            try:
                oauth_provider = KafkaSchemaRegistryBearerAuthProvider()
                logger.info("OAuth Bearer Auth Provider initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OAuth Bearer Auth Provider: {e}")
                oauth_provider = None
        else:
            oauth_provider = None

        def require_scopes(*required_scopes: str):
            """
            Decorator to require specific OAuth scopes for FastMCP 2.8+ tools.
            Uses FastMCP's dependency injection system to access token information.
            """

            def decorator(func):
                async def wrapper(*args, **kwargs):
                    try:
                        # Access token information using FastMCP's dependency system
                        access_token: AccessToken = get_access_token()
                        user_scopes = (
                            set(access_token.scopes) if access_token.scopes else set()
                        )

                        if oauth_provider and not oauth_provider.check_scopes(
                            user_scopes, set(required_scopes)
                        ):
                            return {
                                "error": "Insufficient permissions",
                                "required_scopes": list(required_scopes),
                                "user_scopes": list(user_scopes),
                            }

                        return (
                            await func(*args, **kwargs)
                            if asyncio.iscoroutinefunction(func)
                            else func(*args, **kwargs)
                        )
                    except Exception as e:
                        if ENABLE_AUTH:
                            logger.warning(f"Authentication check failed: {e}")
                            return {
                                "error": "Authentication required",
                                "required_scopes": list(required_scopes),
                            }
                        else:
                            # If auth is disabled, just proceed
                            return (
                                await func(*args, **kwargs)
                                if asyncio.iscoroutinefunction(func)
                                else func(*args, **kwargs)
                            )

                # Preserve function metadata
                wrapper.__name__ = func.__name__
                wrapper.__doc__ = func.__doc__
                wrapper.__annotations__ = func.__annotations__
                return wrapper

            return decorator

    except ImportError as e:
        logger.warning(f"FastMCP auth imports not available: {e}")
        ENABLE_AUTH = False
        oauth_provider = None

        def require_scopes(*required_scopes: str):
            """Fallback decorator when FastMCP auth is not available."""

            def decorator(func):
                return func

            return decorator

else:
    oauth_provider = None

    def require_scopes(*required_scopes: str):
        """Decorator when authentication is disabled."""

        def decorator(func):
            return func

        return decorator


def get_oauth_scopes_info() -> Dict[str, Any]:
    """Get information about available OAuth scopes and their definitions."""
    return {
        "oauth_enabled": ENABLE_AUTH,
        "enabled": ENABLE_AUTH,
        "provider": AUTH_PROVIDER,
        "issuer_url": AUTH_ISSUER_URL,
        "issuer": AUTH_ISSUER_URL,
        "valid_scopes": AUTH_VALID_SCOPES,
        "default_scopes": AUTH_DEFAULT_SCOPES,
        "required_scopes": AUTH_REQUIRED_SCOPES,
        "scope_definitions": SCOPE_DEFINITIONS,
        "client_registration_enabled": AUTH_CLIENT_REG_ENABLED,
        "revocation_enabled": AUTH_REVOCATION_ENABLED,
        "jwt_available": JWT_AVAILABLE,
    }


def get_oauth_provider_configs():
    """Get OAuth provider configuration examples for all supported providers."""
    # Return comprehensive provider configurations for testing and documentation
    return {
        "azure": {
            "name": "Azure AD / Entra ID",
            "issuer_url": "https://login.microsoftonline.com/{tenant-id}/v2.0",
            "auth_url": "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token",
            "jwks_uri": "https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys",
            "scopes": [
                "openid",
                "email",
                "profile",
                "https://graph.microsoft.com/User.Read",
            ],
            "client_id_env": "AZURE_CLIENT_ID",
            "client_secret_env": "AZURE_CLIENT_SECRET",
            "tenant_id_env": "AZURE_TENANT_ID",
            "setup_docs": "https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app",
        },
        "google": {
            "name": "Google OAuth 2.0",
            "issuer_url": "https://accounts.google.com",
            "auth_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "GOOGLE_CLIENT_ID",
            "client_secret_env": "GOOGLE_CLIENT_SECRET",
            "setup_docs": "https://developers.google.com/identity/protocols/oauth2",
        },
        "keycloak": {
            "name": "Keycloak",
            "issuer_url": "https://{keycloak-server}/auth/realms/{realm}",
            "auth_url": "https://{keycloak-server}/auth/realms/{realm}/protocol/openid-connect/auth",
            "token_url": "https://{keycloak-server}/auth/realms/{realm}/protocol/openid-connect/token",
            "jwks_uri": "https://{keycloak-server}/auth/realms/{realm}/protocol/openid-connect/certs",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "KEYCLOAK_CLIENT_ID",
            "client_secret_env": "KEYCLOAK_CLIENT_SECRET",
            "keycloak_server_env": "KEYCLOAK_SERVER_URL",
            "keycloak_realm_env": "KEYCLOAK_REALM",
            "setup_docs": "https://www.keycloak.org/docs/latest/securing_apps/#_oidc",
        },
        "okta": {
            "name": "Okta",
            "issuer_url": "https://{okta-domain}/oauth2/default",
            "auth_url": "https://{okta-domain}/oauth2/default/v1/authorize",
            "token_url": "https://{okta-domain}/oauth2/default/v1/token",
            "jwks_uri": "https://{okta-domain}/oauth2/default/v1/keys",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "OKTA_CLIENT_ID",
            "client_secret_env": "OKTA_CLIENT_SECRET",
            "okta_domain_env": "OKTA_DOMAIN",
            "setup_docs": "https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/",
        },
        "github": {
            "name": "GitHub OAuth",
            "issuer_url": "https://api.github.com",
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "api_url": "https://api.github.com/user",
            "scopes": ["read:user", "user:email", "read:org"],
            "client_id_env": "GITHUB_CLIENT_ID",
            "client_secret_env": "GITHUB_CLIENT_SECRET",
            "github_org_env": "GITHUB_ORG",
            "setup_docs": "https://docs.github.com/en/developers/apps/building-oauth-apps/creating-an-oauth-app",
            "token_validation": {
                "type": "api_based",
                "required_env": ["GITHUB_CLIENT_ID"],
                "validation_endpoint": "https://api.github.com/user",
                "scope_mapping": {
                    "read:user": "read",
                    "user:email": "read",
                    "repo": "write",
                    "admin:org": "admin",
                },
            },
        },
    }


def get_fastmcp_config(server_name: str):
    """Get FastMCP configuration with optional OAuth authentication and MCP 2025-06-18 compliance."""
    config = {
        "name": server_name,
        # Note: MCP 2025-06-18 compliance is handled at the application level,
        # not through FastMCP configuration parameters
    }

    if ENABLE_AUTH and oauth_provider:
        config["auth"] = oauth_provider
        logger.info("FastMCP configured with Bearer token authentication (MCP 2025-06-18 compliant)")
    else:
        logger.info("FastMCP configured without authentication (MCP 2025-06-18 compliant)")

    # Log the compliance information for clarity
    logger.info("🚫 JSON-RPC batching disabled per MCP 2025-06-18 specification (application-level)")
    logger.info("💡 Application-level batch operations (clear_context_batch, etc.) remain available")

    return config


# Export main components
__all__ = [
    "ENABLE_AUTH",
    "AUTH_ISSUER_URL",
    "AUTH_VALID_SCOPES",
    "AUTH_DEFAULT_SCOPES",
    "AUTH_REQUIRED_SCOPES",
    "AUTH_CLIENT_REG_ENABLED",
    "AUTH_REVOCATION_ENABLED",
    "AUTH_PROVIDER",
    "AUTH_AUDIENCE",
    "AUTH_AZURE_TENANT_ID",
    "AUTH_KEYCLOAK_REALM",
    "AUTH_OKTA_DOMAIN",
    "AUTH_GITHUB_CLIENT_ID",
    "AUTH_GITHUB_ORG",
    "JWT_AVAILABLE",
    "SCOPE_DEFINITIONS",
    "oauth_provider",
    "require_scopes",
    "get_oauth_scopes_info",
    "get_oauth_provider_configs",
    "get_fastmcp_config",
]
