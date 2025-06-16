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
import inspect
import json
import logging
import os
import time
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
        from mcp.server.auth.provider import OAuthAuthorizationServerProvider
        from mcp.server.auth.settings import (
            AuthSettings,
            ClientRegistrationOptions,
            RevocationOptions,
        )

        class KafkaSchemaRegistryOAuthProvider(OAuthAuthorizationServerProvider):
            """
            OAuth Authorization Server Provider for Kafka Schema Registry MCP Server.

            Implements scope-based authorization with three levels:
            - read: Can view schemas, subjects, configurations
            - write: Can register schemas, update configs
            - admin: Can delete subjects, manage registries
            """

            def __init__(self):
                self.valid_scopes = set(AUTH_VALID_SCOPES)
                self.required_scopes = set(AUTH_REQUIRED_SCOPES)
                self.jwks_cache = {}
                self.jwks_cache_timestamps = {}
                logger.info(
                    f"OAuth Provider initialized with scopes: {self.valid_scopes}"
                )
                logger.info(f"JWT validation available: {JWT_AVAILABLE}")
                if JWT_AVAILABLE:
                    logger.info(
                        f"OAuth provider: {AUTH_PROVIDER}, Issuer: {AUTH_ISSUER_URL}"
                    )

            async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
                """
                Validate an access token and return user information with scopes.

                In a real implementation, this would:
                1. Verify token signature (JWT validation)
                2. Check token expiration
                3. Validate issuer
                4. Extract user info and scopes

                For now, this is a development stub that accepts any token
                with the format: "dev-token-{scopes}"
                """
                try:
                    # Development mode: accept tokens in format "dev-token-read,write,admin"
                    if token.startswith("dev-token-"):
                        scopes_str = token.replace("dev-token-", "")
                        scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]

                        # Validate scopes are known
                        invalid_scopes = set(scopes) - self.valid_scopes
                        if invalid_scopes:
                            logger.warning(f"Invalid scopes in token: {invalid_scopes}")
                            return None

                        return {
                            "sub": "dev-user",
                            "scopes": scopes,
                            "iss": AUTH_ISSUER_URL,
                            "exp": 9999999999,  # Far future for dev
                            "iat": 1640991600,
                        }

                    # Real JWT token validation for production
                    validated_payload = await self.validate_jwt_token(token)
                    if validated_payload:
                        return self.extract_scopes_from_jwt(validated_payload)
                    return None

                    logger.warning(f"Invalid token format: {token[:20]}...")
                    return None

                except Exception as e:
                    logger.error(f"Token validation error: {e}")
                    return None

            def extract_scopes_from_jwt(
                self, jwt_payload: Dict[str, Any]
            ) -> Dict[str, Any]:
                """
                Extract MCP scopes from different OAuth provider JWT token formats.

                Handles various ways providers include scopes:
                - Azure AD: 'roles' claim
                - Google: Custom attributes or group membership
                - Keycloak: 'scope' or 'realm_access.roles'
                - Okta: Custom claim or 'groups'
                """
                user_scopes = []

                # Method 1: Direct scope claim (space-separated string)
                if "scope" in jwt_payload:
                    scope_str = jwt_payload["scope"]
                    if isinstance(scope_str, str):
                        potential_scopes = scope_str.split()
                        user_scopes.extend(
                            [s for s in potential_scopes if s in self.valid_scopes]
                        )

                # Method 2: Scope array claim
                if "scp" in jwt_payload:
                    scp_array = jwt_payload["scp"]
                    if isinstance(scp_array, list):
                        user_scopes.extend(
                            [s for s in scp_array if s in self.valid_scopes]
                        )

                # Method 3: Azure AD roles
                if "roles" in jwt_payload:
                    roles = jwt_payload["roles"]
                    if isinstance(roles, list):
                        user_scopes.extend([r for r in roles if r in self.valid_scopes])

                # Method 4: Keycloak realm roles
                if (
                    "realm_access" in jwt_payload
                    and "roles" in jwt_payload["realm_access"]
                ):
                    realm_roles = jwt_payload["realm_access"]["roles"]
                    if isinstance(realm_roles, list):
                        # Map realm roles to MCP scopes
                        role_mapping = {
                            "mcp-reader": "read",
                            "mcp-writer": "write",
                            "mcp-admin": "admin",
                        }
                        for role in realm_roles:
                            if role in role_mapping:
                                user_scopes.append(role_mapping[role])

                # Method 5: Group-based scopes (Okta, Google)
                if "groups" in jwt_payload:
                    groups = jwt_payload["groups"]
                    if isinstance(groups, list):
                        group_mapping = {
                            "MCP-Readers": "read",
                            "MCP-Writers": "write",
                            "MCP-Admins": "admin",
                            "mcp-readers@company.com": "read",
                            "mcp-writers@company.com": "write",
                            "mcp-admins@company.com": "admin",
                        }
                        for group in groups:
                            if group in group_mapping:
                                user_scopes.append(group_mapping[group])

                # Method 6: Custom attributes (Google Workspace, Okta)
                if "mcp_scopes" in jwt_payload:
                    custom_scopes = jwt_payload["mcp_scopes"]
                    if isinstance(custom_scopes, list):
                        user_scopes.extend(
                            [s for s in custom_scopes if s in self.valid_scopes]
                        )
                    elif isinstance(custom_scopes, str):
                        user_scopes.extend(
                            [
                                s.strip()
                                for s in custom_scopes.split()
                                if s.strip() in self.valid_scopes
                            ]
                        )

                # Method 7: GitHub scopes mapping
                if (
                    "github_scopes" in jwt_payload
                    or "github_permissions" in jwt_payload
                ):
                    github_scopes = jwt_payload.get(
                        "github_scopes", jwt_payload.get("github_permissions", [])
                    )
                    if isinstance(github_scopes, list):
                        # Map GitHub scopes to MCP scopes
                        github_mapping = {
                            "read:user": "read",
                            "user:email": "read",
                            "read:org": "read",
                            "repo": "write",  # Repository access implies write capability
                            "admin:org": "admin",
                            "admin:repo_hook": "admin",
                        }
                        for github_scope in github_scopes:
                            if github_scope in github_mapping:
                                user_scopes.append(github_mapping[github_scope])
                    elif isinstance(github_scopes, str):
                        github_scopes_list = github_scopes.split(",")
                        github_mapping = {
                            "read:user": "read",
                            "user:email": "read",
                            "read:org": "read",
                            "repo": "write",
                            "admin:org": "admin",
                            "admin:repo_hook": "admin",
                        }
                        for github_scope in github_scopes_list:
                            scope = github_scope.strip()
                            if scope in github_mapping:
                                user_scopes.append(github_mapping[scope])

                # Remove duplicates and enforce hierarchy
                user_scopes = list(set(user_scopes))
                user_scopes = self.enforce_scope_hierarchy(user_scopes)

                # Return enhanced payload with normalized scopes
                enhanced_payload = jwt_payload.copy()
                enhanced_payload["scopes"] = user_scopes

                logger.info(
                    f"Extracted scopes for user {jwt_payload.get('sub', 'unknown')}: {user_scopes}"
                )
                return enhanced_payload

            def enforce_scope_hierarchy(self, scopes: list) -> list:
                """
                Enforce scope hierarchy rules:
                - admin includes write and read
                - write includes read
                """
                scope_set = set(scopes)

                if "admin" in scope_set:
                    scope_set.update(["write", "read"])
                elif "write" in scope_set:
                    scope_set.add("read")

                return list(scope_set)

            async def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
                """
                Validate JWT token using provider-specific validation.

                Supports Azure AD, Google, Keycloak, Okta, and GitHub with automatic provider detection.
                """
                if not JWT_AVAILABLE:
                    logger.warning("JWT validation libraries not available")
                    return None

                try:
                    # For GitHub, try API validation first as it's more common
                    if AUTH_PROVIDER == "github" or (
                        AUTH_PROVIDER == "auto"
                        and len(token) > 20
                        and token.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_"))
                    ):
                        github_result = await self.validate_github_token(token)
                        if github_result:
                            return github_result

                    # Try JWT validation for all providers including GitHub Apps
                    # Decode token without verification to get header and payload
                    unverified_header = jwt.get_unverified_header(token)
                    unverified_payload = jwt.decode(
                        token, options={"verify_signature": False}
                    )

                    # Detect provider if set to auto
                    provider = AUTH_PROVIDER
                    if provider == "auto":
                        provider = self.detect_provider_from_token(unverified_payload)
                        logger.info(f"Auto-detected provider: {provider}")

                    # For GitHub, try API validation if JWT fails
                    if provider == "github":
                        github_result = await self.validate_github_token(token)
                        if github_result:
                            return github_result

                    # Get provider-specific configuration
                    config = self.get_provider_config(provider)
                    if not config:
                        logger.error(f"No configuration found for provider: {provider}")
                        return None

                    # Skip JWKS validation for GitHub API tokens
                    if (
                        provider == "github"
                        and config.get("validation_type") == "hybrid"
                    ):
                        logger.info("GitHub API token validation already attempted")
                        return None

                    # Fetch JWKS and get public key
                    public_key = await self.get_public_key_from_jwks(
                        config["jwks_url"], unverified_header.get("kid")
                    )
                    if not public_key:
                        logger.error("Could not obtain public key for token validation")
                        return None

                    # Validate token with all checks
                    validated_payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=config["algorithms"],
                        issuer=config["issuer"],
                        audience=config.get("audience"),
                        options={
                            "verify_signature": True,
                            "verify_exp": True,
                            "verify_iat": True,
                            "verify_iss": True,
                            "verify_aud": config.get("audience") is not None,
                            "require": ["exp", "iat", "iss"],
                        },
                    )

                    logger.info(
                        f"JWT token validated successfully for user: {validated_payload.get('sub', 'unknown')}"
                    )
                    return validated_payload

                except jwt.ExpiredSignatureError:
                    logger.warning("JWT token has expired")
                    return None
                except jwt.InvalidTokenError as e:
                    logger.warning(f"Invalid JWT token: {e}")
                    return None
                except Exception as e:
                    logger.error(f"JWT validation error: {e}")
                    return None

            async def validate_github_token(
                self, token: str
            ) -> Optional[Dict[str, Any]]:
                """
                Validate GitHub access token by calling GitHub API.

                GitHub OAuth tokens are not JWTs but access tokens that need API validation.
                """
                try:
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    }

                    async with aiohttp.ClientSession() as session:
                        # Get user information
                        async with session.get(
                            "https://api.github.com/user", headers=headers, timeout=10
                        ) as response:
                            if response.status != 200:
                                logger.warning(
                                    f"GitHub API validation failed: HTTP {response.status}"
                                )
                                return None

                            user_data = await response.json()

                        # Get user's organization memberships if ORG is specified
                        user_orgs = []
                        if AUTH_GITHUB_ORG:
                            try:
                                async with session.get(
                                    "https://api.github.com/user/orgs",
                                    headers=headers,
                                    timeout=10,
                                ) as org_response:
                                    if org_response.status == 200:
                                        orgs_data = await org_response.json()
                                        user_orgs = [org["login"] for org in orgs_data]

                                        # Check if user is member of required organization
                                        if AUTH_GITHUB_ORG not in user_orgs:
                                            logger.warning(
                                                f"User {user_data.get('login')} is not a member of required organization: {AUTH_GITHUB_ORG}"
                                            )
                                            return None
                            except Exception as e:
                                logger.warning(
                                    f"Could not verify GitHub organization membership: {e}"
                                )

                        # Get user's scopes from the token
                        scopes = []
                        if "X-OAuth-Scopes" in response.headers:
                            scopes = [
                                s.strip()
                                for s in response.headers["X-OAuth-Scopes"].split(",")
                            ]

                    # Create JWT-like payload for consistency
                    github_payload = {
                        "iss": "https://api.github.com",
                        "sub": str(user_data["id"]),
                        "aud": AUTH_AUDIENCE or AUTH_GITHUB_CLIENT_ID,
                        "exp": int(time.time())
                        + 3600,  # GitHub tokens don't expire quickly
                        "iat": int(time.time()),
                        "login": user_data["login"],
                        "email": user_data.get("email"),
                        "name": user_data.get("name"),
                        "github_scopes": scopes,
                        "github_orgs": user_orgs,
                        "github_id": user_data["id"],
                        "url": user_data.get("html_url", ""),
                        "github_permissions": scopes,  # For scope extraction compatibility
                    }

                    logger.info(
                        f"GitHub token validated successfully for user: {user_data['login']}"
                    )
                    return github_payload

                except asyncio.TimeoutError:
                    logger.error("Timeout validating GitHub token")
                    return None
                except Exception as e:
                    logger.error(f"GitHub token validation error: {e}")
                    return None

            def detect_provider_from_token(self, payload: Dict[str, Any]) -> str:
                """Auto-detect OAuth provider from token payload."""
                issuer = payload.get("iss", "")

                if "login.microsoftonline.com" in issuer:
                    return "azure"
                elif "accounts.google.com" in issuer:
                    return "google"
                elif AUTH_OKTA_DOMAIN and AUTH_OKTA_DOMAIN in issuer:
                    return "okta"
                elif "keycloak" in issuer.lower() or AUTH_KEYCLOAK_REALM:
                    return "keycloak"
                elif "github.com" in issuer or "api.github.com" in issuer:
                    return "github"
                elif (
                    payload.get("login")
                    and payload.get("id")
                    and "github" in str(payload.get("url", "")).lower()
                ):
                    # GitHub access token response format detection
                    return "github"
                else:
                    logger.warning(
                        f"Could not auto-detect provider from issuer: {issuer}"
                    )
                    return "unknown"

            def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
                """Get provider-specific JWT validation configuration."""
                configs = {
                    "azure": {
                        "jwks_url": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/discovery/v2.0/keys",
                        "issuer": f"https://login.microsoftonline.com/{AUTH_AZURE_TENANT_ID}/v2.0",
                        "audience": AUTH_AUDIENCE,
                        "algorithms": ["RS256"],
                    },
                    "google": {
                        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
                        "issuer": "https://accounts.google.com",
                        "audience": AUTH_AUDIENCE,
                        "algorithms": ["RS256"],
                    },
                    "keycloak": {
                        "jwks_url": f"{AUTH_ISSUER_URL}/protocol/openid-connect/certs",
                        "issuer": AUTH_ISSUER_URL,
                        "audience": AUTH_AUDIENCE,
                        "algorithms": ["RS256"],
                    },
                    "okta": {
                        "jwks_url": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default/v1/keys",
                        "issuer": f"https://{AUTH_OKTA_DOMAIN}/oauth2/default",
                        "audience": AUTH_AUDIENCE,
                        "algorithms": ["RS256"],
                    },
                    "github": {
                        # GitHub supports both JWT (GitHub Apps) and access token validation
                        "jwks_url": f"https://api.github.com/app/installations/{AUTH_GITHUB_CLIENT_ID}/access_tokens",
                        "issuer": "https://api.github.com",
                        "audience": AUTH_AUDIENCE or AUTH_GITHUB_CLIENT_ID,
                        "algorithms": ["RS256"],
                        "validation_type": "hybrid",  # Supports both JWT and API validation
                        "api_validation_url": "https://api.github.com/user",
                    },
                }

                config = configs.get(provider)
                if not config:
                    return None

                # Validate required fields are present
                if provider == "azure" and not AUTH_AZURE_TENANT_ID:
                    logger.error("AZURE_TENANT_ID required for Azure AD validation")
                    return None
                elif provider == "okta" and not AUTH_OKTA_DOMAIN:
                    logger.error("OKTA_DOMAIN required for Okta validation")
                    return None
                elif provider == "keycloak" and not AUTH_ISSUER_URL:
                    logger.error("AUTH_ISSUER_URL required for Keycloak validation")
                    return None
                elif provider == "github" and not AUTH_GITHUB_CLIENT_ID:
                    logger.error("GITHUB_CLIENT_ID required for GitHub validation")
                    return None

                return config

            async def get_public_key_from_jwks(
                self, jwks_url: str, kid: str
            ) -> Optional[str]:
                """Fetch public key from JWKS endpoint with caching."""
                cache_key = f"{jwks_url}:{kid}"

                # Check cache first
                if cache_key in self.jwks_cache:
                    cache_time = self.jwks_cache_timestamps.get(cache_key, 0)
                    if time.time() - cache_time < JWKS_CACHE_TTL:
                        logger.debug("Using cached JWKS public key")
                        return self.jwks_cache[cache_key]

                try:
                    # Fetch JWKS
                    async with aiohttp.ClientSession() as session:
                        async with session.get(jwks_url, timeout=10) as response:
                            if response.status != 200:
                                logger.error(
                                    f"Failed to fetch JWKS: HTTP {response.status}"
                                )
                                return None

                            jwks_data = await response.json()

                    # Find the key with matching kid
                    for key_data in jwks_data.get("keys", []):
                        if key_data.get("kid") == kid and key_data.get("kty") == "RSA":
                            # Convert JWK to PEM format
                            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
                            pem_key = (
                                public_key.public_key()
                                .public_bytes(
                                    encoding=serialization.Encoding.PEM,
                                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                                )
                                .decode("utf-8")
                            )

                            # Cache the key
                            self.jwks_cache[cache_key] = pem_key
                            self.jwks_cache_timestamps[cache_key] = time.time()

                            logger.debug(
                                f"Successfully fetched and cached public key for kid: {kid}"
                            )
                            return pem_key

                    logger.error(f"Public key with kid '{kid}' not found in JWKS")
                    return None

                except asyncio.TimeoutError:
                    logger.error(f"Timeout fetching JWKS from {jwks_url}")
                    return None
                except Exception as e:
                    logger.error(f"Error fetching JWKS: {e}")
                    return None

            def check_scopes(
                self, user_scopes: Set[str], required_scopes: Set[str]
            ) -> bool:
                """Check if user has all required scopes."""
                return required_scopes.issubset(user_scopes)

            def has_read_access(self, user_scopes: Set[str]) -> bool:
                """Check if user has read access."""
                return "read" in user_scopes

            def has_write_access(self, user_scopes: Set[str]) -> bool:
                """Check if user has write access (implies read)."""
                return "write" in user_scopes and "read" in user_scopes

            def has_admin_access(self, user_scopes: Set[str]) -> bool:
                """Check if user has admin access (implies write and read)."""
                return (
                    "admin" in user_scopes
                    and "write" in user_scopes
                    and "read" in user_scopes
                )

        # Initialize OAuth provider
        oauth_provider = KafkaSchemaRegistryOAuthProvider()

        # Create OAuth settings
        oauth_settings = AuthSettings(
            issuer_url=AUTH_ISSUER_URL,
            revocation_options=RevocationOptions(enabled=AUTH_REVOCATION_ENABLED),
            client_registration_options=ClientRegistrationOptions(
                enabled=AUTH_CLIENT_REG_ENABLED,
                valid_scopes=AUTH_VALID_SCOPES,
                default_scopes=AUTH_DEFAULT_SCOPES,
            ),
            required_scopes=AUTH_REQUIRED_SCOPES,
        )

        # Scope validation decorator
        def require_scopes(*required_scopes: str):
            """Decorator to check if current user has required scopes."""

            def decorator(func):
                async def wrapper(*args, **kwargs):
                    # In a real MCP implementation, you'd get the current user context here
                    # For now, this is a placeholder that shows the pattern
                    #
                    # Example implementation:
                    # current_user = get_current_user_from_context()
                    # if not current_user:
                    #     return {"error": "Authentication required", "required_scopes": list(required_scopes)}
                    #
                    # user_scopes = set(current_user.get("scopes", []))
                    # if not oauth_provider.check_scopes(user_scopes, set(required_scopes)):
                    #     return {
                    #         "error": "Insufficient permissions",
                    #         "required_scopes": list(required_scopes),
                    #         "user_scopes": list(user_scopes)
                    #     }

                    return (
                        await func(*args, **kwargs)
                        if inspect.iscoroutinefunction(func)
                        else func(*args, **kwargs)
                    )

                return wrapper

            return decorator

    except ImportError:
        logger.warning(
            "MCP auth modules not available. OAuth functionality will be disabled."
        )
        oauth_provider = None
        oauth_settings = None

        def require_scopes(*required_scopes: str):
            def decorator(func):
                return func

            return decorator

