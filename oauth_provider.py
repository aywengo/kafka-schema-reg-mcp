#!/usr/bin/env python3
"""
OAuth Provider for Kafka Schema Registry MCP Server

This module provides OAuth 2.0 authentication and authorization functionality
with scope-based permissions for the Kafka Schema Registry MCP server.

Scopes:
- read: Can view schemas, subjects, configurations
- write: Can register schemas, update configs (includes read permissions)
- admin: Can delete subjects, manage registries (includes write and read permissions)
"""

import os
import json
import logging
import inspect
from typing import Optional, Dict, Any, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# OAuth configuration from environment variables
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() in ("true", "1", "yes", "on")
AUTH_ISSUER_URL = os.getenv("AUTH_ISSUER_URL", "https://example.com")
AUTH_VALID_SCOPES = [s.strip() for s in os.getenv("AUTH_VALID_SCOPES", "read,write,admin").split(",") if s.strip()]
AUTH_DEFAULT_SCOPES = [s.strip() for s in os.getenv("AUTH_DEFAULT_SCOPES", "read").split(",") if s.strip()]
AUTH_REQUIRED_SCOPES = [s.strip() for s in os.getenv("AUTH_REQUIRED_SCOPES", "read").split(",") if s.strip()]
AUTH_CLIENT_REG_ENABLED = os.getenv("AUTH_CLIENT_REG_ENABLED", "true").lower() in ("true", "1", "yes", "on")
AUTH_REVOCATION_ENABLED = os.getenv("AUTH_REVOCATION_ENABLED", "true").lower() in ("true", "1", "yes", "on")

# Scope definitions and hierarchy
SCOPE_DEFINITIONS = {
    "read": {
        "description": "Can view schemas, subjects, configurations",
        "includes": ["list_registries", "get_subjects", "get_schema", "get_global_config", "compare_registries"],
        "level": 1
    },
    "write": {
        "description": "Can register schemas, update configs (includes read permissions)",
        "includes": ["register_schema", "update_global_config", "update_subject_config", "update_mode"],
        "requires": ["read"],
        "level": 2
    },
    "admin": {
        "description": "Can delete subjects, manage registries (includes write and read permissions)",
        "includes": ["delete_subject", "clear_context_batch", "migrate_schema", "migrate_context"],
        "requires": ["write", "read"],
        "level": 3
    }
}

if ENABLE_AUTH:
    try:
        from mcp.server.auth.provider import OAuthAuthorizationServerProvider
        from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
        
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
                logger.info(f"OAuth Provider initialized with scopes: {self.valid_scopes}")
            
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
                            "iat": 1640991600
                        }
                    
                    # TODO: Implement real JWT token validation here
                    # Example with PyJWT:
                    # import jwt
                    # payload = jwt.decode(token, public_key, algorithms=['RS256'])
                    # return payload
                    
                    logger.warning(f"Invalid token format: {token[:20]}...")
                    return None
                    
                except Exception as e:
                    logger.error(f"Token validation error: {e}")
                    return None
            
            def check_scopes(self, user_scopes: Set[str], required_scopes: Set[str]) -> bool:
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
                return "admin" in user_scopes and "write" in user_scopes and "read" in user_scopes

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
                    
                    return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
                return wrapper
            return decorator

    except ImportError:
        logger.warning("MCP auth modules not available. OAuth functionality will be disabled.")
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
        test_tokens = {
            "read_only": "dev-token-read",
            "read_write": "dev-token-read,write", 
            "full_admin": "dev-token-read,write,admin"
        } if ENABLE_AUTH else None
        
        return {
            "oauth_enabled": ENABLE_AUTH,
            "issuer_url": AUTH_ISSUER_URL if ENABLE_AUTH else None,
            "valid_scopes": AUTH_VALID_SCOPES if ENABLE_AUTH else [],
            "default_scopes": AUTH_DEFAULT_SCOPES if ENABLE_AUTH else [],
            "required_scopes": AUTH_REQUIRED_SCOPES if ENABLE_AUTH else [],
            "scope_definitions": SCOPE_DEFINITIONS,
            "test_tokens": test_tokens,
            "usage_example": {
                "description": "To test with development tokens, use them in Authorization header",
                "curl_example": "curl -H 'Authorization: Bearer dev-token-read,write' http://localhost:8000/api",
                "note": "In production, replace with real JWT tokens from your OAuth provider"
            } if ENABLE_AUTH else None
        }
    except Exception as e:
        return {"error": str(e)}

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
            "auth": oauth_settings
        }
    else:
        return {
            "name": server_name
        }

# Export main components
__all__ = [
    "ENABLE_AUTH",
    "AUTH_ISSUER_URL", 
    "AUTH_VALID_SCOPES",
    "AUTH_DEFAULT_SCOPES",
    "AUTH_REQUIRED_SCOPES",
    "AUTH_CLIENT_REG_ENABLED",
    "AUTH_REVOCATION_ENABLED",
    "SCOPE_DEFINITIONS",
    "oauth_provider",
    "oauth_settings",
    "require_scopes",
    "get_oauth_scopes_info",
    "get_fastmcp_config"
] 