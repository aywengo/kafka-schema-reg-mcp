"""Resources require the read scope when authentication is enabled."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types

if importlib.util.find_spec("mcp_types") is None:
    _stub = types.ModuleType("mcp_types")

    class _ToolAnnotations:
        """Stand-in for the generated mcp_types.ToolAnnotations."""

        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    _stub.ToolAnnotations = _ToolAnnotations  # type: ignore[attr-defined]
    sys.modules["mcp_types"] = _stub

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, AuthContext, require_scopes

from edition import Edition
from edition_gate import EditionGate


def _token(scopes: list[str]) -> AccessToken:
    return AccessToken(token="t", client_id="c", scopes=scopes, expires_at=None)


def _registered(gate: EditionGate, uri: str):
    resources = asyncio.run(gate._server._local_provider.list_resources())
    matched = [resource for resource in resources if str(resource.uri) == uri]
    assert len(matched) == 1
    return matched[0]


def test_auth_on_resource_requires_read() -> None:
    gate = EditionGate(FastMCP("gate"), Edition.ADMIN, auth_enabled=True)

    @gate.resource("schema://example")
    def example() -> str:
        return "{}"

    resource = _registered(gate, "schema://example")
    assert resource.auth is not None
    assert resource.auth(AuthContext(token=_token(["read"]), component=resource)) is True
    assert resource.auth(AuthContext(token=_token(["write"]), component=resource)) is False
    assert resource.auth(AuthContext(token=None, component=resource)) is False


def test_auth_off_resource_has_no_check() -> None:
    gate = EditionGate(FastMCP("gate"), Edition.ADMIN, auth_enabled=False)

    @gate.resource("schema://open")
    def example() -> str:
        return "{}"

    resource = _registered(gate, "schema://open")
    assert resource.auth is None


def test_explicit_resource_auth_is_kept() -> None:
    gate = EditionGate(FastMCP("gate"), Edition.ADMIN, auth_enabled=True)

    @gate.resource("schema://custom", auth=require_scopes("admin"))
    def example() -> str:
        return "{}"

    resource = _registered(gate, "schema://custom")
    assert resource.auth is not None
    assert resource.auth(AuthContext(token=_token(["admin"]), component=resource)) is True
    assert resource.auth(AuthContext(token=_token(["read"]), component=resource)) is False
