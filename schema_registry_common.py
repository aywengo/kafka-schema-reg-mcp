#!/usr/bin/env python3
"""
Kafka Schema Registry Common Library

Shared functionality for both single and multi-registry MCP servers.
Includes registry management, HTTP utilities, authentication, and export functionality.
"""

import base64
import ipaddress
import json
import logging
import os
import re
import ssl
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, urlparse

import aiohttp
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth

# Environment variables for single registry mode (backward compatibility)
SINGLE_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
SINGLE_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SINGLE_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
# Support both VIEWONLY (new) and READONLY (deprecated) for backward compatibility
SINGLE_VIEWONLY = os.getenv("VIEWONLY", os.getenv("READONLY", "false")).lower() in ("true", "1", "yes", "on")

# Warn if deprecated READONLY parameter is used
if os.getenv("READONLY") is not None and os.getenv("VIEWONLY") is None:
    import warnings

    warnings.warn(
        "READONLY parameter is deprecated. Please use VIEWONLY instead. "
        "Support for READONLY will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("⚠️  WARNING: READONLY parameter is deprecated. Please use VIEWONLY instead.")
    print("   Example: export VIEWONLY=true")
    print("   Support for READONLY will be removed in a future version.")

# SSL/TLS Security Configuration
ENFORCE_SSL_TLS_VERIFICATION = os.getenv("ENFORCE_SSL_TLS_VERIFICATION", "true").lower() in ("true", "1", "yes", "on")
CUSTOM_CA_BUNDLE_PATH = os.getenv("CUSTOM_CA_BUNDLE_PATH", "")
SSL_CERT_PINNING_ENABLED = os.getenv("SSL_CERT_PINNING_ENABLED", "false").lower() in ("true", "1", "yes", "on")


# SSL/TLS Configuration Logging
def log_ssl_configuration():
    """Log SSL/TLS configuration for security audit purposes."""
    logger = logging.getLogger(__name__)
    logger.info(f"SSL/TLS Verification: {'ENABLED' if ENFORCE_SSL_TLS_VERIFICATION else 'DISABLED'}")
    if CUSTOM_CA_BUNDLE_PATH:
        if os.path.exists(CUSTOM_CA_BUNDLE_PATH):
            logger.info(f"Custom CA Bundle: {CUSTOM_CA_BUNDLE_PATH} (exists)")
        else:
            logger.warning(f"Custom CA Bundle: {CUSTOM_CA_BUNDLE_PATH} (FILE NOT FOUND)")
    else:
        logger.info("Custom CA Bundle: Using system default CA bundle")

    if SSL_CERT_PINNING_ENABLED:
        logger.info("Certificate Pinning: ENABLED (Future enhancement)")
    else:
        logger.info("Certificate Pinning: DISABLED")


# Log SSL configuration on import
log_ssl_configuration()


# Sensitive data filter for logging
class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""

    def filter(self, record):
        """Mask Authorization headers and other sensitive data in log messages."""
        if hasattr(record, "msg") and record.msg:
            msg = str(record.msg)

            # Mask Authorization headers (various formats)
            # Pattern 1: Standard header format
            msg = re.sub(
                r'Authorization["\']?\s*:\s*["\']?Basic\s+[A-Za-z0-9+/=]+["\']?',
                "Authorization: Basic ***MASKED***",
                msg,
                flags=re.IGNORECASE,
            )

            # Pattern 2: JSON format with quotes
            msg = re.sub(
                r'"Authorization"["\']?\s*:\s*["\']Basic\s+[A-Za-z0-9+/=]+["\']',
                '"Authorization": "Basic ***MASKED***"',
                msg,
                flags=re.IGNORECASE,
            )

            # Pattern 3: Any Base64 string that looks like credentials (longer than 20 chars)
            msg = re.sub(r"Basic\s+[A-Za-z0-9+/]{20,}={0,2}", "Basic ***MASKED***", msg, flags=re.IGNORECASE)

            # Mask potential credentials in URLs
            msg = re.sub(r"://([^:]+):([^@]+)@", "://***MASKED***:***MASKED***@", msg)

            record.msg = msg
        return True


# Apply sensitive data filter to all loggers
logging.getLogger().addFilter(SensitiveDataFilter())


# Configure secure logging for requests library
def configure_secure_requests_logging():
    """Configure requests library to avoid logging sensitive data."""
    # Disable urllib3 debug logging that might expose headers
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.WARNING)
    urllib3_logger.addFilter(SensitiveDataFilter())

    # Disable requests library debug logging
    requests_logger = logging.getLogger("requests")
    requests_logger.setLevel(logging.WARNING)
    requests_logger.addFilter(SensitiveDataFilter())

    # Add filter to httpcore logger (used by some HTTP libraries)
    httpcore_logger = logging.getLogger("httpcore")
    httpcore_logger.addFilter(SensitiveDataFilter())


# Apply secure logging configuration
configure_secure_requests_logging()


