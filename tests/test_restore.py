"""Restore an export document through a recording fleet. No socket."""

from __future__ import annotations

import inspect
import json
from typing import Any

import pytest

from _version import __version__
from migration_tools import ImportModeUnavailable, open_import_mode, restore_previous_mode
from restore import restore
from schema_registry_common import ViewOnlyError

USER_SCHEMA = {"type": "record", "name": "User", "fields": [{"name": "id", "type": "int"}]}
ORDER_SCHEMA = {"type": "record", "name": "Order", "fields": [{"name": "user", "type": "string"}]}


class RecordingFleet:
    """Scripted fleet. Stores each dispatch and never opens a socket."""

    def __init__(
        self,
        names: list[str],
        *,
        viewonly: bool = False,
        import_denied: bool = False,
        versions: dict[tuple[str | None, str, int], dict[str, Any]] | None = None,
        fail_tool: str | None = None,
        post_conflict: bool = False,
    ) -> None:
        self._names = list(names)
        self.viewonly = viewonly
        self.import_denied = import_denied
        self.versions = dict(versions or {})
        self.fail_tool = fail_tool
        self.post_conflict = post_conflict
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._next_id = 1000

    def names(self) -> list[str]:
        return list(self._names)

    async def dispatch(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, dict(arguments)))
        if self.fail_tool == tool:
            return {"ok": False, "error": f"{tool} failed"}
        if tool == "registry_info":
            return {"viewonly": self.viewonly, "name": arguments["registry"]}
        if tool == "begin_import":
            if self.import_denied:
                return {"ok": False, "error": "permission denied"}
            return {"ok": True, "previous_mode": "READWRITE"}
        if tool == "end_import":
            return {"ok": True}
        if tool == "get_subject_version":
            key = (arguments.get("context"), arguments["subject"], arguments["version"])
            stored = self.versions.get(key)
            if stored is None:
                return {"found": False}
            return {"found": True, "id": stored["id"], "schema": stored["schema"]}
        if tool == "import_schema_version":
            if self.post_conflict:
                return {"ok": False, "error": "Conflict"}
            new_id = arguments.get("schema_id")
            if new_id is None:
                new_id = self._next_id
                self._next_id += 1
            return {"ok": True, "id": new_id}
        if tool in {"update_subject_config", "update_global_config", "update_mode"}:
            return {"ok": True}
        return {"ok": False, "error": f"unknown operation {tool}"}


def _tools(fleet: RecordingFleet) -> list[str]:
    return [name for name, _ in fleet.calls]


def _subject_bundle(export_version: str | None = "1.7.0") -> dict[str, Any]:
    document: dict[str, Any] = {
        "subject": "user",
        "versions": [
            {"subject": "user", "version": 1, "id": 7, "schemaType": "AVRO", "schema": USER_SCHEMA},
        ],
    }
    if export_version is not None:
        document["metadata"] = {"export_version": export_version}
    return document


@pytest.mark.asyncio
async def test_dry_run_reports_import_and_writes_nothing() -> None:
    fleet = RecordingFleet(["dev"])
    report = await restore(_subject_bundle(), "dev", fleet)
    assert report.status == "dry_run"
    assert report.id_preservation == "import_required"
    assert report.export_version == "1.7.0"
    assert report.created == []
    assert fleet.calls == []


@pytest.mark.asyncio
async def test_dry_run_without_ids_is_preserved() -> None:
    bundle = _subject_bundle(None)
    del bundle["versions"][0]["id"]
    fleet = RecordingFleet(["dev"])
    report = await restore(bundle, "dev", fleet)
    assert report.status == "dry_run"
    assert report.id_preservation == "preserved"
    assert report.export_version is None
    assert fleet.calls == []


@pytest.mark.asyncio
async def test_import_failure_confirms_and_writes_nothing() -> None:
    fleet = RecordingFleet(["dev"], import_denied=True)
    report = await restore(_subject_bundle(), "dev", fleet, apply=True)
    assert report.status == "confirmation_required"
    assert report.id_preservation == "import_required"
    assert report.created == []
    assert _tools(fleet) == ["registry_info", "begin_import"]


