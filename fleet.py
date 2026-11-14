"""Route ``registry=`` to the process that owns that registry.

An in-process deployment keeps calling ``RegistryClient``. A front holds shard
URLs and a directory, and no registry password. Each call opens its own session
to the shard that owns the registry. The shared object is the request-bearer
auth, which does not store a token.
"""

from __future__ import annotations

import copy
import os
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from fastmcp.server.middleware import Middleware

from mrtr import is_modern_connection
from protocol_version import current_protocol_version
from resource_linking import add_links_to_response
from schema_validation import create_error_response
from tracing import inject_outbound

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
        "list_workflows",
        "describe_workflow",
        "start_workflow",
        "guided_schema_evolution",
        "guided_schema_migration",
        "guided_context_reorganization",
        "guided_disaster_recovery",
        "bulk_operations_wizard",
        "preview_bulk_operation",
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
        """Yield ``request`` with the caller bearer and the current trace.

        ``traceparent`` and ``tracestate`` are the only trace headers added.
        A context with no bearer still sends no Authorization header.
        """
        token = inbound_bearer()
        if token:
            request.headers["Authorization"] = _authorization_value(token)
        inject_outbound(request.headers)
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

    async def dispatch(self, tool: str, arguments: Mapping[str, Any], **_forward: Any) -> Any:
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

    async def dispatch(self, tool: str, arguments: Mapping[str, Any], **_forward: Any) -> Any:
        """Invoke the injected runner. The runner is the registered tool body."""
        return await self._runner(tool, dict(arguments))


class ClientGroupFleet:
    """Forwards a tool to the shard client that owns ``registry``.

    ``clients`` are disconnected templates. Each call clones one template, so
    the handshake uses the bearer on that call and the session is not shared.
    """

    def __init__(self, directory: Mapping[str, str], clients: Mapping[str, Any]) -> None:
        self._directory = dict(directory)
        self._clients = clients

    def names(self) -> list[str]:
        """Return directory registry names."""
        return list(self._directory)

    def member_for(self, registry: str) -> str | None:
        """Return the shard member for ``registry``."""
        return self._directory.get(registry)

    async def dispatch(self, tool: str, arguments: Mapping[str, Any], **forward: Any) -> Any:
        """Call the unprefixed tool on a fresh session for its member.

        An omitted registry is sent as the directory default only when the tool
        declares that argument. A pair call keeps the caller's arguments and uses
        the source registry's member. An unknown name returns the same
        ``REGISTRY_NOT_FOUND`` dict ``get_registry`` leads to, and does not open
        a session.
        """
        payload = dict(arguments)
        registry = _routing_registry(tool, payload)
        if registry is None:
            registry = self.names()[0] if self.names() else None
            if registry is not None:
                _assign_default_registry(tool, payload, registry, forward.get("fields"))
        if registry is None or self.member_for(registry) is None:
            return _registry_not_found(registry or "")
        member = self.member_for(registry)
        return await self._call_member(member, tool, payload, registry, forward)

    async def _call_member(
        self,
        member: str | None,
        tool: str,
        payload: dict[str, Any],
        registry: str,
        forward: Mapping[str, Any],
    ) -> Any:
        """Open one session on ``member`` and call ``tool``."""
        template = self._clients.get(member or "")
        if template is None:
            return _registry_not_found(registry)
        session = template.new()
        _align_session_protocol(session)
        async with session:
            result = await _invoke_session(session, tool, payload, forward)
            if _is_input_required(result) and not is_modern_connection():
                result = await _resolve_legacy_input(session, tool, payload, result)
        if _is_input_required(result):
            return result
        _raise_shard_error(result)
        return _unwrap_tool_result(result)


