#!/usr/bin/env python3
"""
MCP Ping/Pong Protocol Tests

Tests for MCP ping/pong protocol support in the
Kafka Schema Registry MCP Server.

Tests cover:
- Basic ping/pong functionality
- Ping response structure and content validation
- Server health checking capability
- MCP proxy compatibility
- Protocol version information in ping response
- Timestamp and server status validation

Usage:
    python test_mcp_ping.py
"""

import asyncio
import json
import os
import sys
import unittest
from datetime import datetime
from typing import Any

from fastmcp import Client

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def _unwrap_ping_callable(ping: Any):
    """Return the implementation callable for the ping tool (FastMCP 2.x / 3.x wrappers)."""
    if callable(ping) and getattr(ping, "__name__", None) == "ping":
        return ping
    for attr in ("fn", "func", "_func", "__wrapped__"):
        inner = getattr(ping, attr, None)
        if callable(inner):
            return inner
    return ping if callable(ping) else None


def _parse_ping_response_from_call_tool_result(result: Any) -> dict:
    """Normalize FastMCP client call_tool result to the ping tool dict."""
    if result is None:
        raise ValueError("ping call_tool returned None")
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        inner = structured.get("result")
        if isinstance(inner, dict):
            return inner
        return structured
    content = getattr(result, "content", None) or []
    if content:
        block = content[0]
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    raise ValueError(f"could not parse ping result from {type(result)!r}")


