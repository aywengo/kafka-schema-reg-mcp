"""Disaster-recovery plan rules for ``guided_disaster_recovery``.

``build_dr_plan`` turns recovery objectives into a plan and a Markdown runbook.
It names tools for the operator to run and calls none of them.
"""

from __future__ import annotations

from typing import Any, Iterable

RPO_OPTIONS = ("real-time", "under-1-hour", "under-24-hours", "weekly")
RTO_OPTIONS = ("under-5-minutes", "under-1-hour", "under-4-hours", "under-24-hours")
SCENARIO_OPTIONS = ("datacenter-failure", "region-outage", "corruption", "accidental-deletion")

DEFAULT_SCHEDULE = "daily"

# Export cadence that meets each RPO. None means exports cannot meet it.
_RPO_CADENCE: dict[str, str | None] = {
    "real-time": None,
    "under-1-hour": "hourly",
    "under-24-hours": "daily",
    "weekly": "weekly",
}

_SCHEDULE_RANK = {"hourly": 1, "daily": 2, "weekly": 3}

_RTO_RECOVERY: dict[str, str] = {
    "under-5-minutes": "warm_standby",
    "under-1-hour": "restore_to_prepared_registry",
    "under-4-hours": "restore_to_prepared_registry",
    "under-24-hours": "restore_to_new_registry",
}

_RECOVERY_TEXT = {
    "warm_standby": (
        "Fail clients over to a warm standby registry kept in sync outside this server. "
        "Check drift with compare_registries and find_missing_schemas before switching."
    ),
    "restore_to_prepared_registry": (
        "Keep an empty registry provisioned. Apply the latest backup to it with restore_bundle, "
        "dry run first, then apply=true."
    ),
    "restore_to_new_registry": (
        "Provision a registry at recovery time and apply the latest backup to it with "
        "restore_bundle, dry run first, then apply=true."
    ),
}

_SCENARIO_RUNBOOK: dict[str, tuple[str, list[str]]] = {
    "datacenter-failure": (
        "Data center failure",
        [
            "Confirm the primary registry is unreachable with test_registry_connection.",
            "Recover into a registry outside the failed data center using the recovery path above.",
            "Repoint producers and consumers at the recovered registry.",
        ],
    ),
    "region-outage": (
        "Region outage",
        [
            "Keep the backup target and the recovery registry in a different region from the primary.",
            "Recover in the surviving region using the recovery path above.",
            "After the region returns, compare_registries before moving traffic back.",
        ],
    ),
    "corruption": (
        "Corruption",
        [
            "Stop writes to the affected registry with update_mode READONLY.",
            "Find the damage with read-only queries: export_subject or export_context from the affected "
            "registry, and compare each version's schema id and body with the backup document.",
            "Recover the affected subjects into a clean registry with restore_bundle, preview with "
            "apply=false, then apply=true. Restore never overwrites an existing id with a different body.",
        ],
    ),
    "accidental-deletion": (
        "Accidental deletion",
        [
            "Find what is missing with find_missing_schemas against a standby, or by reading the backup.",
            "Run restore_bundle narrowed with context and subject, apply=false first.",
            "Apply it; versions already present are skipped and schema ids are preserved.",
        ],
    ),
}


def _check(value: str | None, options: tuple[str, ...], name: str) -> None:
    if value is not None and value not in options:
        raise ValueError(f"{name} must be one of {', '.join(options)}; got '{value}'")


def _normalise_scenarios(scenarios: Iterable[str] | None) -> list[str]:
    seen: list[str] = []
    for scenario in scenarios or []:
        _check(scenario, SCENARIO_OPTIONS, "scenario")
        if scenario not in seen:
            seen.append(scenario)
    return seen


def _warnings(
    *,
    rpo: str | None,
    schedule: str,
    explicit_schedule: bool,
    verify_restore: bool,
) -> list[str]:
    warnings: list[str] = []
    cadence = _RPO_CADENCE.get(rpo) if rpo else None
    if rpo == "real-time":
        warnings.append(
            "A real-time RPO cannot be met by scheduled exports. Run a standby registry replicated "
            "outside this server; exports remain the fallback."
        )
    elif cadence and explicit_schedule:
        rank = _SCHEDULE_RANK.get(schedule.strip().lower())
        if rank is None:
            warnings.append(f"Schedule '{schedule}' could not be checked against RPO {rpo}; use {cadence} or faster.")
        elif rank > _SCHEDULE_RANK[cadence]:
            warnings.append(f"Schedule '{schedule}' is slower than RPO {rpo} allows; use {cadence} or faster.")
    if not verify_restore:
        warnings.append("Restore verification is off. An untested backup may not meet the RTO.")
    return warnings


