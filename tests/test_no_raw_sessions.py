"""Static boundary checks for registry HTTP access."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {
    "schema_registry_common.py",
    "oauth_provider.py",
    "remote-mcp-server.py",
    "kafka_schema_registry_unified_mcp.py",
}


def test_no_registry_sessions_outside_common():
    offenders = []
    for path in ROOT.glob("*.py"):
        if path.name in ALLOWED:
            continue
        text = path.read_text()
        if "requests.Session()" in text or "aiohttp.ClientSession(" in text:
            offenders.append(path.name)
    assert not offenders, f"construct registry HTTP sessions in schema_registry_common.py: {offenders}"


def test_no_direct_aiohttp_delete_in_core_tools():
    text = (ROOT / "core_registry_tools.py").read_text()
    assert "aiohttp.ClientSession(" not in text
