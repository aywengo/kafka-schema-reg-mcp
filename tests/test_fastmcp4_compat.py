"""FastMCP 4 compatibility checks (v3.0 / issue #187)."""

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
    """FastMCP 3+ removed BearerAuthProvider; JWTVerifier is the replacement."""
    import fastmcp.server.auth as auth

    assert not hasattr(auth, "BearerAuthProvider")
    assert JWTVerifier is not None


def test_server_lists_tools_via_list_tools() -> None:
    """FastMCP 3+ uses list_tools() (Sequence[Tool]), not get_tools() (dict)."""
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
    """JWTVerifier must construct from our FastMCP 4 helper kwargs."""
    kwargs: dict[str, Any] = oauth_provider._fastmcp_jwt_verifier_kwargs()
    assert "jwks_uri" in kwargs or "public_key" in kwargs
    verifier = JWTVerifier(**kwargs)
    assert verifier.issuer == oauth_provider.AUTH_ISSUER_URL


@pytest.mark.asyncio
async def test_jwt_verifier_rejects_wrong_issuer() -> None:
    """The issuer check still rejects a token minted by another issuer."""
    import time

    import jwt

    secret = "compat-test-secret-compat-test-secret"
    verifier = JWTVerifier(public_key=secret, issuer="https://good.example", algorithm="HS256")
    now = int(time.time())
    claims = {"sub": "user", "aud": "api", "exp": now + 300, "iat": now}

    wrong = jwt.encode({**claims, "iss": "https://evil.example"}, secret, algorithm="HS256")
    right = jwt.encode({**claims, "iss": "https://good.example"}, secret, algorithm="HS256")

    assert await verifier.verify_token(wrong) is None
    assert await verifier.verify_token(right) is not None
