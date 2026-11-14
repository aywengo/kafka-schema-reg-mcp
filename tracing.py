"""Continue a caller's W3C trace and attribute the tool span (#201).

FastMCP opens one SERVER span per request and parents it from JSON-RPC
``_meta``. Callers in the SRE stack send ``traceparent`` and ``tracestate``
on the HTTP request instead, so this module attaches those two headers for
the request. The tool span FastMCP already opened then becomes a child of
the caller's span.

Export is OTLP over HTTP, and only when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is
set. Baggage is not read and not written. Schema documents, credentials,
and exception messages are not exported.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import re
from collections.abc import Mapping
from typing import Any

from fastmcp.exceptions import AuthorizationError
from fastmcp.server.middleware import Middleware
from opentelemetry import context as otel_context
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
SERVICE_ENV = "OTEL_SERVICE_NAME"
DEFAULT_SERVICE_NAME = "kafka-schema-registry-mcp"

#: W3C trace context only. The composite propagator would also carry baggage.
PROPAGATOR = TraceContextTextMapPropagator()

_TRACE_HEADERS = frozenset({"traceparent", "tracestate"})

#: Longer than any subject or schema id this server addresses. A schema
#: document pasted into an allowlisted argument is left off the span.
_MAX_IDENTITY_LENGTH = 256

#: One name token. A schema document, space, or credential URL does not match.
_NAME_TOKEN = re.compile(r"^[A-Za-z0-9._:-]+$")

_NAME_FIELDS = frozenset(
    {
        "subject",
        "source_subject",
        "target_subject",
        "context",
        "registry",
        "source_registry",
        "target_registry",
    }
)

#: Result statuses that are a failed call. dry_run, applied, and
#: confirmation_required stay ok.
_FAILURE_STATUS = frozenset({"rejected", "incomplete", "compatibility_error", "error"})

# Argument name to span attribute. Anything else on the call, including
# schema documents and secrets, is ignored.
_IDENTITY: dict[str, str] = {
    "subject": "schema.subject",
    "source_subject": "schema.source_subject",
    "target_subject": "schema.target_subject",
    "context": "schema.context",
    "registry": "schema.registry",
    "source_registry": "schema.source_registry",
    "target_registry": "schema.target_registry",
    "schema_id": "schema.id",
    "version": "schema.version",
}

_provider: Any = None


def configure(environ: Mapping[str, str] | None = None) -> bool:
    """Install an OTLP/HTTP exporter when the endpoint is set.

    An empty endpoint leaves the no-op provider in place. A second call
    does not replace a provider this function already installed.

    Args:
        environ: Environment to read. Defaults to ``os.environ``.

    Returns:
        Whether this process exports traces.
    """
    global _provider
    if _provider is not None:
        return True
    env = os.environ if environ is None else environ
    endpoint = env.get(ENDPOINT_ENV, "").strip()
    if not endpoint:
        logger.debug("no %s; trace export is off", ENDPOINT_ENV)
        return False

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service = env.get(SERVICE_ENV, "").strip() or DEFAULT_SERVICE_NAME
    url = _traces_endpoint(endpoint)
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    # Before the exporter, so a status description or exception event that
    # FastMCP records never leaves the process.
    provider.add_span_processor(_DropExceptionDetail())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url)))
    trace_api.set_tracer_provider(provider)
    _provider = provider
    atexit.register(_shutdown)
    logger.info("exporting traces to %s as %s", url, service)
    return True


def _traces_endpoint(endpoint: str) -> str:
    """The traces URL. ``endpoint`` is the OTLP base, as the spec defines it."""
    base = endpoint.rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return f"{base}/v1/traces"


class _DropExceptionDetail(SpanProcessor):
    """Remove exception text from a span before it is exported.

    FastMCP sets the status description to the exception message and records
    an exception event. That message can hold a token or a schema body.
    ``mcp.outcome`` and ``error.type`` stay.
    """

    def on_end(self, span: Any) -> None:
        """Clear the description and drop exception events."""
        _strip_exception_detail(span)


def _strip_exception_detail(span: Any) -> None:
    """Clear an error status description and drop exception events."""
    status = getattr(span, "status", None)
    if status is not None and status.status_code is StatusCode.ERROR and status.description:
        span._status = Status(status.status_code)
    events = getattr(span, "_events", None)
    if events is None:
        return
    kept = tuple(event for event in events if getattr(event, "name", None) != "exception")
    if len(kept) != len(tuple(events)):
        span._events = kept


def _shutdown() -> None:
    """Flush the exporter. Safe to call more than once."""
    global _provider
    provider, _provider = _provider, None
    if provider is None:
        return
    try:
        provider.force_flush()
    except Exception:
        logger.debug("trace flush failed", exc_info=True)
    try:
        provider.shutdown()
    except Exception:
        logger.debug("trace shutdown failed", exc_info=True)


def carrier_from_scope(scope: Mapping[str, Any]) -> dict[str, str]:
    """``traceparent`` and ``tracestate`` from an ASGI scope. Baggage is ignored."""
    found: dict[str, str] = {}
    raw = scope.get("headers") or ()
    for item in raw:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        name = _as_text(item[0])
        value = _as_text(item[1])
        if name is None or value is None:
            continue
        key = name.lower()
        if key == "tracestate":
            # A request may repeat tracestate. Keep every field, in order.
            found[key] = f"{found[key]},{value}" if key in found else value
        elif key in _TRACE_HEADERS:
            found[key] = value
    return found


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("latin-1")
    return None


def attach_carrier(carrier: Mapping[str, str]) -> Any:
    """Attach the extracted context. The caller detaches the returned token."""
    return otel_context.attach(PROPAGATOR.extract(dict(carrier)))


class TraceContextMiddleware:
    """Continue the caller's trace for one HTTP request.

    Pure ASGI, not ``BaseHTTPMiddleware``, so a streamable-HTTP body is not
    buffered. A request with no ``traceparent`` keeps the current context,
    and the span FastMCP opens starts its own trace.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Mapping[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        token = attach_carrier(carrier_from_scope(scope))
        try:
            await self.app(scope, receive, send)
        finally:
            otel_context.detach(token)


def asgi_middleware() -> list[Any]:
    """The Starlette middleware list ``mcp.run`` accepts."""
    from starlette.middleware import Middleware

    return [Middleware(TraceContextMiddleware)]


def inject_outbound(headers: Any) -> None:
    """Add ``traceparent`` and ``tracestate`` for the current span.

    Nothing else is written. A context with no valid span adds no header.
    """
    carrier: dict[str, str] = {}
    PROPAGATOR.inject(carrier)
    for key, value in carrier.items():
        headers[key] = value


def identity_attributes(arguments: Mapping[str, Any] | None) -> dict[str, str | int]:
    """Allowlisted subject and schema identifiers. No payloads."""
    if not arguments:
        return {}
    attrs: dict[str, str | int] = {}
    for name, attribute in _IDENTITY.items():
        if name not in arguments:
            continue
        value = _identity_value(name, arguments[name])
        if value is not None:
            attrs[attribute] = value
    return attrs


def _identity_value(name: str, value: Any) -> str | int | None:
    """A subject, registry, schema id, or version. Payloads and URLs are omitted."""
    if isinstance(value, bool) or value is None:
        return None
    if name == "schema_id":
        if isinstance(value, int) and value >= 0:
            return value
        return None
    if name == "version":
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str):
            return _name_token(value)
        return None
    if name in _NAME_FIELDS and isinstance(value, str):
        return _name_token(value)
    return None


