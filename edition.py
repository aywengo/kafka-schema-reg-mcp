"""Edition resolution for the Kafka Schema Registry MCP server.

An edition decides which tools, prompts and resources are registered. It is
resolved once at import time and never changes for the lifetime of a process.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum


class Edition(IntEnum):
    VIEWER = 1
    EDITOR = 2
    ADMIN = 3


_NAMES = {
    "viewer": Edition.VIEWER,
    "editor": Edition.EDITOR,
    "admin": Edition.ADMIN,
}


@dataclass(frozen=True)
class EditionResolution:
    edition: Edition
    source: str


def _parse(value: str, variable: str) -> Edition:
    try:
        return _NAMES[value.strip().lower()]
    except KeyError:
        valid = ", ".join(_NAMES)
        raise RuntimeError(f"{variable}={value!r} is not a valid edition; choose one of: {valid}") from None


def _is_slim() -> bool:
    return os.getenv("SLIM_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_edition() -> EditionResolution:
    """Resolve the active edition using the documented precedence order."""
    explicit = os.getenv("MCP_EDITION")
    slim = _is_slim()

    if explicit and slim:
        raise RuntimeError(
            "MCP_EDITION and SLIM_MODE are both set. SLIM_MODE is a deprecated alias for "
            "MCP_EDITION=editor; set only one of them."
        )

    if explicit:
        return EditionResolution(_parse(explicit, "MCP_EDITION"), "MCP_EDITION")

    if slim:
        return EditionResolution(Edition.EDITOR, "SLIM_MODE alias")

    image_default = os.getenv("MCP_EDITION_DEFAULT")
    if image_default:
        return EditionResolution(_parse(image_default, "MCP_EDITION_DEFAULT"), "MCP_EDITION_DEFAULT")

    return EditionResolution(Edition.VIEWER, "default")


def edition_name(edition: Edition) -> str:
    return edition.name.lower()
