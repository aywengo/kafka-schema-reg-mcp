import asyncio
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest

from mrtr import MODERN_PROTOCOL_VERSION, _legacy_response_model, ask, elicitation_request, guard, input_required


class FakeContext:
    def __init__(self, responses=None):
        self.input_responses = responses


def test_elicitation_request_shape():
    request = elicitation_request("Name?", {"type": "object", "properties": {"name": {"type": "string"}}})
    assert request.method == "elicitation/create"
    assert request.params.message == "Name?"
    assert request.params.mode == "form"


def test_input_required_requires_payload():
    result = input_required({"name": elicitation_request("Name?", {})}, "sealed")
    assert result.result_type == "input_required"
    assert result.request_state == "sealed"
    assert "name" in result.input_requests


@pytest.mark.asyncio
async def test_modern_connection_suspends():
    legacy = AsyncMock()
    with patch("mrtr.current_protocol_version", return_value=MODERN_PROTOCOL_VERSION):
        kind, value = await guard(
            FakeContext(),
            requests={"name": elicitation_request("Name?", {})},
            request_state="sealed",
            legacy=legacy,
        )
    assert kind == "suspend"
    assert isinstance(value, mcp_types.InputRequiredResult)
    legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_connection_elicitates():
    legacy = AsyncMock(return_value={"action": "accept", "content": {"name": "x"}})
    with patch("mrtr.current_protocol_version", return_value="2025-11-25"):
        kind, value = await guard(
            FakeContext(),
            requests={"name": elicitation_request("Name?", {})},
            legacy=legacy,
        )
    assert kind == "legacy"
    assert value["content"]["name"] == "x"
    legacy.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_returns_responses():
    legacy = AsyncMock()
    responses = {"name": mcp_types.ElicitResult(action="accept", content={"name": "x"})}
    with patch("mrtr.current_protocol_version", return_value=MODERN_PROTOCOL_VERSION):
        kind, value = await guard(FakeContext(responses=responses), requests={}, legacy=legacy)
    assert kind == "responses"
    assert value is responses
    legacy.assert_not_awaited()


def test_legacy_response_model_uses_object_schema():
    model = _legacy_response_model(
        {
            "type": "object",
            "properties": {"subject": {"type": "string"}},
            "required": ["subject"],
        }
    )
    schema = model.model_json_schema()
    assert schema["type"] == "object"
    assert schema["properties"]["subject"]["type"] == "string"


@pytest.mark.asyncio
async def test_legacy_ask_passes_model_to_elicit():
    class ElicitContext(FakeContext):
        async def elicit(self, message, response_type):
            assert response_type.model_json_schema()["type"] == "object"
            return type("Response", (), {"action": "accept", "data": response_type(subject="x")})()

    with patch("mrtr.current_protocol_version", return_value="2025-11-25"):
        kind, value = await ask(
            ElicitContext(),
            message="Subject?",
            schema={"type": "object", "properties": {"subject": {"type": "string"}}, "required": ["subject"]},
        )
    assert kind == "answered"
    assert value == {"subject": "x"}


def test_legacy_response_model_accepts_null_optional_field():
    model = _legacy_response_model(
        {
            "type": "object",
            "properties": {"subject": {"type": "string"}, "current_schema": {"type": "string"}},
            "required": ["subject"],
        }
    )
    assert model(subject="x", current_schema=None).current_schema == ""
