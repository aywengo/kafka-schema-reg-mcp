"""Edition catalog snapshots and resolution precedence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _run(code: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **env}
    for key in ("MCP_EDITION", "MCP_EDITION_DEFAULT", "SLIM_MODE"):
        if key not in env:
            full_env.pop(key, None)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


TOOLS_CODE = """
import asyncio, json
from fastmcp import Client
import kafka_schema_registry_unified_mcp as m
async def main():
    async with Client(m.mcp) as c:
        print(json.dumps(sorted(t.name for t in await c.list_tools())))
asyncio.run(main())
"""


def _tools(env: dict[str, str]) -> list[str]:
    result = _run(TOOLS_CODE, env)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_viewer_edition_snapshot():
    from edition import Edition
    from tool_catalog import TOOL_CATALOG

    expected = sorted(s.name for s in TOOL_CATALOG.values() if s.min_edition <= Edition.VIEWER)
    assert len(expected) == 39
    assert _tools({"MCP_EDITION": "viewer"}) == expected


def test_editor_edition_snapshot():
    from edition import Edition
    from tool_catalog import TOOL_CATALOG

    expected = sorted(s.name for s in TOOL_CATALOG.values() if s.min_edition <= Edition.EDITOR)
    assert len(expected) == 42
    assert _tools({"MCP_EDITION": "editor"}) == expected


def test_admin_final_snapshot():
    from edition import Edition
    from tool_catalog import TOOL_CATALOG

    expected = sorted(s.name for s in TOOL_CATALOG.values() if s.min_edition <= Edition.ADMIN)
    assert len(expected) == 66
    assert _tools({"MCP_EDITION": "admin"}) == expected


def test_default_edition_is_viewer():
    assert len(_tools({})) == 39


def test_image_default_applies_when_operator_is_silent():
    assert len(_tools({"MCP_EDITION_DEFAULT": "editor"})) == 42


def test_slim_mode_alias_selects_editor():
    assert len(_tools({"SLIM_MODE": "true"})) == 42


def test_explicit_edition_wins_over_image_default():
    assert len(_tools({"MCP_EDITION": "admin", "MCP_EDITION_DEFAULT": "viewer"})) == 66


def test_editor_config_example_selects_editor():
    config = json.loads((ROOT / "config-examples/claude_desktop_editor_config.json").read_text())
    env = config["mcpServers"]["kafka-schema-registry"]["env"]
    assert env["MCP_EDITION"] == "editor"
    assert len(_tools({"MCP_EDITION": env["MCP_EDITION"]})) == 42


def test_explicit_edition_and_slim_mode_conflict():
    result = _run("import kafka_schema_registry_unified_mcp", {"MCP_EDITION": "viewer", "SLIM_MODE": "true"})
    assert result.returncode != 0
    assert "SLIM_MODE" in result.stderr


def test_scope_definitions_are_generated_from_catalog():
    from oauth_provider import SCOPE_DEFINITIONS
    from tool_catalog import TOOL_CATALOG

    read = sorted(n for n, s in TOOL_CATALOG.items() if s.scope == "read")
    write = sorted(n for n, s in TOOL_CATALOG.items() if s.scope == "write")
    admin = sorted(n for n, s in TOOL_CATALOG.items() if s.scope == "admin")
    assert SCOPE_DEFINITIONS["read"]["includes"] == read
    assert SCOPE_DEFINITIONS["write"]["includes"] == read + write
    assert SCOPE_DEFINITIONS["admin"]["includes"] == read + write + admin


def test_statistics_tools_are_catalogued_as_tasks():
    from tool_catalog import TOOL_CATALOG

    assert TOOL_CATALOG["count_schemas"].task
    assert TOOL_CATALOG["get_registry_statistics"].task


def test_unknown_edition_fails_fast():
    result = _run("import kafka_schema_registry_unified_mcp", {"MCP_EDITION": "superuser"})
    assert result.returncode != 0
    assert "not a valid edition" in result.stderr


def test_planner_tools_are_read_only():
    from tool_catalog import TOOL_CATALOG

    for name in (
        "guided_schema_evolution",
        "guided_schema_migration",
        "guided_context_reorganization",
        "guided_disaster_recovery",
        "bulk_operations_wizard",
    ):
        spec = TOOL_CATALOG[name]
        assert spec.mutates is False
        assert spec.annotations.read_only_hint is True
