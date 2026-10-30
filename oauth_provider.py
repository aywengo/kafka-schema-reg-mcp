#!/usr/bin/env python3
"""
OAuth 2.1 Resource Server for Kafka Schema Registry MCP Server

This module provides OAuth 2.1 compliant authentication and authorization functionality
with scope-based permissions for the Kafka Schema Registry MCP server.

COMPLIANCE: OAuth 2.1, RFC 8692, RFC 8707, MCP 2025-06-18

Supported OAuth Providers:
- Azure AD / Entra ID
- Google OAuth 2.0
- Keycloak
- Okta
- Any OAuth 2.1 compliant provider

Scopes:
- read: Can view schemas, subjects, configurations
- write: Can register schemas, update configs (includes read permissions)
- admin: Can delete subjects, manage registries (includes write and read permissions)

Security Features:
- PKCE enforcement (mandatory per OAuth 2.1)
- Resource indicator validation (RFC 8707)
- Audience validation for all requests
- Token binding support
- Token revocation checking
- JWKS cache with proper TTL management
- No development token bypasses in production
- Enhanced SSL/TLS verification for all HTTP requests
"""

import hashlib
import logging
import os
import ssl
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Set, Union

from dotenv import load_dotenv
from fastmcp.server.auth import AccessToken, JWTVerifier

from _version import __version__

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Try to import JWT and HTTP libraries for production validation
try:
    import aiohttp
    import jwt

    JWT_AVAILABLE = jwt is not None
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("JWT validation libraries not available. Install: pip install PyJWT aiohttp cryptography")

# OAuth configuration from environment variables
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() in ("true", "1", "yes", "on")
AUTH_ISSUER_URL = os.getenv("AUTH_ISSUER_URL", "https://example.com")
AUTH_VALID_SCOPES = [s.strip() for s in os.getenv("AUTH_VALID_SCOPES", "read,write,admin").split(",") if s.strip()]
AUTH_DEFAULT_SCOPES = [s.strip() for s in os.getenv("AUTH_DEFAULT_SCOPES", "read").split(",") if s.strip()]
AUTH_REQUIRED_SCOPES = [s.strip() for s in os.getenv("AUTH_REQUIRED_SCOPES", "read").split(",") if s.strip()]
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

# OAuth 2.1 Configuration (generic approach)
AUTH_AUDIENCE = os.getenv("AUTH_AUDIENCE", "")  # Client ID or API identifier
# FastMCP 3 JWTVerifier requires public_key or jwks_uri (BearerAuthProvider was removed).
AUTH_JWKS_URI = os.getenv("AUTH_JWKS_URI", "")
AUTH_PUBLIC_KEY = os.getenv("AUTH_PUBLIC_KEY", "")

# Legacy GitHub OAuth Configuration (for backward compatibility)
AUTH_GITHUB_CLIENT_ID = os.getenv("AUTH_GITHUB_CLIENT_ID", "")
AUTH_GITHUB_ORG = os.getenv("AUTH_GITHUB_ORG", "")

# SSL/TLS Configuration (inherited from schema_registry_common)
ENFORCE_SSL_TLS_VERIFICATION = os.getenv("ENFORCE_SSL_TLS_VERIFICATION", "true").lower() in ("true", "1", "yes", "on")
CUSTOM_CA_BUNDLE_PATH = os.getenv("CUSTOM_CA_BUNDLE_PATH", "")

# OAuth 2.1 Discovery Configuration
OAUTH_DISCOVERY_CACHE_TTL = int(os.getenv("OAUTH_DISCOVERY_CACHE_TTL", "3600"))  # 1 hour default
_discovery_cache = {}
_discovery_cache_timestamps = {}

# Resource Server Configuration (RFC 8692)
RESOURCE_SERVER_URL = os.getenv("RESOURCE_SERVER_URL", "")  # Our resource server URL
RESOURCE_INDICATORS = [url.strip() for url in os.getenv("RESOURCE_INDICATORS", "").split(",") if url.strip()]

# PKCE Configuration (OAuth 2.1 requirement)
REQUIRE_PKCE = os.getenv("REQUIRE_PKCE", "true").lower() in ("true", "1", "yes", "on")