def _name_token(value: str) -> str | None:
    """A single name token, or None when the value is a payload or URL."""
    text = value.strip()
    if text and len(text) <= _MAX_IDENTITY_LENGTH and _NAME_TOKEN.fullmatch(text):
        return text
    return None


def outcome_of(result: Any) -> str:
    """``ok`` or ``error`` for a result that did not raise.

    A dict from ``create_error_response`` has an ``error`` string and no
    schema body. ``rejected``, ``incomplete``, ``compatibility_error``,
    and ``error`` are failures. A migration with failed attempts and no
    successful attempt is a failure. ``dry_run``, ``applied``,
    ``confirmation_required``, and ``cancelled`` are not. The message
    itself is not an attribute. A result that carries a schema body is a
    successful read, not that error shape.
    """
    if getattr(result, "is_error", False):
        return "error"
    body = _result_body(result)
    if _is_failure(body):
        return "error"
    return "ok"


def _is_failure(body: Any) -> bool:
    """Whether a result body reports a failed call."""
    if not isinstance(body, dict):
        return False
    if isinstance(body.get("error"), str) and "schema" not in body:
        return True
    status = body.get("status")
    if isinstance(status, str) and status in _FAILURE_STATUS:
        return True
    failed = body.get("failed_migrations")
    successful = body.get("successful_migrations")
    return isinstance(failed, int) and not isinstance(failed, bool) and failed > 0 and successful == 0


def _result_body(result: Any) -> Any:
    """Structured content, a dict result, or one JSON object in text content."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    if isinstance(result, dict):
        return result
    text = _text_content(result)
    if text is None:
        return None
    return _json_object(text)


def _text_content(result: Any) -> str | None:
    """The text of a single text block. Mixed content is left unread."""
    content = getattr(result, "content", None)
    if not isinstance(content, list) or len(content) != 1:
        return None
    block = content[0]
    text = getattr(block, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(block, dict) and isinstance(block.get("text"), str):
        return block["text"]
    return None


def _json_object(text: str) -> dict[str, Any] | None:
    """A JSON object. Other text, including a schema document, is ignored."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _call_attributes(context: Any) -> dict[str, str | int]:
    message = getattr(context, "message", None)
    name = getattr(message, "name", None)
    arguments = getattr(message, "arguments", None)
    attrs = identity_attributes(arguments if isinstance(arguments, Mapping) else None)
    if isinstance(name, str) and name:
        attrs["mcp.tool"] = name
    return attrs


def _set_outcome(span: Any, outcome: str) -> None:
    if not span.is_recording():
        return
    span.set_attribute("mcp.outcome", outcome)
    if outcome != "ok":
        span.set_status(Status(StatusCode.ERROR))


class ToolCallSpans(Middleware):
    """Write tool identity and outcome onto the span FastMCP already opened."""

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        """Attribute the current span, then let the tool run."""
        span = trace_api.get_current_span()
        if span.is_recording():
            span.set_attributes(_call_attributes(context))
        try:
            result = await call_next(context)
        except AuthorizationError:
            _set_outcome(span, "refused")
            raise
        except Exception:
            _set_outcome(span, "error")
            raise
        _set_outcome(span, outcome_of(result))
        return result
