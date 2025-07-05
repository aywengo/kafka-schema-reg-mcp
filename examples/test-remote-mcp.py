#!/usr/bin/env python3
"""
Test Script for Remote MCP Server Deployment

This script tests the remote MCP server deployment to ensure:
1. Server starts correctly with remote transport
2. OAuth authentication works
3. MCP tools are accessible
4. Client connectivity is working

Usage:
    # Test local remote server
    python examples/test-remote-mcp.py --url http://localhost:8000/mcp

    # Test production remote server
    python examples/test-remote-mcp.py --url https://mcp-schema-registry.your-domain.com/mcp --auth-token "your-jwt-token"

    # Test with development token
    python examples/test-remote-mcp.py --url http://localhost:8000/mcp --auth-token "dev-token-read"
"""

import argparse
import asyncio
import json
from typing import Any, Dict, Optional

import aiohttp


class RemoteMCPTester:
    """Test remote MCP server functionality."""

    def __init__(self, server_url: str, auth_token: Optional[str] = None):
        self.server_url = server_url
        self.auth_token = auth_token
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for MCP requests."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers

    async def send_mcp_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        request_data = {"jsonrpc": "2.0", "id": 1, "method": method}

        if params:
            request_data["params"] = params

        try:
            async with self.session.post(
                self.server_url,
                headers=self.get_headers(),
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "error": {
                            "code": response.status,
                            "message": f"HTTP {response.status}: {await response.text()}",
                        }
                    }
        except Exception as e:
            return {"error": {"code": -1, "message": f"Connection error: {str(e)}"}}

    async def test_server_connection(self) -> bool:
        """Test basic server connectivity."""
        print("🔗 Testing server connection...")

        try:
            # Test health endpoint if available
            health_url = self.server_url.replace("/mcp", "/health").replace(
                "/sse", "/health"
            )
            async with self.session.get(
                health_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    print(f"✅ Health check passed: {response.status}")
                    return True
        except Exception:
            pass  # Health endpoint might not exist

        # Test MCP endpoint with initialize
        result = await self.send_mcp_request(
            "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}}
        )

        if "error" in result:
            print(f"❌ Server connection failed: {result['error']['message']}")
            return False
        else:
            print("✅ Server connection successful")
            return True

    async def test_oauth_authentication(self) -> bool:
        """Test OAuth authentication."""
        print("🔐 Testing OAuth authentication...")

        if not self.auth_token:
            print("⚠️  No auth token provided, skipping OAuth test")
            return True

        # Test getting OAuth scopes info
        result = await self.send_mcp_request(
            "tools/call", {"name": "get_oauth_scopes_info", "arguments": {}}
        )

        if "error" in result:
            print(f"❌ OAuth authentication failed: {result['error']['message']}")
            return False
        elif "result" in result and "content" in result["result"]:
            oauth_info = json.loads(result["result"]["content"][0]["text"])
            print("✅ OAuth authentication successful")
            print(f"   OAuth enabled: {oauth_info.get('oauth_enabled', False)}")
            print(f"   Valid scopes: {oauth_info.get('valid_scopes', [])}")
            return True
        else:
            print(f"❌ Unexpected OAuth response: {result}")
            return False

    async def test_mcp_tools_list(self) -> bool:
        """Test listing MCP tools."""
        print("🛠️ Testing MCP tools listing...")

        result = await self.send_mcp_request("tools/list")

        if "error" in result:
            print(f"❌ Tools list failed: {result['error']['message']}")
            return False
        elif "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
            print(f"✅ Tools list successful: {len(tools)} tools available")

            # Show first few tools
            for i, tool in enumerate(tools[:5]):
                print(
                    f"   {i+1}. {tool['name']}: {tool.get('description', 'No description')}"
                )

            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more tools")

            return True
        else:
            print(f"❌ Unexpected tools response: {result}")
            return False

    async def test_simple_tool_call(self) -> bool:
        """Test calling a simple MCP tool."""
        print("⚙️ Testing simple tool call...")

        # Try to call list_registries (should work with read scope)
        result = await self.send_mcp_request(
            "tools/call", {"name": "list_registries", "arguments": {}}
        )

        if "error" in result:
            print(f"❌ Tool call failed: {result['error']['message']}")
            return False
        elif "result" in result and "content" in result["result"]:
            response_text = result["result"]["content"][0]["text"]
            registries = json.loads(response_text)
            print("✅ Tool call successful")
            print(f"   Found {len(registries)} registries")

            if registries:
                for i, registry in enumerate(registries[:3]):
                    name = registry.get("name", "Unknown")
                    url = registry.get("url", "No URL")
                    print(f"   {i+1}. {name}: {url}")

            return True
        else:
            print(f"❌ Unexpected tool response: {result}")
            return False

    async def test_resources_list(self) -> bool:
        """Test listing MCP resources."""
        print("📚 Testing MCP resources listing...")

        result = await self.send_mcp_request("resources/list")

        if "error" in result:
            print(f"❌ Resources list failed: {result['error']['message']}")
            return False
        elif "result" in result and "resources" in result["result"]:
            resources = result["result"]["resources"]
            print(f"✅ Resources list successful: {len(resources)} resources available")

            # Show first few resources
            for i, resource in enumerate(resources[:3]):
                print(
                    f"   {i+1}. {resource['uri']}: {resource.get('description', 'No description')}"
                )

            return True
        else:
            print(f"❌ Unexpected resources response: {result}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        print(f"🚀 Testing Remote MCP Server: {self.server_url}")
        print(f"🔑 Auth token: {'Provided' if self.auth_token else 'None'}")
        print("=" * 60)

        tests = [
            ("Server Connection", self.test_server_connection),
            ("OAuth Authentication", self.test_oauth_authentication),
            ("MCP Tools List", self.test_mcp_tools_list),
            ("Simple Tool Call", self.test_simple_tool_call),
            ("Resources List", self.test_resources_list),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                success = await test_func()
                if success:
                    passed += 1
                print()  # Add spacing between tests
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
                print()

        print("=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Remote MCP server is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test Remote MCP Server")
    parser.add_argument(
        "--url",
        required=True,
        help="Remote MCP server URL (e.g., https://mcp-schema-registry.your-domain.com/mcp)",
    )
    parser.add_argument(
        "--auth-token",
        help="OAuth JWT token or development token (e.g., dev-token-read)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    try:
        async with RemoteMCPTester(args.url, args.auth_token) as tester:
            success = await tester.run_all_tests()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"💥 Testing failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
