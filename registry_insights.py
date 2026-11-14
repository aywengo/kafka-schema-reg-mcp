"""Point-in-time insights about a registry's current state.

``get_registry_insights`` reads subjects, versions, latest schemas and
compatibility settings and reports distributions plus rule-based findings.
The registry API carries no usage, consumer or history data, so none of that
is reported here; ``limitations`` says so on every result.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional

from fastmcp.dependencies import Progress

from protocol_version import current_protocol_version
from schema_registry_common import get_default_client
from schema_validation import create_error_response, structured_output

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_LABEL = "default"
VERSION_BUCKETS = (("1", 1, 1), ("2-5", 2, 5), ("6-20", 6, 20), ("21+", 21, None))
SCHEMA_TYPES = ("AVRO", "JSON", "PROTOBUF")
_SUBJECT_WORKERS = 8
LIST_TIMEOUT_SECONDS = 30
_NOT_FOUND = re.compile(r"^\s*404\b")

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
    override_unknown: bool = False
    references: list[tuple[Optional[str], str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ContextRecord:
    """One context's subjects and its compatibility level."""

    context: Optional[str]
    level: Optional[str]
    subjects: list[SubjectRecord]
    error: Optional[str] = None
    config_error: Optional[str] = None


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
        return _normalise_context(f".{qualified}" if qualified else None), name
    return context, subject


def _level(config: Any) -> Optional[str]:
    if isinstance(config, dict) and "error" not in config:
        return config.get("compatibilityLevel") or config.get("compatibility")
    return None


def _config_error(config: Any) -> Optional[str]:
    if isinstance(config, dict) and "error" in config:
        return str(config["error"])
    if not isinstance(config, dict):
        return f"unexpected config response: {config!r}"
    return None


def _strict_list(client: Any, path: str, context: Optional[str], fallback: Callable[[], Any]) -> list:
    """GET a list and raise on failure.

    ``RegistryClient.get_subjects`` and ``get_contexts`` turn every failure into ``[]``,
    which would read as an empty registry. A client without a session uses ``fallback``.
    """
    session = getattr(client, "session", None)
    build = getattr(client, "build_context_url", None)
    if session is None or build is None:
        result = fallback()
    else:
        # requests ignores session.timeout, so the timeout has to be passed on the call.
        response = session.get(
            build(path, context), auth=client.auth, headers=client.headers, timeout=LIST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()
    if not isinstance(result, list):
        raise ValueError(f"unexpected listing response: {result!r}")
    return result


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

        config = client.get_subject_config(subject, context)
        error = _config_error(config)
        if error is None:
            record.override = _level(config)
        elif not _NOT_FOUND.match(error):
            # Only a 404 means "no override"; any other failure leaves the effective level unknown.
            record.override_unknown = True
            record.errors.append(f"config: {error}")
    except Exception as e:
        record.errors.append(str(e))
    return record


def collect_context(client: Any, context: Optional[str], keep_foreign: bool = False) -> ContextRecord:
    """Read one context: its compatibility level and every subject in it."""
    config = None
    try:
        config = client.get_global_config(context)
        subjects = _strict_list(client, "/subjects", context, lambda: client.get_subjects(context))
    except Exception as e:
        return ContextRecord(context, _level(config), [], error=f"subjects: {e}", config_error=_config_error(config))
    level, config_error = _level(config), _config_error(config)
    try:
        if not keep_foreign:
            # A listing can include qualified subjects of other contexts; keep only this context's own.
            own = _key(context)
            subjects = [s for s in subjects if _key(_split_qualified(s, context)[0]) == own]
        with ThreadPoolExecutor(max_workers=_SUBJECT_WORKERS) as executor:
            records = list(executor.map(lambda s: _inspect_subject(client, context, s), subjects))
        return ContextRecord(context, level, records, config_error=config_error)
    except Exception as e:
        return ContextRecord(context, level, [], error=str(e), config_error=config_error)


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
    known = {}
    for record in records:
        target_context, name = _split_qualified(record.subject, record.context)
        known[(_key(target_context), name)] = (record.context, record.subject)
    scanned = {_key(ctx.context) for ctx in contexts if not ctx.error}
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
        effective = None if record.override_unknown else (record.override or context_level)
        by_level[effective or "UNKNOWN"] += 1
        if record.override:
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
    unverified = []
    for record in records:
        for target in record.references:
            found = known.get((_key(target[0]), target[1]))
            if found:
                referenced_by[found] += 1
                continue
            if _key(target[0]) not in scanned:
                # The target's context was out of scope or failed to list; absence is not proven.
                unverified.append(
                    {
                        "context": _label(record.context),
                        "subject": record.subject,
                        "target_context": _label(target[0]),
                        "target_subject": target[1],
                    }
                )
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
        if ctx.config_error:
            errors.append({"context": _label(ctx.context), "subject": None, "error": f"config: {ctx.config_error}"})
        if not ctx.error and ctx.context is not None and not ctx.subjects:
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
        "references": {"most_referenced": most_referenced, "dangling": dangling, "unverified": unverified},
        "findings": findings,
        "errors": errors,
        "limitations": LIMITATIONS,
    }


def _contexts_to_scan(client: Any, context: Optional[str]) -> tuple[list[Optional[str]], Optional[str]]:
    """Return the contexts to read and, when listing contexts failed, that error."""
    if context is not None:
        return [_normalise_context(context)], None
    names: list[Optional[str]] = [None]
    try:
        listed = _strict_list(client, "/contexts", None, client.get_contexts)
    except Exception as e:
        return names, f"contexts: {e}"
    for name in listed:
        normalised = _normalise_context(name)
        if normalised not in names:
            names.append(normalised)
    return names, None


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
        names, listing_error = await asyncio.to_thread(_contexts_to_scan, client, context)
        await progress.set_total(len(names))
        # Without a context list, other contexts' subjects are only reachable through the default listing.
        keep_foreign = context is None and len(names) == 1

        collected = []
        for name in names:
            await progress.set_message(f"Analyzing context {_label(name)}")
            collected.append(await asyncio.to_thread(collect_context, client, name, keep_foreign))
            await progress.increment()

        report = summarise(collected, top_n=top_n, version_sprawl_threshold=version_sprawl_threshold)
        if listing_error:
            report["errors"].insert(0, {"context": "all", "subject": None, "error": listing_error})
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
