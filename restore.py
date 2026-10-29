"""Apply an export document to one registry, preserving schema ids.

``restore`` talks only to a ``Fleet``. The in-process adapter turns those
calls into ``RegistryClient`` operations. A front process can replace the
adapter and dispatch the whole ``restore_bundle`` call to the shard.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.parse import quote

from migration_tools import ImportModeUnavailable, open_import_mode, restore_previous_mode
from schema_registry_common import ViewOnlyError

logger = logging.getLogger(__name__)

OP_INFO = "registry_info"
OP_BEGIN_IMPORT = "begin_import"
OP_END_IMPORT = "end_import"
OP_CREATE_CONTEXT = "create_context"
OP_SCHEMA_BY_ID = "get_schema_by_id"
OP_IMPORT_VERSION = "import_schema_version"
OP_SUBJECT_CONFIG = "update_subject_config"
OP_GLOBAL_CONFIG = "update_global_config"
OP_MODE = "update_mode"

_DEFAULT_CONTEXTS = (None, "", ".")


class Fleet(Protocol):
    """Section 4 fleet. M3 supplies the front and group implementations."""

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Run one operation against a registry named in ``arguments``."""

    def names(self) -> list[str]:
        """Return the registry names this fleet can address."""


@dataclass
class RestoreReport:
    """Result of one restore call.

    ``status`` is ``dry_run``, ``applied``, ``incomplete``,
    ``confirmation_required``, or ``rejected``.
    ``id_preservation`` is ``preserved``, ``import_required``, or ``new_ids``.
    """

    status: str
    created: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    id_preservation: str
    export_version: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the report as a JSON-ready dictionary."""
        return {
            "status": self.status,
            "created": self.created,
            "skipped": self.skipped,
            "conflicts": self.conflicts,
            "id_preservation": self.id_preservation,
            "export_version": self.export_version,
            "reason": self.reason,
        }


@dataclass
class VersionPlan:
    """One schema version inside an export document."""

    version: int | None
    schema_id: int | None
    schema: Any
    schema_type: str
    references: list[dict[str, Any]]


@dataclass
class SubjectPlan:
    """One subject, already narrowed to the requested context."""

    context: str | None
    name: str
    versions: list[VersionPlan]
    compatibility: str | None


@dataclass
class ContextPlan:
    """A context to create, plus the compatibility and mode to write afterwards."""

    name: str | None
    compatibility: str | None
    mode: str | None


@dataclass
class Document:
    """A recognized export document, filtered and ordered for writing."""

    contexts: list[ContextPlan]
    subjects: list[SubjectPlan]
    ordered: list[SubjectPlan]
    cycle: bool
    export_version: str | None


@dataclass
class Outcome:
    """Versions and settings touched during an apply."""

    created: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    failed: bool = False
    reason: str | None = None


class RegistryFleet:
    """In-process fleet. ``dispatch`` becomes ``RegistryClient`` calls.

    Schema-id posts use the private ``import_schema_version`` operation.
    The public ``register_schema`` tool does not learn ``schema_id``.
    """

    def __init__(self, registry_manager: Any) -> None:
        self._manager = registry_manager
        self._imports: dict[str, tuple[Any, str]] = {}

    def names(self) -> list[str]:
        """Return configured registry names."""
        return list(self._manager.list_registries())

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Run one restore operation against the named registry."""
        registry = str(arguments["registry"])
        client = self._manager.get_registry(registry)
        if client is None:
            return {"ok": False, "error": f"Registry '{registry}' not found"}
        handler = {
            OP_INFO: self._info,
            OP_BEGIN_IMPORT: self._begin_import,
            OP_END_IMPORT: self._end_import,
            OP_CREATE_CONTEXT: self._create_context,
            OP_SCHEMA_BY_ID: self._schema_by_id,
            OP_IMPORT_VERSION: self._import_version,
            OP_SUBJECT_CONFIG: self._subject_config,
            OP_GLOBAL_CONFIG: self._global_config,
            OP_MODE: self._mode,
        }.get(tool)
        if handler is None:
            return {"ok": False, "error": f"Unknown operation '{tool}'"}
        return handler(client, arguments)

    def _info(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {"viewonly": bool(client.config.viewonly), "name": client.config.name}

    def _begin_import(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        try:
            previous = open_import_mode(client)
        except ImportModeUnavailable as exc:
            return {"ok": False, "reason": exc.reason, "error": exc.detail}
        self._imports[client.config.name] = (client, previous)
        return {"ok": True, "previous_mode": previous}

    def _end_import(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        pair = self._imports.pop(client.config.name, None)
        if pair is None:
            return {"ok": True}
        stored, previous = pair
        return {"ok": restore_previous_mode(stored, previous)}

    def _create_context(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        name = str(arguments["context"])
        url = f"{client.config.url}/contexts/{quote(name, safe='')}"
        response = client.session.post(url, auth=client.auth, headers=client.headers, timeout=10)
        if response.status_code in (200, 201, 204, 409):
            return {"ok": True}
        return {"ok": False, "error": response.text}

    def _schema_by_id(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        schema_id = arguments["schema_id"]
        url = f"{client.config.url}/schemas/ids/{schema_id}"
        response = client.session.get(url, auth=client.auth, headers=client.headers, timeout=10)
        if response.status_code == 404:
            return {"found": False}
        if response.status_code != 200:
            return {"found": False, "error": response.text}
        try:
            body = response.json()
        except ValueError:
            return {"found": False, "error": "schema by id was not JSON"}
        return {"found": True, "id": schema_id, "schema": body.get("schema")}

    def _import_version(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        subject = str(arguments["subject"])
        context = arguments.get("context")
        payload: dict[str, Any] = {
            "schema": _schema_text(arguments.get("schema")),
            "schemaType": arguments.get("schema_type") or "AVRO",
        }
        references = arguments.get("references") or []
        if references:
            payload["references"] = references
        schema_id = arguments.get("schema_id")
        if schema_id is not None:
            payload["id"] = schema_id
        version = arguments.get("version")
        if version is not None:
            payload["version"] = version
        url = client.build_context_url(f"/subjects/{quote(subject, safe='')}/versions", context)
        response = client.session.post(
            url,
            json=payload,
            auth=client.auth,
            headers={**client.headers, "Content-Type": "application/vnd.schemaregistry.v1+json"},
            timeout=10,
        )
        if response.status_code not in (200, 409):
            return {"ok": False, "error": response.text}
        new_id = schema_id
        if response.status_code == 200:
            try:
                new_id = response.json().get("id", schema_id)
            except ValueError:
                new_id = schema_id
        return {"ok": True, "id": new_id}

    def _subject_config(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        result = client.update_subject_config(
            str(arguments["subject"]),
            str(arguments["compatibility"]),
            arguments.get("context"),
        )
        return _ok_result(result)

    def _global_config(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        result = client.update_global_config(str(arguments["compatibility"]), arguments.get("context"))
        return _ok_result(result)

    def _mode(self, client: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        _require_write(client)
        result = client.update_mode(str(arguments["mode"]), arguments.get("context"))
        return _ok_result(result)


def _require_write(client: Any) -> None:
    if client.config.viewonly:
        raise ViewOnlyError(f"Registry '{client.config.name}' is VIEWONLY")


def _ok_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"]}
    return {"ok": True}


def _schema_text(schema: Any) -> str:
    if isinstance(schema, str):
        return schema
    return json.dumps(schema)


async def restore(
    bundle: Any,
    target: str,
    fleet: Fleet,
    *,
    apply: bool = False,
    accept_new_ids: bool = False,
    context: str | None = None,
    subject: str | None = None,
) -> RestoreReport:
    """Apply an export document to ``target``.

    ``apply`` defaults to false and writes nothing. ``accept_new_ids`` is the
    retry after IMPORT mode cannot be set. ``subject`` requires ``context``.

    Args:
        bundle: An ``export_global``, ``export_context``, or ``export_subject`` document.
        target: Registry name in ``fleet``.
        fleet: Dispatch target. Tests pass a recording fleet.
        apply: Write when true. Preview when false.
        accept_new_ids: Register new schema ids instead of preserving them.
        context: Optional context filter. ``"."`` is the default context.
        subject: Optional subject filter. Requires ``context``.

    Returns:
        The restore report. No registry mode is changed when ``apply`` is false.
    """
    prepared = _prepare(bundle, context, subject)
    if isinstance(prepared, RestoreReport):
        return prepared
    preservation = _id_preservation(prepared, accept_new_ids)
    if prepared.cycle:
        return _finish("incomplete", prepared, id_preservation=preservation, reason="reference cycle")
    if target not in fleet.names():
        return _finish(
            "rejected",
            prepared,
            id_preservation=preservation,
            reason=f"Unknown registry '{target}'",
        )
    if not apply:
        return _finish("dry_run", prepared, id_preservation=preservation)
    try:
        info = await fleet.dispatch(OP_INFO, {"registry": target})
    except ViewOnlyError:
        return _finish("rejected", prepared, id_preservation=preservation, reason="Registry is VIEWONLY")
    if not isinstance(info, Mapping) or info.get("viewonly") or info.get("error"):
        reason = "Registry is VIEWONLY"
        if isinstance(info, Mapping) and info.get("error") and not info.get("viewonly"):
            reason = str(info["error"])
        return _finish("rejected", prepared, id_preservation=preservation, reason=reason)
    return await _apply(fleet, target, prepared, accept_new_ids, preservation)


def _finish(
    status: str,
    document: Document,
    outcome: Outcome | None = None,
    *,
    id_preservation: str,
    reason: str | None = None,
) -> RestoreReport:
    return RestoreReport(
        status=status,
        created=list(outcome.created) if outcome else [],
        skipped=list(outcome.skipped) if outcome else [],
        conflicts=list(outcome.conflicts) if outcome else [],
        id_preservation=id_preservation,
        export_version=document.export_version,
        reason=reason,
    )


def _rejected(reason: str, export_version: str | None = None) -> RestoreReport:
    return RestoreReport(
        status="rejected",
        created=[],
        skipped=[],
        conflicts=[],
        id_preservation="preserved",
        export_version=export_version,
        reason=reason,
    )


async def _apply(
    fleet: Fleet,
    target: str,
    document: Document,
    accept_new_ids: bool,
    preservation: str,
) -> RestoreReport:
    """Open IMPORT for version posts, then write config and the document mode."""
    outcome = Outcome()
    status = "applied"
    reason: str | None = None
    opened = False
    viewonly = False
    try:
        if preservation == "import_required":
            begin = await fleet.dispatch(OP_BEGIN_IMPORT, {"registry": target})
            if not isinstance(begin, Mapping) or not begin.get("ok"):
                detail = begin.get("error") if isinstance(begin, Mapping) else None
                status = "confirmation_required"
                reason = str(detail or "IMPORT mode could not be set")
            else:
                opened = True
        if status == "applied":
            await _write_versions(fleet, target, document, accept_new_ids, outcome)
            if outcome.failed:
                status = "incomplete"
                reason = outcome.reason
    except ViewOnlyError:
        viewonly = True
    finally:
        if opened:
            try:
                end = await fleet.dispatch(OP_END_IMPORT, {"registry": target})
            except ViewOnlyError:
                viewonly = True
            else:
                if not isinstance(end, Mapping) or not end.get("ok"):
                    if status == "applied":
                        status = "incomplete"
                        reason = "failed to restore the previous registry mode"
    if viewonly:
        return _finish("rejected", document, outcome, id_preservation=preservation, reason="Registry is VIEWONLY")
    if status != "applied":
        kept = "new_ids" if accept_new_ids else preservation
        return _finish(status, document, outcome, id_preservation=kept, reason=reason)
    try:
        await _write_settings(fleet, target, document, outcome)
    except ViewOnlyError:
        return _finish("rejected", document, outcome, id_preservation=preservation, reason="Registry is VIEWONLY")
    if outcome.failed:
        return _finish(
            "incomplete",
            document,
            outcome,
            id_preservation="new_ids" if accept_new_ids else "preserved",
            reason=outcome.reason,
        )
    final = "new_ids" if accept_new_ids else "preserved"
    return _finish("applied", document, outcome, id_preservation=final)


async def _write_versions(
    fleet: Fleet,
    target: str,
    document: Document,
    accept_new_ids: bool,
    outcome: Outcome,
) -> None:
    for plan in document.contexts:
        if _is_default(plan.name):
            continue
        result = await fleet.dispatch(OP_CREATE_CONTEXT, {"registry": target, "context": plan.name})
        if not _succeeded(result):
            outcome.failed = True
            outcome.reason = _error_text(result, f"cannot create context '{plan.name}'")
            return
    for subject in document.ordered:
        for version in subject.versions:
            if outcome.failed:
                return
            await _write_version(fleet, target, subject, version, accept_new_ids, outcome)


async def _write_version(
    fleet: Fleet,
    target: str,
    subject: SubjectPlan,
    version: VersionPlan,
    accept_new_ids: bool,
    outcome: Outcome,
) -> None:
    preserve = version.schema_id is not None and not accept_new_ids
    if preserve:
        found = await fleet.dispatch(OP_SCHEMA_BY_ID, {"registry": target, "schema_id": version.schema_id})
        if isinstance(found, Mapping) and found.get("found"):
            if _same_schema(found.get("schema"), version.schema):
                outcome.skipped.append(_entry(subject, version, version.schema_id))
                return
            outcome.conflicts.append(
                {**_entry(subject, version, version.schema_id), "reason": "schema id exists with a different body"}
            )
            return
        if isinstance(found, Mapping) and found.get("error"):
            outcome.failed = True
            outcome.reason = str(found["error"])
            return
    posted = await fleet.dispatch(OP_IMPORT_VERSION, _version_arguments(target, subject, version, preserve))
    if not _succeeded(posted):
        outcome.failed = True
        outcome.reason = _error_text(posted, f"cannot import {subject.name} version {version.version}")
        return
    new_id = posted.get("id") if isinstance(posted, Mapping) else version.schema_id
    outcome.created.append(_entry(subject, version, new_id))


def _version_arguments(target: str, subject: SubjectPlan, version: VersionPlan, preserve: bool) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "registry": target,
        "subject": subject.name,
        "context": subject.context,
        "schema": version.schema,
        "schema_type": version.schema_type,
        "references": version.references,
    }
    if preserve:
        arguments["schema_id"] = version.schema_id
        arguments["version"] = version.version
    return arguments


async def _write_settings(fleet: Fleet, target: str, document: Document, outcome: Outcome) -> None:
    for subject in document.ordered:
        if not subject.compatibility:
            continue
        result = await fleet.dispatch(
            OP_SUBJECT_CONFIG,
            {
                "registry": target,
                "subject": subject.name,
                "context": subject.context,
                "compatibility": subject.compatibility,
            },
        )
        if not _succeeded(result):
            outcome.failed = True
            outcome.reason = _error_text(result, f"cannot update config for '{subject.name}'")
            return
    for plan in document.contexts:
        if plan.compatibility:
            result = await fleet.dispatch(
                OP_GLOBAL_CONFIG,
                {"registry": target, "context": plan.name, "compatibility": plan.compatibility},
            )
            if not _succeeded(result):
                outcome.failed = True
                outcome.reason = _error_text(result, "cannot update compatibility")
                return
        if plan.mode:
            result = await fleet.dispatch(OP_MODE, {"registry": target, "context": plan.name, "mode": plan.mode})
            if not _succeeded(result):
                outcome.failed = True
                outcome.reason = _error_text(result, "cannot update mode")
                return


def _succeeded(result: Any) -> bool:
    return isinstance(result, Mapping) and bool(result.get("ok"))


def _error_text(result: Any, fallback: str) -> str:
    if isinstance(result, Mapping) and result.get("error"):
        return str(result["error"])
    return fallback


def _entry(subject: SubjectPlan, version: VersionPlan, schema_id: Any) -> dict[str, Any]:
    return {
        "context": "." if _is_default(subject.context) else subject.context,
        "subject": subject.name,
        "version": version.version,
        "schema_id": schema_id,
    }


def _same_schema(left: Any, right: Any) -> bool:
    return _canonical(left) == _canonical(right)


def _canonical(schema: Any) -> str:
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            return schema
    try:
        return json.dumps(schema, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return str(schema)


def _prepare(bundle: Any, context: str | None, subject: str | None) -> Document | RestoreReport:
    if isinstance(bundle, str):
        return _rejected("not an export document")
    if not isinstance(bundle, dict):
        return _rejected("not an export document")
    if subject is not None and context is None:
        return _rejected("subject requires context")
    kind = _document_kind(bundle)
    if kind is None:
        return _rejected("not an export document")
    stamp = _stamp(bundle)
    document = _parse(bundle, kind, stamp)
    narrowed = _filter(document, context, subject)
    if narrowed is None:
        return _rejected("nothing in the bundle matches the filter", stamp)
    return narrowed


def _document_kind(bundle: Mapping[str, Any]) -> str | None:
    if "contexts" in bundle and "default_context" in bundle:
        return "global"
    if "context" in bundle and "subjects" in bundle:
        return "context"
    if "subject" in bundle and isinstance(bundle.get("versions"), list):
        return "subject"
    return None


def _stamp(bundle: Mapping[str, Any]) -> str | None:
    metadata = bundle.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("export_version")
        if isinstance(value, str):
            return value
    return None


def _parse(bundle: Mapping[str, Any], kind: str, stamp: str | None) -> Document:
    if kind == "global":
        contexts, subjects = _parse_global(bundle)
    elif kind == "context":
        plan, subjects = _parse_context(bundle)
        contexts = [plan]
    else:
        meta = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
        subject_plan = _parse_subject(bundle, _normalize_context(meta.get("context")))
        contexts = [ContextPlan(subject_plan.context, None, None)]
        subjects = [subject_plan]
    ordered, cycle = _order_subjects(subjects)
    return Document(contexts, subjects, ordered, cycle, stamp)


def _parse_global(bundle: Mapping[str, Any]) -> tuple[list[ContextPlan], list[SubjectPlan]]:
    contexts: list[ContextPlan] = []
    subjects: list[SubjectPlan] = []
    default_raw = bundle.get("default_context")
    for raw in bundle.get("contexts") or []:
        if not isinstance(raw, dict):
            continue
        if isinstance(default_raw, dict) and _is_default(raw.get("context")):
            continue
        plan, found = _parse_context(raw)
        contexts.append(plan)
        subjects.extend(found)
    if isinstance(default_raw, dict):
        plan, found = _parse_context(default_raw)
        plan.name = None
        contexts.append(plan)
        subjects.extend(found)
    else:
        plan = ContextPlan(None, None, None)
        contexts.append(plan)
    _overlay_registry_config(contexts, bundle)
    return contexts, subjects


def _overlay_registry_config(contexts: list[ContextPlan], bundle: Mapping[str, Any]) -> None:
    compatibility = _compatibility(bundle.get("global_config"))
    mode = _mode_name(bundle.get("global_mode"))
    for plan in contexts:
        if not _is_default(plan.name):
            continue
        if plan.compatibility is None:
            plan.compatibility = compatibility
        if plan.mode is None:
            plan.mode = mode
        return
    contexts.append(ContextPlan(None, compatibility, mode))


def _parse_context(raw: Mapping[str, Any]) -> tuple[ContextPlan, list[SubjectPlan]]:
    name = _normalize_context(raw.get("context"))
    subjects = [
        _parse_subject(item, name)
        for item in raw.get("subjects") or []
        if isinstance(item, dict) and item.get("subject")
    ]
    return ContextPlan(name, _compatibility(raw.get("global_config")), _mode_name(raw.get("global_mode"))), subjects


def _parse_subject(raw: Mapping[str, Any], context: str | None) -> SubjectPlan:
    versions = [_parse_version(item) for item in raw.get("versions") or [] if isinstance(item, dict)]
    versions.sort(key=_version_key)
    return SubjectPlan(context, str(raw.get("subject")), versions, _compatibility(raw.get("config")))


def _parse_version(raw: Mapping[str, Any]) -> VersionPlan:
    references = raw.get("references")
    if not isinstance(references, list):
        references = []
    clean = [item for item in references if isinstance(item, dict)]
    version = raw.get("version")
    return VersionPlan(
        version if isinstance(version, int) and not isinstance(version, bool) else None,
        _as_int(raw.get("id")),
        raw.get("schema"),
        str(raw.get("schemaType") or raw.get("schema_type") or "AVRO"),
        clean,
    )


def _version_key(version: VersionPlan) -> tuple[int, int]:
    if isinstance(version.version, int):
        return (0, version.version)
    return (1, 0)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _filter(document: Document, context: str | None, subject: str | None) -> Document | None:
    if context is None and subject is None:
        return document
    want = _normalize_context(context)
    contexts = [plan for plan in document.contexts if plan.name == want]
    subjects = [plan for plan in document.subjects if plan.context == want]
    if subject is not None:
        subjects = [plan for plan in subjects if plan.name == subject]
        for plan in contexts:
            plan.compatibility = None
            plan.mode = None
    if not contexts or (subject is not None and not subjects):
        return None
    ordered, cycle = _order_subjects(subjects)
    return Document(contexts, subjects, ordered, cycle, document.export_version)


def _order_subjects(subjects: list[SubjectPlan]) -> tuple[list[SubjectPlan], bool]:
    remaining = {index: _dependencies(subjects, index) for index in range(len(subjects))}
    ordered: list[SubjectPlan] = []
    placed: set[int] = set()
    ready = [index for index, deps in remaining.items() if not deps]
    while ready:
        ready.sort()
        index = ready.pop(0)
        if index in placed:
            continue
        placed.add(index)
        ordered.append(subjects[index])
        for other, deps in remaining.items():
            deps.discard(index)
            if not deps and other not in placed and other not in ready:
                ready.append(other)
    if len(ordered) != len(subjects):
        return subjects, True
    return ordered, False


def _dependencies(subjects: list[SubjectPlan], index: int) -> set[int]:
    owner = subjects[index]
    deps: set[int] = set()
    for version in owner.versions:
        for ref in version.references:
            other = ref.get("subject")
            if not isinstance(other, str):
                continue
            target = _resolve_reference(subjects, owner, other)
            if target is not None and target != index:
                deps.add(target)
    return deps


def _resolve_reference(subjects: list[SubjectPlan], owner: SubjectPlan, name: str) -> int | None:
    same = [index for index, plan in enumerate(subjects) if plan.name == name and plan.context == owner.context]
    if same:
        return same[0]
    anywhere = [index for index, plan in enumerate(subjects) if plan.name == name]
    if anywhere:
        return anywhere[0]
    return None


def _id_preservation(document: Document, accept_new_ids: bool) -> str:
    if accept_new_ids:
        return "new_ids"
    if any(version.schema_id is not None for subject in document.subjects for version in subject.versions):
        return "import_required"
    return "preserved"


def _compatibility(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    level = value.get("compatibilityLevel", value.get("compatibility"))
    if isinstance(level, str) and level:
        return level
    return None


def _mode_name(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        mode = value.get("mode")
        if isinstance(mode, str) and mode:
            return mode
    return None


def _normalize_context(value: Any) -> str | None:
    if value in _DEFAULT_CONTEXTS:
        return None
    return str(value)


def _is_default(value: str | None) -> bool:
    return value in _DEFAULT_CONTEXTS
