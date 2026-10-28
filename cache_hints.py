"""Per-resource SEP-2549 cache hints (v3.1 M4).

One table maps a `resources/read` URI to the `ttlMs` / `cacheScope` the server
emits for it. The server-level `cache_ttl` in `get_fastmcp_config` stays the
positive hint for the list methods and `server/discover`; it cannot express
`ttlMs` 0, and FastMCP has no per-component argument, so per-resource rows are
stamped on the wire result instead.

FastMCP's own `Middleware.on_read_resource` returns a `ResourceResult` that is
converted to the wire `ReadResourceResult` after the middleware chain, so the
cache fields cannot be set there. The hook that works is the SDK request
handler: `install_read_resource_hints` wraps the `resources/read` handler
FastMCP registered and sets `ttl_ms` / `cache_scope` on the returned
`ReadResourceResult`. The SDK runner's `apply_cache_hint` fills only fields the
handler left unset, so the stamped values win over the server-level default.

Tests read `hint_for` directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

CacheScope = Literal["public", "private"]

SCHEMA_BY_ID_TTL_MS = 86_400_000
LATEST_TTL_MS = 15_000
COLLECTION_TTL_MS = 60_000
STALE_TTL_MS = 0


@dataclass(frozen=True, slots=True)
class ResourceCacheHint:
    """What the server says about one resource read."""

    ttl_ms: int
    cache_scope: CacheScope = "private"

    def __post_init__(self) -> None:
        if self.ttl_ms < 0:
            raise ValueError(f"ttl_ms must be >= 0, got {self.ttl_ms}")


# Rows from docs/v3.1-roadmap.md section 5, in evaluation order. The first
# matching pattern wins; the final row is the default for any other read.
# Patterns match the path of the URI (everything after `scheme://`).
_ROWS: tuple[tuple[str, re.Pattern[str], ResourceCacheHint], ...] = (
    # schema://{name}/ids/{schema_id} — immutable body, one day.
    ("schema", re.compile(r"^[^/]+/ids/\d+$"), ResourceCacheHint(SCHEMA_BY_ID_TTL_MS)),
    # Version lists (collections), before the latest-schema rows so the
    # `/versions` suffix is not read as a subject.
    ("schema", re.compile(r"^[^/]+/(?:[^/]+/)?[^/]+/versions$"), ResourceCacheHint(COLLECTION_TTL_MS)),
    # schema://{name}/{subject} and schema://{name}/{context}/{subject} — latest.
    ("schema", re.compile(r"^[^/]+/(?:[^/]+/)?[^/]+$"), ResourceCacheHint(LATEST_TTL_MS)),
    # subject://…/config, subject://…/mode.
    ("subject", re.compile(r"^.+/(?:config|mode)$"), ResourceCacheHint(LATEST_TTL_MS)),
    # registry://{name}/tasks, registry://{name}/migrations — stale on arrival.
    ("registry", re.compile(r"^[^/]+/(?:tasks|migrations)$"), ResourceCacheHint(STALE_TTL_MS)),
    # registry://{name}/config, registry://mode, registry://mode/{name}.
    ("registry", re.compile(r"^[^/]+/config$"), ResourceCacheHint(LATEST_TTL_MS)),
    ("registry", re.compile(r"^mode(?:/[^/]+)?$"), ResourceCacheHint(LATEST_TTL_MS)),
    # The other registry:// collections: names, info, status, subjects, contexts.
    ("registry", re.compile(r"^(?:names|info|status)(?:/[^/]+)?$"), ResourceCacheHint(COLLECTION_TTL_MS)),
    ("registry", re.compile(r"^[^/]+/(?:subjects|contexts)$"), ResourceCacheHint(COLLECTION_TTL_MS)),
    ("registry", re.compile(r"^[^/]+/contexts/[^/]+/subjects$"), ResourceCacheHint(COLLECTION_TTL_MS)),
)

DEFAULT_HINT = ResourceCacheHint(STALE_TTL_MS)


def _split(uri: str) -> tuple[str, str]:
    scheme, _, rest = uri.partition("://")
    if not rest:
        return "", ""
    # Drop a query string; the hint is about the resource, not its filters.
    path = urlsplit(f"x://{rest}").netloc + urlsplit(f"x://{rest}").path
    return scheme, path.rstrip("/")


def hint_for(uri: str) -> ResourceCacheHint:
    """Return the hint for a `resources/read` URI. Unknown URIs are stale."""
    scheme, path = _split(str(uri))
    for row_scheme, pattern, hint in _ROWS:
        if scheme == row_scheme and pattern.match(path):
            return hint
    return DEFAULT_HINT


def stamp(result: Any, uri: str) -> Any:
    """Set `ttl_ms` / `cache_scope` on a wire `ReadResourceResult`.

    Anything that is not a `ReadResourceResult` (an `InputRequiredResult`, a
    mapping an extension owns) is returned unchanged.
    """
    from mcp_types import ReadResourceResult

    if not isinstance(result, ReadResourceResult):
        return result
    hint = hint_for(uri)
    return result.model_copy(update={"ttl_ms": hint.ttl_ms, "cache_scope": hint.cache_scope})


def install_read_resource_hints(server: Any) -> None:
    """Wrap the low-level `resources/read` handler of a FastMCP server.

    `server` is the FastMCP instance (or an `EditionGate` around one). The
    wrapper calls the handler FastMCP registered and stamps its result.
    """
    low_level = getattr(server, "_mcp_server", None)
    if low_level is None:  # pragma: no cover - defensive; FastMCP always has it
        raise RuntimeError("install_read_resource_hints needs a FastMCP server")

    entry = low_level._request_handlers.get("resources/read")
    if entry is None:  # pragma: no cover - FastMCP always registers it
        raise RuntimeError("FastMCP has not registered a resources/read handler")
    params_type, inner = entry.params_type, entry.handler

    async def read_resource_with_hints(ctx: Any, params: Any) -> Any:
        result = await inner(ctx, params)
        return stamp(result, str(params.uri))

    low_level.add_request_handler("resources/read", params_type, read_resource_with_hints)