@pytest.mark.asyncio
async def test_accept_new_ids_registers_without_opening_import() -> None:
    fleet = RecordingFleet(["dev"], import_denied=True)
    report = await restore(_subject_bundle(), "dev", fleet, apply=True, accept_new_ids=True)
    assert report.status == "applied"
    assert report.id_preservation == "new_ids"
    assert report.created[0]["schema_id"] == 1000
    posted = [args for name, args in fleet.calls if name == "import_schema_version"]
    assert posted and "schema_id" not in posted[0]
    assert "begin_import" not in _tools(fleet)


@pytest.mark.asyncio
async def test_matching_id_is_skipped() -> None:
    fleet = RecordingFleet(
        ["dev"],
        versions={(None, "user", 1): {"id": 7, "schema": json.dumps(USER_SCHEMA)}},
    )
    report = await restore(_subject_bundle(), "dev", fleet, apply=True)
    assert report.status == "applied"
    assert report.id_preservation == "preserved"
    assert report.skipped[0]["schema_id"] == 7
    assert report.created == []
    assert "import_schema_version" not in _tools(fleet)
    assert "end_import" in _tools(fleet)


@pytest.mark.asyncio
async def test_conflicting_id_is_not_overwritten_and_other_versions_continue() -> None:
    bundle = _subject_bundle()
    bundle["versions"].append(
        {"subject": "user", "version": 2, "id": 8, "schemaType": "AVRO", "schema": {"type": "string"}}
    )
    fleet = RecordingFleet(
        ["dev"],
        versions={(None, "user", 1): {"id": 7, "schema": {"type": "string"}}},
    )
    report = await restore(bundle, "dev", fleet, apply=True)
    assert report.status == "applied"
    assert report.conflicts[0]["schema_id"] == 7
    assert [item["schema_id"] for item in report.created] == [8]
    assert 7 not in {args.get("schema_id") for name, args in fleet.calls if name == "import_schema_version"}


@pytest.mark.asyncio
async def test_shared_schema_id_is_posted_for_each_subject() -> None:
    bundle = {
        "context": "orders",
        "subjects": [
            {"subject": "user", "versions": [{"version": 1, "id": 7, "schemaType": "AVRO", "schema": USER_SCHEMA}]},
            {"subject": "alias", "versions": [{"version": 1, "id": 7, "schemaType": "AVRO", "schema": USER_SCHEMA}]},
        ],
    }
    fleet = RecordingFleet(["dev"])
    report = await restore(bundle, "dev", fleet, apply=True)
    assert report.status == "applied"
    assert report.skipped == []
    posted = [(args["subject"], args["schema_id"]) for name, args in fleet.calls if name == "import_schema_version"]
    assert posted == [("user", 7), ("alias", 7)]
    lookups = [args for name, args in fleet.calls if name == "get_subject_version"]
    assert [(args["subject"], args["context"]) for args in lookups] == [("user", "orders"), ("alias", "orders")]


@pytest.mark.asyncio
async def test_post_conflict_is_incomplete_and_not_created() -> None:
    fleet = RecordingFleet(["dev"], post_conflict=True)
    report = await restore(_subject_bundle(), "dev", fleet, apply=True)
    assert report.status == "incomplete"
    assert report.created == []
    assert "import_schema_version" in _tools(fleet)


@pytest.mark.asyncio
async def test_schema_id_without_version_is_rejected_unless_new_ids() -> None:
    bundle = _subject_bundle()
    del bundle["versions"][0]["version"]
    fleet = RecordingFleet(["dev"])
    rejected = await restore(bundle, "dev", fleet, apply=True)
    assert rejected.status == "rejected"
    assert rejected.reason == "a schema id requires a version number"
    assert fleet.calls == []
    accepted = await restore(bundle, "dev", fleet, apply=True, accept_new_ids=True)
    assert accepted.status == "applied"
    assert accepted.id_preservation == "new_ids"


@pytest.mark.asyncio
async def test_viewonly_is_rejected_before_any_write() -> None:
    fleet = RecordingFleet(["dev"], viewonly=True)
    report = await restore(_subject_bundle(), "dev", fleet, apply=True)
    assert report.status == "rejected"
    assert report.reason == "Registry is VIEWONLY"
    assert _tools(fleet) == ["registry_info"]


@pytest.mark.asyncio
async def test_string_error_dict_and_bare_schema_are_rejected_before_the_fleet() -> None:
    fleet = RecordingFleet(["dev"])
    idl = await restore("record User { int id; }", "dev", fleet, apply=True)
    error = await restore({"error": "export failed"}, "dev", fleet, apply=True)
    bare = await restore({"subject": "user", "version": 1, "id": 7, "schema": USER_SCHEMA}, "dev", fleet, apply=True)
    assert idl.status == error.status == bare.status == "rejected"
    assert fleet.calls == []


