"""Fleet routing. No socket: a fake group and a recording fleet stand in."""

from __future__ import annotations

from typing import Any

import pytest

from fleet import (
    ClientGroupFleet,
    InProcessFleet,
    RecordingFleet,
    RequestBearerAuth,
    inbound_bearer,
    load_fleet_config,
    route_tool,
)

_FRONT_ENV = {
    "FLEET_ROLE": "front",
    "FLEET_SHARDS": "alpha=http://shard-a:8080/mcp,beta=http://shard-b:8080/mcp",
    "FLEET_DIRECTORY": "prod=alpha,staging=beta",
}


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        self.calls.append((name, dict(arguments)))
        return {"ok": True, "tool": name}


class _FakeRoute:
    def __init__(self, client: _FakeClient, upstream_name: str) -> None:
        self.client = client
        self.upstream_name = upstream_name
        self.server_name = "alpha"


class _FakeGroup:
    def __init__(self, routes: dict[str, _FakeRoute]) -> None:
        self.routes = routes
        self.resolved: list[str] = []

    async def resolve_tool(self, name: str) -> _FakeRoute:
        self.resolved.append(name)
        return self.routes[name]


def _group() -> tuple[ClientGroupFleet, _FakeGroup, _FakeClient]:
    client = _FakeClient()
    route = _FakeRoute(client, "list_subjects")
    group = _FakeGroup({"alpha_list_subjects": route})
    fleet = ClientGroupFleet({"prod": "alpha", "staging": "beta"}, group)
    return fleet, group, client


@pytest.mark.asyncio
async def test_resolve_tool_uses_member_route_and_unprefixed_name() -> None:
    fleet, group, client = _group()
    arguments = {"registry": "prod", "context": "."}

    await fleet.dispatch("list_subjects", arguments)

    assert group.resolved == ["alpha_list_subjects"]
    assert client.calls == [("list_subjects", arguments)]
    assert client.calls[0][1]["registry"] == "prod"


@pytest.mark.asyncio
async def test_unknown_registry_does_not_resolve_a_tool() -> None:
    fleet, group, client = _group()

    result = await fleet.dispatch("list_subjects", {"registry": "missing"})

    assert result["error_code"] == "REGISTRY_NOT_FOUND"
    assert result["error"] == "Registry 'missing' not found"
    assert group.resolved == []
    assert client.calls == []


@pytest.mark.asyncio
async def test_cross_shard_compare_exports_each_side_and_holds_no_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCHEMA_REGISTRY_PASSWORD", "s3cret")
    source = {
        "contexts": [{"context": "orders", "subjects": []}],
        "default_context": {
            "context": "",
            "subjects": [{"subject": "user", "versions": [{"version": 1, "id": 1}]}],
        },
        "global_config": {"compatibility": "BACKWARD"},
    }
    target = {
        "contexts": [],
        "default_context": {
            "context": "",
            "subjects": [{"subject": "order", "versions": [{"version": 2, "id": 9}]}],
        },
        "global_config": {"compatibility": "FULL"},
    }
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_global", "prod"): source, ("export_global", "staging"): target},
    )

    result = await route_tool(
        "compare_registries",
        {"source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_global", "export_global"]
    assert fleet.calls[0][1]["registry"] == "prod"
    assert fleet.calls[1][1]["registry"] == "staging"
    assert "s3cret" not in repr(fleet.__dict__)
    assert "password" not in fleet.__dict__
    assert result["differences"]["subjects"]["only_in_source"] == ["user"]
    assert result["differences"]["subjects"]["only_in_target"] == ["order"]


@pytest.mark.asyncio
async def test_cross_shard_migrate_exports_then_restores() -> None:
    document = {
        "subject": ":.orders:user",
        "versions": [
            {"version": 1, "id": 1, "schema": {"type": "record"}},
            {"version": 2, "id": 2, "schema": {"type": "record"}},
        ],
        "metadata": {"context": "orders", "export_version": "1.7.0"},
    }
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {
            ("export_subject", "prod"): document,
            ("restore_bundle", "staging"): {"status": "applied"},
        },
    )

    result = await route_tool(
        "migrate_schema",
        {
            "subject": ":.orders:user",
            "source_registry": "prod",
            "target_registry": "staging",
            "source_context": "orders",
            "target_context": "billing",
            "versions": [2],
            "dry_run": False,
            "preserve_ids": True,
        },
        fleet,
    )

    export_tool, export_args = fleet.calls[0]
    restore_tool, restore_args = fleet.calls[1]
    assert export_tool == "export_subject"
    assert export_args["registry"] == "prod"
    assert export_args["context"] == "orders"
    assert export_args["include_versions"] == "all"
    assert restore_tool == "restore_bundle"
    assert restore_args["target"] == "staging"
    assert restore_args["apply"] is True
    assert restore_args["accept_new_ids"] is False
    assert restore_args["bundle"]["subject"] == "user"
    assert restore_args["bundle"]["metadata"]["context"] == "billing"
    assert [item["version"] for item in restore_args["bundle"]["versions"]] == [2]
    assert result == {"status": "applied"}