class FrontRouter(Middleware):
    """On a front, route tools/call and leave single-registry bodies on the shard."""

    def __init__(self, fleet: RoutingFleet) -> None:
        self._fleet = fleet

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        """Dispatch the tool, or run a process-local tool through ``call_next``.

        The registered tool is resolved first. FastMCP applies the edition and
        scope checks inside ``get_tool``, which a returned result would skip.
        """
        from fastmcp.tools.base import ToolResult

        tool = await _require_registered_tool(context)
        message = context.message
        arguments = _validated_arguments(tool, dict(message.arguments or {}))
        result = await route_tool(
            message.name,
            arguments,
            self._fleet,
            fields=_tool_fields(tool),
            input_responses=getattr(message, "input_responses", None),
            request_state=getattr(message, "request_state", None),
        )
        if result is LOCAL:
            return await call_next(context)
        if _is_input_required(result):
            from fastmcp.tools.base import InputRequiredToolResult

            return InputRequiredToolResult(result)
        if isinstance(result, str):
            return ToolResult(content=result)
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


def build_client_group(config: FleetConfig) -> dict[str, Any]:
    """Build one disconnected client per shard.

    One ``RequestBearerAuth`` is shared and does not store a token. Sessions
    are opened per call, not from a server lifespan.
    """
    from fastmcp import Client

    auth = RequestBearerAuth()
    return {
        member: Client(url, auth=auth, elicitation_handler=_bridge_elicitation) for member, url in config.shards.items()
    }


async def _require_registered_tool(context: Any) -> Any:
    """Refuse a call the front did not register or this caller may not use."""
    from fastmcp.exceptions import AuthorizationError

    message = getattr(context, "message", None)
    name = getattr(message, "name", None)
    server = getattr(getattr(context, "fastmcp_context", None), "fastmcp", None)
    if not isinstance(name, str) or server is None:
        raise AuthorizationError("Authorization failed: missing tool context")
    tool = await server.get_tool(name)
    if tool is None:
        raise AuthorizationError(f"Authorization failed for tool {name!r}: not found or not authorized")
    return tool


