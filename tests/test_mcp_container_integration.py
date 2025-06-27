#!/usr/bin/env python3
"""
Integration tests for MCP server running in Docker container.

This test suite verifies that the MCP server works correctly when deployed
in a Docker container, testing both single and multi-registry modes.
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MCPContainerClient:
    """Client for communicating with MCP server in Docker container."""

    def __init__(self, container_name: str = "mcp-server"):
        self.container_name = container_name
        self._verify_container_running()

    def _verify_container_running(self):
        """Verify the MCP container is running."""
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={self.container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
        )
        if self.container_name not in result.stdout:
            raise RuntimeError(f"Container {self.container_name} is not running")

    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server and get response."""
        # Convert request to JSON
        request_json = json.dumps(request)

        # Send request via docker exec
        cmd = [
            "docker",
            "exec",
            "-i",
            self.container_name,
            "python",
            "kafka_schema_registry_unified_mcp.py",
        ]

        result = subprocess.run(cmd, input=request_json, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"MCP command failed: {result.stderr}")

        # Parse response
        try:
            # MCP responses are line-delimited JSON
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if line.strip():
                    response = json.loads(line)
                    if "result" in response or "error" in response:
                        return response
            raise ValueError("No valid response found")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse MCP response: {e}\nOutput: {result.stdout}")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool and return the result."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        response = self.send_request(request)

        if "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")

        return response.get("result", {}).get("content", [])

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available MCP tools."""
        request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}

        response = self.send_request(request)

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {}).get("tools", [])


class TestMCPContainerIntegration:
    """Test suite for MCP server container integration."""

    @pytest.fixture
    def mcp_client(self):
        """Create MCP client for testing."""
        # Wait a bit for container to be fully ready
        time.sleep(2)
        return MCPContainerClient()

    def test_container_health(self):
        """Test that the MCP container is healthy."""
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", "mcp-server"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "healthy" in result.stdout.lower()

    def test_list_tools(self, mcp_client):
        """Test listing available MCP tools."""
        tools = mcp_client.list_tools()

        # Verify we have tools
        assert len(tools) > 0

        # Check for some expected tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "list_subjects",
            "get_schema",
            "register_schema",
            "get_schema_versions",
            "compare_schemas",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Expected tool {expected} not found"

        # Verify tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_single_registry_mode(self, mcp_client):
        """Test MCP server in single registry mode."""
        # List subjects from default registry
        result = mcp_client.call_tool("list_subjects", {})

        # Should return a list (might be empty)
        assert isinstance(result, list)

        # Get server info to verify single registry mode
        result = mcp_client.call_tool("get_server_info", {})

        # Check that we're connected to the dev registry
        assert any("schema-registry-dev:8081" in str(item) for item in result)

    def test_multi_registry_mode(self, mcp_client):
        """Test MCP server in multi-registry mode."""
        # List subjects from dev registry
        result = mcp_client.call_tool("list_subjects", {"registry_name": "dev"})
        assert isinstance(result, list)

        # List subjects from prod registry
        result = mcp_client.call_tool("list_subjects", {"registry_name": "prod"})
        assert isinstance(result, list)

        # Try to use invalid registry
        with pytest.raises(RuntimeError) as exc_info:
            mcp_client.call_tool("list_subjects", {"registry_name": "invalid"})
        assert "error" in str(exc_info.value).lower()

    def test_schema_registration_and_retrieval(self, mcp_client):
        """Test registering and retrieving schemas."""
        # Test subject and schema
        subject = f"test-container-subject-{int(time.time())}"
        schema = {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }

        # Register schema
        result = mcp_client.call_tool("register_schema", {"subject": subject, "schema": json.dumps(schema)})

        # Should return schema ID
        assert any("id" in str(item) for item in result)

        # Retrieve the schema
        result = mcp_client.call_tool("get_schema", {"subject": subject, "version": "latest"})

        # Verify schema content
        assert any("TestRecord" in str(item) for item in result)

        # List versions
        result = mcp_client.call_tool("get_schema_versions", {"subject": subject})

        # Should have version 1
        assert any("1" in str(item) for item in result)

        # Clean up
        mcp_client.call_tool("delete_subject", {"subject": subject})

    def test_schema_comparison(self, mcp_client):
        """Test schema comparison functionality."""
        # Create two test subjects
        base_subject = f"test-compare-base-{int(time.time())}"
        new_subject = f"test-compare-new-{int(time.time())}"

        # Base schema
        base_schema = {
            "type": "record",
            "name": "User",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }

        # Modified schema (added field)
        new_schema = {
            "type": "record",
            "name": "User",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string", "default": ""},
            ],
        }

        # Register both schemas
        mcp_client.call_tool(
            "register_schema",
            {"subject": base_subject, "schema": json.dumps(base_schema)},
        )

        mcp_client.call_tool(
            "register_schema",
            {"subject": new_subject, "schema": json.dumps(new_schema)},
        )

        # Compare schemas
        result = mcp_client.call_tool(
            "compare_schemas",
            {
                "subject1": base_subject,
                "version1": "latest",
                "subject2": new_subject,
                "version2": "latest",
            },
        )

        # Should detect the difference
        result_str = str(result)
        assert "email" in result_str or "field" in result_str.lower()

        # Clean up
        mcp_client.call_tool("delete_subject", {"subject": base_subject})
        mcp_client.call_tool("delete_subject", {"subject": new_subject})

    def test_error_handling(self, mcp_client):
        """Test error handling in containerized MCP server."""
        # Try to get non-existent schema
        with pytest.raises(RuntimeError) as exc_info:
            mcp_client.call_tool("get_schema", {"subject": "non-existent-subject", "version": "latest"})

        # Should get an error
        assert "error" in str(exc_info.value).lower()

        # Try invalid schema
        with pytest.raises(RuntimeError) as exc_info:
            mcp_client.call_tool(
                "register_schema",
                {"subject": "test-invalid", "schema": "not-valid-json"},
            )

        assert "error" in str(exc_info.value).lower()

    def test_concurrent_requests(self, mcp_client):
        """Test handling concurrent requests to containerized MCP server."""
        import concurrent.futures

        def list_subjects_task(registry_name=None):
            """Task to list subjects."""
            args = {"registry_name": registry_name} if registry_name else {}
            return mcp_client.call_tool("list_subjects", args)

        # Run multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            # Mix of requests to different registries
            for _ in range(3):
                futures.append(executor.submit(list_subjects_task))
                futures.append(executor.submit(list_subjects_task, "dev"))
                futures.append(executor.submit(list_subjects_task, "prod"))

            # Wait for all to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Concurrent request failed: {e}")

        # All requests should succeed
        assert len(results) == 9
        for result in results:
            assert isinstance(result, list)

    def test_container_restart_recovery(self):
        """Test that MCP server recovers properly after container restart."""
        # Create a test subject before restart
        client = MCPContainerClient()
        subject = f"test-restart-{int(time.time())}"
        schema = {"type": "string"}

        client.call_tool("register_schema", {"subject": subject, "schema": json.dumps(schema)})

        # Restart the container
        subprocess.run(["docker", "restart", "mcp-server"], check=True)

        # Wait for container to be healthy again
        max_attempts = 30
        for i in range(max_attempts):
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    "mcp-server",
                ],
                capture_output=True,
                text=True,
            )
            if "healthy" in result.stdout.lower():
                break
            time.sleep(1)
        else:
            pytest.fail("Container did not become healthy after restart")

        # Create new client and verify we can still access the schema
        new_client = MCPContainerClient()
        result = new_client.call_tool("get_schema", {"subject": subject, "version": "latest"})

        assert any("string" in str(item) for item in result)

        # Clean up
        new_client.call_tool("delete_subject", {"subject": subject})


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