@pytest.mark.asyncio
async def test_same_shard_compare_dispatches_the_tool_once() -> None:
    arguments = {
        "source_registry": "prod",
        "target_registry": "staging",
        "include_contexts": True,
        "include_configs": False,
    }
    fleet = RecordingFleet({"prod": "alpha", "staging": "alpha"})

    await route_tool("compare_registries", arguments, fleet)

    assert fleet.calls == [("compare_registries", arguments)]


@pytest.mark.asyncio
async def test_omitted_registry_stays_omitted_and_uses_the_default_member() -> None:
    fleet, group, client = _group()

    await fleet.dispatch("list_subjects", {"context": "."})

    assert group.resolved == ["alpha_list_subjects"]
    assert client.calls == [("list_subjects", {"context": "."})]


@pytest.mark.asyncio
async def test_find_missing_in_a_context_exports_that_context() -> None:
    document = {"context": "orders", "subjects": [{"subject": "user", "versions": [{"version": 1, "id": 4}]}]}
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_context", "prod"): document, ("export_context", "staging"): {"context": "orders", "subjects": []}},
    )

    result = await route_tool(
        "find_missing_schemas",
        {"source_registry": "prod", "target_registry": "staging", "context": "orders"},
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_context", "export_context"]
    assert fleet.calls[0][1]["context"] == "orders"
    assert result["missing_subjects"] == ["user"]


@pytest.mark.asyncio
async def test_cross_shard_dry_run_does_not_apply_and_accepts_new_ids() -> None:
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {
            ("export_subject", "prod"): {"subject": "user", "versions": [{"version": 1}]},
            ("restore_bundle", "staging"): {"status": "dry_run"},
        },
    )

    await route_tool(
        "migrate_schema",
        {
            "subject": "user",
            "source_registry": "prod",
            "target_registry": "staging",
            "dry_run": True,
            "preserve_ids": False,
        },
        fleet,
    )

    assert fleet.calls[1][1]["apply"] is False
    assert fleet.calls[1][1]["accept_new_ids"] is True


@pytest.mark.asyncio
async def test_other_cross_shard_tool_does_not_dispatch() -> None:
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})

    result = await route_tool(
        "migrate_context",
        {"source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert fleet.calls == []
    assert result["error_code"] == "CROSS_SHARD_UNSUPPORTED"


@pytest.mark.asyncio
async def test_list_registries_does_not_dispatch() -> None:
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})

    result = await route_tool("list_registries", {}, fleet)

    assert fleet.calls == []
    assert result["total_count"] == 2
    assert result["default_registry"] == "prod"
    assert [item["name"] for item in result["registries"]] == ["prod", "staging"]


@pytest.mark.asyncio
async def test_one_auth_sends_the_bearer_from_each_context() -> None:
    from fastmcp.server.dependencies import _background_task_headers
    from httpx2 import Request

    auth = RequestBearerAuth()

    def authorization(bearer: str | None) -> str | None:
        payload = {"authorization": f"Bearer {bearer}"} if bearer else {}
        token = _background_task_headers.set(payload)
        try:
            request = Request("POST", "http://shard.example/mcp")
            list(auth.auth_flow(request))
            return request.headers.get("authorization")
        finally:
            _background_task_headers.reset(token)

    assert authorization("one") == "Bearer one"
    assert authorization("two") == "Bearer two"
    assert authorization(None) is None
    assert inbound_bearer() is None


@pytest.mark.asyncio
async def test_in_process_fleet_runs_the_injected_tool() -> None:
    seen: list[tuple[str, dict[str, Any]]] = []

    async def runner(tool: str, arguments: dict[str, Any]) -> dict[str, str]:
        seen.append((tool, dict(arguments)))
        return {"ran": tool}

    fleet = InProcessFleet(["dev"], runner)
    result = await fleet.dispatch("list_subjects", {"registry": "dev"})

    assert result == {"ran": "list_subjects"}
    assert seen == [("list_subjects", {"registry": "dev"})]
    assert "password" not in fleet.__dict__


def test_front_startup_rejects_a_registry_password() -> None:
    with pytest.raises(RuntimeError, match="registry passwords"):
        load_fleet_config({**_FRONT_ENV, "SCHEMA_REGISTRY_PASSWORD": "secret"})
    with pytest.raises(RuntimeError, match="SCHEMA_REGISTRY_USER_1"):
        load_fleet_config({**_FRONT_ENV, "SCHEMA_REGISTRY_USER_1": "schema"})


def test_inprocess_role_keeps_a_registry_password() -> None:
    config = load_fleet_config({"SCHEMA_REGISTRY_PASSWORD": "secret"})
    assert config.role == "inprocess"
    assert config.directory == {}
