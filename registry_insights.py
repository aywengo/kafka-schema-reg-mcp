"""Point-in-time insights about a registry's current state.

``get_registry_insights`` reads subjects, versions, latest schemas and
compatibility settings and reports distributions plus rule-based findings.
The registry API carries no usage, consumer or history data, so none of that
is reported here; ``limitations`` says so on every result.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from fastmcp.dependencies import Progress

from protocol_version import current_protocol_version
from schema_registry_common import get_default_client
from schema_validation import create_error_response, structured_output

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_LABEL = "default"
VERSION_BUCKETS = (("1", 1, 1), ("2-5", 2, 5), ("6-20", 6, 20), ("21+", 21, None))
SCHEMA_TYPES = ("AVRO", "JSON", "PROTOBUF")
_SUBJECT_WORKERS = 8

LIMITATIONS = [
    "Usage frequency, consumer counts and consumer dependencies are not exposed by the Schema Registry API.",
    "This is a point-in-time snapshot. For trends, scrape the remote server's /metrics endpoint "
    "and use docs/grafana-dashboard-mcp-metrics.json.",
    "A subject nothing references may still be read by producers and consumers; it is not proven unused.",
]


@dataclass
class SubjectRecord:
    """What the registry reports about one subject."""

    context: Optional[str]
    subject: str
    versions: Optional[int] = None
    schema_type: Optional[str] = None
    override: Optional[str] = None
    references: list[tuple[Optional[str], str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ContextRecord:
    """One context's subjects and its compatibility level."""

    context: Optional[str]
    level: Optional[str]
    subjects: list[SubjectRecord]
    error: Optional[str] = None


def _label(context: Optional[str]) -> str:
    return context if context else DEFAULT_CONTEXT_LABEL


def _normalise_context(context: Optional[str]) -> Optional[str]:
    if context in (None, "", ".", DEFAULT_CONTEXT_LABEL):
        return None
    return context


def _key(context: Optional[str]) -> Optional[str]:
    """Compare contexts with or without the leading dot the registry may list."""
    normalised = _normalise_context(context)
    return normalised.lstrip(".") if normalised else None


def _split_qualified(subject: str, context: Optional[str]) -> tuple[Optional[str], str]:
    """Resolve ``:.ctx:name`` to ``(ctx, name)``; a plain name stays in ``context``."""
    if subject.startswith(":."):
        qualified, _, name = subject[2:].partition(":")
        return _normalise_context(qualified), name
    return context, subject


def _level(config: Any) -> Optional[str]:
    if isinstance(config, dict) and "error" not in config:
        return config.get("compatibilityLevel") or config.get("compatibility")
    return None


def _inspect_subject(client: Any, context: Optional[str], subject: str) -> SubjectRecord:
    record = SubjectRecord(context=context, subject=subject)
    try:
        versions = client.get_schema_versions(subject, context)
        if isinstance(versions, list):
            record.versions = len(versions)
        else:
            record.errors.append(f"versions: {versions.get('error', versions)}")

        latest = client.get_schema(subject, "latest", context)
        if isinstance(latest, dict) and "error" not in latest:
            record.schema_type = (latest.get("schemaType") or "AVRO").upper()
            for reference in latest.get("references") or []:
                target = reference.get("subject")
                if target:
                    record.references.append(_split_qualified(target, context))
        else:
            record.errors.append(f"latest: {latest.get('error', latest)}")

        # A subject without an override answers with an error; it inherits the context level.
        record.override = _level(client.get_subject_config(subject, context))
    except Exception as e:
        record.errors.append(str(e))
    return record


def collect_context(client: Any, context: Optional[str], skip_qualified: bool = False) -> ContextRecord:
    """Read one context: its compatibility level and every subject in it."""
    try:
        level = _level(client.get_global_config(context))
        subjects = client.get_subjects(context)
        if not isinstance(subjects, list):
            return ContextRecord(context, level, [], error=str(subjects))
        if skip_qualified:
            subjects = [s for s in subjects if not s.startswith(":.")]
        with ThreadPoolExecutor(max_workers=_SUBJECT_WORKERS) as executor:
            records = list(executor.map(lambda s: _inspect_subject(client, context, s), subjects))
        return ContextRecord(context, level, records)
    except Exception as e:
        return ContextRecord(context, None, [], error=str(e))


def _finding(code: str, severity: str, context: Optional[str], subject: Optional[str], message: str) -> dict:
    return {"code": code, "severity": severity, "context": _label(context), "subject": subject, "message": message}


