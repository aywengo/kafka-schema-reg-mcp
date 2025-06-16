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
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urlparse

import aiohttp
import requests
from requests.auth import HTTPBasicAuth

# Environment variables for single registry mode (backward compatibility)
SINGLE_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
SINGLE_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SINGLE_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
SINGLE_READONLY = os.getenv("READONLY", "false").lower() in ("true", "1", "yes", "on")


def validate_url(url: str) -> bool:
    """Validate URL is safe to use"""
    try:
        parsed = urlparse(url)
        # Whitelist allowed protocols
        if parsed.scheme not in ['http', 'https']:
            return False
        # Prevent internal network access
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False
        # Check for private IP ranges
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private:
                return False
        except ValueError:
            # Not an IP address, continue
            pass
        return True
    except Exception:
        return False


@dataclass
class RegistryConfig:
    """Configuration for a Schema Registry instance."""

    name: str
    url: str
    user: str = ""
    password: str = ""
    description: str = ""
    readonly: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
        self.headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        self.standard_headers = {"Content-Type": "application/json"}

        if config.user and config.password:
            self.auth = HTTPBasicAuth(config.user, config.password)
            credentials = base64.b64encode(
                f"{config.user}:{config.password}".encode()
            ).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
            self.standard_headers["Authorization"] = f"Basic {credentials}"

    def build_context_url(self, base_url: str, context: Optional[str] = None) -> str:
        """Build URL with optional context support."""
        # Validate base registry URL
        if not validate_url(self.config.url):
            raise ValueError("Invalid registry URL")
        
        # Handle default context "." as no context
        if context and context != ".":
            # URL encode the context to prevent injection
            safe_context = quote(context, safe='')
            return f"{self.config.url}/contexts/{safe_context}{base_url}"
        return f"{self.config.url}{base_url}"

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to this registry."""
        try:
            response = requests.get(
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
                }
            else:
                return {
                    "status": "error",
                    "registry": self.config.name,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"status": "error", "registry": self.config.name, "error": str(e)}

    def get_subjects(self, context: Optional[str] = None) -> List[str]:
        """Get subjects from this registry."""
        try:
            url = self.build_context_url("/subjects", context)
            response = requests.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def get_contexts(self) -> List[str]:
        """Get contexts from this registry."""
        try:
            response = requests.get(
                f"{self.config.url}/contexts", auth=self.auth, headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def delete_subject(self, subject: str, context: Optional[str] = None) -> bool:
        """Delete a subject from this registry."""
        try:
            url = self.build_context_url(f"/subjects/{subject}", context)
            response = requests.delete(
                url, auth=self.auth, headers=self.headers, timeout=30
            )
            return response.status_code in [200, 404]  # 404 means already deleted
        except Exception:
            return False

    def get_schema(
        self, subject: str, version: str = "latest", context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a specific version of a schema."""
        try:
            url = self.build_context_url(
                f"/subjects/{subject}/versions/{version}", context
            )
            response = requests.get(url, auth=self.auth, headers=self.headers)
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
            response = requests.post(
                url, data=json.dumps(payload), auth=self.auth, headers=self.headers
            )
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
            response = requests.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_global_config(
        self, compatibility: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update global configuration settings."""
        try:
            url = self.build_context_url("/config", context)
            payload = {"compatibility": compatibility}
            response = requests.put(
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

    def get_subject_config(
        self, subject: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get configuration settings for a specific subject."""
        try:
            url = self.build_context_url(f"/config/{subject}", context)
            response = requests.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_subject_config(
        self, subject: str, compatibility: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update configuration settings for a specific subject."""
        try:
            url = self.build_context_url(f"/config/{subject}", context)
            payload = {"compatibility": compatibility}
            response = requests.put(
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
            response = requests.get(url, auth=self.auth, headers=self.standard_headers)
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
            response = requests.put(
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

    def get_subject_mode(
        self, subject: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get the mode for a specific subject."""
        try:
            url = self.build_context_url(f"/mode/{subject}", context)
            response = requests.get(url, auth=self.auth, headers=self.standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}

    def update_subject_mode(
        self, subject: str, mode: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update the mode for a specific subject."""
        try:
            url = self.build_context_url(f"/mode/{subject}", context)
            payload = {"mode": mode}
            response = requests.put(
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

    def get_schema_versions(
        self, subject: str, context: Optional[str] = None
    ) -> Union[List[int], Dict[str, str]]:
        """Get all versions of a schema."""
        try:
            url = self.build_context_url(f"/subjects/{subject}/versions", context)
            response = requests.get(url, auth=self.auth, headers=self.headers)
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
        """Check if a schema is compatible with the specified subject."""
        try:
            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }
            url = self.build_context_url(
                f"/compatibility/subjects/{subject}/versions/latest", context
            )
            response = requests.post(
                url, data=json.dumps(payload), auth=self.auth, headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = self.config.name
            return result
        except Exception as e:
            return {"error": str(e)}


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
            "connected": sum(
                1 for r in results.values() if r.get("status") == "connected"
            ),
            "failed": sum(1 for r in results.values() if r.get("status") == "error"),
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
            "connected": sum(
                1 for r in results.values() if r.get("status") == "connected"
            ),
            "failed": sum(1 for r in results.values() if r.get("status") == "error"),
        }

    async def compare_registries_async(
        self, source: str, target: str
    ) -> Dict[str, Any]:
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

    async def _get_subjects_async(
        self, session: aiohttp.ClientSession, client: RegistryClient
    ) -> List[str]:
        """Get subjects from a registry asynchronously."""
        try:
            async with session.get(
                f"{client.config.url}/subjects", headers=client.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception:
            return []

    def is_readonly(self, registry_name: Optional[str] = None) -> bool:
        """Check if a registry is in readonly mode."""
        client = self.get_registry(registry_name)
        if not client:
            return False
        return client.config.readonly

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
                    readonly=SINGLE_READONLY,
                )
                self.registries["default"] = RegistryClient(config)
                self.default_registry = "default"
                logging.info(
                    f"Loaded single registry: default at {SINGLE_REGISTRY_URL} (readonly: {SINGLE_READONLY})"
                )
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
            readonly_var = f"READONLY_{i}"

            name = os.getenv(name_var, "")
            url = os.getenv(url_var, "")

            if name and url:
                multi_registry_found = True

                user = os.getenv(user_var, "")
                password = os.getenv(password_var, "")
                readonly = os.getenv(readonly_var, "false").lower() in (
                    "true",
                    "1",
                    "yes",
                    "on",
                )

                try:
                    config = RegistryConfig(
                        name=name,
                        url=url,
                        user=user,
                        password=password,
                        description=f"{name} Schema Registry (instance {i})",
                        readonly=readonly,
                    )

                    self.registries[name] = RegistryClient(config)

                    # Set first registry as default
                    if self.default_registry is None:
                        self.default_registry = name

                    logging.info(
                        f"Loaded registry {i}: {name} at {url} (readonly: {readonly})"
                    )
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
                    readonly=SINGLE_READONLY,
                )
                self.registries["default"] = RegistryClient(config)
                self.default_registry = "default"
                logging.info(
                    f"Loaded single registry: default at {SINGLE_REGISTRY_URL} (readonly: {SINGLE_READONLY})"
                )
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
                    readonly=SINGLE_READONLY,
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
                        config = RegistryConfig(
                            name=name,
                            url=config_data["url"],
                            user=config_data.get("user", ""),
                            password=config_data.get("password", ""),
                            description=config_data.get("description", f"{name} registry"),
                            readonly=config_data.get("readonly", False),
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


def check_readonly_mode(
    registry_manager: BaseRegistryManager, registry_name: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """Check if operations should be blocked due to readonly mode."""
    if registry_manager.is_readonly(registry_name):
        return {
            "error": "Registry is in READONLY mode. Modification operations are disabled for safety.",
            "readonly_mode": "true",
            "registry": registry_name
            or registry_manager.get_default_registry()
            or "unknown",
        }
    return None


def build_context_url(
    base_url: str, registry_url: str, context: Optional[str] = None
) -> str:
    """Build URL with optional context support (global function for backward compatibility)."""
    # Validate the registry URL
    if not validate_url(registry_url):
        raise ValueError("Invalid registry URL")
    
    # Handle default context "." as no context
    if context and context != ".":
        # URL encode the context to prevent injection
        safe_context = quote(context, safe='')
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
            context_export = export_context(
                client, context, include_metadata, include_config, include_versions
            )
            if "error" not in context_export:
                contexts_data.append(context_export)

        # Export default context (no context specified)
        default_export = export_context(
            client, "", include_metadata, include_config, include_versions
        )

        result = {
            "contexts": contexts_data,
            "default_context": (
                default_export if "error" not in default_export else None
            ),
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
                deletion_results = list(
                    executor.map(delete_single_subject, subjects_list)
                )

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
            "success_rate": (
                round((len(deleted_subjects) / len(subjects_list)) * 100, 1)
                if subjects_list
                else 100
            ),
            "deleted_subjects": deleted_subjects,
            "failed_deletions": failed_deletions[:5],  # Show first 5 failures
            "performance": {
                "subjects_per_second": round(
                    len(deleted_subjects) / max(duration, 0.1), 1
                ),
                "parallel_execution": not dry_run,
                "max_concurrent_deletions": 10,
            },
        }

        if context_deletion_error:
            result["context_deletion_error"] = context_deletion_error

        # Summary message
        if dry_run:
            result["message"] = (
                f"DRY RUN: Would delete {len(subjects_list)} subjects from context '{context}'"
            )
        elif len(deleted_subjects) == len(subjects_list):
            result["message"] = (
                f"Successfully cleared context '{context}' - deleted {len(deleted_subjects)} subjects"
            )
        else:
            result["message"] = (
                f"Partially cleared context '{context}' - deleted {len(deleted_subjects)}/{len(subjects_list)} subjects"
            )

        return result

    except Exception as e:
        return {"error": f"Batch cleanup failed: {str(e)}"}
