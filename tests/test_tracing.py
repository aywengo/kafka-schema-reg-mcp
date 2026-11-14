"""W3C traceparent continuation (#201). No Docker and no collector."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp.exceptions import AuthorizationError
from fastmcp.tools.base import ToolResult
from opentelemetry import baggage
from opentelemetry import context as otel_context
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tracing  # noqa: E402
from schema_validation import create_error_response  # noqa: E402
from tracing import (  # noqa: E402
    ToolCallSpans,
    TraceContextMiddleware,
    _DropExceptionDetail,
    asgi_middleware,
    configure,
    inject_outbound,
)

CALLER = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT_ID = "00f067aa0ba902b7"
TRACE_STATE = "congo=t61rcWkgMzE"
BAGGAGE = "password=hunter2"
SCHEMA = {"type": "record", "name": "User", "fields": [{"name": "id", "type": "string"}]}


class _Memory:
    def __init__(self, tracer: Any, exporter: InMemorySpanExporter) -> None:
        self.tracer = tracer
        self.exporter = exporter


@pytest.fixture
def memory() -> Iterator[_Memory]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    try:
        yield _Memory(provider.get_tracer("test"), exporter)
    finally:
        provider.shutdown()


def _one(exporter: InMemorySpanExporter) -> Any:
    finished = exporter.get_finished_spans()
    assert len(finished) == 1, finished
    return finished[0]


def _hex(value: int, width: int) -> str:
    return format(value, f"0{width}x")


async def _invoke(app: Any, headers: list[tuple[bytes, bytes]]) -> None:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {"type": "http", "method": "POST", "path": "/mcp", "headers": headers}
    await TraceContextMiddleware(app)(scope, receive, send)
    assert sent[0]["status"] == 200


def _call(name: str, arguments: dict[str, Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(name=name, arguments=arguments or {}))


def _values(span: Any) -> str:
    return " ".join(str(value) for value in (span.attributes or {}).values())


# ---- inbound context ------------------------------------------------------


@pytest.mark.asyncio
async def test_traceparent_is_the_parent_of_the_request_span(memory: _Memory) -> None:
    outbound: dict[str, str] = {}

    async def app(_scope: Any, _receive: Any, send: Any) -> None:
        with memory.tracer.start_as_current_span("tools/call"):
            inject_outbound(outbound)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    await _invoke(
        app,
        [
            (b"traceparent", CALLER.encode()),
            (b"tracestate", TRACE_STATE.encode()),
            (b"baggage", BAGGAGE.encode()),
        ],
    )

    span = _one(memory.exporter)
    assert _hex(span.context.trace_id, 32) == TRACE_ID
    assert span.parent is not None
    assert _hex(span.parent.span_id, 16) == PARENT_ID
    assert span.context.trace_state.get("congo") == "t61rcWkgMzE"
    assert outbound["traceparent"].split("-")[1] == TRACE_ID
    assert outbound["traceparent"].split("-")[2] == _hex(span.context.span_id, 16)
    assert "baggage" not in {key.lower() for key in outbound}
    assert "hunter2" not in _values(span)
    assert "hunter2" not in " ".join(outbound.values())


@pytest.mark.asyncio
async def test_request_without_traceparent_starts_its_own_trace(memory: _Memory) -> None:
    async def app(_scope: Any, _receive: Any, send: Any) -> None:
        with memory.tracer.start_as_current_span("tools/call"):
            pass
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    await _invoke(app, [(b"baggage", BAGGAGE.encode()), (b"tracestate", TRACE_STATE.encode())])

    span = _one(memory.exporter)
    parent = span.parent
    assert parent is None or not parent.is_valid
    assert _hex(span.context.trace_id, 32) != TRACE_ID
    assert "hunter2" not in _values(span)


@pytest.mark.asyncio
async def test_seam_span_uses_the_http_traceparent_as_its_parent(memory: _Memory) -> None:
    async def app(_scope: Any, _receive: Any, send: Any) -> None:
        parent = otel_context.get_current()
        with memory.tracer.start_as_current_span("tools/call", context=parent):
            pass
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    await _invoke(
        app,
        [
            (b"traceparent", CALLER.encode()),
            (b"tracestate", TRACE_STATE.encode()),
        ],
    )

    span = _one(memory.exporter)
    assert _hex(span.context.trace_id, 32) == TRACE_ID
    assert span.parent is not None
    assert _hex(span.parent.span_id, 16) == PARENT_ID


# ---- tool span ------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_span_records_the_subject_and_not_the_payload(memory: _Memory) -> None:
    compact_schema = '{"type":"record","name":"U"}'
    arguments = {
        "subject": "user-events",
        "schema_id": 42,
        "registry": "production",
        "context": "prod",
        "source_subject": compact_schema,
        "target_registry": "https://user:pass@registry",
        "schema": SCHEMA,
        "authorization": "Bearer secret-token",
        "version": "v" * 300,
    }

    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(structured_content={"subject": "user-events", "schema": SCHEMA})

    with memory.tracer.start_as_current_span("tools/call"):
        result = await ToolCallSpans().on_call_tool(_call("get_schema", arguments), call_next)

    assert result.structured_content is not None
    span = _one(memory.exporter)
    assert span.attributes["mcp.tool"] == "get_schema"
    assert span.attributes["mcp.outcome"] == "ok"
    assert span.attributes["schema.subject"] == "user-events"
    assert span.attributes["schema.id"] == 42
    assert span.attributes["schema.registry"] == "production"
    assert span.attributes["schema.context"] == "prod"
    assert "schema.version" not in span.attributes
    assert "schema.source_subject" not in span.attributes
    assert "schema.target_registry" not in span.attributes
    rendered = _values(span)
    assert "secret-token" not in rendered
    assert "record" not in rendered
    assert "user:pass" not in rendered
    assert compact_schema not in rendered
    assert "authorization" not in span.attributes


@pytest.mark.asyncio
async def test_refused_call_is_an_error_span_without_the_message(memory: _Memory) -> None:
    async def call_next(_context: Any) -> Any:
        raise AuthorizationError("denied secret-token")

    with memory.tracer.start_as_current_span("tools/call"):
        with pytest.raises(AuthorizationError):
            await ToolCallSpans().on_call_tool(_call("get_schema", {"subject": "user-events"}), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == "refused"
    assert span.status.status_code == StatusCode.ERROR
    assert "secret-token" not in _values(span)
    assert span.status.description is None or "secret-token" not in span.status.description


@pytest.mark.asyncio
async def test_error_dict_is_an_error_span_without_the_message(memory: _Memory) -> None:
    message = 'password=hunter2 schema {"type":"record"}'
    body = create_error_response(message, error_code="REGISTRY_NOT_FOUND")

    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(structured_content=body)

    with memory.tracer.start_as_current_span("tools/call"):
        await ToolCallSpans().on_call_tool(_call("get_schema", {"subject": "missing"}), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == "error"
    assert span.status.status_code == StatusCode.ERROR
    assert "hunter2" not in _values(span)
    assert "record" not in _values(span)
    assert message not in _values(span)


@pytest.mark.asyncio
async def test_tool_result_is_error_flag_marks_the_span(memory: _Memory) -> None:
    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(structured_content={"subject": "user-events"}, is_error=True)

    with memory.tracer.start_as_current_span("tools/call"):
        await ToolCallSpans().on_call_tool(_call("get_schema"), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == "error"
    assert span.status.status_code == StatusCode.ERROR


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "outcome"),
    [
        ({"status": "rejected", "reason": "secret-token"}, "error"),
        ({"status": "incomplete", "reason": "secret-token"}, "error"),
        ({"status": "compatibility_error", "message": "secret-token"}, "error"),
        ({"status": "dry_run"}, "ok"),
        ({"status": "applied"}, "ok"),
        ({"status": "confirmation_required"}, "ok"),
    ],
)
async def test_failure_status_marks_the_span(memory: _Memory, body: dict[str, Any], outcome: str) -> None:
    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(structured_content=body)

    with memory.tracer.start_as_current_span("tools/call"):
        await ToolCallSpans().on_call_tool(_call("restore_bundle", {"subject": "user-events"}), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == outcome
    assert "secret-token" not in _values(span)


@pytest.mark.asyncio
async def test_text_json_error_marks_the_span_without_the_message(memory: _Memory) -> None:
    from mcp.types import TextContent

    message = "Schema evolution input was declined secret-token"

    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(content=[TextContent(type="text", text=json.dumps({"error": message}))])

    with memory.tracer.start_as_current_span("tools/call"):
        await ToolCallSpans().on_call_tool(_call("guided_schema_evolution"), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == "error"
    assert "secret-token" not in _values(span)
    assert message not in _values(span)


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["not json", json.dumps({"status": "dry_run"})])
async def test_plain_text_and_success_json_stay_ok(memory: _Memory, text: str) -> None:
    from mcp.types import TextContent

    async def call_next(_context: Any) -> ToolResult:
        return ToolResult(content=[TextContent(type="text", text=text)])

    with memory.tracer.start_as_current_span("tools/call"):
        await ToolCallSpans().on_call_tool(_call("guided_schema_evolution"), call_next)

    span = _one(memory.exporter)
    assert span.attributes["mcp.outcome"] == "ok"


def test_export_drops_the_exception_message() -> None:
    message = 'denied secret-token schema {"type":"record"}'
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(_DropExceptionDetail())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    try:
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("tools/call") as span:
            span.set_attribute("mcp.outcome", "refused")
            span.set_attribute("error.type", "AuthorizationError")
            try:
                raise AuthorizationError(message)
            except AuthorizationError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
        finished = exporter.get_finished_spans()
        assert len(finished) == 1
        exported = finished[0]
        assert exported.attributes["mcp.outcome"] == "refused"
        assert exported.attributes["error.type"] == "AuthorizationError"
        assert exported.status.status_code == StatusCode.ERROR
        assert not exported.status.description
        assert exported.events == ()
        rendered = _values(exported)
        assert "secret-token" not in rendered
        assert "record" not in rendered
        assert message not in rendered
    finally:
        provider.shutdown()


# ---- outbound ------------------------------------------------------------


def test_outbound_inject_writes_traceparent_and_not_baggage(memory: _Memory) -> None:
    headers: dict[str, str] = {}
    with memory.tracer.start_as_current_span("tools/call"):
        token = otel_context.attach(baggage.set_baggage("password", "hunter2"))
        try:
            inject_outbound(headers)
        finally:
            otel_context.detach(token)

    assert headers["traceparent"].startswith("00-")
    assert "baggage" not in {key.lower() for key in headers}
    assert "hunter2" not in " ".join(headers.values())
    assert set(key.lower() for key in headers) <= {"traceparent", "tracestate"}


def test_shard_auth_forwards_the_current_trace(memory: _Memory) -> None:
    from httpx2 import Request

    from fleet import RequestBearerAuth

    request = Request("POST", "http://shard.example/mcp")
    with memory.tracer.start_as_current_span("tools/call"):
        token = otel_context.attach(baggage.set_baggage("password", "hunter2"))
        try:
            list(RequestBearerAuth().auth_flow(request))
        finally:
            otel_context.detach(token)

    assert "traceparent" in request.headers
    assert "baggage" not in {key.lower() for key in request.headers}
    assert "hunter2" not in " ".join(str(value) for value in request.headers.values())


# ---- export ---------------------------------------------------------------


def test_configure_without_an_endpoint_does_not_install_a_provider() -> None:
    before = trace_api.get_tracer_provider()
    assert configure({}) is False
    assert configure({"OTEL_EXPORTER_OTLP_ENDPOINT": "  "}) is False
    assert trace_api.get_tracer_provider() is before
    assert tracing._provider is None


def test_traces_endpoint_uses_the_otlp_http_path() -> None:
    assert tracing._traces_endpoint("http://otel:4318") == "http://otel:4318/v1/traces"
    assert tracing._traces_endpoint("http://otel:4318/") == "http://otel:4318/v1/traces"
    assert tracing._traces_endpoint("http://otel:4318/v1/traces") == "http://otel:4318/v1/traces"


# ---- middleware order -----------------------------------------------------


@pytest.mark.asyncio
async def test_later_middleware_records_a_short_circuit(memory: _Memory) -> None:
    from fastmcp import FastMCP
    from fastmcp.server.middleware import Middleware

    class _Stop(Middleware):
        async def on_call_tool(self, context: Any, call_next: Any) -> ToolResult:
            return ToolResult(structured_content={"status": "rejected", "reason": "secret-token"})

    mcp = FastMCP("trace-order")

    @mcp.tool
    def get_schema(subject: str) -> dict[str, str]:
        return {"subject": subject}

    mcp.add_middleware(ToolCallSpans())
    mcp.add_middleware(_Stop())

    with memory.tracer.start_as_current_span("tools/call"):
        await mcp.call_tool("get_schema", {"subject": "user-events"})

    span = _one(memory.exporter)
    assert span.attributes["mcp.tool"] == "get_schema"
    assert span.attributes["mcp.outcome"] == "error"
    assert span.attributes["schema.subject"] == "user-events"
    assert "secret-token" not in _values(span)


# ---- streamable HTTP ------------------------------------------------------

CALLER_2 = "00-11111111111111111111111111111111-00f067aa0ba902b7-01"
TRACE_ID_2 = "11111111111111111111111111111111"
_ACCEPT = "application/json, text/event-stream"


def _tool_spans(exporter: InMemorySpanExporter) -> list[Any]:
    return [span for span in exporter.get_finished_spans() if (span.attributes or {}).get("mcp.tool") == "get_schema"]


def _span_text(span: Any) -> str:
    parts = [_values(span)]
    if span.status.description:
        parts.append(span.status.description)
    for event in span.events:
        parts.append(event.name)
        if event.attributes:
            parts.extend(str(value) for value in event.attributes.values())
    return " ".join(parts)


async def _post(client: Any, payload: dict[str, Any], headers: dict[str, str]) -> Any:
    return await client.post("/mcp", json=payload, headers={"accept": _ACCEPT, **headers})


@pytest.mark.asyncio
async def test_streamable_http_continues_each_requests_trace() -> None:
    import httpx
    from fastmcp import FastMCP

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(_DropExceptionDetail())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    previous = trace_api.get_tracer_provider()
    trace_api.set_tracer_provider(provider)
    mcp = FastMCP("trace-http")

    @mcp.tool
    def get_schema(subject: str) -> dict[str, str]:
        raise AuthorizationError("denied secret-token")

    mcp.add_middleware(ToolCallSpans())
    app = mcp.http_app(
        path="/mcp",
        middleware=asgi_middleware(),
        transport="streamable-http",
        json_response=True,
    )
    try:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                opened = await _post(
                    client,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2026-07-28",
                            "capabilities": {},
                            "clientInfo": {"name": "trace-test", "version": "0"},
                        },
                    },
                    {},
                )
                assert opened.status_code == 200, opened.text
                session = opened.headers["mcp-session-id"]
                session_header = {"mcp-session-id": session}
                noted = await _post(
                    client,
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    session_header,
                )
                assert noted.status_code == 202, noted.text

                async def call(trace: dict[str, str]) -> Any:
                    return await _post(
                        client,
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {"name": "get_schema", "arguments": {"subject": "user-events"}},
                        },
                        {**session_header, **trace},
                    )

                refused = await call({"traceparent": CALLER, "tracestate": TRACE_STATE})
                assert refused.status_code == 200, refused.text
                first = _tool_spans(exporter)[-1]
                assert _hex(first.context.trace_id, 32) == TRACE_ID
                assert first.parent is not None
                assert _hex(first.parent.span_id, 16) == PARENT_ID
                assert first.context.trace_state.get("congo") == "t61rcWkgMzE"
                assert first.attributes["mcp.outcome"] == "refused"
                assert first.attributes["schema.subject"] == "user-events"
                assert "secret-token" not in _span_text(first)

                fresh = await call({})
                assert fresh.status_code == 200, fresh.text
                second = _tool_spans(exporter)[-1]
                assert _hex(second.context.trace_id, 32) not in {TRACE_ID, TRACE_ID_2}

                again = await call({"traceparent": CALLER_2, "tracestate": TRACE_STATE})
                assert again.status_code == 200, again.text
                third = _tool_spans(exporter)[-1]
                assert _hex(third.context.trace_id, 32) == TRACE_ID_2
                assert third.attributes["mcp.outcome"] == "refused"
    finally:
        trace_api.set_tracer_provider(previous)
        provider.shutdown()
