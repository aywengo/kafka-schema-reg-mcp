"""Argument completion tests."""

from types import SimpleNamespace

import pytest

import kafka_schema_registry_unified_mcp as server


@pytest.mark.asyncio
async def test_registry_names_are_completed():
    original = server.registry_manager.registries
    server.registry_manager.registries = {"dev": object(), "prod": object()}
    try:
        argument = SimpleNamespace(name="name", value="")
        values = await server.complete_arguments(None, argument, None)
        assert values == ["dev", "prod"]
    finally:
        server.registry_manager.registries = original


@pytest.mark.asyncio
async def test_unknown_argument_has_no_candidates():
    argument = SimpleNamespace(name="subject", value="")
    assert await server.complete_arguments(None, argument, None) == []