def _validated_arguments(tool: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    """Reject arguments the registered tool would reject, and apply its defaults.

    Cross-shard orchestration returns before ``call_next``, so FastMCP never
    validates that call. A falsy non-boolean such as ``dry_run: []`` would
    otherwise be treated as a real write.
    """
    schema = getattr(tool, "parameters", None)
    if not isinstance(schema, dict) or not schema.get("properties"):
        return arguments
    import jsonschema
    from fastmcp.exceptions import ValidationError

    try:
        jsonschema.validate(instance=arguments, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValidationError(exc.message) from exc
    validated = dict(arguments)
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, prop in properties.items():
            if name not in validated and isinstance(prop, dict) and prop.get("default") is not None:
                validated[name] = prop["default"]
    return validated


def _tool_fields(tool: Any) -> frozenset[str]:
    """Parameter names declared by the front's registered tool."""
    parameters = getattr(tool, "parameters", None)
    properties = parameters.get("properties") if isinstance(parameters, Mapping) else None
    if not isinstance(properties, Mapping):
        return frozenset()
    return frozenset(str(name) for name in properties)


async def _bridge_elicitation(message: str, response_type: Any, _params: Any, _request_context: Any) -> Any:
    """Relay a shard elicitation to the caller that is current on the front."""
    from fastmcp.client.elicitation import ElicitResult

    try:
        from fastmcp.server.dependencies import get_context

        context = get_context()
        result = await context.elicit(message, response_type if response_type is not None else dict)
    except Exception:
        return ElicitResult(action="decline")
    action = getattr(result, "action", None)
    if action == "accept":
        return getattr(result, "data", None)
    if action in {"decline", "cancel"}:
        return ElicitResult(action=action)
    return result


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


async def route_tool(name: str, arguments: Mapping[str, Any], fleet: RoutingFleet, **forward: Any) -> Any:
    """Route one front tool call. ``LOCAL`` means the process should run it."""
    args = dict(arguments)
    special = _special_tool(name, fleet)
    if special is not None:
        return special
    if name in _LOCAL_TOOLS:
        return LOCAL
    if _supplied_registry(args, "source_registry") or _supplied_registry(args, "target_registry"):
        return await _route_pair(name, args, fleet, forward)
    return await _route_one(name, args, fleet, forward)


def _supplied_registry(arguments: Mapping[str, Any], name: str) -> str | None:
    """A registry endpoint the caller named. Omitted and null are not endpoints."""
    value = arguments.get(name)
    if isinstance(value, str) and value:
        return value
    return None


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


async def _route_one(name: str, arguments: dict[str, Any], fleet: RoutingFleet, forward: Mapping[str, Any]) -> Any:
    registry = _explicit_registry(name, arguments)
    if registry is not None and fleet.member_for(registry) is None:
        return _registry_not_found(registry)
    return await fleet.dispatch(name, arguments, **dict(forward))


async def _route_pair(name: str, arguments: dict[str, Any], fleet: RoutingFleet, forward: Mapping[str, Any]) -> Any:
    source = str(arguments.get("source_registry") or "")
    target = str(arguments.get("target_registry") or "")
    source_member = fleet.member_for(source)
    if source_member is None:
        return _named_not_found("Source", source)
    target_member = fleet.member_for(target)
    if target_member is None:
        return _named_not_found("Target", target)
    if source_member == target_member:
        return await fleet.dispatch(name, arguments, **dict(forward))
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
    export_arguments: dict[str, Any] = {
        "subject": subject,
        "registry": source,
        "include_metadata": True,
        "include_config": False,
        "include_versions": "all",
    }
    if source_context and source_context != ".":
        export_arguments["context"] = source_context
    document = await fleet.dispatch("export_subject", export_arguments)
    if _is_export_error(document):
        return document
    source_doc = document if isinstance(document, Mapping) else {}
    incomplete = _incomplete_export(source_doc)
    if incomplete:
        return create_error_response(incomplete, error_code="EXPORT_INCOMPLETE", registry_mode="multi")
    available = [item for item in source_doc.get("versions") or [] if isinstance(item, dict)]
    bundle = _migrate_document(source_doc, arguments, str(target_context))
    if not bundle.get("versions"):
        return _nothing_to_migrate(arguments, len(available))
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
    return _migration_from_restore(restored, arguments, bundle, len(available))


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
    """A top-level error is a failed export, even when empty collections were added."""
    return isinstance(document, dict) and bool(document.get("error"))


def _incomplete_export(document: Mapping[str, Any]) -> str | None:
    """Refuse a subject export that dropped a source version.

    ``export_subject`` used to skip a version whose schema fetch failed and
    still return the rest. ``version_numbers`` is the registry's list. A
    missing or shorter ``versions`` array is not a complete history.
    """
    failed = document.get("failed_versions")
    if isinstance(failed, list) and failed:
        detail = document.get("error")
        return str(detail) if detail else "Export omitted source versions"
    numbers = document.get("version_numbers")
    if not isinstance(numbers, list):
        return "Export did not report the source version list"
    expected: list[int] = []
    for number in numbers:
        if isinstance(number, int):
            expected.append(number)
        elif isinstance(number, str) and number.isdigit():
            expected.append(int(number))
        else:
            return "Export did not report the source version list"
    exported = [
        item.get("version") for item in document.get("versions") or [] if isinstance(item, dict) and "version" in item
    ]
    if sorted(exported, key=_version_sort_key) != sorted(expected):
        return "Export did not include every source version"
    return None


def _version_sort_key(value: Any) -> tuple[int, str]:
    if isinstance(value, int):
        return (0, f"{value:020d}")
    return (1, str(value))


def _nothing_to_migrate(arguments: Mapping[str, Any], available: int) -> dict[str, Any]:
    """Match in-process migrate when the requested versions do not exist."""
    return {
        "total_versions": available,
        "versions_to_migrate": 0,
        "successful_migrations": 0,
        "failed_migrations": 0,
        "skipped_migrations": 0,
        "message": "No versions to migrate",
        "dry_run": bool(arguments.get("dry_run") or False),
        "registry_mode": "multi",
        "mcp_protocol_version": current_protocol_version(),
    }


def _migrate_document(document: Mapping[str, Any], arguments: Mapping[str, Any], target_context: str) -> dict[str, Any]:
    """Apply the target context and version subset the way migrate qualifies a subject."""
    bundle = copy.deepcopy(dict(document))
    bundle["subject"] = _bare_subject(str(bundle.get("subject") or ""))
    metadata = dict(bundle.get("metadata") or {})
    metadata["context"] = "." if not target_context or target_context == "." else target_context
    bundle["metadata"] = metadata
    bundle.pop("config", None)
    bundle["versions"] = _select_versions(
        bundle.get("versions") or [],
        arguments.get("versions"),
        bool(arguments.get("migrate_all_versions")),
    )
    return bundle


def _select_versions(available: Any, requested: Any, migrate_all: bool) -> list[dict[str, Any]]:
    """Keep the versions migrate would copy. ``total`` is counted before this filter."""
    items = [item for item in available or [] if isinstance(item, dict)]
    if isinstance(requested, list) and requested:
        wanted = set(requested)
        return [item for item in items if item.get("version") in wanted]
    if migrate_all:
        return items
    numbers = [item.get("version") for item in items if isinstance(item.get("version"), int)]
    if not numbers:
        return []
    latest = max(numbers)
    return [item for item in items if item.get("version") == latest]


def _bare_subject(subject: str) -> str:
    """Strip a ``:.context:subject`` prefix. Migrate registers the bare name on the target."""
    if subject.startswith(":.") and ":" in subject[2:]:
        parts = subject.split(":", 2)
        if len(parts) >= 3 and parts[2]:
            return parts[2]
    return subject


def _subjects_from_export(document: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    scoped = "subjects" in document and "context" in document
    if scoped and "contexts" not in document and "default_context" not in document:
        _collect_subjects(document, found, qualify=False)
        return found
    default = document.get("default_context")
    if isinstance(default, dict):
        _collect_subjects(default, found, qualify=True)
    for raw in document.get("contexts") or []:
        if isinstance(raw, dict):
            _collect_subjects(raw, found, qualify=True)
    return found


def _collect_subjects(raw: Mapping[str, Any], found: dict[str, list[dict[str, Any]]], *, qualify: bool) -> None:
    for subject in raw.get("subjects") or []:
        if isinstance(subject, dict) and subject.get("subject"):
            versions = [item for item in subject.get("versions") or [] if isinstance(item, dict)]
            found[_subject_key(raw, str(subject["subject"]), qualify=qualify)] = versions


def _subject_key(raw: Mapping[str, Any], name: str, *, qualify: bool) -> str:
    """Qualify a global-export subject. A context export keeps the bare name."""
    if not qualify:
        return name
    context = raw.get("context")
    if not isinstance(context, str) or context in {"", "."}:
        return name
    return f":.{context}:{name}"


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


def _routing_registry(tool: str, arguments: Mapping[str, Any]) -> str | None:
    """The registry that selects a shard. None means the caller named none."""
    explicit = _explicit_registry(tool, arguments)
    if explicit:
        return explicit
    source = arguments.get("source_registry")
    if isinstance(source, str) and source:
        return source
    return None


def _assign_default_registry(tool: str, payload: dict[str, Any], registry: str, fields: Any) -> None:
    """Put the directory default on a call that omitted it and declares the field.

    ``fields is None`` means the caller did not supply a schema. Direct tests
    and internal exports use that path. A front passes the registered names and
    leaves a registry-free tool unchanged.
    """
    if tool == "restore_bundle":
        if fields is None or "target" in fields:
            payload["target"] = registry
        return
    if fields is None or "registry" in fields:
        payload["registry"] = registry


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


def _align_session_protocol(session: Any) -> None:
    """Negotiate the shard at the caller's era.

    A legacy caller cannot answer ``InputRequiredResult``. A legacy session
    makes the shard use in-request elicitation, which the elicitation handler
    relays. A modern caller keeps the template's mode and receives the input
    request on the next tools/call.
    """
    if not hasattr(session, "mode"):
        return
    if not is_modern_connection():
        session.mode = "legacy"


def _raise_shard_error(result: Any) -> None:
    """A shard ``is_error`` result is a tool failure, not a successful payload."""
    if not getattr(result, "is_error", False):
        return
    from fastmcp.exceptions import ToolError

    raise ToolError(_shard_error_text(result))


def _shard_error_text(result: Any) -> str:
    content = getattr(result, "content", None) or []
    texts = [getattr(block, "text", None) for block in content]
    texts = [text for text in texts if isinstance(text, str) and text]
    if texts:
        return "\n".join(texts)
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, Mapping):
        error = structured.get("error")
        if error:
            return str(error)
    return "Shard tool call failed"


async def _resolve_legacy_input(session: Any, tool: str, payload: dict[str, Any], result: Any) -> Any:
    """Answer a modern shard input request with in-request elicitation and retry."""
    from fastmcp.exceptions import ToolError

    pending = result
    for _ in range(4):
        requests = getattr(pending, "input_requests", None) or {}
        if not requests:
            break
        responses = {}
        for key, request in requests.items():
            if getattr(request, "method", None) != "elicitation/create":
                break
            params = getattr(request, "params", None)
            schema = getattr(params, "requested_schema", None)
            if not isinstance(schema, Mapping):
                schema = {"type": "object", "properties": {}}
            responses[key] = await _elicit_form(str(getattr(params, "message", "") or ""), schema)
        else:
            pending = await _invoke_session(
                session,
                tool,
                payload,
                {
                    "input_responses": responses,
                    "request_state": getattr(pending, "request_state", None),
                },
            )
            if not _is_input_required(pending):
                return pending
            continue
        break
    raise ToolError("Shard asked for input a legacy caller cannot answer")


async def _elicit_form(message: str, schema: Mapping[str, Any]) -> Any:
    """Ask the current caller with the legacy in-request elicitation path."""
    from mcp.types import ElicitResult

    try:
        from fastmcp.server.dependencies import get_context

        from mrtr import ask

        outcome, value = await ask(get_context(), message=message, schema=dict(schema))
    except Exception:
        return ElicitResult(action="decline")
    if outcome != "answered" or not isinstance(value, Mapping):
        return ElicitResult(action="decline")
    return ElicitResult(action="accept", content=dict(value))


def _unwrap_tool_result(result: Any) -> Any:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    data = getattr(result, "data", None)
    if isinstance(data, (dict, str)):
        return data
    content = getattr(result, "content", None)
    texts = [getattr(block, "text", None) for block in content or []]
    texts = [text for text in texts if isinstance(text, str)]
    if len(texts) == 1:
        return texts[0]
    if texts:
        return "".join(texts)
    return result


def _is_input_required(result: Any) -> bool:
    """True for a shard ask that the caller must answer on the next tools/call."""
    return type(result).__name__ == "InputRequiredResult"


async def _invoke_session(session: Any, tool: str, payload: dict[str, Any], forward: Mapping[str, Any]) -> Any:
    """Call the shard, carrying a multi-round-trip retry when the caller sent one."""
    mcp_session = getattr(session, "session", None)
    if mcp_session is None:
        return await session.call_tool(tool, payload)
    return await mcp_session.call_tool(
        name=tool,
        arguments=payload,
        input_responses=forward.get("input_responses"),
        request_state=forward.get("request_state"),
        allow_input_required=True,
    )


def _migration_from_restore(
    restored: Any,
    arguments: Mapping[str, Any],
    bundle: Mapping[str, Any],
    available: int,
) -> Any:
    """Shape a restore report like in-process ``migrate_schema``."""
    if not isinstance(restored, Mapping) or "status" not in restored:
        return restored
    versions = bundle.get("versions") if isinstance(bundle.get("versions"), list) else []
    status = restored.get("status")
    successful, failed, skipped_count, details = _migration_tally(restored, versions)
    dry_run = status == "dry_run"
    body: dict[str, Any] = {
        "total_versions": available,
        "versions_to_migrate": len(versions),
        "successful_migrations": successful,
        "failed_migrations": failed,
        "skipped_migrations": skipped_count,
        "migration_details": details,
        "dry_run": dry_run or bool(arguments.get("dry_run") or False),
        "preserve_ids": arguments.get("preserve_ids", True) is not False,
        "message": _migration_message(successful, len(versions), dry_run, restored.get("reason")),
        "subject": bundle.get("subject"),
        "source_registry": arguments.get("source_registry"),
        "target_registry": arguments.get("target_registry"),
        "source_context": arguments.get("source_context") or ".",
        "target_context": arguments.get("target_context") or ".",
        "registry_mode": "multi",
        "mcp_protocol_version": current_protocol_version(),
    }
    if status == "confirmation_required":
        body["error"] = str(restored.get("reason") or "confirmation required")
        body["error_type"] = "confirmation_required"
        body["confirmation_details"] = {
            "reason": restored.get("reason"),
            "id_preservation": restored.get("id_preservation"),
        }
    elif status in {"rejected", "incomplete"} and restored.get("reason"):
        body["error"] = str(restored["reason"])
    return add_links_to_response(
        body,
        "migration",
        str(arguments.get("source_registry") or ""),
        source_registry=arguments.get("source_registry"),
        target_registry=arguments.get("target_registry"),
    )


def _migration_tally(
    restored: Mapping[str, Any],
    versions: list[Any],
) -> tuple[int, int, int, list[dict[str, Any]]]:
    """Count created, skipped, failed, and versions the restore never wrote."""
    status = restored.get("status")
    created = list(restored.get("created") or [])
    skipped = list(restored.get("skipped") or [])
    conflicts = list(restored.get("conflicts") or [])
    if status == "dry_run":
        details = [
            {"version": item.get("version"), "status": "simulated", "message": "Would migrate this version"}
            for item in versions
            if isinstance(item, dict)
        ]
        return len(versions), 0, 0, details
    if any(key in restored for key in ("created", "skipped", "conflicts")):
        missed = _unattempted_versions(versions, created, skipped, conflicts, restored.get("reason"), status)
        details = (
            [_migration_detail(item, "migrated") for item in created]
            + [_migration_detail(item, "skipped") for item in skipped]
            + [_migration_detail(item, "failed") for item in conflicts]
            + missed
        )
        return len(created), len(conflicts) + len(missed), len(skipped), details
    successful = len(versions) if status == "applied" else 0
    failed = 0
    details = [_migration_detail(item, "migrated") for item in versions]
    if status in {"rejected", "incomplete"} and successful == 0:
        failed = len(versions) or 1
        details = [_unattempted_detail(item, restored.get("reason")) for item in versions if isinstance(item, dict)]
    return successful, failed, 0, details


def _unattempted_versions(
    versions: list[Any],
    created: list[Any],
    skipped: list[Any],
    conflicts: list[Any],
    reason: Any,
    status: Any,
) -> list[dict[str, Any]]:
    """Versions absent from an incomplete or rejected restore report."""
    if status not in {"rejected", "incomplete"}:
        return []
    seen = {_version_number(item) for item in (*created, *skipped, *conflicts)}
    seen.discard(None)
    return [
        _unattempted_detail(item, reason)
        for item in versions
        if isinstance(item, dict) and item.get("version") not in seen
    ]


def _unattempted_detail(item: Mapping[str, Any], reason: Any) -> dict[str, Any]:
    detail = {"version": item.get("version"), "status": "failed"}
    if reason:
        detail["error"] = str(reason)
    return detail


def _version_number(item: Any) -> Any:
    if isinstance(item, Mapping):
        return item.get("version")
    return None


def _migration_detail(item: Any, status: str) -> dict[str, Any]:
    version = item.get("version") if isinstance(item, Mapping) else None
    detail: dict[str, Any] = {"version": version, "status": status}
    if isinstance(item, Mapping) and status == "failed":
        reason = item.get("reason") or item.get("error")
        if reason:
            detail["error"] = str(reason)
    return detail


def _migration_message(successful: int, total: int, dry_run: bool, reason: Any) -> str:
    if isinstance(reason, str) and reason:
        return reason
    suffix = " (dry run)" if dry_run else ""
    return f"Migrated {successful}/{total} versions successfully{suffix}"