else:
    # OAuth disabled
    oauth_provider = None
    oauth_settings = None

    # No-op decorator when auth is disabled
    def require_scopes(*required_scopes: str):
        def decorator(func):
            return func

        return decorator


def get_oauth_scopes_info() -> Dict[str, Any]:
    """
    Get information about OAuth scopes and permissions.

    Returns:
        Dictionary containing scope definitions, required permissions per tool, and test tokens
    """
    try:
        test_tokens = (
            {
                "read_only": "dev-token-read",
                "read_write": "dev-token-read,write",
                "full_admin": "dev-token-read,write,admin",
            }
            if ENABLE_AUTH
            else None
        )

        return {
            "oauth_enabled": ENABLE_AUTH,
            "issuer_url": AUTH_ISSUER_URL if ENABLE_AUTH else None,
            "valid_scopes": AUTH_VALID_SCOPES if ENABLE_AUTH else [],
            "default_scopes": AUTH_DEFAULT_SCOPES if ENABLE_AUTH else [],
            "required_scopes": AUTH_REQUIRED_SCOPES if ENABLE_AUTH else [],
            "scope_definitions": SCOPE_DEFINITIONS,
            "test_tokens": test_tokens,
            "usage_example": (
                {
                    "description": "To test with development tokens, use them in Authorization header",
                    "curl_example": "curl -H 'Authorization: Bearer dev-token-read,write' http://localhost:8000/api",
                    "note": "In production, replace with real JWT tokens from your OAuth provider",
                }
                if ENABLE_AUTH
                else None
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def get_oauth_provider_configs():
    """
    Get OAuth configuration examples for supported providers.

    Returns:
        Dictionary containing configuration examples for Azure, Google, Keycloak, and Okta
    """
    return {
        "azure": {
            "name": "Azure AD / Entra ID",
            "issuer_url": "https://login.microsoftonline.com/{tenant-id}/v2.0",
            "auth_url": "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token",
            "jwks_url": "https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys",
            "scopes": [
                "openid",
                "email",
                "profile",
                "https://graph.microsoft.com/User.Read",
            ],
            "client_id_env": "AZURE_CLIENT_ID",
            "client_secret_env": "AZURE_CLIENT_SECRET",
            "tenant_id_env": "AZURE_TENANT_ID",
            "jwt_validation": {
                "required_env": [
                    "AUTH_PROVIDER=azure",
                    "AZURE_TENANT_ID",
                    "AUTH_AUDIENCE",
                ],
                "algorithms": ["RS256"],
                "claims": {
                    "iss": "Issuer validation",
                    "aud": "Audience validation",
                    "exp": "Expiration check",
                },
            },
            "setup_docs": "https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app",
        },
        "google": {
            "name": "Google OAuth 2.0",
            "issuer_url": "https://accounts.google.com",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "GOOGLE_CLIENT_ID",
            "client_secret_env": "GOOGLE_CLIENT_SECRET",
            "jwt_validation": {
                "required_env": ["AUTH_PROVIDER=google", "AUTH_AUDIENCE"],
                "algorithms": ["RS256"],
                "claims": {
                    "iss": "https://accounts.google.com",
                    "aud": "Client ID",
                    "exp": "Expiration check",
                },
            },
            "setup_docs": "https://developers.google.com/identity/protocols/oauth2",
        },
        "keycloak": {
            "name": "Keycloak",
            "issuer_url": "https://{keycloak-server}/realms/{realm}",
            "auth_url": "https://{keycloak-server}/realms/{realm}/protocol/openid-connect/auth",
            "token_url": "https://{keycloak-server}/realms/{realm}/protocol/openid-connect/token",
            "jwks_url": "https://{keycloak-server}/realms/{realm}/protocol/openid-connect/certs",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "KEYCLOAK_CLIENT_ID",
            "client_secret_env": "KEYCLOAK_CLIENT_SECRET",
            "keycloak_server_env": "KEYCLOAK_SERVER_URL",
            "keycloak_realm_env": "KEYCLOAK_REALM",
            "jwt_validation": {
                "required_env": [
                    "AUTH_PROVIDER=keycloak",
                    "AUTH_ISSUER_URL",
                    "AUTH_AUDIENCE",
                ],
                "algorithms": ["RS256"],
                "claims": {
                    "iss": "Realm issuer URL",
                    "aud": "Client ID",
                    "exp": "Expiration check",
                },
            },
            "setup_docs": "https://www.keycloak.org/docs/latest/server_admin/#_clients",
        },
        "okta": {
            "name": "Okta",
            "issuer_url": "https://{okta-domain}/oauth2/default",
            "auth_url": "https://{okta-domain}/oauth2/default/v1/authorize",
            "token_url": "https://{okta-domain}/oauth2/default/v1/token",
            "jwks_url": "https://{okta-domain}/oauth2/default/v1/keys",
            "scopes": ["openid", "email", "profile"],
            "client_id_env": "OKTA_CLIENT_ID",
            "client_secret_env": "OKTA_CLIENT_SECRET",
            "okta_domain_env": "OKTA_DOMAIN",
            "jwt_validation": {
                "required_env": ["AUTH_PROVIDER=okta", "OKTA_DOMAIN", "AUTH_AUDIENCE"],
                "algorithms": ["RS256"],
                "claims": {
                    "iss": "Okta domain issuer",
                    "aud": "Client ID",
                    "exp": "Expiration check",
                },
            },
            "setup_docs": "https://developer.okta.com/docs/guides/implement-oauth-for-okta/",
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
            "organization_env": "GITHUB_ORG",
            "token_validation": {
                "type": "api_based",
                "required_env": ["AUTH_PROVIDER=github", "GITHUB_CLIENT_ID"],
                "optional_env": ["GITHUB_ORG"],
                "validation_endpoint": "https://api.github.com/user",
                "scope_mapping": {
                    "read:user": "read",
                    "user:email": "read",
                    "read:org": "read",
                    "repo": "write",
                    "admin:org": "admin",
                    "admin:repo_hook": "admin",
                },
            },
            "features": {
                "organization_restriction": "Restrict access to specific GitHub organization members",
                "scope_mapping": "Maps GitHub scopes to MCP permissions",
                "api_validation": "Uses GitHub API for token validation (not JWT)",
                "hybrid_support": "Supports both OAuth tokens and GitHub App JWT tokens",
            },
            "setup_docs": "https://docs.github.com/en/developers/apps/building-oauth-apps",
        },
    }


def get_fastmcp_config(server_name: str):
    """
    Get FastMCP configuration with or without OAuth based on ENABLE_AUTH setting.

    Args:
        server_name: Name of the MCP server

    Returns:
        Dictionary containing FastMCP initialization parameters
    """
    if ENABLE_AUTH and oauth_provider and oauth_settings:
        return {
            "name": server_name,
            "auth_server_provider": oauth_provider,
            "auth": oauth_settings,
        }
    else:
        return {"name": server_name}


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
    "oauth_settings",
    "require_scopes",
    "get_oauth_scopes_info",
    "get_oauth_provider_configs",
    "get_fastmcp_config",
]
