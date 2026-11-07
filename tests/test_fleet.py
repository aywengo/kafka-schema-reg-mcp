"""Fleet routing. No socket: a fake group and a recording fleet stand in."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fleet import (
    ClientGroupFleet,
    FrontRouter,
    InProcessFleet,
    RecordingFleet,
    RequestBearerAuth,
    build_client_group,
    inbound_bearer,
    load_fleet_config,
    route_tool,
)

_FRONT_ENV = {
    "FLEET_ROLE": "front",
    "FLEET_SHARDS": "alpha=http://shard-a:8080/mcp,beta=http://shard-b:8080/mcp",
    "FLEET_DIRECTORY": "prod=alpha,staging=beta",
}


class _Template:
    """A disconnected shard client. ``new`` opens a session for one call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.opened = 0

    def new(self) -> "_Session":
        return _Session(self)


class _Session:
    def __init__(self, template: _Template) -> None:
        self._template = template

    async def __aenter__(self) -> "_Session":
        self._template.opened += 1
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def call_tool(self, name: str, arguments: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        self._template.calls.append((name, dict(arguments)))
        return {"ok": True, "tool": name}


class _Catalog:
    def __init__(self, names: set[str]) -> None:
        self._names = names
        self.lookups: list[str] = []

    async def get_tool(self, name: str, version: Any = None) -> object | None:
        self.lookups.append(name)
        if name in self._names:
            return object()
        return None


def _Call(name: str, arguments: dict[str, Any], server: _Catalog) -> SimpleNamespace:
    return SimpleNamespace(
        message=SimpleNamespace(name=name, arguments=arguments),
        fastmcp_context=SimpleNamespace(fastmcp=server),
    )


async def _not_called(context: Any) -> None:
    raise AssertionError("local tool should not run")


def _group() -> tuple[ClientGroupFleet, _Template]:
    client = _Template()
    fleet = ClientGroupFleet({"prod": "alpha", "staging": "beta"}, {"alpha": client, "beta": _Template()})
    return fleet, client


@pytest.mark.asyncio
async def test_dispatch_calls_the_member_with_the_unprefixed_name() -> None:
    fleet, client = _group()
    arguments = {"registry": "prod", "context": "."}

    await fleet.dispatch("list_subjects", arguments)

    assert client.opened == 1
    assert client.calls == [("list_subjects", arguments)]
    assert client.calls[0][1]["registry"] == "prod"


@pytest.mark.asyncio
async def test_unknown_registry_does_not_open_a_session() -> None:
    fleet, client = _group()

    result = await fleet.dispatch("list_subjects", {"registry": "missing"})

    assert result["error_code"] == "REGISTRY_NOT_FOUND"
    assert result["error"] == "Registry 'missing' not found"
    assert client.opened == 0
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
        "version_numbers": [1, 2],
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
    assert export_args["include_config"] is False
    assert restore_tool == "restore_bundle"
    assert restore_args["target"] == "staging"
    assert restore_args["apply"] is True
    assert restore_args["accept_new_ids"] is False
    assert restore_args["bundle"]["subject"] == "user"
    assert restore_args["bundle"]["metadata"]["context"] == "billing"
    assert [item["version"] for item in restore_args["bundle"]["versions"]] == [2]
    assert "config" not in restore_args["bundle"]
    assert result["successful_migrations"] == 1
    assert result["failed_migrations"] == 0
    assert result["total_versions"] == 2
    assert result["versions_to_migrate"] == 1
    assert result["dry_run"] is False


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
async def test_omitted_registry_is_sent_as_the_directory_default() -> None:
    fleet, client = _group()

    await fleet.dispatch("list_subjects", {"context": "."})

    assert client.opened == 1
    assert client.calls == [("list_subjects", {"context": ".", "registry": "prod"})]


@pytest.mark.asyncio
async def test_same_shard_pair_uses_the_source_member_and_keeps_arguments() -> None:
    alpha = _Template()
    beta = _Template()
    fleet = ClientGroupFleet({"prod": "alpha", "staging": "beta"}, {"alpha": alpha, "beta": beta})
    arguments = {"source_registry": "staging", "target_registry": "staging"}

    await fleet.dispatch("compare_registries", arguments)

    assert alpha.opened == 0
    assert beta.opened == 1
    assert beta.calls == [("compare_registries", arguments)]


@pytest.mark.asyncio
async def test_each_call_opens_its_own_session() -> None:
    fleet, client = _group()

    await fleet.dispatch("list_subjects", {"registry": "prod"})
    await fleet.dispatch("list_subjects", {"registry": "prod"})

    assert client.opened == 2


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
            ("export_subject", "prod"): {
                "subject": "user",
                "versions": [{"version": 1}],
                "version_numbers": [1],
            },
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


@pytest.mark.asyncio
async def test_failed_export_is_not_restored() -> None:
    document = {
        "error": "subject missing",
        "error_code": "SUBJECT_EXPORT_FAILED",
        "subject": "user",
        "versions": [],
    }
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"}, {("export_subject", "prod"): document})

    result = await route_tool(
        "migrate_schema",
        {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_subject"]
    assert result["error"] == "subject missing"


@pytest.mark.asyncio
async def test_global_compare_keeps_the_same_subject_in_two_contexts() -> None:
    source = {
        "default_context": {"context": "", "subjects": [{"subject": "user", "versions": [{"version": 1, "id": 1}]}]},
        "contexts": [{"context": "orders", "subjects": [{"subject": "user", "versions": [{"version": 1, "id": 2}]}]}],
    }
    target = {"default_context": {"context": "", "subjects": []}, "contexts": []}
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_global", "prod"): source, ("export_global", "staging"): target},
    )

    result = await route_tool(
        "compare_registries",
        {"source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert result["differences"]["subjects"]["only_in_source"] == [":.orders:user", "user"]


@pytest.mark.asyncio
async def test_missing_requested_version_does_not_restore() -> None:
    document = {
        "subject": "user",
        "versions": [{"version": 1, "id": 1}],
        "version_numbers": [1],
        "config": {"compatibilityLevel": "FULL"},
        "metadata": {"context": "."},
    }
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"}, {("export_subject", "prod"): document})

    result = await route_tool(
        "migrate_schema",
        {
            "subject": "user",
            "source_registry": "prod",
            "target_registry": "staging",
            "versions": [9],
            "dry_run": False,
        },
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_subject"]
    assert result["message"] == "No versions to migrate"
    assert result["successful_migrations"] == 0
    assert result["total_versions"] == 1
    assert result["versions_to_migrate"] == 0


@pytest.mark.asyncio
async def test_front_refuses_a_tool_the_catalog_did_not_register() -> None:
    fleet = RecordingFleet({"prod": "alpha"})
    server = _Catalog({"list_registries"})
    context = _Call("delete_subject", {}, server)

    with pytest.raises(Exception, match="not found or not authorized"):
        await FrontRouter(fleet).on_call_tool(context, _not_called)

    assert fleet.calls == []
    assert server.lookups == ["delete_subject"]


@pytest.mark.asyncio
async def test_front_authorizes_a_directory_tool_before_answering() -> None:
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})
    server = _Catalog({"list_registries"})
    context = _Call("list_registries", {}, server)

    result = await FrontRouter(fleet).on_call_tool(context, _not_called)

    assert server.lookups == ["list_registries"]
    assert fleet.calls == []
    assert result.structured_content["default_registry"] == "prod"


def test_shard_clients_stay_disconnected_and_share_request_auth() -> None:
    clients = build_client_group(load_fleet_config(_FRONT_ENV))

    auths = [client.transport.auth for client in clients.values()]
    assert set(clients) == {"alpha", "beta"}
    assert len({id(auth) for auth in auths}) == 1
    assert all(isinstance(auth, RequestBearerAuth) for auth in auths)
    assert all(not client.is_connected() for client in clients.values())


@pytest.mark.asyncio
async def test_registry_free_tool_keeps_its_arguments() -> None:
    fleet, client = _group()

    await fleet.dispatch("list_workflows", {}, fields=frozenset())

    assert client.calls == [("list_workflows", {})]


@pytest.mark.asyncio
async def test_guided_schema_migration_stays_on_the_front() -> None:
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})

    result = await route_tool(
        "guided_schema_migration",
        {"source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert result is not None
    assert fleet.calls == []
    from fleet import LOCAL

    assert result is LOCAL


@pytest.mark.asyncio
async def test_export_without_versions_does_not_restore() -> None:
    document = {
        "subject": "user",
        "versions": [],
        "version_numbers": [],
        "config": {"compatibilityLevel": "NONE"},
    }
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"}, {("export_subject", "prod"): document})

    result = await route_tool(
        "migrate_schema",
        {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_subject"]
    assert result["message"] == "No versions to migrate"


@pytest.mark.asyncio
async def test_text_shard_result_is_the_text() -> None:
    class _TextTemplate:
        def new(self) -> "_TextSession":
            return _TextSession()

    class _TextSession:
        async def __aenter__(self) -> "_TextSession":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        async def call_tool(self, name: str, arguments: dict[str, Any], **kwargs: Any) -> Any:
            return SimpleNamespace(structured_content=None, data='{"status": "plan"}', content=[])

    fleet = ClientGroupFleet({"prod": "alpha"}, {"alpha": _TextTemplate()})
    result = await fleet.dispatch("guided_disaster_recovery", {"registry": "prod"})

    assert result == '{"status": "plan"}'


@pytest.mark.asyncio
async def test_input_required_is_returned_to_the_caller() -> None:
    from mcp_types import InputRequiredResult

    required = InputRequiredResult(input_requests={}, request_state="again")

    class _AskTemplate:
        def new(self) -> "_AskSession":
            return _AskSession()

    class _AskSession:
        async def __aenter__(self) -> "_AskSession":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        @property
        def session(self) -> "_AskSession":
            return self

        async def call_tool(self, name: str, arguments: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            self.seen = kwargs
            return required

    template = _AskTemplate()
    fleet = ClientGroupFleet({"prod": "alpha"}, {"alpha": template})
    result = await fleet.dispatch(
        "export_global_interactive",
        {"registry": "prod"},
        input_responses={"answer": "yes"},
        request_state="again",
    )

    assert result is required


def test_inprocess_role_keeps_a_registry_password() -> None:
    config = load_fleet_config({"SCHEMA_REGISTRY_PASSWORD": "secret"})
    assert config.role == "inprocess"
    assert config.directory == {}


@pytest.mark.asyncio
async def test_start_workflow_stays_on_the_front() -> None:
    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})

    result = await route_tool("start_workflow", {"workflow_id": "evolve"}, fleet)

    assert result is not None
    assert fleet.calls == []
    from fleet import LOCAL

    assert result is LOCAL


@pytest.mark.asyncio
async def test_latest_migrate_counts_every_source_version() -> None:
    document = {
        "subject": "user",
        "versions": [
            {"version": 1, "id": 1},
            {"version": 2, "id": 2},
            {"version": 3, "id": 3},
        ],
        "version_numbers": [1, 2, 3],
        "metadata": {"context": "."},
    }
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_subject", "prod"): document, ("restore_bundle", "staging"): {"status": "applied"}},
    )

    result = await route_tool(
        "migrate_schema",
        {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    restored = fleet.calls[1][1]["bundle"]["versions"]
    assert [item["version"] for item in restored] == [3]
    assert fleet.calls[0][1]["include_versions"] == "all"
    assert result["total_versions"] == 3
    assert result["versions_to_migrate"] == 1
    assert result["successful_migrations"] == 1


@pytest.mark.asyncio
async def test_incomplete_restore_counts_the_version_it_did_not_write() -> None:
    document = {
        "subject": "user",
        "versions": [{"version": 1, "id": 1}, {"version": 2, "id": 2}],
        "version_numbers": [1, 2],
        "metadata": {"context": "."},
    }
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {
            ("export_subject", "prod"): document,
            ("restore_bundle", "staging"): {
                "status": "incomplete",
                "created": [{"version": 1}],
                "reason": "cannot import user version 2",
            },
        },
    )

    result = await route_tool(
        "migrate_schema",
        {
            "subject": "user",
            "source_registry": "prod",
            "target_registry": "staging",
            "migrate_all_versions": True,
        },
        fleet,
    )

    assert result["successful_migrations"] == 1
    assert result["failed_migrations"] == 1
    failed = [item for item in result["migration_details"] if item["status"] == "failed"]
    assert failed == [{"version": 2, "status": "failed", "error": "cannot import user version 2"}]


@pytest.mark.asyncio
async def test_shard_tool_error_stops_before_restore() -> None:
    from fastmcp.exceptions import ToolError

    class _FailTemplate:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def new(self) -> "_FailSession":
            return _FailSession(self)

    class _FailSession:
        def __init__(self, template: _FailTemplate) -> None:
            self._template = template

        async def __aenter__(self) -> "_FailSession":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        async def call_tool(self, name: str, arguments: dict[str, Any], **kwargs: Any) -> Any:
            self._template.calls.append(name)
            return SimpleNamespace(
                is_error=True,
                structured_content=None,
                data=None,
                content=[SimpleNamespace(text="export failed")],
            )

    template = _FailTemplate()
    fleet = ClientGroupFleet({"prod": "alpha", "staging": "beta"}, {"alpha": template, "beta": _FailTemplate()})

    with pytest.raises(ToolError, match="export failed"):
        await route_tool(
            "migrate_schema",
            {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
            fleet,
        )

    assert template.calls == ["export_subject"]


@pytest.mark.asyncio
async def test_legacy_caller_opens_a_legacy_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fleet.is_modern_connection", lambda: False)

    class _LegacyTemplate:
        def __init__(self) -> None:
            self.session = _LegacySession()

        def new(self) -> "_LegacySession":
            return self.session

    class _LegacySession:
        def __init__(self) -> None:
            self.mode = "auto"

        async def __aenter__(self) -> "_LegacySession":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        async def call_tool(self, name: str, arguments: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            self.mode_at_call = self.mode
            return {"ok": True}

    template = _LegacyTemplate()
    fleet = ClientGroupFleet({"prod": "alpha"}, {"alpha": template})

    await fleet.dispatch("list_subjects", {"registry": "prod"})

    assert template.session.mode_at_call == "legacy"


@pytest.mark.asyncio
async def test_legacy_caller_answers_input_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.types import ElicitRequest, ElicitRequestFormParams, ElicitResult, InputRequiredResult

    monkeypatch.setattr("fleet.is_modern_connection", lambda: False)

    async def _answered(message: str, schema: dict[str, Any]) -> ElicitResult:
        assert message == "Confirm"
        return ElicitResult(action="accept", content={"ok": True})

    monkeypatch.setattr("fleet._elicit_form", _answered)
    required = InputRequiredResult(
        input_requests={
            "form": ElicitRequest(
                params=ElicitRequestFormParams(
                    message="Confirm",
                    requestedSchema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
                )
            )
        },
        request_state="sealed",
    )

    class _AskTemplate:
        def __init__(self) -> None:
            self.rounds: list[Any] = []

        def new(self) -> "_AskSession":
            return _AskSession(self)

    class _AskSession:
        def __init__(self, template: _AskTemplate) -> None:
            self._template = template
            self.mode = "auto"

        async def __aenter__(self) -> "_AskSession":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        @property
        def session(self) -> "_AskSession":
            return self

        async def call_tool(self, name: str, arguments: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            self._template.rounds.append(kwargs.get("input_responses"))
            if kwargs.get("input_responses"):
                return {"status": "done"}
            return required

    template = _AskTemplate()
    fleet = ClientGroupFleet({"prod": "alpha"}, {"alpha": template})

    result = await fleet.dispatch("export_global_interactive", {"registry": "prod"})

    assert result == {"status": "done"}
    assert template.rounds[0] is None
    assert template.rounds[1]["form"].action == "accept"
    assert template.rounds[1]["form"].content == {"ok": True}


_MIGRATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "subject": {"type": "string"},
        "source_registry": {"type": "string"},
        "target_registry": {"type": "string"},
        "dry_run": {"default": False, "type": "boolean"},
        "preserve_ids": {"default": True, "type": "boolean"},
        "migrate_all_versions": {"default": False, "type": "boolean"},
    },
    "required": ["subject", "source_registry", "target_registry"],
}


class _SchemaCatalog:
    def __init__(self, schema: dict[str, Any]) -> None:
        self._schema = schema

    async def get_tool(self, name: str, version: Any = None) -> object | None:
        return SimpleNamespace(parameters=self._schema)


@pytest.mark.asyncio
async def test_cross_shard_migrate_rejects_a_non_boolean_dry_run() -> None:
    from fastmcp.exceptions import ValidationError

    fleet = RecordingFleet({"prod": "alpha", "staging": "beta"})
    context = _Call(
        "migrate_schema",
        {
            "subject": "user",
            "source_registry": "prod",
            "target_registry": "staging",
            "dry_run": [],
        },
        _SchemaCatalog(_MIGRATE_SCHEMA),
    )

    with pytest.raises(ValidationError):
        await FrontRouter(fleet).on_call_tool(context, _not_called)

    assert fleet.calls == []


@pytest.mark.asyncio
async def test_omitted_dry_run_uses_the_schema_default() -> None:
    document = {"subject": "user", "versions": [{"version": 1}], "version_numbers": [1]}
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_subject", "prod"): document, ("restore_bundle", "staging"): {"status": "applied"}},
    )
    context = _Call(
        "migrate_schema",
        {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
        _SchemaCatalog(_MIGRATE_SCHEMA),
    )

    result = await FrontRouter(fleet).on_call_tool(context, _not_called)

    assert fleet.calls[1][1]["apply"] is True
    assert result.structured_content["dry_run"] is False


@pytest.mark.asyncio
async def test_partial_export_does_not_restore() -> None:
    document = {
        "subject": "user",
        "versions": [{"version": 1, "id": 1}],
        "version_numbers": [1, 2],
    }
    fleet = RecordingFleet(
        {"prod": "alpha", "staging": "beta"},
        {("export_subject", "prod"): document, ("restore_bundle", "staging"): {"status": "applied"}},
    )

    result = await route_tool(
        "migrate_schema",
        {"subject": "user", "source_registry": "prod", "target_registry": "staging"},
        fleet,
    )

    assert [call[0] for call in fleet.calls] == ["export_subject"]
    assert result["error_code"] == "EXPORT_INCOMPLETE"


def test_export_subject_fails_when_a_version_fetch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from schema_registry_common import export_subject

    client = SimpleNamespace(
        get_schema_versions=lambda subject, context=None: [1, 2],
        get_subject_config=lambda subject, context=None: {"compatibilityLevel": "BACKWARD"},
        config=SimpleNamespace(url="http://registry"),
    )

    def _fetch(_client: Any, _subject: str, version: str, _context: Any) -> dict[str, Any]:
        if version == "2":
            return {"error": "schema fetch failed"}
        return {"version": 1, "schema": "{}"}

    monkeypatch.setattr("schema_registry_common.get_schema_with_metadata", _fetch)

    result = export_subject(client, "user")

    assert result["error_code"] == "SUBJECT_EXPORT_INCOMPLETE"
    assert result["failed_versions"] == [{"version": "2", "error": "schema fetch failed"}]
    assert "version_numbers" not in result