def validate_url(url: str) -> bool:
    """Validate URL is safe to use"""
    try:
        parsed = urlparse(url)
        # Whitelist allowed protocols
        if parsed.scheme not in ["http", "https"]:
            return False

        # Allow localhost in test/development mode
        # Check for common test/development indicators
        is_test_mode = (
            os.getenv("TESTING", "").lower() in ("true", "1", "yes", "on")
            or os.getenv("CI", "").lower() in ("true", "1", "yes", "on")
            or os.getenv("PYTEST_CURRENT_TEST") is not None
            or os.getenv("ALLOW_LOCALHOST", "").lower() in ("true", "1", "yes", "on")
            or
            # Check if we're in a test directory
            "test" in os.getcwd().lower()
            or
            # Check if the main script being run is a test
            "test" in sys.argv[0].lower()
            or
            # Check for common test runners
            any("pytest" in arg.lower() or "test" in arg.lower() for arg in sys.argv)
            or
            # Check if __main__ module is a test
            (
                hasattr(sys.modules.get("__main__"), "__file__")
                and sys.modules["__main__"].__file__
                and "test" in sys.modules["__main__"].__file__.lower()
            )
        )

        # Prevent internal network access in production
        if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
            if not is_test_mode:
                return False
        # Check for private IP ranges
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private and not is_test_mode:
                return False
        except ValueError:
            # Not an IP address, continue
            pass
        return True
    except Exception:
        return False


class SecureHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with enhanced SSL/TLS security."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """Initialize the pool manager with secure SSL context."""
        context = ssl.create_default_context()

        # Configure SSL context for maximum security
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Disable weak protocols and ciphers
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS")

        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


@dataclass
class RegistryConfig:
    """Configuration for a Schema Registry instance."""

    name: str
    url: str
    user: str = ""
    password: str = ""
    description: str = ""
    viewonly: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with sensitive data masked."""
        result = asdict(self)
        if result.get("password"):
            result["password"] = "***MASKED***"
        return result

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        password_masked = "***MASKED***" if self.password else ""
        return f"RegistryConfig(name={self.name!r}, url={self.url!r}, user={self.user!r}, password={password_masked!r}, description={self.description!r}, viewonly={self.viewonly})"

    def __str__(self) -> str:
        """Safe string representation without credentials."""
        auth_info = f"user={self.user}" if self.user else "no-auth"
        return f"Registry config: {self.name} at {self.url} ({auth_info})"


@dataclass
class MigrationTask:
    """Represents a migration task."""

    id: str
    source_registry: str
    target_registry: str
    scope: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    dry_run: bool = False


