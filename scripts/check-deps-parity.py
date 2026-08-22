#!/usr/bin/env python3
"""Verify overlapping dependency floor pins match between requirements.txt and pyproject.toml."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"
PYPROJECT = ROOT / "pyproject.toml"

REQ_PATTERN = re.compile(
    r"^([a-zA-Z0-9_.\-\[\]]+)(?:\[[^\]]+\])?\s*(>=|==|~=|<=|<|!=)\s*([^\s#,]+)",
    re.MULTILINE,
)
TOML_DEP_PATTERN = re.compile(
    r'"([a-zA-Z0-9_.\-\[\]]+)(?:\[[^\]]+\])?\s*(>=|==|~=|<=|<|!=)\s*([^"]+)"',
)


def normalize_name(name: str) -> str:
    """Normalize package names for comparison (ignore extras)."""
    return name.split("[", 1)[0].lower().replace("_", "-")


def parse_requirements(path: Path) -> dict[str, str]:
    """Parse floor pins from requirements.txt."""
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = REQ_PATTERN.match(stripped)
        if not match:
            continue
        name, op, version = match.groups()
        if op == ">=":
            pins[normalize_name(name)] = version
    return pins


def parse_pyproject(path: Path) -> dict[str, str]:
    """Parse floor pins from pyproject.toml [project].dependencies."""
    text = path.read_text(encoding="utf-8")
    start = text.find("dependencies = [")
    if start == -1:
        return {}
    optional_start = text.find("[project.optional-dependencies]", start)
    if optional_start == -1:
        optional_start = text.find("[project.urls]", start)
    if optional_start == -1:
        optional_start = len(text)
    block = text[start:optional_start]
    pins: dict[str, str] = {}
    for match in TOML_DEP_PATTERN.finditer(block):
        name, op, version = match.groups()
        if op == ">=":
            base_version = version.split(",", 1)[0].strip()
            pins[normalize_name(name)] = base_version
    return pins


def main() -> int:
    req_pins = parse_requirements(REQUIREMENTS)
    py_pins = parse_pyproject(PYPROJECT)
    shared = sorted(set(req_pins) & set(py_pins))
    mismatches: list[str] = []

    for name in shared:
        req_version = req_pins[name]
        py_version = py_pins[name]
        if req_version != py_version:
            mismatches.append(f"{name}: requirements.txt>={req_version} vs pyproject.toml>={py_version}")

    if mismatches:
        print("Dependency pin mismatches between requirements.txt and pyproject.toml:")
        for item in mismatches:
            print(f"  - {item}")
        return 1

    print(f"OK: {len(shared)} shared dependency floor pins match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
