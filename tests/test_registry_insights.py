"""Tests for get_registry_insights against an in-memory registry client."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry_insights import LIMITATIONS, get_registry_insights_tool  # noqa: E402


class FakeClient:
    """Answers like RegistryClient: lists on success, ``{"error": ...}`` dicts on failure."""

    def __init__(self, contexts, subjects, global_levels, overrides=None, failing=()):
        self.config = Mock()
        self.config.name = "test-registry"
        self._contexts = contexts
        self._subjects = subjects
        self._global = global_levels
        self._overrides = overrides or {}
        self._failing = set(failing)

    def get_contexts(self):
        return list(self._contexts)

    def get_subjects(self, context=None):
        return list(self._subjects.get(context, {}))

    def get_global_config(self, context=None):
        return {"compatibilityLevel": self._global.get(context, "BACKWARD")}

    def get_schema_versions(self, subject, context=None):
        if (context, subject) in self._failing:
            return {"error": "500 Server Error"}
        return list(range(1, self._subjects[context][subject]["versions"] + 1))

    def get_schema(self, subject, version="latest", context=None):
        entry = self._subjects[context][subject]
        result = {"subject": subject, "version": entry["versions"], "schema": "{}"}
        if entry.get("type"):
            result["schemaType"] = entry["type"]
        if entry.get("refs"):
            result["references"] = [{"name": ref, "subject": ref, "version": 1} for ref in entry["refs"]]
        return result

    def get_subject_config(self, subject, context=None):
        level = self._overrides.get((context, subject))
        if level is None:
            return {"error": "404 Client Error: Subject not found"}
        return {"compatibilityLevel": level}


def _client(**overrides):
    subjects = {
        None: {
            "orders-value": {"versions": 1, "refs": ["customer"]},
            "customer": {"versions": 3},
            "payments-value": {"versions": 25, "type": "PROTOBUF", "refs": ["money", ":.billing:invoice"]},
            ":.billing:invoice": {"versions": 1},
        },
        ".billing": {
            "invoice": {"versions": 7, "type": "JSON"},
        },
        ".archive": {},
    }
    kwargs = {
        "contexts": [".", ".billing", ".archive"],
        "subjects": subjects,
        "global_levels": {None: "BACKWARD", ".billing": "FULL", ".archive": "BACKWARD"},
        "overrides": {(None, "customer"): "NONE"},
    }
    kwargs.update(overrides)
    return FakeClient(**kwargs)


def _manager(client):
    manager = Mock()
    manager.get_registry.return_value = client
    return manager


def _progress():
    progress = Mock()
    progress.set_message = AsyncMock()
    progress.set_total = AsyncMock()
    progress.increment = AsyncMock()
    return progress


async def _insights(client=None, **kwargs):
    return await get_registry_insights_tool(
        _manager(client or _client()), "multi", registry="test-registry", progress=_progress(), **kwargs
    )


def _codes(report, code):
    return [finding for finding in report["findings"] if finding["code"] == code]


async def test_contexts_and_subjects_are_counted_once() -> None:
    report = await _insights()
    assert report["contexts_analyzed"] == ["default", ".billing", ".archive"]
    # The qualified ":.billing:invoice" listed in the default context is counted under .billing only.
    assert report["total_subjects"] == 4
    assert report["scope"] == "all"
    assert report["limitations"] == LIMITATIONS


async def test_version_buckets_and_top_subjects() -> None:
    report = await _insights(top_n=2)
    assert report["version_distribution"]["buckets"] == {"1": 1, "2-5": 1, "6-20": 1, "21+": 1}
    top = report["version_distribution"]["top_subjects"]
    assert [entry["subject"] for entry in top] == ["payments-value", "invoice"]


async def test_schema_type_mix_defaults_to_avro() -> None:
    report = await _insights()
    assert report["schema_types"] == {"AVRO": 2, "JSON": 1, "PROTOBUF": 1}


async def test_overrides_and_effective_levels() -> None:
    report = await _insights()
    compatibility = report["compatibility"]
    assert compatibility["global_level"] == "BACKWARD"
    assert compatibility["context_levels"][".billing"] == "FULL"
    assert compatibility["overrides"] == [{"context": "default", "subject": "customer", "level": "NONE"}]
    assert compatibility["by_effective_level"] == {"BACKWARD": 2, "NONE": 1, "FULL": 1}
    assert [f["subject"] for f in _codes(report, "COMPATIBILITY_NONE")] == ["customer"]


async def test_references_resolve_across_contexts_and_report_dangling() -> None:
    report = await _insights()
    most = {
        (entry["context"], entry["subject"]): entry["referenced_by"]
        for entry in report["references"]["most_referenced"]
    }
    assert most == {("default", "customer"): 1, (".billing", "invoice"): 1}
    assert report["references"]["dangling"] == [
        {"context": "default", "subject": "payments-value", "missing_context": "default", "missing_subject": "money"}
    ]
    assert len(_codes(report, "DANGLING_REFERENCE")) == 1


async def test_version_sprawl_uses_the_threshold() -> None:
    assert [f["subject"] for f in _codes(await _insights(), "VERSION_SPRAWL")] == ["payments-value"]
    assert {f["subject"] for f in _codes(await _insights(version_sprawl_threshold=5), "VERSION_SPRAWL")} == {
        "payments-value",
        "invoice",
    }


async def test_empty_named_context_is_a_finding() -> None:
    assert [f["context"] for f in _codes(await _insights(), "EMPTY_CONTEXT")] == [".archive"]


async def test_one_failing_subject_does_not_fail_the_report() -> None:
    report = await _insights(_client(failing={(None, "customer")}))
    assert report["total_subjects"] == 4
    assert report["errors"] == [{"context": "default", "subject": "customer", "error": "versions: 500 Server Error"}]
    assert sum(report["version_distribution"]["buckets"].values()) == 3


async def test_context_argument_limits_the_scope() -> None:
    report = await _insights(context=".billing")
    assert report["scope"] == ".billing"
    assert report["contexts_analyzed"] == [".billing"]
    assert report["total_subjects"] == 1


async def test_override_equal_to_the_context_level_is_still_listed() -> None:
    client = _client(overrides={(None, "customer"): "NONE", (".billing", "invoice"): "FULL"})
    overrides = (await _insights(client))["compatibility"]["overrides"]
    assert {"context": ".billing", "subject": "invoice", "level": "FULL"} in overrides


async def test_failed_subject_config_is_unknown_not_inherited() -> None:
    client = _client()
    original = client.get_subject_config

    def failing(subject, context=None):
        if subject == "customer":
            return {"error": "403 Client Error: Forbidden"}
        return original(subject, context)

    client.get_subject_config = failing
    report = await _insights(client)
    assert report["compatibility"]["by_effective_level"]["UNKNOWN"] == 1
    assert {"context": "default", "subject": "customer", "error": "config: 403 Client Error: Forbidden"} in report[
        "errors"
    ]
    assert _codes(report, "COMPATIBILITY_NONE") == []


async def test_failed_context_config_is_reported_and_collection_continues() -> None:
    client = _client()
    client.get_global_config = lambda context=None: (
        {"error": "500 Server Error"} if context == ".billing" else {"compatibilityLevel": "BACKWARD"}
    )
    report = await _insights(client)
    assert report["total_subjects"] == 4
    assert {"context": ".billing", "subject": None, "error": "config: 500 Server Error"} in report["errors"]


async def test_qualified_names_in_a_named_context_resolve_references() -> None:
    subjects = {
        None: {"orders-value": {"versions": 1, "refs": [":.billing:invoice"]}},
        ".billing": {":.billing:invoice": {"versions": 2}},
    }
    client = FakeClient([".", ".billing"], subjects, {None: "BACKWARD", ".billing": "BACKWARD"})
    report = await _insights(client)
    assert report["references"]["dangling"] == []
    assert report["references"]["most_referenced"] == [
        {"context": ".billing", "subject": ":.billing:invoice", "referenced_by": 1}
    ]


async def test_references_outside_the_scope_are_unverified_not_dangling() -> None:
    client = _client()
    del client._subjects[None][":.billing:invoice"]
    report = await _insights(client, context=".")
    assert report["references"]["unverified"] == [
        {"context": "default", "subject": "payments-value", "target_context": ".billing", "target_subject": "invoice"}
    ]
    assert [d["missing_subject"] for d in report["references"]["dangling"]] == ["money"]


class _Response:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Client Error")

    def json(self):
        return self._payload


class SessionClient(FakeClient):
    """Exposes the session the real RegistryClient lists with, failing for chosen URLs."""

    base = "http://registry"

    def __init__(self, *args, forbidden=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.headers = {}
        self.session = Mock()
        self.session.get = self._get
        self._forbidden = set(forbidden)

    def build_context_url(self, path, context=None):
        if context and context != ".":
            return f"{self.base}/contexts/{context}{path}"
        return f"{self.base}{path}"

    def _get(self, url, **kwargs):
        if url in self._forbidden:
            return _Response(403, {"error_code": 40301})
        if url == f"{self.base}/contexts":
            return _Response(200, self.get_contexts())
        prefix = f"{self.base}/contexts/"
        context = url[len(prefix) :].split("/")[0] if url.startswith(prefix) else None
        return _Response(200, self.get_subjects(context))


async def test_failed_subject_listing_is_an_error_not_an_empty_context() -> None:
    base = _client()
    client = SessionClient(
        base._contexts,
        base._subjects,
        base._global,
        base._overrides,
        forbidden={"http://registry/contexts/.billing/subjects"},
    )
    report = await _insights(client)
    assert {"context": ".billing", "subject": None, "error": "subjects: 403 Client Error"} in report["errors"]
    assert ".billing" not in [f["context"] for f in _codes(report, "EMPTY_CONTEXT")]
    assert {"default", ".archive"} >= {u["context"] for u in report["references"]["unverified"]}
    assert [u["target_subject"] for u in report["references"]["unverified"]] == ["invoice"]


async def test_failed_context_listing_is_reported() -> None:
    base = _client()
    client = SessionClient(
        base._contexts, base._subjects, base._global, base._overrides, forbidden={"http://registry/contexts"}
    )
    report = await _insights(client)
    assert report["errors"][0] == {"context": "all", "subject": None, "error": "contexts: 403 Client Error"}
    assert report["contexts_analyzed"] == ["default"]


async def test_report_validates_against_its_output_schema() -> None:
    report = await _insights()
    assert report["_validation"]["validated"] is True


def test_catalog_entry_is_viewer_read_task() -> None:
    from edition import Edition
    from tool_catalog import TOOL_CATALOG

    spec = TOOL_CATALOG["get_registry_insights"]
    assert spec.min_edition == Edition.VIEWER
    assert spec.scope == "read"
    assert spec.mutates is False
    assert spec.task is True


async def test_unknown_registry_is_an_error() -> None:
    manager = Mock()
    manager.get_registry.return_value = None
    report = await get_registry_insights_tool(manager, "multi", registry="nope", progress=_progress())
    assert report["error_code"] == "REGISTRY_NOT_FOUND"


@pytest.mark.parametrize("kwargs", [{"top_n": 0}, {"version_sprawl_threshold": 0}])
async def test_invalid_limits_are_rejected(kwargs) -> None:
    report = await _insights(**kwargs)
    assert report["error_code"] == "INVALID_ARGUMENT"