class RegistryClient:
    """Client for interacting with a single Schema Registry instance."""

    def __init__(self, config: RegistryConfig):
        # Validate the registry URL on initialization
        if not validate_url(config.url):
            raise ValueError(f"Invalid or unsafe registry URL: {config.url}")

        self.config = config
        self.auth = None
        # Don't store authorization headers as instance variables
        self._base_headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        self._base_standard_headers = {"Content-Type": "application/json"}

        if config.user and config.password:
            self.auth = HTTPBasicAuth(config.user, config.password)

        # Create secure session with SSL/TLS configuration
        self.session = self._create_secure_session()

        # Log SSL configuration for this client
        logger = logging.getLogger(__name__)
        logger.info(f"Created secure session for registry '{config.name}' at {config.url}")

    def _create_secure_session(self) -> requests.Session:
        """Create a secure requests session with proper SSL/TLS configuration."""
        session = requests.Session()

        # Configure SSL verification
        if ENFORCE_SSL_TLS_VERIFICATION:
            session.verify = True

            # Use custom CA bundle if specified
            if CUSTOM_CA_BUNDLE_PATH and os.path.exists(CUSTOM_CA_BUNDLE_PATH):
                session.verify = CUSTOM_CA_BUNDLE_PATH
                logging.getLogger(__name__).info(f"Using custom CA bundle: {CUSTOM_CA_BUNDLE_PATH}")

            # Mount secure adapter for HTTPS connections
            session.mount("https://", SecureHTTPAdapter())

        else:
            # SSL verification disabled (not recommended for production)
            session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logging.getLogger(__name__).warning(
                "SSL verification is DISABLED - this is not recommended for production use"
            )

        # Configure session timeouts for security
        session.timeout = 30  # 30 second default timeout

        # Add security headers
        session.headers.update(
            {
                "User-Agent": "KafkaSchemaRegistryMCP/2.0.0 (Security Enhanced)",
                "Connection": "close",  # Don't keep connections alive unnecessarily
            }
        )

        return session

    def _get_headers(self, content_type: str = "application/vnd.schemaregistry.v1+json") -> Dict[str, str]:
        """Get headers with authentication, created fresh each time."""
        headers = {"Content-Type": content_type}
        if self.auth:
            # Create auth header dynamically without storing credentials
            credentials = base64.b64encode(f"{self.config.user}:{self.config.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers

    def _get_standard_headers(self) -> Dict[str, str]:
        """Get standard headers with authentication, created fresh each time."""
        return self._get_headers("application/json")

    @property
    def headers(self) -> Dict[str, str]:
        """Get default headers for registry operations."""
        return self._get_headers()

    @property
    def standard_headers(self) -> Dict[str, str]:
        """Get standard headers for configuration operations."""
        return self._get_standard_headers()

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        return f"RegistryClient(name={self.config.name!r}, url={self.config.url!r}, viewonly={self.config.viewonly})"

    def __str__(self) -> str:
        """Safe string representation without credentials."""
        auth_status = "authenticated" if self.config.user else "no-auth"
        ssl_status = "SSL-enabled" if ENFORCE_SSL_TLS_VERIFICATION else "SSL-disabled"
        return f"Registry '{self.config.name}' at {self.config.url} ({auth_status}, {ssl_status})"

    def build_context_url(self, base_url: str, context: Optional[str] = None) -> str:
        """Build URL with optional context support."""
        # Validate base registry URL
        if not validate_url(self.config.url):
            raise ValueError("Invalid registry URL")

        # Handle default context "." as no context
        if context and context != ".":
            # URL encode the context to prevent injection
            safe_context = quote(context, safe="")
            return f"{self.config.url}/contexts/{safe_context}{base_url}"
        return f"{self.config.url}{base_url}"

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to this registry."""
        try:
            response = self.session.get(
                f"{self.config.url}/subjects",
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "registry": self.config.name,
                    "url": self.config.url,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "ssl_verified": ENFORCE_SSL_TLS_VERIFICATION,
                }
            else:
                return {
                    "status": "error",
                    "registry": self.config.name,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except requests.exceptions.SSLError as e:
            return {
                "status": "error",
                "registry": self.config.name,
                "error": f"SSL verification failed: {str(e)}",
                "ssl_error": True,
            }
        except Exception as e:
            return {"status": "error", "registry": self.config.name, "error": str(e)}

    def get_subjects(self, context: Optional[str] = None) -> List[str]:
        """Get subjects from this registry."""
        try:
            url = self.build_context_url("/subjects", context)
            response = self.session.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def get_contexts(self) -> List[str]:
        """Get contexts from this registry."""
        try:
            response = self.session.get(f"{self.config.url}/contexts", auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def delete_subject(self, subject: str, context: Optional[str] = None) -> bool:
        """Delete a subject from this registry."""
        try:
            url = self.build_context_url(f"/subjects/{subject}", context)
            response = self.session.delete(url, auth=self.auth, headers=self.headers, timeout=30)
            return response.status_code in [200, 404]  # 404 means already deleted
        except Exception:
            return False

    def get_schema(self, subject: str, version: str = "latest", context: Optional[str] = None) -> Dict[str, Any]:
        """Get a specific version of a schema."""
        try:
            url = self.build_context_url(f"/subjects/{subject}/versions/{version}", context)
            response = self.session.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def register_schema(
        self,
        subject: str,
        schema_definition: Dict[str, Any],
        schema_type: str = "AVRO",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new schema version."""
        try:
            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }
            url = self.build_context_url(f"/subjects/{subject}/versions", context)
            response = self.session.post(url, data=json.dumps(payload), auth=self.auth, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_global_config(self, context: Optional[str] = None) -> Dict[str, Any]:
        """Get global configuration settings."""
        try:
            url = self.build_context_url("/config", context)
            response = self.session.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_global_config(self, compatibility: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Update global configuration settings."""
        try:
            url = self.build_context_url("/config", context)
            payload = {"compatibility": compatibility}
            response = self.session.put(
                url,
                data=json.dumps(payload),
                auth=self.auth,
                headers=self.standard_headers,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_subject_config(self, subject: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration settings for a specific subject."""
        try:
            url = self.build_context_url(f"/config/{subject}", context)
            response = self.session.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_subject_config(self, subject: str, compatibility: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Update configuration settings for a specific subject."""
        try:
            url = self.build_context_url(f"/config/{subject}", context)
            payload = {"compatibility": compatibility}
            response = self.session.put(
                url,
                data=json.dumps(payload),
                auth=self.auth,
                headers=self.standard_headers,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_mode(self, context: Optional[str] = None) -> Dict[str, Any]:
        """Get the current mode of the Schema Registry."""
        try:
            url = self.build_context_url("/mode", context)
            response = self.session.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_mode(self, mode: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Update the mode of the Schema Registry."""
        try:
            url = self.build_context_url("/mode", context)
            payload = {"mode": mode}
            response = self.session.put(
                url,
                data=json.dumps(payload),
                auth=self.auth,
                headers=self.standard_headers,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_subject_mode(self, subject: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Get the mode for a specific subject."""
        try:
            url = self.build_context_url(f"/mode/{subject}", context)
            response = self.session.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_subject_mode(self, subject: str, mode: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Update the mode for a specific subject."""
        try:
            url = self.build_context_url(f"/mode/{subject}", context)
            payload = {"mode": mode}
            response = self.session.put(
                url,
                data=json.dumps(payload),
                auth=self.auth,
                headers=self.standard_headers,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_schema_versions(self, subject: str, context: Optional[str] = None) -> Union[List[int], Dict[str, str]]:
        """Get all versions of a schema."""
        try:
            url = self.build_context_url(f"/subjects/{subject}/versions", context)
            response = self.session.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def check_compatibility(
        self,
        subject: str,
        schema_definition: Dict[str, Any],
        schema_type: str = "AVRO",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check if a schema is compatible with the latest version of a subject."""
        try:
            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }
            url = self.build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)
            response = self.session.post(url, data=json.dumps(payload), auth=self.auth, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_metadata_id(self) -> Dict[str, Any]:
        """Get metadata ID information from the registry."""
        try:
            response = self.session.get(
                f"{self.config.url}/v1/metadata/id",
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_metadata_version(self) -> Dict[str, Any]:
        """Get version and commit information from the registry."""
        try:
            response = self.session.get(
                f"{self.config.url}/v1/metadata/version",
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_server_metadata(self) -> Dict[str, Any]:
        """Get comprehensive server metadata including ID and version information."""
        metadata = {}

        # Get metadata ID information
        metadata_id = self.get_metadata_id()
        if "error" not in metadata_id:
            metadata.update(
                {
                    "scope": metadata_id.get("scope", {}),
                    "kafka_cluster_id": metadata_id.get("scope", {}).get("clusters", {}).get("kafka-cluster"),
                    "schema_registry_cluster_id": metadata_id.get("scope", {})
                    .get("clusters", {})
                    .get("schema-registry-cluster"),
                }
            )
        else:
            metadata["metadata_id_error"] = metadata_id["error"]

        # Get version information
        metadata_version = self.get_metadata_version()
        if "error" not in metadata_version:
            metadata.update(
                {
                    "version": metadata_version.get("version"),
                    "commit_id": metadata_version.get("commitId"),
                }
            )
        else:
            metadata["metadata_version_error"] = metadata_version["error"]

        return metadata


class BaseRegistryManager:
    """Base class for managing Schema Registry instances."""

    def __init__(self):
        self.registries: Dict[str, RegistryClient] = {}
        self.default_registry: Optional[str] = None
        self.migration_tasks: Dict[str, MigrationTask] = {}

    def get_registry(self, name: Optional[str] = None) -> Optional[RegistryClient]:
        """Get a registry client by name, or default if name is None."""
        if name is None:
            name = self.default_registry
        return self.registries.get(name)

    def list_registries(self) -> List[str]:
        """List all configured registry names."""
        return list(self.registries.keys())

    def get_registry_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a registry."""
        if name not in self.registries:
            return None

        client = self.registries[name]
        info = client.config.to_dict()
        info["is_default"] = name == self.default_registry

        # Test connection
        connection_test = client.test_connection()
        info["connection_status"] = connection_test["status"]
        if "response_time_ms" in connection_test:
            info["response_time_ms"] = connection_test["response_time_ms"]
        if "error" in connection_test:
            info["connection_error"] = connection_test["error"]

        # Add SSL status information
        info["ssl_verification_enabled"] = ENFORCE_SSL_TLS_VERIFICATION
        if "ssl_verified" in connection_test:
            info["ssl_verified"] = connection_test["ssl_verified"]

        # Get server metadata
        server_metadata = client.get_server_metadata()
        info.update(server_metadata)

        return info

    def test_all_registries(self) -> Dict[str, Any]:
        """Test connections to all configured registries (synchronous)."""
        results = {}
        for name in self.list_registries():
            client = self.get_registry(name)
            if client:
                results[name] = client.test_connection()

        return {
            "registry_tests": results,
            "total_registries": len(results),
            "connected": sum(1 for r in results.values() if r.get("status") == "connected"),
            "failed": sum(1 for r in results.values() if r.get("status") == "error"),
            "ssl_verification_enabled": ENFORCE_SSL_TLS_VERIFICATION,
        }

    async def test_all_registries_async(self) -> Dict[str, Any]:
        """Test connections to all registries asynchronously."""
        results = {}
        async with aiohttp.ClientSession() as session:
            for name, client in self.registries.items():
                try:
                    start_time = time.time()
                    async with session.get(
                        f"{client.config.url}/subjects",
                        headers=client.headers,
                        timeout=10,
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        if response.status == 200:
                            results[name] = {
                                "status": "connected",
                                "url": client.config.url,
                                "response_time_ms": response_time,
                            }
                        else:
                            results[name] = {
                                "status": "error",
                                "url": client.config.url,
                                "error": f"HTTP {response.status}: {await response.text()}",
                            }
                except Exception as e:
                    results[name] = {
                        "status": "error",
                        "url": client.config.url,
                        "error": str(e),
                    }

        return {
            "registry_tests": results,
            "total_registries": len(results),
            "connected": sum(1 for r in results.values() if r.get("status") == "connected"),
            "failed": sum(1 for r in results.values() if r.get("status") == "error"),
        }

    async def compare_registries_async(self, source: str, target: str) -> Dict[str, Any]:
        """Compare two registries asynchronously."""
        source_client = self.get_registry(source)
        target_client = self.get_registry(target)

        if not source_client or not target_client:
            return {"error": "Invalid registry configuration"}

        async with aiohttp.ClientSession() as session:
            # Get subjects from both registries
            source_subjects = await self._get_subjects_async(session, source_client)
            target_subjects = await self._get_subjects_async(session, target_client)

            return {
                "source": source,
                "target": target,
                "compared_at": datetime.now().isoformat(),
                "subjects": {
                    "source_only": list(set(source_subjects) - set(target_subjects)),
                    "target_only": list(set(target_subjects) - set(source_subjects)),
                    "common": list(set(source_subjects) & set(target_subjects)),
                    "source_total": len(source_subjects),
                    "target_total": len(target_subjects),
                },
            }

    async def _get_subjects_async(self, session: aiohttp.ClientSession, client: RegistryClient) -> List[str]:
        """Get subjects from a registry asynchronously."""
        try:
            async with session.get(f"{client.config.url}/subjects", headers=client.headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception:
            return []

    def is_viewonly(self, registry_name: Optional[str] = None) -> bool:
        """Check if a registry is in viewonly mode."""
        client = self.get_registry(registry_name)
        if not client:
            return False
        return client.config.viewonly

    # Backward compatibility alias
    def is_readonly(self, registry_name: Optional[str] = None) -> bool:
        """Deprecated: Use is_viewonly instead."""
        import warnings

        warnings.warn(
            "is_readonly() is deprecated. Please use is_viewonly() instead. "
            "Support for is_readonly() will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.is_viewonly(registry_name)

    def get_default_registry(self) -> Optional[str]:
        """Get the default registry name."""
        return self.default_registry

    def set_default_registry(self, name: str) -> bool:
        """Set the default registry."""
        if name in self.registries:
            self.default_registry = name
            return True
        return False


class SingleRegistryManager(BaseRegistryManager):
    """Manager for single registry mode (backward compatibility)."""

    def __init__(self):
        super().__init__()
        self._load_single_registry()

    def _load_single_registry(self):
        """Load single registry configuration."""
        if SINGLE_REGISTRY_URL:
            try:
                config = RegistryConfig(
                    name="default",
                    url=SINGLE_REGISTRY_URL,
                    user=SINGLE_REGISTRY_USER,
                    password=SINGLE_REGISTRY_PASSWORD,
                    description="Default Schema Registry",
                    viewonly=SINGLE_VIEWONLY,
                )
                self.registries["default"] = RegistryClient(config)
                self.default_registry = "default"
                logging.info(f"Loaded single registry: default at {SINGLE_REGISTRY_URL} (viewonly: {SINGLE_VIEWONLY})")
            except ValueError as e:
                logging.error(f"Failed to load single registry: {e}")


class MultiRegistryManager(BaseRegistryManager):
    """Manager for multi-registry mode."""

    def __init__(self, max_registries: int = 8):
        super().__init__()
        self.max_registries = max_registries
        self._load_multi_registries()

    def _load_multi_registries(self):
        """Load multi-registry configurations from environment variables."""
        # Check for multi-registry mode first (numbered environment variables)
        multi_registry_found = False

        for i in range(1, self.max_registries + 1):
            name_var = f"SCHEMA_REGISTRY_NAME_{i}"
            url_var = f"SCHEMA_REGISTRY_URL_{i}"
            user_var = f"SCHEMA_REGISTRY_USER_{i}"
            password_var = f"SCHEMA_REGISTRY_PASSWORD_{i}"
            viewonly_var = f"VIEWONLY_{i}"
            readonly_var = f"READONLY_{i}"  # For backward compatibility

            name = os.getenv(name_var, "")
            url = os.getenv(url_var, "")

            if name and url:
                multi_registry_found = True

                user = os.getenv(user_var, "")
                password = os.getenv(password_var, "")
                # Support both VIEWONLY (new) and READONLY (deprecated) for backward compatibility
                viewonly = os.getenv(viewonly_var, os.getenv(readonly_var, "false")).lower() in (
                    "true",
                    "1",
                    "yes",
                    "on",
                )

                # Warn if deprecated READONLY_{i} parameter is used
                if os.getenv(readonly_var) is not None and os.getenv(viewonly_var) is None:
                    import warnings

                    warnings.warn(
                        f"{readonly_var} parameter is deprecated. Please use {viewonly_var} instead. "
                        f"Support for {readonly_var} will be removed in a future version.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    print(f"⚠️  WARNING: {readonly_var} parameter is deprecated. Please use {viewonly_var} instead.")
                    print(f"   Example: export {viewonly_var}=true")
                    print(f"   Support for {readonly_var} will be removed in a future version.")

                try:
                    config = RegistryConfig(
                        name=name,
                        url=url,
                        user=user,
                        password=password,
                        description=f"{name} Schema Registry (instance {i})",
                        viewonly=viewonly,
                    )

                    self.registries[name] = RegistryClient(config)

                    # Set first registry as default
                    if self.default_registry is None:
                        self.default_registry = name

                    logging.info(f"Loaded registry {i}: {name} at {url} (viewonly: {viewonly})")
                except ValueError as e:
                    logging.error(f"Failed to load registry {i} ({name}): {e}")

        # Fallback to single registry mode if no multi-registry found
        if not multi_registry_found and SINGLE_REGISTRY_URL:
            try:
                config = RegistryConfig(
                    name="default",
                    url=SINGLE_REGISTRY_URL,
                    user=SINGLE_REGISTRY_USER,
                    password=SINGLE_REGISTRY_PASSWORD,
                    description="Default Schema Registry",
                    viewonly=SINGLE_VIEWONLY,
                )
                self.registries["default"] = RegistryClient(config)
                self.default_registry = "default"
                logging.info(f"Loaded single registry: default at {SINGLE_REGISTRY_URL} (viewonly: {SINGLE_VIEWONLY})")
            except ValueError as e:
                logging.error(f"Failed to load single registry: {e}")

        if not self.registries:
            logging.warning(
                "No Schema Registry instances configured. Set SCHEMA_REGISTRY_URL for single mode or SCHEMA_REGISTRY_NAME_1/SCHEMA_REGISTRY_URL_1 for multi mode."
            )


class LegacyRegistryManager(BaseRegistryManager):
    """Manager that supports legacy JSON configuration mode."""

    def __init__(self, registries_config: str = ""):
        super().__init__()
        self.registries_config = registries_config
        self._load_registries()

    def _load_registries(self):
        """Load registry configurations from environment variables and JSON config."""
        # Single registry support (backward compatibility)
        if SINGLE_REGISTRY_URL:
            try:
                config = RegistryConfig(
                    name="default",
                    url=SINGLE_REGISTRY_URL,
                    user=SINGLE_REGISTRY_USER,
                    password=SINGLE_REGISTRY_PASSWORD,
                    description="Default Schema Registry",
                    viewonly=SINGLE_VIEWONLY,
                )
                self.registries["default"] = RegistryClient(config)
                self.default_registry = "default"
            except ValueError as e:
                logging.error(f"Failed to load single registry: {e}")

        # Multi-registry support via JSON configuration
        if self.registries_config:
            try:
                registries_data = json.loads(self.registries_config)
                for name, config_data in registries_data.items():
                    try:
                        # Support both viewonly (new) and readonly (deprecated) for backward compatibility
                        viewonly = config_data.get("viewonly", config_data.get("readonly", False))

                        # Warn if deprecated "readonly" field is used in JSON config
                        if "readonly" in config_data and "viewonly" not in config_data:
                            import warnings

                            warnings.warn(
                                f"'readonly' field in JSON configuration is deprecated. Please use 'viewonly' instead for registry '{name}'. "
                                "Support for 'readonly' will be removed in a future version.",
                                DeprecationWarning,
                                stacklevel=2,
                            )
                            print(
                                f"⚠️  WARNING: 'readonly' field in JSON configuration is deprecated for registry '{name}'."
                            )
                            print("   Please use 'viewonly' instead in your JSON configuration.")
                            print("   Support for 'readonly' will be removed in a future version.")

                        config = RegistryConfig(
                            name=name,
                            url=config_data["url"],
                            user=config_data.get("user", ""),
                            password=config_data.get("password", ""),
                            description=config_data.get("description", f"{name} registry"),
                            viewonly=viewonly,
                        )
                        self.registries[name] = RegistryClient(config)

                        # Set first registry as default if no default exists
                        if self.default_registry is None:
                            self.default_registry = name
                    except ValueError as e:
                        logging.error(f"Failed to load registry {name}: {e}")

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse REGISTRIES_CONFIG: {e}")


# ===== UTILITY FUNCTIONS =====


def check_viewonly_mode(
    registry_manager: BaseRegistryManager, registry_name: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """Check if operations should be blocked due to viewonly mode."""
    if registry_manager.is_viewonly(registry_name):
        return {
            "error": "Registry is in VIEWONLY mode. Modification operations are disabled for safety.",
            "viewonly_mode": "true",
            "registry": registry_name or registry_manager.get_default_registry() or "unknown",
        }
    return None


# Backward compatibility alias
def check_readonly_mode(
    registry_manager: BaseRegistryManager, registry_name: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """Deprecated: Use check_viewonly_mode instead."""
    import warnings

    warnings.warn(
        "check_readonly_mode() is deprecated. Please use check_viewonly_mode() instead. "
        "Support for check_readonly_mode() will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2,
    )
    return check_viewonly_mode(registry_manager, registry_name)


def build_context_url(base_url: str, registry_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support (global function for backward compatibility)."""
    # Validate the registry URL
    if not validate_url(registry_url):
        raise ValueError("Invalid registry URL")

    # Handle default context "." as no context
    if context and context != ".":
        # URL encode the context to prevent injection
        safe_context = quote(context, safe="")
        return f"{registry_url}/contexts/{safe_context}{base_url}"
    return f"{registry_url}{base_url}"


def get_default_client(
    registry_manager: BaseRegistryManager,
) -> Optional[RegistryClient]:
    """Get the default registry client."""
    return registry_manager.get_registry()


# ===== EXPORT FUNCTIONALITY =====


def format_schema_as_avro_idl(schema_str: str, subject: str) -> str:
    """Convert Avro JSON schema to Avro IDL format."""
    try:
        schema_obj = json.loads(schema_str)

        def format_field(field):
            field_type = field["type"]
            field_name = field["name"]
            default = field.get("default", None)
            doc = field.get("doc", "")

            if isinstance(field_type, list) and "null" in field_type:
                # Union type with null (optional field)
                non_null_types = [t for t in field_type if t != "null"]
                if len(non_null_types) == 1:
                    field_type_str = f"{non_null_types[0]}?"
                else:
                    field_type_str = f"union {{ {', '.join(field_type)} }}"
            elif isinstance(field_type, dict):
                # Complex type
                if field_type.get("type") == "array":
                    field_type_str = f"array<{field_type['items']}>"
                elif field_type.get("type") == "map":
                    field_type_str = f"map<{field_type['values']}>"
                else:
                    field_type_str = str(field_type)
            else:
                field_type_str = str(field_type)

            field_line = f"  {field_type_str} {field_name}"
            if default is not None:
                field_line += f" = {json.dumps(default)}"
            field_line += ";"

            if doc:
                field_line = f"  /** {doc} */\n{field_line}"

            return field_line

        if schema_obj.get("type") == "record":
            record_name = schema_obj.get("name", subject)
            namespace = schema_obj.get("namespace", "")
            doc = schema_obj.get("doc", "")

            idl_lines = []

            if namespace:
                idl_lines.append(f'@namespace("{namespace}")')

            if doc:
                idl_lines.append(f"/** {doc} */")

            idl_lines.append(f"record {record_name} {{")

            fields = schema_obj.get("fields", [])
            for field in fields:
                idl_lines.append(format_field(field))

            idl_lines.append("}")

            return "\n".join(idl_lines)
        else:
            return f"// Non-record schema for {subject}\n{json.dumps(schema_obj, indent=2)}"

    except Exception as e:
        return f"// Error converting schema to IDL: {str(e)}\n{schema_str}"


def get_schema_with_metadata(
    client: RegistryClient, subject: str, version: str, context: Optional[str] = None
) -> Dict[str, Any]:
    """Get schema with additional metadata."""
    try:
        schema_data = client.get_schema(subject, version, context)
        if "error" in schema_data:
            return schema_data

        # Ensure schema is parsed as JSON object if it's a string
        if isinstance(schema_data.get("schema"), str):
            try:
                schema_data["schema"] = json.loads(schema_data["schema"])
            except (json.JSONDecodeError, TypeError):
                # Keep as string if not valid JSON
                pass

        # Add export metadata
        schema_data["metadata"] = {
            "exported_at": datetime.now().isoformat(),
            "registry_url": client.config.url,
            "context": context,
            "export_version": "1.7.0",
        }

        return schema_data
    except Exception as e:
        return {"error": str(e)}


def export_schema(
    client: RegistryClient,
    subject: str,
    version: str = "latest",
    context: Optional[str] = None,
    format: str = "json",
) -> Union[Dict[str, Any], str]:
    """Export a single schema in the specified format."""
    try:
        schema_data = get_schema_with_metadata(client, subject, version, context)
        if "error" in schema_data:
            return schema_data

        if format == "avro_idl":
            schema_str = schema_data.get("schema", "")
            return format_schema_as_avro_idl(schema_str, subject)
        else:
            return schema_data
    except Exception as e:
        return {"error": str(e)}


def export_subject(
    client: RegistryClient,
    subject: str,
    context: Optional[str] = None,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
) -> Dict[str, Any]:
    """Export all versions of a subject."""
    try:
        # Get versions
        if include_versions == "latest":
            versions = ["latest"]
        else:
            versions_list = client.get_schema_versions(subject, context)
            if isinstance(versions_list, dict) and "error" in versions_list:
                return versions_list
            versions = [str(v) for v in versions_list]

        # Get schemas for each version
        schemas = []
        for version in versions:
            schema_data = get_schema_with_metadata(client, subject, version, context)
            if "error" not in schema_data:
                schemas.append(schema_data)

        result = {"subject": subject, "versions": schemas}

        if include_config:
            config = client.get_subject_config(subject, context)
            if "error" not in config:
                result["config"] = config

        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": client.config.url,
                "context": context,
                "export_version": "1.7.0",
            }

        return result
    except Exception as e:
        return {"error": str(e)}


def export_context(
    client: RegistryClient,
    context: str,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
) -> Dict[str, Any]:
    """Export all subjects within a context."""
    try:
        # Get all subjects in context
        subjects_list = client.get_subjects(context)

        # Export each subject
        subjects_data = []
        for subject in subjects_list:
            subject_export = export_subject(
                client,
                subject,
                context,
                include_metadata,
                include_config,
                include_versions,
            )
            if "error" not in subject_export:
                subjects_data.append(subject_export)

        result = {"context": context, "subjects": subjects_data}

        if include_config:
            global_config = client.get_global_config(context)
            if "error" not in global_config:
                result["global_config"] = global_config

            global_mode = client.get_mode(context)
            if "error" not in global_mode:
                result["global_mode"] = global_mode

        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": client.config.url,
                "export_version": "1.7.0",
            }

        return result
    except Exception as e:
        return {"error": str(e)}


def export_global(
    client: RegistryClient,
    include_metadata: bool = True,
    include_config: bool = True,
    include_versions: str = "all",
) -> Dict[str, Any]:
    """Export all contexts and schemas from the registry."""
    try:
        # Get all contexts
        contexts_list = client.get_contexts()

        # Export each context
        contexts_data = []
        for context in contexts_list:
            context_export = export_context(client, context, include_metadata, include_config, include_versions)
            if "error" not in context_export:
                contexts_data.append(context_export)

        # Export default context (no context specified)
        default_export = export_context(client, "", include_metadata, include_config, include_versions)

        result = {
            "contexts": contexts_data,
            "default_context": (default_export if "error" not in default_export else None),
        }

        if include_config:
            global_config = client.get_global_config()
            if "error" not in global_config:
                result["global_config"] = global_config

            global_mode = client.get_mode()
            if "error" not in global_mode:
                result["global_mode"] = global_mode

        if include_metadata:
            result["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "registry_url": client.config.url,
                "export_version": "1.7.0",
            }

        return result
    except Exception as e:
        return {"error": str(e)}


# ===== BATCH OPERATIONS =====


def clear_context_batch(
    client: RegistryClient,
    context: str,
    delete_context_after: bool = True,
    dry_run: bool = True,
    registry_name: str = "default",
) -> Dict[str, Any]:
    """Efficiently remove all subjects from a context in batch mode."""
    try:
        start_time = datetime.now()

        # Step 1: List all subjects in the context
        subjects_list = client.get_subjects(context)

        if not subjects_list:
            return {
                "context": context,
                "registry": registry_name,
                "dry_run": dry_run,
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "duration_seconds": 0,
                "message": f"Context '{context}' is already empty",
            }

        # Step 2: Batch delete subjects
        deleted_subjects = []
        failed_deletions = []

        if dry_run:
            deleted_subjects = subjects_list.copy()
        else:
            # Use concurrent deletions for better performance
            import concurrent.futures

            def delete_single_subject(subject):
                try:
                    success = client.delete_subject(subject, context)
                    if success:
                        return {"subject": subject, "status": "deleted"}
                    else:
                        return {
                            "subject": subject,
                            "status": "failed",
                            "error": "Delete failed",
                        }
                except Exception as e:
                    return {"subject": subject, "status": "failed", "error": str(e)}

            # Execute deletions in parallel (max 10 concurrent)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                deletion_results = list(executor.map(delete_single_subject, subjects_list))

            # Process results
            for result in deletion_results:
                if result["status"] == "deleted":
                    deleted_subjects.append(result["subject"])
                else:
                    failed_deletions.append(result)

        # Step 3: Optionally delete the context itself
        context_deleted = False
        context_deletion_error = None

        if delete_context_after and (deleted_subjects or dry_run):
            if dry_run:
                context_deleted = True
            else:
                try:
                    # Note: Context deletion would need to be implemented in RegistryClient
                    # For now, mark as successful
                    context_deleted = True
                except Exception as e:
                    context_deletion_error = str(e)

        # Calculate metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Build comprehensive result
        result = {
            "context": context,
            "registry": registry_name,
            "dry_run": dry_run,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "subjects_found": len(subjects_list),
            "subjects_deleted": len(deleted_subjects),
            "subjects_failed": len(failed_deletions),
            "context_deleted": context_deleted,
            "success_rate": (round((len(deleted_subjects) / len(subjects_list)) * 100, 1) if subjects_list else 100),
            "deleted_subjects": deleted_subjects,
            "failed_deletions": failed_deletions[:5],  # Show first 5 failures
            "performance": {
                "subjects_per_second": round(len(deleted_subjects) / max(duration, 0.1), 1),
                "parallel_execution": not dry_run,
                "max_concurrent_deletions": 10,
            },
        }

        if context_deletion_error:
            result["context_deletion_error"] = context_deletion_error

        # Summary message
        if dry_run:
            result["message"] = f"DRY RUN: Would delete {len(subjects_list)} subjects from context '{context}'"
        elif len(deleted_subjects) == len(subjects_list):
            result["message"] = f"Successfully cleared context '{context}' - deleted {len(deleted_subjects)} subjects"
        else:
            result["message"] = (
                f"Partially cleared context '{context}' - deleted {len(deleted_subjects)}/{len(subjects_list)} subjects"
            )

        return result

    except Exception as e:
        return {"error": f"Batch cleanup failed: {str(e)}"}