def summarise(
    contexts: Iterable[ContextRecord],
    *,
    top_n: int = 10,
    version_sprawl_threshold: int = 20,
) -> dict[str, Any]:
    """Turn collected context records into the insights report sections."""
    contexts = list(contexts)
    records = [record for ctx in contexts for record in ctx.subjects]
    known = {(_key(record.context), record.subject): (record.context, record.subject) for record in records}
    levels = {ctx.context: ctx.level for ctx in contexts}
    findings: list[dict] = []
    errors: list[dict] = []

    buckets = {name: 0 for name, _, _ in VERSION_BUCKETS}
    for record in records:
        if record.versions is None:
            continue
        for name, low, high in VERSION_BUCKETS:
            if record.versions >= low and (high is None or record.versions <= high):
                buckets[name] += 1
                break
        if record.versions > version_sprawl_threshold:
            findings.append(
                _finding(
                    "VERSION_SPRAWL",
                    "info",
                    record.context,
                    record.subject,
                    f"{record.versions} versions, above the threshold of {version_sprawl_threshold}.",
                )
            )
    versioned = [r for r in records if r.versions is not None]
    top = sorted(versioned, key=lambda r: (-(r.versions or 0), _label(r.context), r.subject))[:top_n]

    types = Counter({name: 0 for name in SCHEMA_TYPES})
    types.update(record.schema_type for record in records if record.schema_type)

    by_level: Counter = Counter()
    overrides = []
    for record in records:
        context_level = levels.get(record.context)
        effective = record.override or context_level
        by_level[effective or "UNKNOWN"] += 1
        if record.override and record.override != context_level:
            overrides.append({"context": _label(record.context), "subject": record.subject, "level": record.override})
        if effective and effective.upper() == "NONE":
            findings.append(
                _finding(
                    "COMPATIBILITY_NONE",
                    "warning",
                    record.context,
                    record.subject,
                    "Compatibility is NONE; any change can break consumers.",
                )
            )

    referenced_by: Counter = Counter()
    dangling = []
    for record in records:
        for target in record.references:
            found = known.get((_key(target[0]), target[1]))
            if found:
                referenced_by[found] += 1
                continue
            dangling.append(
                {
                    "context": _label(record.context),
                    "subject": record.subject,
                    "missing_context": _label(target[0]),
                    "missing_subject": target[1],
                }
            )
            findings.append(
                _finding(
                    "DANGLING_REFERENCE",
                    "error",
                    record.context,
                    record.subject,
                    f"References '{target[1]}' in context '{_label(target[0])}', which does not exist.",
                )
            )
    most_referenced = [
        {"context": _label(ctx), "subject": subject, "referenced_by": count}
        for (ctx, subject), count in sorted(referenced_by.items(), key=lambda item: (-item[1], _label(item[0][0])))
    ][:top_n]

    for ctx in contexts:
        if ctx.error:
            errors.append({"context": _label(ctx.context), "subject": None, "error": ctx.error})
        elif ctx.context is not None and not ctx.subjects:
            findings.append(_finding("EMPTY_CONTEXT", "info", ctx.context, None, "Context has no subjects."))
    for record in records:
        for message in record.errors:
            errors.append({"context": _label(record.context), "subject": record.subject, "error": message})

    return {
        "contexts_analyzed": [_label(ctx.context) for ctx in contexts],
        "total_subjects": len(records),
        "version_distribution": {
            "buckets": buckets,
            "top_subjects": [{"context": _label(r.context), "subject": r.subject, "versions": r.versions} for r in top],
        },
        "schema_types": dict(types),
        "compatibility": {
            "global_level": levels.get(None),
            "context_levels": {_label(ctx.context): ctx.level for ctx in contexts},
            "by_effective_level": dict(by_level),
            "overrides": overrides,
        },
        "references": {"most_referenced": most_referenced, "dangling": dangling},
        "findings": findings,
        "errors": errors,
        "limitations": LIMITATIONS,
    }


def _contexts_to_scan(client: Any, context: Optional[str]) -> list[Optional[str]]:
    if context is not None:
        return [_normalise_context(context)]
    listed = client.get_contexts()
    names: list[Optional[str]] = [None]
    if isinstance(listed, list):
        for name in listed:
            normalised = _normalise_context(name)
            if normalised not in names:
                names.append(normalised)
    return names


@structured_output("get_registry_insights", fallback_on_error=True)
async def get_registry_insights_tool(
    registry_manager: Any,
    registry_mode: str,
    registry: Optional[str] = None,
    context: Optional[str] = None,
    top_n: int = 10,
    version_sprawl_threshold: int = 20,
    progress: Progress = Progress(),
) -> dict[str, Any]:
    """Report version spread, schema types, compatibility and reference health for a registry.

    Args:
        registry_manager: Registry manager that resolves ``registry``.
        registry_mode: ``single`` or ``multi``.
        registry: Registry name (ignored in single-registry mode).
        context: Limit the report to one context; all contexts when omitted.
        top_n: Length of the top-subject and most-referenced lists.
        version_sprawl_threshold: Version count above which a subject is flagged.
        progress: FastMCP progress dependency.

    Returns:
        The insights report, or an error response.
    """
    if top_n < 1 or version_sprawl_threshold < 1:
        return create_error_response(
            "top_n and version_sprawl_threshold must be at least 1",
            error_code="INVALID_ARGUMENT",
            registry_mode=registry_mode,
        )
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
        if client is None:
            return create_error_response(
                f"Registry '{registry}' not found", error_code="REGISTRY_NOT_FOUND", registry_mode=registry_mode
            )

        await progress.set_message("Listing contexts")
        names = await asyncio.to_thread(_contexts_to_scan, client, context)
        await progress.set_total(len(names))
        skip_qualified = context is None and len(names) > 1

        collected = []
        for name in names:
            await progress.set_message(f"Analyzing context {_label(name)}")
            collected.append(await asyncio.to_thread(collect_context, client, name, skip_qualified and name is None))
            await progress.increment()

        report = summarise(collected, top_n=top_n, version_sprawl_threshold=version_sprawl_threshold)
        report.update(
            {
                "registry": getattr(client.config, "name", "default"),
                "scope": _label(_normalise_context(context)) if context is not None else "all",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "registry_mode": registry_mode,
                "mcp_protocol_version": current_protocol_version(),
            }
        )
        await progress.set_message("Insights complete")
        return report
    except Exception as e:
        logger.error(f"Registry insights failed: {e}")
        return create_error_response(str(e), error_code="REGISTRY_INSIGHTS_FAILED", registry_mode=registry_mode)