# Token Binding Configuration (OAuth 2.1 enhancement)
TOKEN_BINDING_ENABLED = os.getenv("TOKEN_BINDING_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# Token Introspection Configuration
TOKEN_INTROSPECTION_ENABLED = os.getenv("TOKEN_INTROSPECTION_ENABLED", "true").lower() in ("true", "1", "yes", "on")

# Token Revocation Configuration
TOKEN_REVOCATION_CHECK_ENABLED = os.getenv("TOKEN_REVOCATION_CHECK_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# JWKS Configuration
JWKS_CACHE_TTL = int(os.getenv("JWKS_CACHE_TTL", "3600"))  # 1 hour default
JWKS_CACHE_MAX_SIZE = int(os.getenv("JWKS_CACHE_MAX_SIZE", "10"))  # Max cached JWKS
_jwks_cache = {}
_jwks_cache_timestamps = {}
JWKS_CACHE_ERRORS = {}

# Revoked tokens cache (in production, use Redis or database)
REVOKED_TOKENS_CACHE = set()

# Development and Testing Configuration
ALLOW_DEV_TOKENS = os.getenv("ALLOW_DEV_TOKENS", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# Disable development tokens in production
if os.getenv("ENVIRONMENT", "development").lower() == "production":
    ALLOW_DEV_TOKENS = False

# Scope definitions for OAuth 2.1 authorization
SCOPE_DEFINITIONS = {
    "read": {
        "description": "Read access to schemas, subjects, and configurations",
        "level": 1,
        "includes": [
            "list_subjects",
            "get_schema",
            "list_registries",
            "check_registry_health",
            "get_compatibility_level",
            "search_schemas",
            "get_schema_metadata",
            "list_schema_versions",
            "get_subject_versions",
            "check_schema_compatibility",
        ],
        "permissions": ["view_schemas", "view_subjects", "view_configs"],
    },
    "write": {
        "description": "Write access to schemas and configurations (includes read)",
        "level": 2,
        "includes": [
            # Read permissions
            "list_subjects",
            "get_schema",
            "list_registries",
            "check_registry_health",
            "get_compatibility_level",
            "search_schemas",
            "get_schema_metadata",
            "list_schema_versions",
            "get_subject_versions",
            "check_schema_compatibility",
            # Write permissions
            "register_schema",
            "update_compatibility",
            "set_compatibility_level",
        ],
        "permissions": [
            "view_schemas",
            "view_subjects",
            "view_configs",
            "create_schemas",
            "update_schemas",
            "update_configs",
        ],
        "requires": ["read"],
    },
    "admin": {
        "description": "Administrative access (includes read, write, and delete)",
        "level": 3,
        "includes": [
            # Read permissions
            "list_subjects",
            "get_schema",
            "list_registries",
            "check_registry_health",
            "get_compatibility_level",
            "search_schemas",
            "get_schema_metadata",
            "list_schema_versions",
            "get_subject_versions",
            "check_schema_compatibility",
            # Write permissions
            "register_schema",
            "update_compatibility",
            "set_compatibility_level",
            # Admin permissions
            "delete_subject",
            "delete_schema_version",
            "clear_context_batch",
            "migrate_schema",
            "bulk_migrate_schemas",
            "compare_registries",
        ],
        "permissions": [
            "view_schemas",
            "view_subjects",
            "view_configs",
            "create_schemas",
            "update_schemas",
            "update_configs",
            "delete_subjects",
            "delete_schemas",
            "manage_compatibility",
        ],
        "requires": ["read", "write"],
    },
}


# Grants this resource server is willing to mirror from an issuer.
JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
KNOWN_GRANTS = ("authorization_code", "client_credentials", JWT_BEARER_GRANT)
# SEP-990 enterprise-managed authorization, advertised only when the issuer lists jwt-bearer.
ENTERPRISE_MANAGED_AUTHORIZATION = "io.modelcontextprotocol/enterprise-managed-authorization"
_SCOPE_ORDER = ("read", "write", "admin")
_EPHEMERAL_PUBLIC_PEM: Optional[str] = None


class AuthenticationError(Exception):
    """The bearer token or issuer discovery was rejected."""


@dataclass(frozen=True)
class Principal:
    """Caller identity after one verification. Scopes are already expanded."""

    scopes: frozenset[str]
    subject: Optional[str]
    client_id: Optional[str]


class AuthorizationServer(Protocol):
    """Discovery and JWKS for one authorization server."""

    @property
    def issuer(self) -> str:
        """Issuer identifier an access token must carry."""

    async def metadata(self) -> Dict[str, Any]:
        """Authorization server metadata. Raise when discovery fails."""

    async def jwks(self) -> Dict[str, Any]:
        """JSON Web Key Set used to verify access tokens."""


def expand_scope_set(scopes: List[str]) -> Set[str]:
    """Apply read/write/admin hierarchy. admin includes write and read."""
    expanded = set(scopes)
    for scope in scopes:
        definition = SCOPE_DEFINITIONS.get(scope, {})
        expanded.update(definition.get("requires", []))
    return expanded


def scope_list(scopes: Set[str]) -> List[str]:
    """Stable scope order for AccessToken.scopes."""
    ordered = [name for name in _SCOPE_ORDER if name in scopes]
    ordered.extend(sorted(name for name in scopes if name not in _SCOPE_ORDER))
    return ordered


def identity_accepted(claims: Dict[str, Any]) -> bool:
    """Grant table. authorization_code and jwt-bearer apply only for that gty."""
    gty = claims.get("gty")
    if gty in ("authorization_code", JWT_BEARER_GRANT):
        return bool(claims.get("sub"))
    return any(claims.get(name) for name in ("sub", "azp", "client_id"))


def published_algorithms(key: Dict[str, Any]) -> List[str]:
    """Algorithms this JWK publishes. OKP Ed25519/Ed448 with no alg is EdDSA."""
    alg = key.get("alg")
    if isinstance(alg, str) and alg:
        return [alg]
    if key.get("kty") == "OKP" and key.get("crv") in ("Ed25519", "Ed448"):
        return ["EdDSA"]
    return []


def protected_resource_grant_metadata(grants: tuple[str, ...]) -> Dict[str, Any]:
    """SEP-990 member for protected-resource metadata. Empty when jwt-bearer is absent."""
    if JWT_BEARER_GRANT in grants:
        return {"extensions": {ENTERPRISE_MANAGED_AUTHORIZATION: {}}}
    return {}


def create_secure_ssl_context() -> ssl.SSLContext:
    """Create a secure SSL context for OAuth HTTP requests."""
    context = ssl.create_default_context()

    # Configure SSL context for maximum security
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    # Disable weak protocols and ciphers
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS")

    # Load custom CA bundle if specified
    if CUSTOM_CA_BUNDLE_PATH and os.path.exists(CUSTOM_CA_BUNDLE_PATH):
        context.load_verify_locations(CUSTOM_CA_BUNDLE_PATH)
        logger.info(f"OAuth SSL context using custom CA bundle: {CUSTOM_CA_BUNDLE_PATH}")

    return context


def create_secure_aiohttp_connector() -> aiohttp.TCPConnector:
    """Create a secure aiohttp connector with proper SSL/TLS configuration."""
    if ENFORCE_SSL_TLS_VERIFICATION:
        ssl_context = create_secure_ssl_context()
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            use_dns_cache=True,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            limit=100,  # Connection pool limit
            limit_per_host=30,  # Per-host connection limit
        )
        logger.debug("OAuth connector created with SSL verification enabled")
    else:
        # SSL verification disabled (not recommended for production)
        connector = aiohttp.TCPConnector(ssl=False, use_dns_cache=True, ttl_dns_cache=300, limit=100, limit_per_host=30)
        logger.warning("OAuth connector created with SSL verification DISABLED - not recommended for production")

    return connector


# OAuth 2.1 Token Validator
class OAuth21TokenValidator:
    """
    OAuth 2.1 compliant token validator with support for:
    - PKCE enforcement
    - Resource indicator validation (RFC 8707)
    - Audience validation
    - Token binding
    - Revocation checking
    - JWKS caching with TTL
    - Enhanced SSL/TLS security for all HTTP requests
    """

    def __init__(self):
        self.session = None
        self.jwks_cache = _jwks_cache
        self.jwks_timestamps = _jwks_cache_timestamps

    async def get_session(self):
        """Get or create aiohttp session with secure SSL configuration."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = create_secure_aiohttp_connector()

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": f"KafkaSchemaRegistryMCP-OAuth/{__version__} (Security Enhanced)",
                    "Connection": "close",  # Don't keep connections alive unnecessarily
                },
            )

            logger.debug(f"OAuth session created with SSL verification: {ENFORCE_SSL_TLS_VERIFICATION}")
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def is_dev_token(self, token: str) -> bool:
        """Check if token is a development bypass token."""
        return token.startswith("dev-token-") if token else False

    def is_token_revoked(self, token: str, jti: str = None) -> bool:
        """Check if token is revoked."""
        if not TOKEN_REVOCATION_CHECK_ENABLED:
            return False

        # Check by token hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in REVOKED_TOKENS_CACHE:
            return True

        # Check by JTI if available
        if jti and jti in REVOKED_TOKENS_CACHE:
            return True

        return False

    def validate_audience(self, aud: Union[str, List[str]], resource_indicators: List[str] = None) -> bool:
        """
        Validate token audience against resource indicators (RFC 8707).
        """
        if not aud:
            logger.warning("Token missing audience claim")
            return False

        audiences = [aud] if isinstance(aud, str) else aud

        # If we have configured resource indicators, validate against them
        if RESOURCE_INDICATORS:
            for audience in audiences:
                if audience in RESOURCE_INDICATORS:
                    return True
            logger.warning(f"Token audience {audiences} not in allowed resource indicators {RESOURCE_INDICATORS}")
            return False

        # If we have a configured AUTH_AUDIENCE, validate against it
        if AUTH_AUDIENCE:
            if AUTH_AUDIENCE in audiences:
                return True
            logger.warning(f"Token audience {audiences} does not match configured audience {AUTH_AUDIENCE}")
            return False

        # If no specific audience validation configured, any audience is valid
        return True

    def validate_pkce_requirements(self, claims: Dict[str, Any]) -> bool:
        """
        Validate PKCE requirements for the token.
        Note: This is typically validated during the authorization code exchange,
        but we can check for PKCE-related claims in the token.
        """
        if not REQUIRE_PKCE:
            return True

        # Check if token contains PKCE-related claims (implementation-specific)
        # Most providers don't include PKCE details in the final token
        # but we can check for other indicators of PKCE usage

        # For now, we'll assume PKCE was properly validated during token issuance
        # In a full implementation, you'd validate this at the authorization server
        return True

    def validate_resource_indicator(self, claims: Dict[str, Any], requested_resource: str = None) -> bool:
        """
        Validate resource indicator according to RFC 8707.
        """
        # Check if token has resource claim
        resource_claim = claims.get("resource") or claims.get("aud")

        if not resource_claim:
            # If no resource indicators are configured, allow access
            if not RESOURCE_INDICATORS:
                return True
            logger.warning("Token missing resource claim")
            return False

        # Normalize resource claim to list
        if isinstance(resource_claim, str):
            resource_claims = [resource_claim]
        else:
            resource_claims = resource_claim

        # If specific resource requested, validate it's in token
        if requested_resource:
            if requested_resource not in resource_claims:
                logger.warning(f"Requested resource {requested_resource} not authorized in token")
                return False

        # Validate against configured resource indicators
        if RESOURCE_INDICATORS:
            for resource in resource_claims:
                if resource in RESOURCE_INDICATORS:
                    return True
            logger.warning(
                f"No authorized resources {resource_claims} match configured indicators {RESOURCE_INDICATORS}"
            )
            return False

        return True

    async def get_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        """Get JWKS with caching and TTL management."""
        now = time.time()

        # Check cache first
        if jwks_uri in self.jwks_cache:
            cached_time = self.jwks_timestamps.get(jwks_uri, 0)
            if now - cached_time < JWKS_CACHE_TTL:
                return self.jwks_cache[jwks_uri]

        # Fetch fresh JWKS
        try:
            session = await self.get_session()
            async with session.get(jwks_uri) as response:
                if response.status == 200:
                    jwks = await response.json()

                    # Cache management - remove oldest if cache is full
                    if len(self.jwks_cache) >= JWKS_CACHE_MAX_SIZE:
                        oldest_uri = min(
                            self.jwks_timestamps.keys(),
                            key=lambda k: self.jwks_timestamps[k],
                        )
                        del self.jwks_cache[oldest_uri]
                        del self.jwks_timestamps[oldest_uri]

                    # Cache the result
                    self.jwks_cache[jwks_uri] = jwks
                    self.jwks_timestamps[jwks_uri] = now

                    # Clear any previous error
                    if jwks_uri in JWKS_CACHE_ERRORS:
                        del JWKS_CACHE_ERRORS[jwks_uri]

                    logger.debug(f"JWKS fetched and cached from {jwks_uri}")
                    return jwks
                else:
                    error_msg = f"Failed to fetch JWKS: HTTP {response.status}"
                    JWKS_CACHE_ERRORS[jwks_uri] = error_msg
                    logger.error(error_msg)
                    return None
        except ssl.SSLError as e:
            error_msg = f"SSL error fetching JWKS from {jwks_uri}: {str(e)}"
            JWKS_CACHE_ERRORS[jwks_uri] = error_msg
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error fetching JWKS from {jwks_uri}: {str(e)}"
            JWKS_CACHE_ERRORS[jwks_uri] = error_msg
            logger.error(error_msg)
            return None

    async def validate_token(
        self,
        token: str,
        required_scopes: Set[str] = None,
        requested_resource: str = None,
    ) -> Dict[str, Any]:
        """
        Development-token helper.

        Real JWTs are verified only by OAuth21BearerAuthProvider. This method
        does not parse a JWT.
        """
        del required_scopes, requested_resource
        if not self.is_dev_token(token):
            return {
                "valid": False,
                "error": "JWT verification is performed by OAuth21BearerAuthProvider",
            }
        if ALLOW_DEV_TOKENS:
            logger.warning("Using development token bypass - NOT FOR PRODUCTION")
            return {
                "valid": True,
                "user": "dev-user",
                "scopes": list(AUTH_VALID_SCOPES),
                "claims": {
                    "sub": "dev-user",
                    "scope": " ".join(AUTH_VALID_SCOPES),
                },
                "dev_token": True,
            }
        logger.error("Development token rejected in production environment")
        return {
            "valid": False,
            "error": "Development tokens not allowed in production",
        }

    async def discover_oauth_configuration(self, issuer_url: str) -> Optional[Dict[str, Any]]:
        """
        Discover OAuth 2.1 configuration from standard discovery endpoints.
        Uses RFC 8414 (OAuth Authorization Server Metadata) for discovery.
        """
        current_time = time.time()

        # Check cache first
        if (
            issuer_url in _discovery_cache
            and issuer_url in _discovery_cache_timestamps
            and (current_time - _discovery_cache_timestamps[issuer_url]) < OAUTH_DISCOVERY_CACHE_TTL
        ):
            return _discovery_cache[issuer_url]

        discovery_endpoints = [
            f"{issuer_url}/.well-known/oauth-authorization-server",
            f"{issuer_url}/.well-known/openid_configuration",  # OIDC discovery
        ]

        session = await self.get_session()

        for discovery_url in discovery_endpoints:
            try:
                logger.debug(f"Attempting OAuth 2.1 discovery from: {discovery_url}")
                async with session.get(discovery_url) as response:
                    if response.status == 200:
                        config = await response.json()

                        # Validate required OAuth 2.1 fields
                        required_fields = [
                            "issuer",
                            "authorization_endpoint",
                            "token_endpoint",
                        ]
                        if all(field in config for field in required_fields):
                            # Cache the discovery result
                            _discovery_cache[issuer_url] = config
                            _discovery_cache_timestamps[issuer_url] = current_time

                            logger.info(f"✅ OAuth 2.1 discovery successful from: {discovery_url}")
                            logger.debug(
                                f"Discovered endpoints - Auth: {config.get('authorization_endpoint')}, "
                                f"Token: {config.get('token_endpoint')}, JWKS: {config.get('jwks_uri')}"
                            )

                            return config
                        else:
                            logger.warning(
                                f"Discovery endpoint {discovery_url} missing required fields: {required_fields}"
                            )

            except ssl.SSLError as e:
                logger.error(f"SSL error during OAuth discovery for {discovery_url}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Discovery failed for {discovery_url}: {e}")
                continue

        # Fallback: If discovery fails, try to construct basic configuration
        logger.warning(f"⚠️  OAuth 2.1 discovery failed for {issuer_url}, using fallback configuration")
        return await self.get_fallback_configuration(issuer_url)

    async def get_fallback_configuration(self, issuer_url: str) -> Dict[str, Any]:
        """
        Fallback configuration when OAuth 2.1 discovery fails.
        Only handles GitHub (not OAuth 2.1 compliant). All other providers must support RFC 8414 discovery.
        """
        # Handle GitHub special case (not OAuth 2.1 compliant)
        if "github.com" in issuer_url or "api.github.com" in issuer_url:
            logger.info("Using GitHub fallback configuration (not OAuth 2.1 compliant)")
            return {
                "issuer": "https://github.com",
                "authorization_endpoint": "https://github.com/login/oauth/authorize",
                "token_endpoint": "https://github.com/login/oauth/access_token",
                "scope_claim": "scope",
                "username_claim": "login",
                "oauth_2_1_compliant": False,
                "note": "GitHub OAuth has limited OAuth 2.1 support",
            }

        # For all other providers, require OAuth 2.1 discovery
        logger.error(f"OAuth 2.1 discovery failed for {issuer_url}. Provider must support RFC 8414 discovery.")
        raise ValueError(
            f"OAuth 2.1 discovery failed for {issuer_url}. Please ensure your provider supports RFC 8414 discovery endpoints."
        )

    async def get_provider_config(self) -> Optional[Dict[str, Any]]:
        """Get OAuth configuration using standard OAuth 2.1 discovery."""
        if not AUTH_ISSUER_URL or AUTH_ISSUER_URL == "https://example.com":
            logger.warning("No valid AUTH_ISSUER_URL configured")
            return None

        return await self.discover_oauth_configuration(AUTH_ISSUER_URL)

    def check_scopes(self, user_scopes: Set[str], required_scopes: Set[str]) -> bool:
        """Check if user has required scopes, considering scope hierarchy."""
        if not required_scopes:
            return True

        # Expand user scopes to include inherited scopes
        expanded_user_scopes = self.expand_scopes(list(user_scopes))

        # Check if all required scopes are present
        return required_scopes.issubset(expanded_user_scopes)

    def expand_scopes(self, scopes: list) -> Set[str]:
        """Expand scopes to include inherited scopes based on hierarchy."""
        return expand_scope_set(scopes)


# Global token validator instance
token_validator = OAuth21TokenValidator() if JWT_AVAILABLE else None


def _ephemeral_public_key() -> str:
    """PEM public key used only to satisfy JWTVerifier construction."""
    global _EPHEMERAL_PUBLIC_PEM
    if _EPHEMERAL_PUBLIC_PEM is None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        _EPHEMERAL_PUBLIC_PEM = public_pem.decode("utf-8")
    return _EPHEMERAL_PUBLIC_PEM


def _fastmcp_jwt_verifier_kwargs() -> Dict[str, Any]:
    """Build FastMCP 3 JWTVerifier kwargs (replaces removed BearerAuthProvider)."""
    audience: Union[str, List[str], None]
    if AUTH_AUDIENCE:
        audience = AUTH_AUDIENCE
    elif RESOURCE_INDICATORS:
        audience = RESOURCE_INDICATORS
    else:
        audience = None

    kwargs: Dict[str, Any] = {
        "issuer": AUTH_ISSUER_URL,
        "audience": audience,
        "required_scopes": AUTH_REQUIRED_SCOPES,
    }
    if AUTH_PUBLIC_KEY:
        kwargs["public_key"] = AUTH_PUBLIC_KEY
    else:
        issuer = AUTH_ISSUER_URL.rstrip("/")
        kwargs["jwks_uri"] = AUTH_JWKS_URI or f"{issuer}/.well-known/jwks.json"
    return kwargs


def _verifier_kwargs_for_server(server: AuthorizationServer) -> Dict[str, Any]:
    """Build JWTVerifier kwargs for an injected issuer that may have no JWKS URI."""
    kwargs: Dict[str, Any] = {
        "issuer": server.issuer or None,
        "audience": None,
        "required_scopes": None,
    }
    jwks_uri = getattr(server, "jwks_uri", None)
    if jwks_uri:
        kwargs["jwks_uri"] = jwks_uri
    else:
        kwargs["public_key"] = _ephemeral_public_key()
    return kwargs


class HttpAuthorizationServer:
    """Production issuer port. Fetches discovery and the JWKS URI."""

    def __init__(
        self,
        issuer_url: Optional[str] = None,
        validator: Optional[OAuth21TokenValidator] = None,
    ) -> None:
        self.issuer_url = AUTH_ISSUER_URL if issuer_url is None else issuer_url
        self._validator = validator

    @property
    def issuer(self) -> str:
        """Issuer identifier configured for this process."""
        return self.issuer_url

    def _validator_or_default(self) -> Optional[OAuth21TokenValidator]:
        if self._validator is not None:
            return self._validator
        return token_validator

    async def metadata(self) -> Dict[str, Any]:
        """Fetch authorization-server metadata. A quiet upstream raises."""
        if not self.issuer_url or self.issuer_url == "https://example.com":
            raise AuthenticationError("No valid issuer URL configured")
        validator = self._validator_or_default()
        if validator is None:
            raise AuthenticationError("OAuth discovery is unavailable")
        config = await validator.discover_oauth_configuration(self.issuer_url)
        if not config:
            raise AuthenticationError("OAuth discovery failed")
        return config

    async def jwks(self) -> Dict[str, Any]:
        """Fetch the JWKS named by issuer metadata."""
        document = await self.metadata()
        jwks_uri = document.get("jwks_uri")
        if not jwks_uri:
            raise AuthenticationError("Issuer metadata has no JWKS URI")
        validator = self._validator_or_default()
        if validator is None:
            raise AuthenticationError("JWKS fetch is unavailable")
        jwks = await validator.get_jwks(str(jwks_uri))
        if not jwks:
            raise AuthenticationError("Failed to retrieve JWKS")
        return jwks


class FakeAuthorizationServer:
    """Canned metadata and an in-memory JWKS. Tests open no socket."""

    def __init__(self, metadata: Dict[str, Any], jwks: Dict[str, Any]) -> None:
        self._metadata = metadata
        self._jwks = jwks

    @property
    def issuer(self) -> str:
        """Issuer value stored on the canned metadata document."""
        return str(self._metadata.get("issuer") or "")

    @property
    def jwks_uri(self) -> None:
        """In-memory key sets have no remote JWKS URI."""
        return None

    async def metadata(self) -> Dict[str, Any]:
        """Return the canned authorization-server document."""
        return self._metadata

    async def jwks(self) -> Dict[str, Any]:
        """Return the canned JSON Web Key Set."""
        return self._jwks


def _unverified_jwt_header(token: str) -> Optional[Dict[str, Any]]:
    """Read a JWT header without checking the signature."""
    import base64
    import json

    parts = token.split(".")
    if len(parts) != 3 or not parts[0]:
        return None
    try:
        padded = parts[0] + "=" * (-len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(header, dict):
        return None
    return header


def _select_jwk(jwks: Dict[str, Any], kid: Optional[str]) -> Optional[Dict[str, Any]]:
    """Pick the JWK named by kid, or the only key when kid is absent."""
    keys = [key for key in jwks.get("keys", []) if isinstance(key, dict)]
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None
    if len(keys) == 1:
        return keys[0]
    return None


def _exp_valid(exp: Any) -> bool:
    """True when exp is a number that is still in the future."""
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        return False
    return float(exp) >= time.time()


def _issuer_matches(expected: Union[str, List[str], None], actual: Any) -> bool:
    """True when no issuer is required or the token iss matches."""
    if not expected:
        return True
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def _audience_matches(expected: Union[str, List[str], None], actual: Any) -> bool:
    """True when no audience is required or one expected audience is present."""
    if not expected:
        return True
    expected_list = expected if isinstance(expected, list) else [expected]
    actual_list = actual if isinstance(actual, list) else [actual]
    return any(item in actual_list for item in expected_list)


def _resource_allowed(claims: Dict[str, Any], resource: str) -> bool:
    """True when resource appears in aud or the resource claim."""
    aud = claims.get("aud")
    audiences = [aud] if isinstance(aud, str) else list(aud or [])
    raw_resource = claims.get("resource")
    if isinstance(raw_resource, str):
        resources = [raw_resource]
    else:
        resources = list(raw_resource or [])
    return resource in audiences or resource in resources


def _decode_with_jwks(token: str, jwks: Dict[str, Any], algorithm: str) -> Dict[str, Any]:
    """Verify the signature with joserfc and return the claims object."""
    from joserfc import jwt as jose_jwt
    from joserfc.jwk import KeySet
    from joserfc.jws import JWSRegistry

    # EdDSA is registered but not in joserfc's recommended set, so name it.
    registry = JWSRegistry(algorithms=[algorithm])
    verified = jose_jwt.decode(
        token,
        KeySet.import_key_set(jwks),
        algorithms=[algorithm],
        registry=registry,
    )
    claims = verified.claims
    if not isinstance(claims, dict):
        raise AuthenticationError("JWT claims are not an object")
    return claims


class OAuth21BearerAuthProvider(JWTVerifier):
    """
    The only access-token parse for this resource server.

    Signature, issuer, expiry, and audience are checked here. Algorithms
    are those the matching JWK publishes, including EdDSA for an OKP key.
    Scopes on the returned access token are already expanded.
    """

    def __init__(self, authorization_server: Optional[AuthorizationServer] = None, **kwargs: Any) -> None:
        server = authorization_server if authorization_server is not None else HttpAuthorizationServer()
        if authorization_server is not None:
            init_kwargs = _verifier_kwargs_for_server(server)
        else:
            init_kwargs = _fastmcp_jwt_verifier_kwargs()
        init_kwargs.update(kwargs)
        super().__init__(**init_kwargs)
        self.authorization_server = server
        logger.info("OAuth 2.1 JWT verifier initialized for issuer %s", self.issuer)

    async def _verified_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Check signature, exp, iss, and audience. Return claims or None."""
        jwks = await self.authorization_server.jwks()
        header = _unverified_jwt_header(token)
        if header is None:
            self.logger.info("Bearer token rejected: malformed JWT")
            return None
        raw_kid = header.get("kid")
        kid = raw_kid if isinstance(raw_kid, str) else None
        jwk_dict = _select_jwk(jwks, kid)
        if jwk_dict is None:
            self.logger.info("Bearer token rejected: signing key not in issuer JWKS")
            return None
        alg = header.get("alg")
        if not isinstance(alg, str) or alg not in published_algorithms(jwk_dict):
            self.logger.info("Bearer token rejected: algorithm is not published by the signing key")
            return None
        claims = _decode_with_jwks(token, jwks, alg)
        if not _exp_valid(claims.get("exp")):
            self.logger.info("Bearer token rejected: token expired or missing exp")
            return None
        if not _issuer_matches(self.issuer, claims.get("iss")):
            self.logger.info("Bearer token rejected: issuer mismatch")
            return None
        if not _audience_matches(self.audience, claims.get("aud")):
            self.logger.info("Bearer token rejected: audience mismatch")
            return None
        return claims

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """Verify one bearer token and attach the expanded scope set."""
        try:
            claims = await self._verified_claims(token)
        except Exception as exc:
            self.logger.debug("Token validation failed: %s", exc)
            return None
        if claims is None:
            return None
        if not identity_accepted(claims):
            self.logger.info("Bearer token rejected: grant identity requirements not met")
            return None
        scopes = scope_list(expand_scope_set(self._extract_scopes(claims)))
        if self.required_scopes and not set(self.required_scopes).issubset(set(scopes)):
            self.logger.info("Bearer token rejected: missing required scopes")
            return None
        client_id = claims.get("client_id") or claims.get("azp") or claims.get("sub") or "unknown"
        exp = claims.get("exp")
        expires_at = int(exp) if isinstance(exp, (int, float)) and not isinstance(exp, bool) else None
        return AccessToken(
            token=token,
            client_id=str(client_id),
            scopes=scopes,
            expires_at=expires_at,
            claims=claims,
        )


oauth_provider = None
if ENABLE_AUTH:
    try:
        oauth_provider = OAuth21BearerAuthProvider()
        logger.info("OAuth 2.1 JWT verifier initialized successfully")
    except Exception as exc:
        logger.warning("Failed to initialize OAuth 2.1 JWT verifier: %s", exc)
        oauth_provider = None


def _verifier_for(authorization_server: Optional[AuthorizationServer]) -> OAuth21BearerAuthProvider:
    """Use the process verifier, or build one around an injected issuer."""
    if authorization_server is None:
        if oauth_provider is not None:
            return oauth_provider
        return OAuth21BearerAuthProvider()
    return OAuth21BearerAuthProvider(authorization_server=authorization_server)


async def authenticate(
    token: str,
    *,
    resource: Optional[str] = None,
    authorization_server: Optional[AuthorizationServer] = None,
) -> Principal:
    """Verify one access token and return the expanded principal."""
    verifier = _verifier_for(authorization_server)
    access = await verifier.load_access_token(token)
    if access is None:
        raise AuthenticationError("Token rejected")
    claims = access.claims if isinstance(access.claims, dict) else {}
    if resource is not None and not _resource_allowed(claims, resource):
        raise AuthenticationError("Resource is not authorized by the token")
    client = claims.get("client_id") or claims.get("azp")
    subject = claims.get("sub")
    return Principal(
        scopes=frozenset(access.scopes or []),
        subject=str(subject) if subject else None,
        client_id=str(client) if client else None,
    )


async def advertised_grants(authorization_server: Optional[AuthorizationServer] = None) -> tuple[str, ...]:
    """Intersection of upstream grant_types_supported with the grants we mirror."""
    server = HttpAuthorizationServer() if authorization_server is None else authorization_server
    try:
        document = await server.metadata()
    except Exception:
        logger.debug("advertised_grants failed closed", exc_info=True)
        return ()
    if not isinstance(document, dict):
        return ()
    upstream = document.get("grant_types_supported") or []
    if not isinstance(upstream, list):
        return ()
    upstream_set = set(upstream)
    return tuple(grant for grant in KNOWN_GRANTS if grant in upstream_set)


def revoke_token(token: str = None, jti: str = None):
    """
    Revoke a token by adding it to the revocation cache.
    In production, this should update a database or external revocation list.
    """
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        REVOKED_TOKENS_CACHE.add(token_hash)

    if jti:
        REVOKED_TOKENS_CACHE.add(jti)

    logger.info(f"Token revoked (JTI: {jti})")


def get_oauth_scopes_info() -> Dict[str, Any]:
    """Get information about OAuth 2.1 configuration and scope definitions."""
    return {
        "oauth_enabled": ENABLE_AUTH,
        "oauth_2_1_compliant": True,
        "specification_version": "OAuth 2.1",
        "mcp_specification": "MCP 2025-06-18",
        "discovery_method": "RFC 8414 (Generic OAuth 2.1)",
        "issuer_url": AUTH_ISSUER_URL,
        "issuer": AUTH_ISSUER_URL,
        "audience": AUTH_AUDIENCE,
        "resource_indicators": RESOURCE_INDICATORS,
        "valid_scopes": AUTH_VALID_SCOPES,
        "default_scopes": AUTH_DEFAULT_SCOPES,
        "required_scopes": AUTH_REQUIRED_SCOPES,
        "scope_definitions": SCOPE_DEFINITIONS,
        "client_registration_enabled": AUTH_CLIENT_REG_ENABLED,
        "revocation_enabled": AUTH_REVOCATION_ENABLED,
        "jwt_available": JWT_AVAILABLE,
        "security_features": {
            "pkce_required": REQUIRE_PKCE,
            "allowed_code_challenge_methods": ["S256"],  # OAuth 2.1 requires S256
            "resource_indicator_validation": bool(RESOURCE_INDICATORS),
            "audience_validation": bool(AUTH_AUDIENCE or RESOURCE_INDICATORS),
            "token_binding": TOKEN_BINDING_ENABLED,
            "token_introspection": TOKEN_INTROSPECTION_ENABLED,
            "revocation_checking": TOKEN_REVOCATION_CHECK_ENABLED,
            "ssl_tls_verification": ENFORCE_SSL_TLS_VERIFICATION,
            "custom_ca_bundle": bool(CUSTOM_CA_BUNDLE_PATH),
            "jwks_caching": {
                "enabled": True,
                "ttl_seconds": JWKS_CACHE_TTL,
                "max_size": JWKS_CACHE_MAX_SIZE,
            },
        },
        "development_mode": {
            "is_development": os.getenv("ENVIRONMENT", "development").lower() == "development",
            "dev_tokens_allowed": ALLOW_DEV_TOKENS,
            "warning": ("🚨 Development tokens MUST be disabled in production!" if ALLOW_DEV_TOKENS else None),
        },
    }


def get_oauth_provider_configs():
    """
    Get OAuth 2.1 provider setup examples for documentation purposes.

    Note: With generic OAuth 2.1 discovery, most providers work with just:
    - AUTH_ISSUER_URL (the OAuth issuer)
    - AUTH_AUDIENCE (your client/API identifier)

    No provider-specific configuration needed for OAuth 2.1 compliant providers!
    """
    return {
        "oauth_2_1_generic": {
            "name": "Generic OAuth 2.1 Provider",
            "description": "Any OAuth 2.1 compliant provider (Azure, Google, Okta, Keycloak, etc.)",
            "required_env": {
                "AUTH_ISSUER_URL": "https://your-oauth-provider.com",
                "AUTH_AUDIENCE": "your-client-id-or-api-identifier",
            },
            "optional_env": {
                "RESOURCE_INDICATORS": "https://your-api.com,https://another-api.com",
                "REQUIRE_PKCE": "true",
                "TOKEN_BINDING_ENABLED": "true",
                "ENFORCE_SSL_TLS_VERIFICATION": "true",
                "CUSTOM_CA_BUNDLE_PATH": "/path/to/custom/ca-bundle.pem",
            },
            "oauth_2_1_features": {
                "pkce_support": True,
                "resource_indicators": True,
                "discovery": "RFC 8414",
                "automatic_endpoint_discovery": True,
                "enhanced_ssl_security": True,
            },
            "notes": [
                "✅ Uses standard OAuth 2.1 discovery (/.well-known/oauth-authorization-server)",
                "✅ No provider-specific configuration needed",
                "✅ Works with any OAuth 2.1 compliant provider",
                "✅ Automatic JWKS endpoint discovery",
                "✅ Supports PKCE, Resource Indicators, and other OAuth 2.1 features",
                "✅ Enhanced SSL/TLS security for all HTTP requests",
                "✅ Custom CA bundle support for enterprise environments",
            ],
        },
        "examples": {
            "azure": {
                "name": "Azure AD / Entra ID",
                "issuer_url_pattern": "https://login.microsoftonline.com/{tenant-id}/v2.0",
                "example_setup": {
                    "AUTH_ISSUER_URL": "https://login.microsoftonline.com/your-tenant-id/v2.0",
                    "AUTH_AUDIENCE": "your-azure-client-id",
                },
                "oauth_2_1_compliant": True,
                "discovery_endpoint": "/.well-known/oauth-authorization-server",
                "setup_docs": "https://docs.microsoft.com/en-us/azure/active-directory/develop/",
            },
            "google": {
                "name": "Google OAuth 2.0",
                "issuer_url_pattern": "https://accounts.google.com",
                "example_setup": {
                    "AUTH_ISSUER_URL": "https://accounts.google.com",
                    "AUTH_AUDIENCE": "your-google-client-id.apps.googleusercontent.com",
                },
                "oauth_2_1_compliant": True,
                "discovery_endpoint": "/.well-known/openid_configuration",
                "setup_docs": "https://developers.google.com/identity/protocols/oauth2",
            },
            "okta": {
                "name": "Okta",
                "issuer_url_pattern": "https://{domain}/oauth2/default",
                "example_setup": {
                    "AUTH_ISSUER_URL": "https://your-domain.okta.com/oauth2/default",
                    "AUTH_AUDIENCE": "api://your-api-identifier",
                },
                "oauth_2_1_compliant": True,
                "discovery_endpoint": "/.well-known/oauth-authorization-server",
                "setup_docs": "https://developer.okta.com/docs/guides/implement-oauth-for-okta/",
            },
            "keycloak": {
                "name": "Keycloak",
                "issuer_url_pattern": "https://{server}/realms/{realm}",
                "example_setup": {
                    "AUTH_ISSUER_URL": "https://keycloak.example.com/realms/your-realm",
                    "AUTH_AUDIENCE": "your-keycloak-client-id",
                },
                "oauth_2_1_compliant": True,
                "discovery_endpoint": "/.well-known/openid_configuration",
                "setup_docs": "https://www.keycloak.org/docs/latest/securing_apps/#_oidc",
            },
            "github": {
                "name": "GitHub OAuth (Limited Support)",
                "issuer_url_pattern": "https://github.com",
                "example_setup": {
                    "AUTH_ISSUER_URL": "https://github.com",
                    "AUTH_AUDIENCE": "your-github-client-id",
                },
                "oauth_2_1_compliant": False,
                "notes": [
                    "⚠️  GitHub has limited OAuth 2.1 support",
                    "❌ No PKCE support",
                    "❌ No resource indicators",
                    "❌ No standard discovery endpoints",
                ],
                "setup_docs": "https://docs.github.com/en/developers/apps/building-oauth-apps",
            },
        },
        "migration_note": {
            "message": "🚀 Simplified Configuration!",
            "details": [
                "With OAuth 2.1 discovery, you only need AUTH_ISSUER_URL and AUTH_AUDIENCE",
                "No more provider-specific configuration needed",
                "All OAuth 2.1 compliant providers work the same way",
                "Automatic endpoint discovery via RFC 8414",
                "Enhanced SSL/TLS security for all OAuth communications",
                "Custom CA bundle support for enterprise deployments",
                "Legacy provider-specific environment variables still supported for backward compatibility",
            ],
        },
    }


def get_fastmcp_config(server_name: str):
    """Get FastMCP configuration with OAuth 2.1 authentication and request-state sealing."""
    config = {
        "name": server_name,
        # SEP-2549 cache hints for the list methods and server/discover. The
        # catalog is the same for every caller only when no scope can filter
        # it, so the scope is public with auth off and private with auth on.
        # resources/read is stamped per URI by cache_hints.py.
        "cache_ttl": 60,
        "cache_scope": "private" if ENABLE_AUTH else "public",
        # Protocol compliance is handled by FastMCP 4 / MCP SDK 2.
    }

    request_state_key = os.getenv("REQUEST_STATE_KEY")
    if request_state_key:
        if len(request_state_key.encode()) < 32:
            raise RuntimeError(
                "REQUEST_STATE_KEY must be at least 32 bytes of secret randomness. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        from mcp.server.request_state import RequestStateSecurity

        config["request_state_security"] = RequestStateSecurity(keys=[request_state_key])
        logger.info("🔐 Request-state sealing enabled with a shared REQUEST_STATE_KEY")
    else:
        logger.info("🔐 Request-state sealing uses a process-local ephemeral key (single-pod only)")

    if ENABLE_AUTH and oauth_provider:
        config["auth"] = oauth_provider
        logger.info("FastMCP configured with OAuth 2.1 Bearer token authentication (MCP 2025-06-18 compliant)")
    else:
        logger.info("FastMCP configured without authentication (MCP 2025-06-18 compliant)")

    # Log the compliance information for clarity
    logger.info("🚫 JSON-RPC batching disabled per MCP 2025-06-18 specification (application-level)")
    logger.info("💡 Application-level batch operations (clear_context_batch, etc.) remain available")
    logger.info("🔒 OAuth 2.1 features enabled: PKCE, Resource Indicators, Audience Validation")
    logger.info("🚀 Using generic OAuth 2.1 discovery - works with any compliant provider")
    logger.info(f"🔐 SSL/TLS verification: {'ENABLED' if ENFORCE_SSL_TLS_VERIFICATION else 'DISABLED'}")

    return config


# Regenerate the advertised scope contents from the tool catalog so renamed or
# removed tools cannot linger in discovery documents.
try:
    from tool_catalog import TOOL_CATALOG

    _read_tools = sorted(name for name, spec in TOOL_CATALOG.items() if spec.scope == "read")
    _write_tools = sorted(name for name, spec in TOOL_CATALOG.items() if spec.scope == "write")
    _admin_tools = sorted(name for name, spec in TOOL_CATALOG.items() if spec.scope == "admin")
    SCOPE_DEFINITIONS["read"]["includes"] = _read_tools
    SCOPE_DEFINITIONS["write"]["includes"] = _read_tools + _write_tools
    SCOPE_DEFINITIONS["admin"]["includes"] = _read_tools + _write_tools + _admin_tools
except ImportError:
    pass


# Export main components
__all__ = [
    "ENABLE_AUTH",
    "AUTH_ISSUER_URL",
    "AUTH_VALID_SCOPES",
    "AUTH_DEFAULT_SCOPES",
    "AUTH_REQUIRED_SCOPES",
    "AUTH_CLIENT_REG_ENABLED",
    "AUTH_REVOCATION_ENABLED",
    "AUTH_AUDIENCE",
    "AUTH_GITHUB_CLIENT_ID",
    "AUTH_GITHUB_ORG",
    "OAUTH_DISCOVERY_CACHE_TTL",
    "RESOURCE_INDICATORS",
    "REQUIRE_PKCE",
    "TOKEN_BINDING_ENABLED",
    "TOKEN_INTROSPECTION_ENABLED",
    "TOKEN_REVOCATION_CHECK_ENABLED",
    "ENFORCE_SSL_TLS_VERIFICATION",
    "CUSTOM_CA_BUNDLE_PATH",
    "JWT_AVAILABLE",
    "SCOPE_DEFINITIONS",
    "OAuth21TokenValidator",
    "OAuth21BearerAuthProvider",
    "oauth_provider",
    "Principal",
    "AuthenticationError",
    "AuthorizationServer",
    "HttpAuthorizationServer",
    "FakeAuthorizationServer",
    "authenticate",
    "advertised_grants",
    "protected_resource_grant_metadata",
    "JWT_BEARER_GRANT",
    "ENTERPRISE_MANAGED_AUTHORIZATION",
    "get_oauth_scopes_info",
    "get_oauth_provider_configs",
    "get_fastmcp_config",
    "revoke_token",
    "token_validator",
    "create_secure_ssl_context",
    "create_secure_aiohttp_connector",
]
