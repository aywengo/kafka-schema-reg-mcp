#!/usr/bin/env python3
"""MCP protocol negotiation compliance tests.

FastMCP 4 / MCP SDK 2 serve both the legacy initialize handshake and the modern
per-request era. These tests check that the server advertises both and reports
the version negotiated for the current connection.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class MCPComplianceTestSuite(unittest.TestCase):
    def test_default_protocol_version_is_modern(self):
        from protocol_version import DEFAULT_PROTOCOL_VERSION, current_protocol_version

        self.assertEqual(DEFAULT_PROTOCOL_VERSION, "2026-07-28")
        self.assertEqual(current_protocol_version(), DEFAULT_PROTOCOL_VERSION)

    def test_sdk_knows_both_eras(self):
        from mcp.types.version import KNOWN_PROTOCOL_VERSIONS

        self.assertIn("2025-11-25", KNOWN_PROTOCOL_VERSIONS)
        self.assertIn("2026-07-28", KNOWN_PROTOCOL_VERSIONS)

    def test_compliance_status_reports_sdk_negotiation(self):
        from kafka_schema_registry_unified_mcp import get_mcp_compliance_status

        status = get_mcp_compliance_status()
        self.assertIn("protocol_version", status)
        self.assertIn("supported_versions", status)
        self.assertEqual(status["protocol_negotiation"], "sdk-managed")
        self.assertIn("2025-11-25", status["supported_versions"])
        self.assertIn("2026-07-28", status["supported_versions"])
        self.assertEqual(status["compliance_status"], "COMPLIANT")

    def test_modern_client_negotiates_2026(self):
        from fastmcp import Client

        import kafka_schema_registry_unified_mcp as server

        async def run():
            async with Client(server.mcp, mode="auto") as client:
                result = await client.call_tool("ping", {})
                payload = result.structured_content or {}
                self.assertEqual(payload.get("protocol_version"), client.protocol_version)

        import asyncio

        asyncio.run(run())

    def test_legacy_client_negotiates_2025(self):
        from fastmcp import Client

        import kafka_schema_registry_unified_mcp as server

        async def run():
            async with Client(server.mcp, mode="legacy") as client:
                self.assertEqual(client.protocol_version, "2025-11-25")
                result = await client.call_tool("ping", {})
                payload = result.structured_content or {}
                self.assertEqual(payload.get("protocol_version"), "2025-11-25")

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
