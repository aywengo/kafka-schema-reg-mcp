"""Rule tests for the disaster-recovery planner."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dr_planning import RPO_OPTIONS, RTO_OPTIONS, SCENARIO_OPTIONS, build_dr_plan  # noqa: E402


def _plan(**kwargs):
    base = {"registry": "prod", "backup_target": "s3://bucket/sr", "schedule": None, "verify_restore": True}
    base.update(kwargs)
    return build_dr_plan(**base)


def test_plan_without_objectives_keeps_the_v3_1_shape() -> None:
    plan = _plan()
    assert plan["status"] == "plan"
    assert plan["workflow_id"] == "disaster_recovery_setup"
    assert plan["schedule"] == "daily"
    assert any("restore_bundle" in step for step in plan["steps"])
    assert "restore_bundle" in plan["note"]
    assert plan["objectives"] == {"rpo": None, "rto": None, "scenarios": []}
    assert plan["strategy"]["recovery"] == "restore_to_prepared_registry"
    assert plan["warnings"] == []


@pytest.mark.parametrize(
    ("rpo", "schedule"),
    [("under-1-hour", "hourly"), ("under-24-hours", "daily"), ("weekly", "weekly")],
)
def test_rpo_picks_the_backup_cadence(rpo: str, schedule: str) -> None:
    plan = _plan(rpo=rpo)
    assert plan["schedule"] == schedule
    assert plan["strategy"]["backup_cadence"] == schedule
    assert plan["strategy"]["standby_required"] is False


@pytest.mark.parametrize("rto", [None, "under-1-hour", "under-24-hours"])
def test_real_time_rpo_recovers_from_the_standby(rto) -> None:
    plan = _plan(rpo="real-time", rto=rto)
    assert plan["strategy"]["standby_required"] is True
    assert plan["strategy"]["recovery"] == "warm_standby"
    assert any("real-time RPO" in warning for warning in plan["warnings"])
    assert "compare_registries" in plan["runbook"]
    assert "Fallback only" in plan["runbook"]


def test_corruption_is_found_with_read_only_queries() -> None:
    runbook = _plan(scenarios=["corruption"])["runbook"]
    section = runbook[runbook.index("## Scenario: Corruption") :]
    assert "export_subject or export_context" in section
    assert "conflicts list" not in section


def test_verification_applies_to_a_scratch_registry() -> None:
    runbook = _plan()["runbook"]
    section = runbook[runbook.index("## Verification") :]
    assert "apply=true into an isolated scratch registry" in section
    assert "compare_registries" in section


@pytest.mark.parametrize(
    ("rto", "recovery"),
    [
        ("under-5-minutes", "warm_standby"),
        ("under-1-hour", "restore_to_prepared_registry"),
        ("under-4-hours", "restore_to_prepared_registry"),
        ("under-24-hours", "restore_to_new_registry"),
    ],
)
def test_rto_picks_the_recovery_path(rto: str, recovery: str) -> None:
    plan = _plan(rto=rto)
    assert plan["strategy"]["recovery"] == recovery
    assert plan["strategy"]["standby_required"] is (recovery == "warm_standby")


def test_explicit_schedule_slower_than_rpo_warns() -> None:
    plan = _plan(rpo="under-1-hour", schedule="weekly")
    assert plan["schedule"] == "weekly"
    assert any("slower than RPO under-1-hour" in warning for warning in plan["warnings"])


def test_explicit_schedule_that_meets_rpo_does_not_warn() -> None:
    assert _plan(rpo="under-24-hours", schedule="hourly")["warnings"] == []


def test_unrecognised_schedule_is_reported_as_unchecked() -> None:
    plan = _plan(rpo="under-1-hour", schedule="0 */2 * * *")
    assert any("could not be checked" in warning for warning in plan["warnings"])


def test_verification_off_warns_and_runbook_says_so() -> None:
    plan = _plan(verify_restore=False)
    assert any("verification is off" in warning for warning in plan["warnings"])
    assert "Schedule a restore drill" in plan["runbook"]


def test_each_scenario_adds_a_runbook_section() -> None:
    plan = _plan(scenarios=list(SCENARIO_OPTIONS))
    for title in ("Data center failure", "Region outage", "Corruption", "Accidental deletion"):
        assert f"## Scenario: {title}" in plan["runbook"]
    assert "narrowed with context and subject" in plan["runbook"]
    assert "apply=false" in plan["runbook"]


def test_scenarios_are_deduplicated_in_order() -> None:
    plan = _plan(scenarios=["corruption", "region-outage", "corruption"])
    assert plan["objectives"]["scenarios"] == ["corruption", "region-outage"]


def test_runbook_can_be_omitted() -> None:
    assert _plan(include_runbook=False)["runbook"] is None


def test_runbook_never_calls_a_tool() -> None:
    plan = _plan(rpo="under-1-hour", rto="under-1-hour", scenarios=list(SCENARIO_OPTIONS))
    assert "restore_bundle(" not in plan["runbook"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("rpo", "instant"), ("rto", "never"), ("scenarios", ["meteor"])],
)
def test_unknown_options_are_rejected(field: str, value) -> None:
    with pytest.raises(ValueError):
        _plan(**{field: value})


async def _call(arguments: dict):
    import json

    from fastmcp import Client, FastMCP

    from elicitation import ElicitationManager
    from workflow_mcp_integration import WorkflowMCPTools

    mcp = FastMCP("dr-plan")
    WorkflowMCPTools(mcp, ElicitationManager())
    async with Client(mcp) as client:
        result = await client.call_tool("guided_disaster_recovery", arguments)
    raw = result.data if result.data is not None else result.content[0].text
    return json.loads(raw) if isinstance(raw, str) else raw


async def test_tool_returns_objectives_strategy_and_runbook() -> None:
    plan = await _call(
        {
            "backup_target": "s3://bucket/sr",
            "rpo": "under-1-hour",
            "rto": "under-5-minutes",
            "scenarios": ["region-outage", "accidental-deletion"],
        }
    )
    assert plan["schedule"] == "hourly"
    assert plan["strategy"]["recovery"] == "warm_standby"
    assert plan["objectives"]["scenarios"] == ["region-outage", "accidental-deletion"]
    assert "## Scenario: Region outage" in plan["runbook"]


async def test_tool_without_objectives_matches_the_previous_plan() -> None:
    plan = await _call({"backup_target": "memory://backup", "schedule": "daily"})
    assert plan["schedule"] == "daily"
    assert plan["warnings"] == []
    assert plan["strategy"]["recovery"] == "restore_to_prepared_registry"


async def test_tool_reports_unknown_option_as_error() -> None:
    plan = await _call({"backup_target": "memory://backup", "rpo": "instant"})
    assert "rpo must be one of" in plan["error"]


async def test_tool_can_omit_the_runbook() -> None:
    plan = await _call({"backup_target": "memory://backup", "include_runbook": False})
    assert plan["runbook"] is None


async def test_form_asks_for_objectives_and_uses_the_answers() -> None:
    import json

    from fastmcp import Client, FastMCP

    from elicitation import ElicitationManager
    from workflow_mcp_integration import WorkflowMCPTools

    seen = {}

    async def handler(message, response_type, params, context):
        seen["properties"] = params.requested_schema["properties"]
        return {
            "backup_target": "s3://bucket/sr",
            "rpo": "weekly",
            "rto": "under-24-hours",
            "primary_scenario": "corruption",
        }

    mcp = FastMCP("dr-plan-form")
    WorkflowMCPTools(mcp, ElicitationManager())
    async with Client(mcp, elicitation_handler=handler) as client:
        result = await client.call_tool("guided_disaster_recovery", {})
    raw = result.data if result.data is not None else result.content[0].text
    plan = json.loads(raw) if isinstance(raw, str) else raw

    assert {"rpo", "rto", "primary_scenario"} <= set(seen["properties"])
    assert plan["schedule"] == "weekly"
    assert plan["strategy"]["recovery"] == "restore_to_new_registry"
    assert plan["objectives"]["scenarios"] == ["corruption"]


def test_option_lists_match_the_issue() -> None:
    assert len(RPO_OPTIONS) == 4
    assert len(RTO_OPTIONS) == 4
    assert len(SCENARIO_OPTIONS) == 4
