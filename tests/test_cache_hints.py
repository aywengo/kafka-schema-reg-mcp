"""Per-resource SEP-2549 cache hints (v3.1 M4, docs/v3.1-roadmap.md section 5)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import mcp_types as t
import pytest
from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cache_hints  # noqa: E402
from cache_hints import (  # noqa: E402
    COLLECTION_TTL_MS,
    LATEST_TTL_MS,
    SCHEMA_BY_ID_TTL_MS,
    STALE_TTL_MS,
    hint_for,
    stamp,
)

# ---- the table ------------------------------------------------------------


@pytest.mark.parametrize(
    "uri, ttl_ms",
    [
        ("schema://prod/ids/42", SCHEMA_BY_ID_TTL_MS),
        ("schema://prod/user-events", LATEST_TTL_MS),
        ("schema://prod/users/user-events", LATEST_TTL_MS),
        ("schema://prod/user-events/versions", COLLECTION_TTL_MS),
        ("schema://prod/users/user-events/versions", COLLECTION_TTL_MS),
        ("subject://prod/user-events/config", LATEST_TTL_MS),
        ("subject://prod/users/user-events/config", LATEST_TTL_MS),
        ("subject://prod/user-events/mode", LATEST_TTL_MS),
        ("subject://prod/users/user-events/mode", LATEST_TTL_MS),
        ("registry://prod/config", LATEST_TTL_MS),
        ("registry://mode", LATEST_TTL_MS),
        ("registry://mode/prod", LATEST_TTL_MS),
        ("registry://names", COLLECTION_TTL_MS),
        ("registry://info", COLLECTION_TTL_MS),
        ("registry://info/prod", COLLECTION_TTL_MS),
        ("registry://status", COLLECTION_TTL_MS),
        ("registry://status/prod", COLLECTION_TTL_MS),
        ("registry://prod/subjects", COLLECTION_TTL_MS),
        ("registry://prod/contexts", COLLECTION_TTL_MS),
        ("registry://prod/contexts/users/subjects", COLLECTION_TTL_MS),
        ("registry://prod/tasks", STALE_TTL_MS),
        ("registry://prod/migrations", STALE_TTL_MS),
        ("registry://prod/something-new", STALE_TTL_MS),
        ("other://anything", STALE_TTL_MS),
        ("not a uri", STALE_TTL_MS),
    ],
)
def test_table_rows(uri: str, ttl_ms: int):
    hint = hint_for(uri)
    assert hint.ttl_ms == ttl_ms
    assert hint.cache_scope == "private"


def test_query_string_does_not_change_the_row():
    assert hint_for("registry://prod/subjects?context=users").ttl_ms == COLLECTION_TTL_MS


def test_schema_body_is_private_even_though_immutable():
    assert hint_for("schema://prod/ids/1").cache_scope == "private"


def test_negative_ttl_is_rejected():
    with pytest.raises(ValueError):
        cache_hints.ResourceCacheHint(-1)


# ---- stamping -------------------------------------------------------------


def test_stamp_sets_fields_as_explicitly_set():
    result = t.ReadResourceResult(contents=[])
    assert "ttl_ms" not in result.model_fields_set
    stamped = stamp(result, "registry://prod/tasks")
    assert stamped.ttl_ms == 0
    assert stamped.cache_scope == "private"
    # apply_cache_hint only fills unset fields, so these must be marked set.
    assert {"ttl_ms", "cache_scope"} <= stamped.model_fields_set


def test_stamp_leaves_other_results_alone():
    sentinel = object()
    assert stamp(sentinel, "registry://prod/tasks") is sentinel


# ---- through the server ---------------------------------------------------


@pytest.fixture
def server():
    import kafka_schema_registry_unified_mcp as m

    return m


async def _read(client: Client, uri: str) -> t.ReadResourceResult:
    return await client.session.send_request(
        t.ReadResourceRequest(params=t.ReadResourceRequestParams(uri=uri)),
        t.ReadResourceResult,
    )


@pytest.mark.asyncio
async def test_tasks_resource_is_stale_on_the_wire(server):
    """The constructor's 60 s default must not reach a task resource read."""
    async with Client(server.mcp) as client:
        result = await _read(client, "registry://default/tasks")
    assert result.ttl_ms == 0
    assert result.cache_scope == "private"


@pytest.mark.asyncio
async def test_migrations_resource_is_stale_on_the_wire(server):
    async with Client(server.mcp) as client:
        result = await _read(client, "registry://default/migrations")
    assert result.ttl_ms == 0


@pytest.mark.asyncio
async def test_schema_by_id_resource_routes_and_carries_one_day(server, monkeypatch):
    seen: list[tuple] = []

    def fake_get_schema_by_id(schema_id, *args, **kwargs):
        seen.append((schema_id,))
        return {"id": schema_id, "schema": "{}", "schemaType": "AVRO"}

    monkeypatch.setattr(server, "get_schema_by_id_tool", fake_get_schema_by_id)
    async with Client(server.mcp) as client:
        result = await _read(client, "schema://default/ids/42")
    assert seen == [(42,)]
    assert result.ttl_ms == SCHEMA_BY_ID_TTL_MS
    assert result.cache_scope == "private"
    assert '"resource_uri": "schema://default/ids/42"' in result.contents[0].text


@pytest.mark.asyncio
async def test_default_context_versions_template_is_not_shadowed(server, monkeypatch):
    """`schema://{name}/{subject}/versions` must win over `schema://{name}/{context}/{subject}`."""
    called: list[str] = []
    monkeypatch.setattr(server, "get_schema_tool", lambda *a, **k: (called.append("schema"), {"schema": "{}"})[1])
    monkeypatch.setattr(
        server, "get_schema_versions_tool", lambda *a, **k: (called.append("versions"), {"versions": [1]})[1]
    )
    async with Client(server.mcp) as client:
        result = await _read(client, "schema://default/user-events/versions")
    assert called == ["versions"]
    assert result.ttl_ms == COLLECTION_TTL_MS


@pytest.mark.asyncio
async def test_list_hint_is_the_constructor_default(server):
    async with Client(server.mcp) as client:
        result = await client.session.send_request(t.ListToolsRequest(), t.ListToolsResult)
    assert result.ttl_ms == 60_000


# ---- list scope follows auth ---------------------------------------------

SCOPE_CODE = """
from oauth_provider import get_fastmcp_config
print(get_fastmcp_config("t")["cache_scope"])
"""


def _list_scope(env: dict[str, str]) -> str:
    full_env = {**os.environ, **env}
    result = subprocess.run(
        [sys.executable, "-c", SCOPE_CODE], cwd=ROOT, env=full_env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout.strip().splitlines()[-1]


def test_list_scope_is_public_with_auth_off():
    assert _list_scope({"ENABLE_AUTH": "false"}) == "public"


def test_list_scope_is_private_with_auth_on():
    assert (
        _list_scope(
            {
                "ENABLE_AUTH": "true",
                "AUTH_ISSUER_URL": "https://issuer.example",
                "AUTH_AUDIENCE": "test",
            }
        )
        == "private"
    )
