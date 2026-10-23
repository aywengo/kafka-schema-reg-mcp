import asyncio
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest

from mrtr import MODERN_PROTOCOL_VERSION, elicitation_request, guard, input_required


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
