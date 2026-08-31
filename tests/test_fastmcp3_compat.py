"""FastMCP 3.4 compatibility checks (issue #177 Phase 1)."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from fastmcp.server.auth import JWTVerifier

sys.path.insert(0, str(Path(__file__).parent.parent))

import oauth_provider
from kafka_schema_registry_unified_mcp import mcp


def test_bearer_auth_provider_is_gone() -> None:
    """FastMCP 3 removed BearerAuthProvider; JWTVerifier is the replacement."""
    import fastmcp.server.auth as auth

    assert not hasattr(auth, "BearerAuthProvider")
    assert JWTVerifier is not None


def test_server_lists_tools_via_list_tools() -> None:
    """FastMCP 3 uses list_tools() (Sequence[Tool]), not get_tools() (dict)."""
    assert hasattr(mcp, "list_tools")
    assert not hasattr(mcp, "get_tools")


@pytest.mark.asyncio
async def test_list_tools_returns_named_tools() -> None:
    tools = await mcp.list_tools()
    assert isinstance(tools, Sequence)
    assert tools
    names = {t.name for t in tools if getattr(t, "name", None)}
    assert "ping" in names


def test_jwt_verifier_accepts_project_kwargs() -> None:
    """JWTVerifier must construct from our FastMCP 3 helper kwargs."""
    kwargs: dict[str, Any] = oauth_provider._fastmcp_jwt_verifier_kwargs()
    assert "jwks_uri" in kwargs or "public_key" in kwargs
    verifier = JWTVerifier(**kwargs)
    assert verifier.issuer == oauth_provider.AUTH_ISSUER_URL
