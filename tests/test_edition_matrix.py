"""Edition and protocol-mode matrix checks against the stdio server."""

import os
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "kafka_schema_registry_unified_mcp.py"
EXPECTED = {"viewer": 39, "editor": 42, "admin": 66}


@pytest.mark.asyncio
@pytest.mark.parametrize("edition,count", EXPECTED.items())
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_edition_tool_count_and_ping(edition, count, mode):
    env = os.environ.copy()
    env["MCP_EDITION"] = edition
    env.setdefault("SCHEMA_REGISTRY_URL", "http://localhost:38081")
    transport = StdioTransport(sys.executable, [str(SERVER)], env=env)

    async with Client(transport, mode=mode) as client:
        tools = await client.list_tools()
        assert len(tools) == count
        ping = await client.call_tool("ping", {})
        payload = ping.structured_content
        assert payload["edition"] == edition
        if mode == "legacy":
            assert payload["protocol_version"] == "2025-11-25"
        else:
            assert payload["protocol_version"] == "2026-07-28"