@pytest.mark.asyncio
async def test_subject_filter_requires_context() -> None:
    fleet = RecordingFleet(["dev"])
    report = await restore(_subject_bundle(), "dev", fleet, subject="user")
    assert report.status == "rejected"
    assert fleet.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("stamp", ["1.7.0", __version__])
async def test_present_stamps_are_copied_and_are_not_a_gate(stamp: str) -> None:
    if stamp == "1.7.0":
        bundle: dict[str, Any] = _subject_bundle(stamp)
    else:
        bundle = {
            "contexts": [],
            "default_context": {"context": ".", "subjects": []},
            "metadata": {"export_version": stamp},
        }
    fleet = RecordingFleet(["dev"])
    report = await restore(bundle, "dev", fleet)
    assert report.status == "dry_run"
    assert report.export_version == stamp


@pytest.mark.asyncio
async def test_reference_order_versions_and_mode_restore_before_document_mode() -> None:
    bundle = {
        "context": "orders",
        "subjects": [
            {
                "subject": "order",
                "versions": [
                    {
                        "version": 2,
                        "id": 12,
                        "schemaType": "AVRO",
                        "schema": ORDER_SCHEMA,
                        "references": [{"name": "user", "subject": "user", "version": 1}],
                    },
                    {
                        "version": 1,
                        "id": 11,
                        "schemaType": "AVRO",
                        "schema": ORDER_SCHEMA,
                        "references": [{"name": "user", "subject": "user", "version": 1}],
                    },
                ],
            },
            {"subject": "user", "versions": [{"version": 1, "id": 7, "schemaType": "AVRO", "schema": USER_SCHEMA}]},
        ],
        "global_config": {"compatibilityLevel": "BACKWARD"},
        "global_mode": {"mode": "READWRITE"},
    }
    fleet = RecordingFleet(["dev"])
    report = await restore(bundle, "dev", fleet, apply=True)
    assert report.status == "applied"
    posted = [(args["subject"], args["version"]) for name, args in fleet.calls if name == "import_schema_version"]
    assert posted == [("user", 1), ("order", 1), ("order", 2)]
    lookups = [args for name, args in fleet.calls if name == "get_subject_version"]
    assert lookups and all(args["context"] == "orders" for args in lookups)
    names = _tools(fleet)
    assert "create_context" not in names
    assert names.index("get_subject_version") < names.index("import_schema_version")
    assert names.index("end_import") < names.index("update_global_config")
    assert names.index("update_global_config") < names.index("update_mode")


@pytest.mark.asyncio
async def test_reference_cycle_is_incomplete_and_writes_nothing() -> None:
    bundle = {
        "context": "loop",
        "subjects": [
            {
                "subject": "a",
                "versions": [{"version": 1, "id": 1, "schema": {}, "references": [{"subject": "b"}]}],
            },
            {
                "subject": "b",
                "versions": [{"version": 1, "id": 2, "schema": {}, "references": [{"subject": "a"}]}],
            },
        ],
    }
    fleet = RecordingFleet(["dev"])
    report = await restore(bundle, "dev", fleet, apply=True)
    assert report.status == "incomplete"
    assert report.reason == "reference cycle"
    assert fleet.calls == []


@pytest.mark.asyncio
async def test_previous_mode_is_restored_when_a_later_step_fails() -> None:
    bundle = _subject_bundle()
    bundle["config"] = {"compatibilityLevel": "FULL"}
    fleet = RecordingFleet(["dev"], fail_tool="update_subject_config")
    report = await restore(bundle, "dev", fleet, apply=True)
    assert report.status == "incomplete"
    names = _tools(fleet)
    assert "end_import" in names
    assert names.index("import_schema_version") < names.index("end_import")
    assert names.index("end_import") < names.index("update_subject_config")


def test_import_helper_restores_the_previous_mode_after_a_failure() -> None:
    session = _Session()
    client = _Client(session)
    previous = open_import_mode(client)
    assert previous == "READWRITE"
    try:
        raise RuntimeError("version write failed")
    except RuntimeError:
        assert restore_previous_mode(client, previous) is True
    puts = [payload for method, _url, payload in session.calls if method == "PUT"]
    assert puts == [{"mode": "IMPORT"}, {"mode": "READWRITE"}]


