"""Route ``registry=`` to the process that owns that registry.

An in-process deployment keeps calling ``RegistryClient``. A front holds shard
URLs and a directory, and no registry password. ``ClientGroupFleet`` sends one
tool call to the shard member that owns the name.
"""

from __future__ import annotations

import copy
import os
import re
from collections.abc import Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from fastmcp.server.middleware import Middleware

from protocol_version import current_protocol_version
from resource_linking import add_links_to_response
from schema_validation import create_error_response

try:
    from httpx2 import Auth as HttpxAuth
except ImportError:  # pragma: no cover - FastMCP 4 ships httpx2
    from httpx import Auth as HttpxAuth

ToolRunner = Callable[[str, Mapping[str, Any]], Awaitable[Any]]

_PASSWORD_ENV = re.compile(r"^SCHEMA_REGISTRY_(USER|PASSWORD)(_\d+)?$")
_LOCAL_TOOLS = frozenset(
    {
        "ping",
        "list_available_resources",
        "suggest_resource_for_tool",
        "generate_resource_templates",
        "list_elicitation_requests",
        "get_elicitation_request",
        "cancel_elicitation_request",
        "get_elicitation_status",
        "submit_elicitation_response",
        "list_available_workflows",
        "get_workflow_status",
        "workflow_status",
        "abort_workflow",
        "get_mcp_compliance_status",
        "get_mcp_compliance_status_tool",
        "get_oauth_scopes_info_tool",
        "get_oauth_scopes_info_tool_wrapper",
        "get_oauth_scopes_info",
        "test_oauth_discovery_endpoints",
    }
)
_CROSS_SHARD_TOOLS = frozenset({"compare_registries", "find_missing_schemas", "migrate_schema"})


class LocalTool:
    """Sentinel: the front runs this tool in-process."""


LOCAL = LocalTool()


class RoutingFleet(Protocol):
    """Section 4 fleet. ``dispatch`` sends a tool, not a registry operation."""

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Send ``tool`` with ``arguments`` to the member that owns its registry."""

    def names(self) -> list[str]:
        """Return the registry names this fleet can address."""

    def member_for(self, registry: str) -> str | None:
        """Return the shard member that owns ``registry``, or None."""


@dataclass(frozen=True)
class FleetConfig:
    """Role, shard URLs, and the registry-to-member directory."""

    role: str
    shards: dict[str, str]
    directory: dict[str, str]

    @property
    def default_registry(self) -> str | None:
        """The first directory entry. Callers that omit ``registry`` use it."""
        return next(iter(self.directory), None)


class RequestBearerAuth(HttpxAuth):
    """Attach the inbound bearer on each outbound call of a pooled client.

    One instance is shared by every shard client. ``auth_flow`` reads the
    request that is current when httpx sends, so two contexts on one client
    send two tokens. A context with no bearer sends no Authorization header.
    """

    def auth_flow(self, request: Any) -> Any:
        """Yield ``request``, with Authorization set when a bearer is present."""
        token = inbound_bearer()
        if token:
            request.headers["Authorization"] = _authorization_value(token)
        yield request


class RecordingFleet:
    """Records ``(tool, arguments)`` and returns scripted results. No socket."""

    def __init__(
        self,
        directory: Mapping[str, str],
        results: Mapping[tuple[str, str], Any] | None = None,
    ) -> None:
        self._directory = dict(directory)
        self._results = dict(results or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def names(self) -> list[str]:
        """Return directory registry names."""
        return list(self._directory)

    def member_for(self, registry: str) -> str | None:
        """Return the scripted member for ``registry``."""
        return self._directory.get(registry)

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Record the call and return the scripted body for that registry."""
        payload = dict(arguments)
        self.calls.append((tool, payload))
        return self._results.get((tool, _call_registry(tool, payload)), {})


