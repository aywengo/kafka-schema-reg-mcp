"""Negotiated MCP protocol version.

FastMCP 4 serves both the handshake era (``2025-11-25`` and older) and the
modern per-request era (``2026-07-28``) from one process. Tool responses report
the version negotiated for the current request instead of a hard-coded literal.
Outside a request (import time, direct unit-test calls) the modern default is
returned.
"""

from __future__ import annotations

DEFAULT_PROTOCOL_VERSION = "2026-07-28"


def current_protocol_version() -> str:
    """Return the protocol version negotiated for the active request."""
    try:
        from fastmcp.server.dependencies import get_context

        request_context = getattr(get_context(), "request_context", None)
        version = getattr(request_context, "protocol_version", None)
        if version:
            return str(version)
    except Exception:
        pass
    return DEFAULT_PROTOCOL_VERSION