def test_import_helper_reports_denial_without_changing_mode() -> None:
    session = _Session(put_status=403)
    with pytest.raises(ImportModeUnavailable) as caught:
        open_import_mode(_Client(session))
    assert caught.value.reason == "Permission denied to set IMPORT mode"
    puts = [payload for method, _url, payload in session.calls if method == "PUT"]
    assert puts == [{"mode": "IMPORT"}]


def test_import_helper_lets_viewonly_propagate() -> None:
    session = _Session(raise_on_put=ViewOnlyError("viewonly"))
    with pytest.raises(ViewOnlyError):
        open_import_mode(_Client(session))


def test_import_helper_default_put_has_no_force_query() -> None:
    session = _Session()
    open_import_mode(_Client(session))
    puts = [url for method, url, _payload in session.calls if method == "PUT"]
    assert puts == ["http://registry.test/mode"]


def test_import_helper_force_adds_the_query() -> None:
    session = _Session()
    open_import_mode(_Client(session), force=True)
    puts = [url for method, url, _payload in session.calls if method == "PUT"]
    assert puts == ["http://registry.test/mode?force=true"]


def test_migrate_confirmation_when_import_is_denied() -> None:
    from migration_tools import MigrationConfirmationRequired, _execute_schema_migration

    source = _Client(_VersionSession())
    target_session = _Session(put_status=403)
    with pytest.raises(MigrationConfirmationRequired) as caught:
        _execute_schema_migration("user", source, _Client(target_session), versions=[1])
    assert caught.value.confirmation_details["error_reason"] == "Permission denied to set IMPORT mode"
    puts = [url for method, url, _payload in target_session.calls if method == "PUT"]
    assert puts and all("force" not in url for url in puts)


def test_restore_bundle_catalog_is_admin_destructive_task() -> None:
    from edition import Edition
    from tool_catalog import TOOL_CATALOG

    spec = TOOL_CATALOG["restore_bundle"]
    assert spec.min_edition == Edition.ADMIN
    assert spec.scope == "admin"
    assert spec.mutates is True
    assert spec.task is True
    assert spec.annotations is not None
    assert spec.annotations.destructive_hint is True


@pytest.mark.asyncio
async def test_disaster_recovery_plan_names_restore_bundle_and_does_not_call_it() -> None:
    from fastmcp import Client, FastMCP

    from elicitation import ElicitationManager
    from workflow_mcp_integration import WorkflowMCPTools

    source = inspect.getsource(WorkflowMCPTools._register_tools)
    body = source[source.index("async def guided_disaster_recovery") :]
    assert "restore_bundle" in body
    assert "restore_bundle(" not in body
    assert "export_global and migrate_context" not in body

    mcp = FastMCP("restore-plan")
    WorkflowMCPTools(mcp, ElicitationManager())
    async with Client(mcp) as client:
        result = await client.call_tool("guided_disaster_recovery", {"backup_target": "memory://backup"})
    raw = result.data if result.data is not None else result.content[0].text
    plan = json.loads(raw) if isinstance(raw, str) else raw
    assert isinstance(plan, dict)
    assert any("restore_bundle" in step for step in plan["steps"])
    assert "restore_bundle" in plan["note"]


class _Response:
    def __init__(self, status: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status
        self._payload = {} if payload is None else payload
        self.text = text or str(payload)

    def json(self) -> Any:
        return self._payload


class _Session:
    def __init__(self, *, put_status: int = 200, raise_on_put: BaseException | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.put_status = put_status
        self.raise_on_put = raise_on_put

    def get(self, url: str, **_kwargs: Any) -> _Response:
        self.calls.append(("GET", url, None))
        return _Response(200, {"mode": "READWRITE"})

    def put(self, url: str, **kwargs: Any) -> _Response:
        if self.raise_on_put is not None:
            raise self.raise_on_put
        payload = kwargs.get("json")
        self.calls.append(("PUT", url, payload))
        return _Response(self.put_status, payload, text="denied")


class _VersionSession(_Session):
    """Source registry that answers the versions list."""

    def get(self, url: str, **_kwargs: Any) -> _Response:
        self.calls.append(("GET", url, None))
        return _Response(200, [1])


class _Config:
    url = "http://registry.test"
    name = "dev"


class _Client:
    def __init__(self, session: _Session) -> None:
        self.session = session
        self.auth = None
        self.headers: dict[str, str] = {}
        self.config = _Config()