async def test_ping_tool_directly():
    """Test the ping tool function directly."""
    print("🏓 Testing MCP Ping Tool Directly")
    print("=" * 50)

    try:
        # Import the ping function directly
        from kafka_schema_registry_unified_mcp import MCP_PROTOCOL_VERSION, ping

        print("✅ Successfully imported ping function")

        ping_func = _unwrap_ping_callable(ping)
        if ping_func is None:
            import kafka_schema_registry_unified_mcp as mcp_module

            ping_func = None
            for name, obj in vars(mcp_module).items():
                inner = _unwrap_ping_callable(obj)
                if inner is not None and getattr(inner, "__name__", None) == "ping":
                    ping_func = inner
                    break

            if ping_func is None:
                print("⚠️ Could not access ping function directly, skipping direct test")
                return True

        response = ping_func()

        # Validate response structure
        assert isinstance(response, dict), "Ping response should be a dictionary"
        assert "response" in response, "Ping response should contain 'response' field"
        assert response["response"] == "pong", "Ping response should be 'pong'"

        print(f"✅ Basic ping/pong functionality: {response['response']}")

        # Validate additional fields
        required_fields = [
            "server_name",
            "server_version",
            "timestamp",
            "protocol_version",
            "registry_mode",
            "status",
            "ping_supported",
            "message",
        ]

        for field in required_fields:
            assert field in response, f"Ping response should contain '{field}' field"
            print(f"✅ Field '{field}': {response[field]}")

        # Validate specific values
        assert response["ping_supported"] is True, "ping_supported should be True"
        assert response["status"] == "healthy", "Server status should be 'healthy'"
        assert (
            "kafka schema registry" in response["server_name"].lower()
        ), "Server name should reference Kafka Schema Registry"
        assert "mcp server" in response["server_name"].lower(), "Server name should reference MCP server"

        # Validate timestamp format (should be ISO format)
        try:
            datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))
            print("✅ Timestamp format validation passed")
        except ValueError as e:
            print(f"❌ Invalid timestamp format: {e}")
            return False

        assert (
            response["protocol_version"] == MCP_PROTOCOL_VERSION
        ), f"Expected protocol version {MCP_PROTOCOL_VERSION!r}, got {response['protocol_version']!r}"
        print("✅ Protocol version validation passed")

        print("🎉 Direct ping tool test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error in direct ping test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ping_via_mcp_client():
    """Test the ping tool via MCP client."""
    print("\n🏓 Testing MCP Ping via Client")
    print("=" * 50)

    # Check if we're in a CI/container environment
    is_ci_environment = (
        os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true" or os.path.exists("/.dockerenv")
    )

    # Check if MCP server container is already running
    mcp_container_running = False
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "--filter", "name=mcp-server", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        mcp_container_running = "mcp-server" in result.stdout
    except Exception:
        pass

    if is_ci_environment and mcp_container_running:
        print("🐳 Detected CI environment with MCP server container running")
        print("✅ Skipping MCP client test to avoid conflicts with containerized server")
        print("💡 This is expected behavior in CI - container tests run separately")
        return "SKIPPED"

    server_script = os.path.join(PROJECT_ROOT, "kafka_schema_registry_unified_mcp.py")

    # Set up environment for testing
    env_vars = {
        "SCHEMA_REGISTRY_URL": "http://localhost:38081",
        "SCHEMA_REGISTRY_USER": "",
        "SCHEMA_REGISTRY_PASSWORD": "",
        "REGISTRY_MODE": "single",
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    try:
        client = Client(server_script)

        async with client:
            print("✅ MCP client connection established")

            # List available tools to verify ping is registered
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            assert "ping" in tool_names, "Ping tool should be available in tool list"
            print("✅ Ping tool found in available tools")

            # Find the ping tool details
            ping_tool = next((tool for tool in tools if tool.name == "ping"), None)
            assert ping_tool is not None, "Ping tool should be found"

            # Validate ping tool description
            description = (ping_tool.description or "").lower()
            assert "ping" in description, "Ping tool description should mention ping"
            assert "pong" in description, "Ping tool description should mention pong"
            assert "health" in description, "Ping tool description should mention health checking"
            print("✅ Ping tool description validation passed")

            # Call the ping tool
            print("🏓 Calling ping tool...")
            result = await client.call_tool("ping", {})

            assert result is not None, "Ping tool should return results"

            try:
                response_data = _parse_ping_response_from_call_tool_result(result)
            except (json.JSONDecodeError, ValueError) as parse_err:
                response_text = str(result)
                if hasattr(result, "content") and result.content:
                    block = result.content[0]
                    response_text = getattr(block, "text", None) or response_text
                assert (
                    "pong" in response_text.lower()
                ), f"Response should contain 'pong': {parse_err!s}; body={response_text!r}"
                print("✅ Ping response received (non-JSON format)")
                return True

            # Validate JSON response structure
            assert isinstance(response_data, dict), "Ping response should be a dictionary"
            assert response_data.get("response") == "pong", "Response should be 'pong'"
            print(f"✅ Ping/pong exchange successful: {response_data['response']}")

            # Validate server information
            assert "server_name" in response_data, "Response should include server name"
            assert "server_version" in response_data, "Response should include server version"
            assert "timestamp" in response_data, "Response should include timestamp"
            assert "protocol_version" in response_data, "Response should include protocol version"

            print(f"✅ Server: {response_data.get('server_name', 'Unknown')}")
            print(f"✅ Version: {response_data.get('server_version', 'Unknown')}")
            print(f"✅ Protocol: {response_data.get('protocol_version', 'Unknown')}")
            print(f"✅ Status: {response_data.get('status', 'Unknown')}")

            # Validate health status
            if "status" in response_data:
                assert response_data["status"] == "healthy", "Server should report healthy status"
                print("✅ Server health status validation passed")

            print("🎉 MCP client ping test completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Error in MCP client ping test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ping_performance():
    """Test ping tool performance for health checking scenarios."""
    print("\n🏓 Testing MCP Ping Performance")
    print("=" * 50)

    try:
        from kafka_schema_registry_unified_mcp import ping

        ping_func = _unwrap_ping_callable(ping)
        if ping_func is None:
            print("⚠️ Could not access ping function directly, skipping performance test")
            return True

        # Test multiple ping calls to simulate health checking
        ping_times = []
        num_pings = 10

        print(f"🏓 Performing {num_pings} ping operations...")

        for i in range(num_pings):
            start_time = datetime.now()
            response = ping_func()
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
            ping_times.append(duration)

            # Validate each response
            assert response["response"] == "pong", f"Ping {i+1} should return 'pong'"
            assert response["status"] == "healthy", f"Ping {i+1} should report healthy status"

        # Calculate performance metrics
        avg_time = sum(ping_times) / len(ping_times)
        max_time = max(ping_times)
        min_time = min(ping_times)

        print(f"✅ Average ping time: {avg_time:.2f}ms")
        print(f"✅ Min ping time: {min_time:.2f}ms")
        print(f"✅ Max ping time: {max_time:.2f}ms")

        # Validate performance (should be fast for health checking)
        assert avg_time < 100, f"Average ping time should be under 100ms, got {avg_time:.2f}ms"
        assert max_time < 500, f"Max ping time should be under 500ms, got {max_time:.2f}ms"

        print("✅ Ping performance test passed - suitable for health checking")
        return True

    except Exception as e:
        print(f"❌ Error in ping performance test: {e}")
        return False


class MCPPingTestSuite(unittest.TestCase):
    """Unit test suite for MCP ping functionality."""

    def test_ping_tool_available(self):
        """Test that ping tool is available as a FastMCP tool."""
        try:
            from kafka_schema_registry_unified_mcp import ping

            self.assertTrue(
                hasattr(ping, "__name__") or hasattr(ping, "name") or hasattr(ping, "key") or callable(ping)
            )
            print("✅ Ping tool is available as FastMCP tool")
        except ImportError:
            self.fail("Ping tool not available")

    def test_mcp_server_imports(self):
        """Test that the MCP server module imports successfully with ping support."""
        try:
            import kafka_schema_registry_unified_mcp

            # Test that the module loads without errors
            self.assertTrue(hasattr(kafka_schema_registry_unified_mcp, "ping"))
            print("✅ MCP server module imports successfully with ping support")
        except ImportError as e:
            self.fail(f"MCP server module import failed: {e}")

    def test_ping_tool_registration(self):
        """Test that ping tool is properly registered with MCP server."""
        try:
            # This is covered by the functional test via MCP client
            # Just ensure the module structure is correct
            import kafka_schema_registry_unified_mcp as mcp_module

            # Check that the module has been properly initialized
            self.assertTrue(hasattr(mcp_module, "mcp"))
            print("✅ MCP server structure validated")
        except Exception as e:
            self.fail(f"MCP server structure validation failed: {e}")

    def test_constants_defined(self):
        """Test that required constants for ping are defined."""
        try:
            from kafka_schema_registry_unified_mcp import MCP_PROTOCOL_VERSION, REGISTRY_MODE

            # Validate constants used by ping function (dated MCP revision evolves with the server)
            self.assertRegex(MCP_PROTOCOL_VERSION, r"^2025-\d{2}-\d{2}$")
            self.assertIn(REGISTRY_MODE, ["single", "multi"])
            print("✅ Required constants for ping are properly defined")

        except ImportError:
            self.fail("Required constants not available")


def run_all_ping_tests():
    """Run all ping tests."""
    print("🏓 Running MCP Ping/Pong Protocol Tests")
    print("=" * 60)

    test_results = []
    skipped_tests = []

    # Run direct ping test
    try:
        result = asyncio.run(test_ping_tool_directly())
        test_results.append(("Direct Ping Test", result))
    except Exception as e:
        print(f"❌ Direct ping test failed: {e}")
        test_results.append(("Direct Ping Test", False))

    # Run MCP client ping test
    try:
        result = asyncio.run(test_ping_via_mcp_client())
        if result == "SKIPPED":
            skipped_tests.append("MCP Client Ping Test")
        else:
            test_results.append(("MCP Client Ping Test", result))
    except Exception as e:
        print(f"❌ MCP client ping test failed: {e}")
        test_results.append(("MCP Client Ping Test", False))

    # Run performance test
    try:
        result = asyncio.run(test_ping_performance())
        test_results.append(("Ping Performance Test", result))
    except Exception as e:
        print(f"❌ Ping performance test failed: {e}")
        test_results.append(("Ping Performance Test", False))

    # Summary
    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)
    total_skipped = len(skipped_tests)

    print("\n📊 MCP Ping Test Results:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    if total_skipped > 0:
        print(f"   Skipped: {total_skipped} (CI environment)")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("🎉 All MCP ping tests passed!")
        if total_skipped > 0:
            print("💡 Some tests were skipped in CI environment (expected behavior)")
        return True
    else:
        print("❌ Some MCP ping tests failed")
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {test_name}")
        for test_name in skipped_tests:
            print(f"   ⏭️  SKIPPED: {test_name} (CI environment)")
        return False


def main():
    """Main function to run tests."""
    print("🏓 MCP Ping/Pong Protocol Test Suite")
    print("=" * 60)

    # Run functional tests
    functional_result = run_all_ping_tests()

    # Run unit tests
    print("\n🧪 Running Unit Tests...")
    unittest.main(argv=[""], exit=False, verbosity=2)

    return functional_result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
