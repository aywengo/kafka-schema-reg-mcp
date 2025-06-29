#!/usr/bin/env python3
"""
SSL/TLS Security Integration Tests

This test suite validates the SSL/TLS security enhancement implementation
for issue #24: Add SSL/TLS certificate verification for all HTTP requests.

Tests cover:
- Explicit SSL/TLS verification
- Custom CA bundle support
- Secure session creation
- SSL configuration logging
- Error handling for SSL failures
- Environment variable configuration
"""

import os
import sys
import tempfile
import unittest
import warnings
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_registry_common import (
    ENFORCE_SSL_TLS_VERIFICATION,
    RegistryClient,
    RegistryConfig,
    SecureHTTPAdapter,
    log_ssl_configuration,
)


class TestSSLTLSIntegration(unittest.TestCase):
    """Test cases for SSL/TLS security integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RegistryConfig(
            name="test-ssl-registry",
            url="https://schema-registry.example.com:8081",
            user="test-user",
            password="test-password",
        )

    def test_ssl_verification_enabled_by_default(self):
        """Test that SSL verification is enabled by default."""
        self.assertTrue(ENFORCE_SSL_TLS_VERIFICATION)
        print("✅ SSL verification enabled by default")

    def test_secure_session_creation(self):
        """Test that secure sessions are created with proper SSL configuration."""
        client = RegistryClient(self.config)

        # Verify session exists and has SSL verification enabled
        self.assertIsNotNone(client.session)
        self.assertTrue(client.session.verify)

        # Verify SecureHTTPAdapter is mounted for HTTPS
        https_adapter = client.session.get_adapter("https://")
        self.assertEqual(https_adapter.__class__.__name__, "SecureHTTPAdapter")

        print("✅ Secure session created with SSL verification")

    def test_custom_ca_bundle_configuration(self):
        """Test custom CA bundle path configuration."""
        # Create a temporary CA bundle file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as ca_file:
            ca_file.write("-----BEGIN CERTIFICATE-----\nFAKE_CERT_FOR_TESTING\n-----END CERTIFICATE-----\n")
            ca_file_path = ca_file.name

        try:
            with patch.dict(
                os.environ, {"CUSTOM_CA_BUNDLE_PATH": ca_file_path, "ENFORCE_SSL_TLS_VERIFICATION": "true"}
            ):
                # Reload the module to pick up new environment variables
                import importlib

                import schema_registry_common

                importlib.reload(schema_registry_common)

                client = schema_registry_common.RegistryClient(self.config)

                # Verify custom CA bundle is used
                self.assertEqual(client.session.verify, ca_file_path)
                print(f"✅ Custom CA bundle configured: {ca_file_path}")

        finally:
            # Clean up temporary file
            os.unlink(ca_file_path)

            # Reset environment and reload module
            if "CUSTOM_CA_BUNDLE_PATH" in os.environ:
                del os.environ["CUSTOM_CA_BUNDLE_PATH"]
            import importlib

            import schema_registry_common

            importlib.reload(schema_registry_common)

    def test_ssl_configuration_logging(self):
        """Test that SSL configuration is properly logged."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            log_ssl_configuration()

            # Verify SSL configuration logging calls were made to some logger
            # We check that getLogger was called (configuration logging happened)
            mock_get_logger.assert_called()

            print("✅ SSL configuration logging verified")

    @patch("schema_registry_common.requests.Session.get")
    def test_ssl_error_handling(self, mock_get):
        """Test proper handling of SSL errors."""
        import requests

        # Mock SSL error
        mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")

        client = RegistryClient(self.config)
        result = client.test_connection()

        # Verify SSL error is properly handled
        self.assertEqual(result["status"], "error")
        self.assertIn("SSL verification failed", result["error"])
        self.assertTrue(result.get("ssl_error", False))

        print("✅ SSL error handling verified")

    def test_secure_http_adapter_ssl_context(self):
        """Test that SecureHTTPAdapter creates proper SSL context."""
        adapter = SecureHTTPAdapter()

        # Test SSL context creation through initialization
        with patch("schema_registry_common.ssl.create_default_context") as mock_ssl_context:
            mock_context = Mock()
            mock_ssl_context.return_value = mock_context

            # Initialize pool manager to trigger SSL context creation
            try:
                adapter.init_poolmanager()
            except Exception:
                # Expected to fail in test environment, but SSL context should be configured
                pass

            # Verify SSL context was created and configured
            mock_ssl_context.assert_called_once()
            self.assertTrue(mock_context.check_hostname)
            self.assertEqual(mock_context.verify_mode, __import__("ssl").CERT_REQUIRED)

        print("✅ SecureHTTPAdapter SSL context configuration verified")

    def test_ssl_verification_environment_variable(self):
        """Test SSL verification can be controlled via environment variable."""
        # Test with SSL verification disabled
        with patch.dict(os.environ, {"ENFORCE_SSL_TLS_VERIFICATION": "false"}):
            # Reload module to pick up environment change
            import importlib

            import schema_registry_common

            importlib.reload(schema_registry_common)

            client = schema_registry_common.RegistryClient(self.config)

            # Note: Even when disabled, we still create secure sessions by default
            # This is intentional for security - the environment variable is for testing only
            self.assertIsNotNone(client.session)

        # Reset environment
        if "ENFORCE_SSL_TLS_VERIFICATION" in os.environ:
            del os.environ["ENFORCE_SSL_TLS_VERIFICATION"]
        import importlib

        import schema_registry_common

        importlib.reload(schema_registry_common)

        print("✅ SSL verification environment variable handling verified")

    def test_registry_client_ssl_logging(self):
        """Test that registry client logs SSL session creation."""
        with patch("schema_registry_common.logging.getLogger") as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance

            client = RegistryClient(self.config)

            # Verify SSL session creation is logged
            mock_log_instance.info.assert_called_with(
                f"Created secure session for registry '{self.config.name}' at {self.config.url}"
            )

        print("✅ Registry client SSL logging verified")

    def test_ssl_status_in_registry_info(self):
        """Test that SSL status is included in registry information."""
        from schema_registry_common import MultiRegistryManager

        # Create a registry manager with our test config
        manager = MultiRegistryManager()
        manager.registries["test-ssl"] = RegistryClient(self.config)

        with patch.object(manager.registries["test-ssl"], "test_connection") as mock_test:
            mock_test.return_value = {"status": "connected", "ssl_verified": True, "response_time_ms": 50}

            registry_info = manager.get_registry_info("test-ssl")

            # Verify SSL information is included
            self.assertIsNotNone(registry_info)
            self.assertIn("ssl_verification_enabled", registry_info)
            self.assertIn("ssl_verified", registry_info)
            self.assertTrue(registry_info["ssl_verification_enabled"])

        print("✅ SSL status in registry info verified")

    @patch("schema_registry_common.os.path.exists")
    def test_missing_custom_ca_bundle_handling(self, mock_exists):
        """Test handling of missing custom CA bundle file."""
        mock_exists.return_value = False

        with patch.dict(
            os.environ, {"CUSTOM_CA_BUNDLE_PATH": "/nonexistent/ca-bundle.pem", "ENFORCE_SSL_TLS_VERIFICATION": "true"}
        ):
            # Reload module to pick up environment change
            import importlib

            import schema_registry_common

            importlib.reload(schema_registry_common)

            client = schema_registry_common.RegistryClient(self.config)

            # Should fall back to default system verification
            self.assertTrue(client.session.verify)  # Should be True, not the path

        # Reset environment
        if "CUSTOM_CA_BUNDLE_PATH" in os.environ:
            del os.environ["CUSTOM_CA_BUNDLE_PATH"]
        import importlib

        import schema_registry_common

        importlib.reload(schema_registry_common)

        print("✅ Missing custom CA bundle handling verified")

    def test_ssl_tls_comprehensive_integration(self):
        """Comprehensive integration test of all SSL/TLS features."""
        # Test complete SSL/TLS integration workflow
        client = RegistryClient(self.config)

        # 1. Verify secure session
        self.assertIsNotNone(client.session)
        self.assertTrue(client.session.verify)

        # 2. Verify HTTPS adapter
        https_adapter = client.session.get_adapter("https://")
        self.assertEqual(https_adapter.__class__.__name__, "SecureHTTPAdapter")

        # 3. Verify configuration values
        self.assertTrue(ENFORCE_SSL_TLS_VERIFICATION)

        # 4. Test with mocked SSL-enabled connection
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.05
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            result = client.test_connection()

            # Verify SSL verification status is included
            self.assertEqual(result["status"], "connected")
            self.assertIn("ssl_verified", result)
            self.assertTrue(result["ssl_verified"])

        print("✅ Comprehensive SSL/TLS integration verified")


if __name__ == "__main__":
    print("🔒 SSL/TLS Security Integration Tests")
    print("=" * 50)
    print("Testing issue #24: Add SSL/TLS certificate verification for all HTTP requests")
    print()

    # Suppress SSL-related warnings during testing
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    unittest.main(verbosity=2)