class InProcessFleet:
    """Runs a tool body already registered in this process. Holds no password."""

    def __init__(self, names: list[str], runner: ToolRunner) -> None:
        self._names = list(names)
        self._runner = runner

    def names(self) -> list[str]:
        """Return the registries this process owns."""
        return list(self._names)

    def member_for(self, registry: str) -> str | None:
        """Every local registry shares the ``inprocess`` member."""
        if registry in self._names:
            return "inprocess"
        return None

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Invoke the injected runner. The runner is the registered tool body."""
        return await self._runner(tool, dict(arguments))


class ClientGroupFleet:
    """Forwards a tool to the ClientGroup member that owns ``registry``."""

    def __init__(self, directory: Mapping[str, str], group: Any) -> None:
        self._directory = dict(directory)
        self._group = group

    def names(self) -> list[str]:
        """Return directory registry names."""
        return list(self._directory)

    def member_for(self, registry: str) -> str | None:
        """Return the shard member for ``registry``."""
        return self._directory.get(registry)

    async def dispatch(self, tool: str, arguments: Mapping[str, Any]) -> Any:
        """Resolve ``{member}_{tool}`` and call the unprefixed upstream name.

        ``registry`` is left as the caller sent it. An unknown name returns
        the same ``REGISTRY_NOT_FOUND`` dict ``get_registry`` leads to, and
        does not call the group.
        """
        payload = dict(arguments)
        registry = _explicit_registry(tool, payload)
        if registry is None:
            registry = self.names()[0] if self.names() else None
        if registry is None or self.member_for(registry) is None:
            return _registry_not_found(registry or "")
        member = self.member_for(registry)
        route = await self._group.resolve_tool(f"{member}_{tool}")
        result = await route.client.call_tool(route.upstream_name, payload)
        return _unwrap_tool_result(result)


class FrontRouter(Middleware):
    """On a front, route tools/call and leave single-registry bodies on the shard."""

    def __init__(self, fleet: RoutingFleet) -> None:
        self._fleet = fleet

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        """Dispatch the tool, or run a process-local tool through ``call_next``."""
        from fastmcp.tools.base import ToolResult

        message = context.message
        arguments = dict(message.arguments or {})
        result = await route_tool(message.name, arguments, self._fleet)
        if result is LOCAL:
            return await call_next(context)
        if not isinstance(result, dict):
            result = {"result": result}
        return ToolResult(structured_content=result)


def load_fleet_config(environ: Mapping[str, str] | None = None) -> FleetConfig:
    """Read ``FLEET_ROLE``, ``FLEET_SHARDS``, and ``FLEET_DIRECTORY``.

    A front refuses to start when a registry user or password is set. The
    directory's first entry is the default registry.

    Args:
        environ: Environment to read. Defaults to ``os.environ``.

    Returns:
        The selected role and, for a front, its directory.

    Raises:
        RuntimeError: A front's environment contains a registry password.
        ValueError: The role or directory is not usable.
    """
    env = os.environ if environ is None else environ
    role = env.get("FLEET_ROLE", "inprocess").strip().lower() or "inprocess"
    if role not in {"inprocess", "front"}:
        raise ValueError(f"FLEET_ROLE must be inprocess or front, got {role!r}")
    shards = _parse_pairs(env.get("FLEET_SHARDS", ""), "FLEET_SHARDS")
    directory = _parse_pairs(env.get("FLEET_DIRECTORY", ""), "FLEET_DIRECTORY")
    if role == "front":
        _refuse_registry_passwords(env)
        if not shards or not directory:
            raise ValueError("A front requires FLEET_SHARDS and FLEET_DIRECTORY")
        missing = sorted({member for member in directory.values() if member not in shards})
        if missing:
            raise ValueError(f"FLEET_DIRECTORY names unknown shards: {', '.join(missing)}")
    return FleetConfig(role=role, shards=shards, directory=directory)


def build_client_group(config: FleetConfig) -> Any:
    """Build one pooled client per shard. Auth is attached here, not via from_config."""
    from fastmcp import Client
    from fastmcp.client.group import ClientGroup

    auth = RequestBearerAuth()
    clients = {member: Client(url, auth=auth) for member, url in config.shards.items()}
    return ClientGroup(clients)


def fleet_lifespan(group: Any) -> Any:
    """Return a FastMCP lifespan that connects the shard pool."""

    @asynccontextmanager
    async def lifespan(server: Any) -> Any:
        async with group:
            yield {}

    return lifespan


def inbound_bearer() -> str | None:
    """Return the raw inbound bearer, or None when the context has no token.

    ``get_access_token`` sees a live HTTP request. A ``task=True`` call has
    already left that request, so the task headers are the fallback.
    """
    try:
        from fastmcp.server.dependencies import get_access_token, get_http_headers
    except ImportError:  # pragma: no cover
        return None
    try:
        access_token = get_access_token()
    except Exception:
        access_token = None
    raw = getattr(access_token, "token", None)
    if isinstance(raw, str) and raw:
        return raw
    try:
        headers = get_http_headers(include={"authorization"})
    except Exception:
        return None
    header = headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        return token or None
    return None


async def route_tool(name: str, arguments: Mapping[str, Any], fleet: RoutingFleet) -> Any:
    """Route one front tool call. ``LOCAL`` means the process should run it."""
    args = dict(arguments)
    special = _special_tool(name, fleet)
    if special is not None:
        return special
    if name in _LOCAL_TOOLS:
        return LOCAL
    if "source_registry" in args or "target_registry" in args:
        return await _route_pair(name, args, fleet)
    return await _route_one(name, args, fleet)


def _parse_pairs(raw: str, label: str) -> dict[str, str]:
    """Parse ``key=value`` items separated by commas. The value may contain ``=``."""
    parsed: dict[str, str] = {}
    if not raw.strip():
        return parsed
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"{label} entry {item!r} must be key=value")
        key, value = item.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError(f"{label} entry {item!r} must be key=value")
        if key in parsed:
            raise ValueError(f"{label} repeats {key!r}")
        parsed[key] = value
    return parsed


def _refuse_registry_passwords(env: Mapping[str, str]) -> None:
    found = sorted(key for key, value in env.items() if value and _PASSWORD_ENV.match(key))
    if found:
        raise RuntimeError("A front holds no registry passwords: " + ", ".join(found))


def _authorization_value(token: str) -> str:
    text = token.strip()
    if text.lower().startswith("bearer "):
        return text
    return f"Bearer {text}"


def _registry_not_found(registry: str) -> dict[str, Any]:
    return create_error_response(
        f"Registry '{registry}' not found",
        error_code="REGISTRY_NOT_FOUND",
        registry_mode="multi",
    )


def _named_not_found(role: str, registry: str) -> dict[str, Any]:
    return create_error_response(
        f"{role} registry '{registry}' not found",
        error_code=f"{role.upper()}_REGISTRY_NOT_FOUND",
        registry_mode="multi",
    )


def _special_tool(name: str, fleet: RoutingFleet) -> dict[str, Any] | None:
    if name == "list_registries":
        return _directory_listing(fleet)
    if name == "test_all_registries":
        return _directory_listing(fleet)
    if name == "get_default_registry":
        return {
            "default_registry": fleet.names()[0] if fleet.names() else None,
            "registry_mode": "multi",
            "mcp_protocol_version": current_protocol_version(),
        }
    if name == "set_default_registry":
        return create_error_response(
            "The fleet directory is environment configuration",
            error_code="FLEET_DIRECTORY_FIXED",
            registry_mode="multi",
        )
    return None


def _directory_listing(fleet: RoutingFleet) -> dict[str, Any]:
    """Names only. A front does not connect to the registries it routes."""
    version = current_protocol_version()
    registries = [{"name": name, "registry_mode": "multi", "mcp_protocol_version": version} for name in fleet.names()]
    result: dict[str, Any] = {
        "registries": registries,
        "total_count": len(registries),
        "registry_mode": "multi",
        "mcp_protocol_version": version,
    }
    if registries:
        result["default_registry"] = registries[0]["name"]
    else:
        result["message"] = "No registries configured"
    return result


async def _route_one(name: str, arguments: dict[str, Any], fleet: RoutingFleet) -> Any:
    registry = _explicit_registry(name, arguments)
    if registry is None:
        return await fleet.dispatch(name, arguments)
    if fleet.member_for(registry) is None:
        return _registry_not_found(registry)
    return await fleet.dispatch(name, arguments)


async def _route_pair(name: str, arguments: dict[str, Any], fleet: RoutingFleet) -> Any:
    source = str(arguments.get("source_registry") or "")
    target = str(arguments.get("target_registry") or "")
    source_member = fleet.member_for(source)
    if source_member is None:
        return _named_not_found("Source", source)
    target_member = fleet.member_for(target)
    if target_member is None:
        return _named_not_found("Target", target)
    if source_member == target_member:
        return await fleet.dispatch(name, arguments)
    if name == "compare_registries":
        return await _compare(arguments, fleet)
    if name == "find_missing_schemas":
        return await _find_missing(arguments, fleet)
    if name == "migrate_schema":
        return await _migrate(arguments, fleet)
    return create_error_response(
        f"{name} cannot run across shards",
        error_code="CROSS_SHARD_UNSUPPORTED",
        registry_mode="multi",
    )


async def _compare(arguments: Mapping[str, Any], fleet: RoutingFleet) -> dict[str, Any]:
    source = str(arguments["source_registry"])
    target = str(arguments["target_registry"])
    source_doc = await _export_global(fleet, source)
    if _is_export_error(source_doc):
        return source_doc
    target_doc = await _export_global(fleet, target)
    if _is_export_error(target_doc):
        return target_doc
    source_subjects = _subjects_from_export(source_doc)
    target_subjects = _subjects_from_export(target_doc)
    source_names = set(source_subjects)
    target_names = set(target_subjects)
    schema_differences = _schema_differences(source_subjects, target_subjects)
    comparison: dict[str, Any] = {
        "source_registry": source,
        "target_registry": target,
        "timestamp": datetime.now().isoformat(),
        "differences": {
            "subjects": _name_diff(source_names, target_names),
            "schemas": {
                "subjects_with_differences": schema_differences,
                "subjects_with_differences_count": len(schema_differences),
            },
        },
        "registry_mode": "multi",
        "mcp_protocol_version": current_protocol_version(),
    }
    if arguments.get("include_contexts", True):
        comparison["differences"]["contexts"] = _name_diff(
            _contexts_from_export(source_doc),
            _contexts_from_export(target_doc),
        )
    if arguments.get("include_configs", True):
        comparison["differences"]["global_config"] = _config_diff(source_doc, target_doc)
    subjects = comparison["differences"]["subjects"]
    comparison["summary"] = {
        "subjects_only_in_source": len(subjects["only_in_source"]),
        "subjects_only_in_target": len(subjects["only_in_target"]),
        "subjects_in_both": len(subjects["in_both"]),
        "schemas_with_differences": len(schema_differences),
        "registries_match": (
            not subjects["only_in_source"] and not subjects["only_in_target"] and not schema_differences
        ),
    }
    return add_links_to_response(
        comparison,
        "comparison",
        source,
        source_registry=source,
        target_registry=target,
    )


async def _find_missing(arguments: Mapping[str, Any], fleet: RoutingFleet) -> dict[str, Any]:
    source = str(arguments["source_registry"])
    target = str(arguments["target_registry"])
    context = arguments.get("context")
    source_doc = await _export_for_missing(fleet, source, context)
    if _is_export_error(source_doc):
        return source_doc
    target_doc = await _export_for_missing(fleet, target, context)
    if _is_export_error(target_doc):
        return target_doc
    source_subjects = _subjects_from_export(source_doc)
    target_names = set(_subjects_from_export(target_doc))
    missing = sorted(set(source_subjects) - target_names)
    details = [_missing_detail(name, source_subjects[name]) for name in missing]
    result: dict[str, Any] = {
        "source_registry": source,
        "target_registry": target,
        "context": context,
        "missing_subjects": missing,
        "missing_count": len(missing),
        "source_subject_count": len(source_subjects),
        "target_subject_count": len(target_names),
        "details": details,
        "timestamp": datetime.now().isoformat(),
        "registry_mode": "multi",
        "mcp_protocol_version": current_protocol_version(),
        "summary": {
            "migration_needed": len(missing) > 0,
            "total_versions_to_migrate": sum(detail.get("version_count", 0) for detail in details),
            "subjects_with_multiple_versions": len(
                [detail for detail in details if detail.get("version_count", 0) > 1]
            ),
        },
    }
    return add_links_to_response(
        result,
        "comparison",
        source,
        source_registry=source,
        target_registry=target,
    )


async def _migrate(arguments: Mapping[str, Any], fleet: RoutingFleet) -> Any:
    source = str(arguments["source_registry"])
    target = str(arguments["target_registry"])
    subject = str(arguments.get("subject") or "")
    source_context = arguments.get("source_context") or "."
    target_context = arguments.get("target_context") or "."
    versions = arguments.get("versions")
    include_versions = "all" if versions or arguments.get("migrate_all_versions") else "latest"
    export_arguments: dict[str, Any] = {
        "subject": subject,
        "registry": source,
        "include_metadata": True,
        "include_config": True,
        "include_versions": include_versions,
    }
    if source_context and source_context != ".":
        export_arguments["context"] = source_context
    document = await fleet.dispatch("export_subject", export_arguments)
    if _is_export_error(document):
        return document
    bundle = _migrate_document(document, versions, str(target_context))
    apply = not bool(arguments.get("dry_run") or False)
    accept_new_ids = arguments.get("preserve_ids", True) is False
    restored = await fleet.dispatch(
        "restore_bundle",
        {
            "bundle": bundle,
            "target": target,
            "apply": apply,
            "accept_new_ids": accept_new_ids,
        },
    )
    return restored


async def _export_global(fleet: RoutingFleet, registry: str) -> Any:
    return await fleet.dispatch(
        "export_global",
        {
            "registry": registry,
            "include_metadata": True,
            "include_config": True,
            "include_versions": "all",
        },
    )


async def _export_for_missing(fleet: RoutingFleet, registry: str, context: Any) -> Any:
    if isinstance(context, str) and context:
        return await fleet.dispatch(
            "export_context",
            {
                "context": context,
                "registry": registry,
                "include_metadata": True,
                "include_config": True,
                "include_versions": "all",
            },
        )
    return await _export_global(fleet, registry)


def _is_export_error(document: Any) -> bool:
    return (
        isinstance(document, dict) and "error" in document and "versions" not in document and "subjects" not in document
    )


def _migrate_document(document: Mapping[str, Any], versions: Any, target_context: str) -> dict[str, Any]:
    """Apply the target context and version subset the way migrate qualifies a subject."""
    bundle = copy.deepcopy(dict(document))
    bundle["subject"] = _bare_subject(str(bundle.get("subject") or ""))
    metadata = dict(bundle.get("metadata") or {})
    metadata["context"] = "." if not target_context or target_context == "." else target_context
    bundle["metadata"] = metadata
    if isinstance(versions, list) and versions:
        wanted = set(versions)
        bundle["versions"] = [
            item for item in bundle.get("versions") or [] if isinstance(item, dict) and item.get("version") in wanted
        ]
    return bundle


def _bare_subject(subject: str) -> str:
    """Strip a ``:.context:subject`` prefix. Migrate registers the bare name on the target."""
    if subject.startswith(":.") and ":" in subject[2:]:
        parts = subject.split(":", 2)
        if len(parts) >= 3 and parts[2]:
            return parts[2]
    return subject


def _subjects_from_export(document: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    if "subjects" in document and "context" in document:
        _collect_subjects(document, found)
        return found
    default = document.get("default_context")
    if isinstance(default, dict):
        _collect_subjects(default, found)
    for raw in document.get("contexts") or []:
        if isinstance(raw, dict):
            _collect_subjects(raw, found)
    return found


def _collect_subjects(raw: Mapping[str, Any], found: dict[str, list[dict[str, Any]]]) -> None:
    for subject in raw.get("subjects") or []:
        if isinstance(subject, dict) and subject.get("subject"):
            versions = [item for item in subject.get("versions") or [] if isinstance(item, dict)]
            found[str(subject["subject"])] = versions


def _contexts_from_export(document: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for raw in document.get("contexts") or []:
        if not isinstance(raw, dict):
            continue
        name = raw.get("context")
        if isinstance(name, str) and name not in {"", "."}:
            names.add(name)
    return names


def _schema_differences(
    source_subjects: Mapping[str, list[dict[str, Any]]],
    target_subjects: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    differences = []
    for subject in sorted(set(source_subjects) & set(target_subjects)):
        source_versions = _version_numbers(source_subjects[subject])
        target_versions = _version_numbers(target_subjects[subject])
        if source_versions != target_versions:
            differences.append(
                {
                    "subject": subject,
                    "source_versions": source_versions,
                    "target_versions": target_versions,
                    "source_version_count": len(source_versions),
                    "target_version_count": len(target_versions),
                }
            )
    return differences


def _version_numbers(versions: list[dict[str, Any]]) -> list[int]:
    numbers = []
    for item in versions:
        version = item.get("version")
        if isinstance(version, int) and not isinstance(version, bool):
            numbers.append(version)
    return numbers


def _name_diff(source: set[str], target: set[str]) -> dict[str, Any]:
    return {
        "only_in_source": sorted(source - target),
        "only_in_target": sorted(target - source),
        "in_both": sorted(source & target),
        "source_total": len(source),
        "target_total": len(target),
        "common_count": len(source & target),
    }


def _config_diff(source_doc: Mapping[str, Any], target_doc: Mapping[str, Any]) -> dict[str, Any]:
    source = _clean_config(source_doc.get("global_config"))
    target = _clean_config(target_doc.get("global_config"))
    source_clean = {key: value for key, value in source.items() if key not in {"registry", "error"}}
    target_clean = {key: value for key, value in target.items() if key not in {"registry", "error"}}
    return {
        "source": source,
        "target": target,
        "match": source_clean == target_clean,
        "differences": {
            key: {"source": source_clean.get(key), "target": target_clean.get(key)}
            for key in set(source_clean) | set(target_clean)
            if source_clean.get(key) != target_clean.get(key)
        },
    }


def _clean_config(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _missing_detail(subject: str, versions: list[dict[str, Any]]) -> dict[str, Any]:
    numbers = _version_numbers(versions)
    latest = max(numbers) if numbers else None
    latest_body = next((item for item in versions if item.get("version") == latest), None)
    return {
        "subject": subject,
        "versions": numbers,
        "version_count": len(numbers),
        "latest_version": latest,
        "latest_schema_id": latest_body.get("id") if isinstance(latest_body, dict) else None,
        "schema_type": (latest_body.get("schemaType", "AVRO") if isinstance(latest_body, dict) else None),
    }


def _explicit_registry(tool: str, arguments: Mapping[str, Any]) -> str | None:
    """The registry the caller named. None means the caller omitted it."""
    if tool == "restore_bundle":
        target = arguments.get("target")
        return str(target) if target else None
    if "registry" not in arguments or arguments.get("registry") in (None, ""):
        return None
    return str(arguments["registry"])


def _call_registry(tool: str, arguments: Mapping[str, Any]) -> str:
    explicit = _explicit_registry(tool, arguments)
    if explicit:
        return explicit
    for field in ("registry", "target", "source_registry"):
        value = arguments.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def _unwrap_tool_result(result: Any) -> Any:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    return result
