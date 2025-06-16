#!/usr/bin/env python3
"""
Test Configuration for Integration Tests

This file provides flexible configuration options for running integration tests
against different Schema Registry setups.
"""

import os
from typing import Dict, Optional


class TestConfig:
    """Configuration class for integration tests"""

    def __init__(self):
        self.schema_registry_url = os.getenv("TEST_SCHEMA_REGISTRY_URL", "http://localhost:38081")
        self.schema_registry_user = os.getenv("TEST_SCHEMA_REGISTRY_USER", "")
        self.schema_registry_password = os.getenv("TEST_SCHEMA_REGISTRY_PASSWORD", "")

        # Multi-registry configuration for testing
        self.registry_configs = self._build_registry_configs()

    def _build_registry_configs(self) -> Dict[str, Dict[str, str]]:
        """Build registry configurations from environment variables or defaults"""
        configs = {}

        # Try to get numbered configurations first
        for i in range(1, 9):  # Support up to 8 registries
            name = os.getenv(f"SCHEMA_REGISTRY_NAME_{i}")
            url = os.getenv(f"SCHEMA_REGISTRY_URL_{i}")

            if name and url:
                configs[f"registry_{i}"] = {
                    "name": name,
                    "url": url,
                    "user": os.getenv(f"SCHEMA_REGISTRY_USER_{i}", ""),
                    "password": os.getenv(f"SCHEMA_REGISTRY_PASSWORD_{i}", ""),
                    "readonly": os.getenv(f"READONLY_{i}", "false").lower() == "true",
                }

        # If no numbered configs found, detect test environment and create appropriate defaults
        if not configs:
            # Check if multi-registry test environment is running
            multi_registry_detected = self._detect_multi_registry_environment()

            if multi_registry_detected:
                # Multi-registry test environment (DEV + PROD)
                configs["registry_1"] = {
                    "name": "development",
                    "url": "http://localhost:38081",
                    "user": "",
                    "password": "",
                    "readonly": False,
                }
                configs["registry_2"] = {
                    "name": "production",
                    "url": "http://localhost:38082",
                    "user": "",
                    "password": "",
                    "readonly": True,
                }
            else:
                # Single registry or custom configuration
                base_port = 8081
                if self.schema_registry_url != f"http://localhost:{base_port}":
                    # If custom URL provided, use it as the primary registry
                    configs["registry_1"] = {
                        "name": "test_primary",
                        "url": self.schema_registry_url,
                        "user": self.schema_registry_user,
                        "password": self.schema_registry_password,
                        "readonly": False,
                    }
                else:
                    # Single registry test environment
                    configs["registry_1"] = {
                        "name": "test",
                        "url": f"http://localhost:{base_port}",
                        "user": "",
                        "password": "",
                        "readonly": False,
                    }

        return configs

    def _detect_multi_registry_environment(self) -> bool:
        """Detect if multi-registry test environment is running"""
        try:
            import requests

            # Check if both DEV (8081) and PROD (8082) registries are accessible
            dev_response = requests.get("http://localhost:38081/subjects", timeout=2)
            prod_response = requests.get("http://localhost:38082/subjects", timeout=2)
            return dev_response.status_code == 200 and prod_response.status_code == 200
        except:
            return False

    def get_primary_registry_config(self) -> Dict[str, str]:
        """Get the primary registry configuration for single-registry tests"""
        if self.registry_configs:
            return list(self.registry_configs.values())[0]

        return {
            "name": "primary",
            "url": self.schema_registry_url,
            "user": self.schema_registry_user,
            "password": self.schema_registry_password,
            "readonly": False,
        }

    def get_multi_registry_configs(self) -> Dict[str, Dict[str, str]]:
        """Get all registry configurations for multi-registry tests"""
        return self.registry_configs

    def setup_environment_variables(self) -> None:
        """Setup environment variables for MCP server"""
        primary_config = self.get_primary_registry_config()

        # Set primary registry environment variables
        os.environ["SCHEMA_REGISTRY_URL"] = primary_config["url"]
        if primary_config["user"]:
            os.environ["SCHEMA_REGISTRY_USER"] = primary_config["user"]
        if primary_config["password"]:
            os.environ["SCHEMA_REGISTRY_PASSWORD"] = primary_config["password"]

        # Set numbered environment variables for multi-registry support
        for i, (key, config) in enumerate(self.registry_configs.items(), 1):
            os.environ[f"SCHEMA_REGISTRY_NAME_{i}"] = config["name"]
            os.environ[f"SCHEMA_REGISTRY_URL_{i}"] = config["url"]
            os.environ[f"SCHEMA_REGISTRY_USER_{i}"] = config["user"]
            os.environ[f"SCHEMA_REGISTRY_PASSWORD_{i}"] = config["password"]
            os.environ[f"READONLY_{i}"] = str(config["readonly"]).lower()


# Global test configuration instance
test_config = TestConfig()
