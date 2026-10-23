"""Registration gate that applies the active edition to the catalog."""

from __future__ import annotations

from typing import Any

from fastmcp.server.auth import require_scopes

from edition import Edition
from tool_catalog import PROMPT_CATALOG, catalog_name, spec_for


class EditionGate:
    """Proxy a FastMCP instance, registering only active-edition components."""

    def __init__(self, server: Any, edition: Edition, *, auth_enabled: bool = False):
        self._server = server
        self.edition = edition
        self.auth_enabled = auth_enabled

    def tool(self, *args: Any, **kwargs: Any):
        def decorator(fn):
            spec = spec_for(fn.__name__)
            if spec is None or spec.min_edition > self.edition:
                return fn
            options = dict(kwargs)
            public_name = catalog_name(fn.__name__)
            if public_name != fn.__name__:
                options["name"] = public_name
            if spec.task and "task" not in options:
                options["task"] = True
            if self.auth_enabled and spec.scope and "auth" not in options:
                options["auth"] = require_scopes(spec.scope)
            return self._server.tool(*args, **options)(fn)

        return decorator

    def prompt(self, *args: Any, **kwargs: Any):
        name = kwargs.get("name")
        spec = PROMPT_CATALOG.get(name)
        if spec is None or spec.min_edition > self.edition:
            return lambda fn: fn
        return self._server.prompt(*args, **kwargs)

    def resource(self, *args: Any, **kwargs: Any):
        return self._server.resource(*args, **kwargs)

    def add_extension(self, *args: Any, **kwargs: Any):
        return self._server.add_extension(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._server, name)
