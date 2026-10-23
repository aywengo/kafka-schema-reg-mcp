#!/usr/bin/env python3
"""Resource linking tests for the unified 3.0 URI scheme."""

import re

import pytest
from fastmcp import Client

import kafka_schema_registry_unified_mcp as server
from resource_linking import RegistryURI, ResourceLinker, create_registry_linker


def _matches(uri: str, templates: list[str]) -> bool:
    for template in templates:
        parts = re.split(r"\{[^}]+\}", template)
        pattern = "[^/]+".join(re.escape(part) for part in parts)
        if re.fullmatch(pattern, uri):
            return True
    return False


@pytest.mark.asyncio
async def test_every_builder_uri_resolves():
    async with Client(server.mcp) as client:
        resources = {str(r.uri) for r in await client.list_resources()}
        templates = [t.uri_template for t in await client.list_resource_templates()]

    builder = RegistryURI("test-registry")
    uris = [
        builder.registry_uri(),
        builder.registry_info_uri(),
        builder.contexts_list_uri(),
        builder.context_uri(),
        builder.context_uri("production"),
        builder.subjects_list_uri(),
        builder.subject_uri("user-events"),
        builder.subject_uri("user-events", "production"),
        builder.subject_config_uri("user-events"),
        builder.subject_config_uri("user-events", "production"),
        builder.subject_mode_uri("user-events"),
        builder.subject_mode_uri("user-events", "production"),
        builder.subject_compatibility_uri("user-events"),
        builder.schema_versions_uri("user-events"),
        builder.schema_versions_uri("user-events", "production"),
        builder.schema_version_uri("user-events", 3),
        builder.migrations_list_uri(),
        builder.migration_uri("migration-123"),
        builder.tasks_list_uri(),
        builder.task_uri("task-123"),
    ]

    for uri in uris:
        assert uri in resources or _matches(uri, templates), f"{uri} has no registered handler"


def test_schema_links_are_resolvable_shapes():
    linker = ResourceLinker("test-registry")
    enhanced = linker.add_schema_links({"id": 1}, "user-events", 3, "production")
    links = enhanced["_links"]

    assert links["self"].startswith("schema://test-registry/production/user-events")
    assert links["subject"].startswith("schema://test-registry/production/user-events")
    assert links["versions"].endswith("/versions")
    assert links["config"].startswith("subject://test-registry/production/user-events/config")
    assert links["mode"].startswith("subject://test-registry/production/user-events/mode")


def test_registry_name_sanitization():
    builder = RegistryURI("registry@with/special:chars")
    assert builder.registry_name == "registry-with-special-chars"


def test_links_added_to_registry_response():
    linker = create_registry_linker("test-registry")
    enhanced = linker.add_registry_links({"status": "ok"})
    assert enhanced["_links"]["self"] == "registry://info/test-registry"
    assert enhanced["_links"]["migrations"] == "registry://test-registry/migrations"
    assert enhanced["_links"]["tasks"] == "registry://test-registry/tasks"
