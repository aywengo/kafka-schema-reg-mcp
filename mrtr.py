"""SEP-2322 multi-round-trip (MRTR) guard helpers.

A guard tool runs once per round. On the first round it returns an
``InputRequiredResult`` and the modern client retries the same call with the
answers and the sealed ``request_state``. Legacy clients never understand that
result, so the same tool falls back to the in-request ``ctx.elicit`` handshake.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal, Mapping

import mcp_types
from fastmcp.server.context import Context
from pydantic import create_model

from protocol_version import current_protocol_version

MODERN_PROTOCOL_VERSION = "2026-07-28"


def is_modern_connection(ctx: Context | None = None) -> bool:
    """True when the active connection negotiated the 2026-07-28 era."""
    return current_protocol_version() >= MODERN_PROTOCOL_VERSION


def elicitation_request(message: str, requested_schema: dict[str, Any]) -> mcp_types.ElicitRequest:
    """Build the elicitation request carried inside an InputRequiredResult."""
    return mcp_types.ElicitRequest(
        params=mcp_types.ElicitRequestFormParams(message=message, requestedSchema=requested_schema)
    )


def input_required(
    requests: Mapping[str, Any],
    request_state: str | None = None,
) -> mcp_types.InputRequiredResult:
    """Suspend a modern call until the client supplies the requested input."""
    return mcp_types.InputRequiredResult(inputRequests=dict(requests), requestState=request_state)


async def guard(
    ctx: Context,
    *,
    requests: Mapping[str, Any] | Callable[[], Mapping[str, Any]],
    request_state: str | None = None,
    legacy: Callable[[], Awaitable[Any]],
) -> tuple[str, Any]:
    """Choose the right round for the connected client.

    Returns ``("responses", input_responses)`` on a retry, ``("suspend", result)``
    when a modern client must be asked, and ``("legacy", value)`` after the
    in-request elicitation fallback ran.
    """
    responses = ctx.input_responses
    if responses is not None:
        return "responses", responses
    if is_modern_connection(ctx):
        resolved = requests() if callable(requests) else requests
        return "suspend", input_required(resolved, request_state)
    return "legacy", await legacy()


_FIELD_TYPES = {
    "string": "string",
    "text": "string",
    "number": "number",
    "integer": "integer",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
}


def request_schema(request: Any) -> dict[str, Any]:
    """Convert the project's ElicitationRequest fields to a JSON form schema."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in getattr(request, "fields", []):
        prop: dict[str, Any] = {
            "type": _FIELD_TYPES.get(getattr(field, "type", "string"), "string"),
            "title": getattr(field, "label", None) or field.name.replace("_", " ").title(),
        }
        if getattr(field, "description", None):
            prop["description"] = field.description
        if getattr(field, "options", None):
            prop["enum"] = field.options
        if getattr(field, "default", None) is not None:
            prop["default"] = field.default
        properties[field.name] = prop
        if getattr(field, "required", False):
            required.append(field.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


async def ask_request(
    ctx: Context,
    request: Any,
    *,
    state: str | None = None,
) -> tuple[str, Any]:
    """Ask for an ElicitationRequest's fields on either protocol era.

    Returns ``("suspend", InputRequiredResult)``, ``("answered", values)`` or
    ``("declined", None)``.
    """
    schema = request_schema(request)
    message = getattr(request, "description", None) or getattr(request, "title", "Information required")
    return await ask(ctx, message=message, schema=schema, state=state)


async def ask(
    ctx: Context,
    *,
    message: str,
    schema: dict[str, Any],
    state: str | None = None,
) -> tuple[str, Any]:
    if ctx.input_responses is not None:
        response = next(iter(ctx.input_responses.values()))
        if getattr(response, "action", None) == "accept":
            return "answered", response.content or {}
        return "declined", None
    if is_modern_connection(ctx):
        return "suspend", input_required({"form": elicitation_request(message, schema)}, state)
    response = await ctx.elicit(message, response_type=_legacy_response_model(schema))
    if response.action == "accept":
        data = response.data
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        return "answered", data or {}
    return "declined", None


def _legacy_response_model(schema: dict[str, Any]):
    """Build a flat pydantic model for the legacy in-request elicitation path.

    FastMCP derives the wire schema from the model. A raw properties mapping is
    not a response type, and optional unions are rejected by strict clients, so
    every field gets one concrete primitive type and a default when optional.
    """
    type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    defaults = {"string": "", "number": 0.0, "integer": 0, "boolean": False, "array": [], "object": {}}

    fields: dict[str, Any] = {}
    for name, prop in properties.items():
        json_type = prop.get("type", "string")
        if prop.get("enum"):
            field_type = Literal.__getitem__(tuple(prop["enum"]))
        else:
            field_type = type_map.get(json_type, str)
        if name in required:
            fields[name] = (field_type, ...)
        else:
            default = prop.get("default")
            if default is None:
                default = prop["enum"][0] if prop.get("enum") else defaults.get(json_type, "")
            fields[name] = (field_type, default)
    return create_model("ElicitationResponse", **fields)


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
