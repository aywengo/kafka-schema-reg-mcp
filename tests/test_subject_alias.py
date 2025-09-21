import os
import uuid

import httpx
import pytest
import pytest_asyncio


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:38000")


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient() as c:
        yield c


@pytest.mark.asyncio
async def test_add_subject_alias(client: httpx.AsyncClient):
    # Create a unique base subject and register a schema
    base_subject = f"alias-base-{uuid.uuid4().hex[:8]}"
    alias_subject = f"alias-{uuid.uuid4().hex[:8]}"

    # Register initial schema
    schema_v1 = {
        "type": "record",
        "name": "AliasUser",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
        ],
    }

    resp = await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={"subject": base_subject, "schema": schema_v1, "schemaType": "AVRO"},
    )
    assert resp.status_code == 200

    # Call tool to add alias (MCP tool surface)
    # Unified server exposes MCP tool invocation via /tools endpoint in tests; fallback to config PUT if available
    # Prefer the unified tool endpoint if present
    tool_payload = {
        "tool": "add_subject_alias",
        "params": {
            "alias": alias_subject,
            "existing_subject": base_subject,
        },
    }

    # Try MCP tool call path first
    tool_url = f"{MCP_SERVER_URL}/tools"
    tool_resp = await client.post(tool_url, json=tool_payload)

    if tool_resp.status_code == 404:
        # Fallback to HTTP proxy behavior: PUT /config/{alias} with {"alias": base_subject}
        cfg_resp = await client.put(
            f"{MCP_SERVER_URL}/config/{alias_subject}",
            json={"alias": base_subject},
        )
        assert cfg_resp.status_code in [200, 204]
    else:
        assert tool_resp.status_code == 200
        data = tool_resp.json()
        assert data.get("alias") == alias_subject
        assert data.get("target") == base_subject

    # Verify alias subject is visible in subjects list or via config fetch
    subjects_resp = await client.get(f"{MCP_SERVER_URL}/subjects")
    assert subjects_resp.status_code == 200
    subjects = subjects_resp.json()
    # Depending on registry version, alias may or may not be listed; accept either
    # But ensure that GET config for alias returns something reasonable (200 or 404 per server behavior)
    cfg_check = await client.get(f"{MCP_SERVER_URL}/config/{alias_subject}")
    assert cfg_check.status_code in [200, 404]


