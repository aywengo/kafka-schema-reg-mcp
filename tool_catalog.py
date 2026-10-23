"""Declarative tool and prompt catalog for the v3.0 editions.

One entry per MCP tool. Registration iterates this table and skips anything
whose ``min_edition`` is above the active edition, so out-of-edition tools are
never registered (and therefore never listed or cached by clients).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from mcp_types import ToolAnnotations

from edition import Edition


@dataclass(frozen=True)
class ToolSpec:
    name: str
    min_edition: Edition
    scope: str
    mutates: bool
    write_targets: tuple[str, ...] = ()
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)
    task: bool = False


@dataclass(frozen=True)
class PromptSpec:
    name: str
    min_edition: Edition


def _read(name: str, *, idempotent: bool = True) -> ToolSpec:
    return ToolSpec(
        name=name,
        min_edition=Edition.VIEWER,
        scope="read",
        mutates=False,
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=idempotent),
    )


def _write(
    name: str,
    edition: Edition = Edition.EDITOR,
    *,
    scope: str = "write",
    targets: tuple[str, ...] = ("registry",),
    destructive: bool = False,
    task: bool = False,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        min_edition=edition,
        scope=scope,
        mutates=True,
        write_targets=targets,
        annotations=ToolAnnotations(destructiveHint=destructive, idempotentHint=False),
        task=task,
    )


def _admin(
    name: str, *, targets: tuple[str, ...] = ("registry",), destructive: bool = False, task: bool = False
) -> ToolSpec:
    return _write(name, Edition.ADMIN, scope="admin", targets=targets, destructive=destructive, task=task)


_SPECS: list[ToolSpec] = []

# Viewer: protocol, discovery, registry info, reads, compatibility, export, comparison, statistics.
for _name in (
    "ping",
    "get_mcp_compliance_status",
    "list_available_resources",
    "suggest_resource_for_tool",
    "generate_resource_templates",
    "get_oauth_scopes_info",
    "test_oauth_discovery_endpoints",
    "list_registries",
    "get_registry_info",
    "test_registry_connection",
    "test_all_registries",
    "get_default_registry",
    "list_subjects",
    "list_contexts",
    "get_schema",
    "get_schema_versions",
    "get_schema_by_id",
    "get_subjects_by_schema_id",
    "get_global_config",
    "get_mode",
    "get_subject_config",
    "get_subject_mode",
    "check_compatibility",
    "check_compatibility_interactive",
    "export_schema",
    "export_subject",
    "export_context",
    "export_global",
    "export_global_interactive",
    "compare_registries",
    "compare_contexts_across_registries",
    "find_missing_schemas",
    "count_contexts",
    "count_schemas",
    "count_schema_versions",
    "get_registry_statistics",
    "list_workflows",
    "describe_workflow",
):
    _SPECS.append(_read(_name))

# Editor: schema authoring.
_SPECS.extend(
    [
        _write("register_schema"),
        _write("register_schema_interactive"),
        _write("guided_schema_evolution"),
    ]
)

# Admin: lifecycle, configuration, migration, bulk, guided workflows.
_SPECS.extend(
    [
        _write("create_context", Edition.ADMIN, destructive=False),
        _write("create_context_interactive", Edition.ADMIN, destructive=False),
        _admin("delete_context", destructive=True),
        _admin("delete_subject", destructive=True),
        _write("update_global_config", Edition.ADMIN),
        _write("update_subject_config", Edition.ADMIN),
        _write("update_mode", Edition.ADMIN),
        _write("update_subject_mode", Edition.ADMIN),
        _admin("add_subject_alias"),
        _admin("delete_subject_alias", destructive=True),
        _admin("migrate_schema", targets=("target_registry",), destructive=True, task=True),
        _admin("migrate_context", targets=("target_registry",), destructive=True, task=True),
        _admin("migrate_context_interactive", targets=("target_registry",), destructive=True),
        _admin("migrate_schema_interactive", targets=("target_registry",), destructive=True),
        _admin("clear_context_batch", destructive=True, task=True),
        _admin("clear_multiple_contexts_batch", destructive=True, task=True),
        _admin("bulk_operations_wizard"),
        _admin("bulk_schema_update", task=True),
        _admin("bulk_schema_cleanup", destructive=True, task=True),
        _admin("bulk_schema_migration", targets=("target_registry",), destructive=True, task=True),
        _admin("bulk_configuration_update", task=True),
        ToolSpec(
            name="preview_bulk_operation",
            min_edition=Edition.ADMIN,
            scope="admin",
            mutates=False,
            annotations=ToolAnnotations(readOnlyHint=True),
        ),
        _admin("start_workflow"),
        _admin("guided_schema_migration", targets=("target_registry",), destructive=True),
        _admin("guided_context_reorganization", targets=("target_registry",), destructive=True),
        _admin("guided_disaster_recovery", targets=("target_registry",), destructive=True),
    ]
)

# Transitional admin-only elicitation fallback (removed once the remaining
# guided workflows move to MRTR in M3).
for _name in (
    "submit_elicitation_response",
    "list_elicitation_requests",
    "get_elicitation_request",
    "get_elicitation_status",
    "cancel_elicitation_request",
):
    _SPECS.append(
        ToolSpec(
            name=_name,
            min_edition=Edition.ADMIN,
            scope="admin",
            mutates=False,
            annotations=ToolAnnotations(readOnlyHint=True),
        )
    )

TOOL_CATALOG: dict[str, ToolSpec] = {spec.name: spec for spec in _SPECS}

# Current decorator names that differ from the 3.0 public name.
REGISTERED_NAME_ALIASES = {
    "get_mcp_compliance_status_tool": "get_mcp_compliance_status",
    "get_oauth_scopes_info_tool": "get_oauth_scopes_info",
}

# Tools that must never be registered in 3.0.
REMOVED_TOOLS = {
    "set_default_registry",
    "workflow_status",
    "get_workflow_status",
    "list_available_workflows",
    "abort_workflow",
}

PROMPT_CATALOG: dict[str, PromptSpec] = {
    "schema-getting-started": PromptSpec("schema-getting-started", Edition.VIEWER),
    "schema-compatibility": PromptSpec("schema-compatibility", Edition.VIEWER),
    "schema-export": PromptSpec("schema-export", Edition.VIEWER),
    "troubleshooting": PromptSpec("troubleshooting", Edition.VIEWER),
    "quick-reference": PromptSpec("quick-reference", Edition.VIEWER),
    "schema-registration": PromptSpec("schema-registration", Edition.EDITOR),
    "schema-evolution": PromptSpec("schema-evolution", Edition.EDITOR),
    "context-management": PromptSpec("context-management", Edition.ADMIN),
    "multi-registry": PromptSpec("multi-registry", Edition.ADMIN),
    "advanced-workflows": PromptSpec("advanced-workflows", Edition.ADMIN),
}


def catalog_name(function_name: str) -> str:
    return REGISTERED_NAME_ALIASES.get(function_name, function_name)


def spec_for(function_name: str) -> ToolSpec | None:
    return TOOL_CATALOG.get(catalog_name(function_name))


def tools_for(edition: Edition) -> list[ToolSpec]:
    return [spec for spec in TOOL_CATALOG.values() if spec.min_edition <= edition]


def prompts_for(edition: Edition) -> list[PromptSpec]:
    return [spec for spec in PROMPT_CATALOG.values() if spec.min_edition <= edition]