def _runbook(
    *,
    registry: str | None,
    backup_target: str,
    schedule: str,
    rpo: str | None,
    rto: str | None,
    recovery: str,
    standby_required: bool,
    scenarios: list[str],
    verify_restore: bool,
) -> str:
    lines = [
        f"# Disaster recovery runbook: {registry or 'default registry'}",
        "",
        "## Objectives",
        "",
        f"- RPO: {rpo or 'not set'}",
        f"- RTO: {rto or 'not set'}",
        "",
        "## Backup",
        "",
        f"- Export with export_global on a {schedule} schedule and store the document at {backup_target}.",
        "- Keep at least one copy outside the primary registry's failure domain.",
    ]
    if standby_required:
        lines.append(
            "- Run a standby registry replicated outside this server; check it with compare_registries "
            "and find_missing_schemas."
        )
    lines += ["", "## Recovery", "", f"- {_RECOVERY_TEXT[recovery]}"]
    if rpo == "real-time":
        lines.append(
            "- Fallback only: if the standby is lost, restore the latest export with restore_bundle. "
            "That loses changes made since the export and does not meet the real-time RPO."
        )
    for scenario in scenarios:
        title, steps = _SCENARIO_RUNBOOK[scenario]
        lines += ["", f"## Scenario: {title}", ""]
        lines += [f"{index}. {step}" for index, step in enumerate(steps, start=1)]
    lines += ["", "## Verification", ""]
    if verify_restore:
        lines += [
            "- After each backup, run restore_bundle with apply=true into an isolated scratch registry. "
            "A preview with apply=false only checks the document; it does not contact the registry.",
            "- Check the report status is applied with no conflicts, then compare_registries between the "
            "source and the scratch registry to confirm every subject and version arrived.",
            "- Clear the scratch registry before the next drill.",
        ]
    else:
        lines.append("- Verification is off. Schedule a restore drill before relying on this plan.")
    return "\n".join(lines) + "\n"


def build_dr_plan(
    *,
    registry: str | None,
    backup_target: str,
    schedule: str | None,
    verify_restore: bool,
    rpo: str | None = None,
    rto: str | None = None,
    scenarios: list[str] | None = None,
    include_runbook: bool = True,
) -> dict[str, Any]:
    """Build a disaster-recovery plan from the operator's objectives.

    Args:
        registry: Registry the plan covers, or None for the default registry.
        backup_target: URI or bucket that receives export documents.
        schedule: Backup schedule. When None it follows the RPO, else ``daily``.
        verify_restore: Whether the plan includes a dry-run restore check.
        rpo: One of ``RPO_OPTIONS``.
        rto: One of ``RTO_OPTIONS``.
        scenarios: Any of ``SCENARIO_OPTIONS``; each adds a runbook section.
        include_runbook: Whether to return the Markdown runbook.

    Returns:
        The plan dictionary returned by ``guided_disaster_recovery``.

    Raises:
        ValueError: If an objective or scenario is not a known option.
    """
    _check(rpo, RPO_OPTIONS, "rpo")
    _check(rto, RTO_OPTIONS, "rto")
    chosen = _normalise_scenarios(scenarios)

    explicit_schedule = bool(schedule)
    effective_schedule = schedule or (_RPO_CADENCE.get(rpo) if rpo else None) or DEFAULT_SCHEDULE
    # Recovering from an export loses changes made since it, so a real-time RPO recovers from the standby.
    if rpo == "real-time":
        recovery = "warm_standby"
    else:
        recovery = _RTO_RECOVERY[rto] if rto else "restore_to_prepared_registry"
    standby_required = recovery == "warm_standby"

    plan: dict[str, Any] = {
        "status": "plan",
        "workflow_id": "disaster_recovery_setup",
        "registry": registry,
        "backup_target": backup_target,
        "schedule": effective_schedule,
        "verify_restore": verify_restore,
        "steps": [
            "Inventory registries, contexts and subjects.",
            "Export a full backup to the chosen target.",
            "Schedule recurring backups and retention.",
            "Verify with restore_bundle against a scratch registry.",
        ],
        "note": "This plan does not call restore_bundle. migrate_schema remains the live-to-live copy.",
        "objectives": {"rpo": rpo, "rto": rto, "scenarios": chosen},
        "strategy": {
            "backup_cadence": effective_schedule,
            "recovery": recovery,
            "standby_required": standby_required,
        },
        "warnings": _warnings(
            rpo=rpo,
            schedule=effective_schedule,
            explicit_schedule=explicit_schedule,
            verify_restore=verify_restore,
        ),
        "runbook": None,
    }
    if include_runbook:
        plan["runbook"] = _runbook(
            registry=registry,
            backup_target=backup_target,
            schedule=effective_schedule,
            rpo=rpo,
            rto=rto,
            recovery=recovery,
            standby_required=standby_required,
            scenarios=chosen,
            verify_restore=verify_restore,
        )
    return plan
