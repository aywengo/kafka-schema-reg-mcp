#!/usr/bin/env python3
"""HTTP live checks for 3.2.0 features: DR plan, registry insights, traceparent.

Self-contained: starts a mock Schema Registry and ``remote-mcp-server.py``,
then drives MCP over streamable-http. Set ``MCP_URL`` to reuse an already
running server (for example the minikube RC2 stack) and skip local startup.

  python3 tests/test_v32_feature_http.py
  MCP_URL=http://127.0.0.1:18080/mcp python3 tests/test_v32_feature_http.py
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import unquote

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROTOCOL = os.environ.get("MCP_PROTOCOL_VERSION", "2025-06-18")
TIMEOUT = float(os.environ.get("MCP_TIMEOUT", "90"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ---- mock Schema Registry -------------------------------------------------


_SR_DATA = {
    "contexts": ["team-a", "empty-ctx"],
    "global": "BACKWARD",
    "subjects": {
        None: {
            "user-value": {
                "versions": [1, 2, 3],
                "schemaType": "AVRO",
                "schema": ('{"type":"record","name":"User","fields":[{"name":"id","type":"int"}]}'),
                "refs": [],
                "compat": None,
            },
            "sprawl-value": {
                "versions": list(range(1, 25)),
                "schemaType": "AVRO",
                "schema": '{"type":"string"}',
                "refs": [],
                "compat": "NONE",
            },
            "dangling-value": {
                "versions": [1],
                "schemaType": "AVRO",
                "schema": '{"type":"record","name":"D","fields":[]}',
                "refs": [{"name": "Missing", "subject": "missing-ref-value", "version": 1}],
                "compat": None,
            },
        },
        "team-a": {
            "order-value": {
                "versions": [1],
                "schemaType": "JSON",
                "schema": '{"type":"object"}',
                "refs": [],
                "compat": "FULL",
            },
        },
        "empty-ctx": {},
    },
}


def _ctx_from(path: str) -> tuple[Optional[str], str]:
    match = re.match(r"^/contexts/([^/]+)(.*)$", path)
    if not match:
        return None, path
    return unquote(match.group(1)), (match.group(2) or "/")


class _MockSRHandler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: Any) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/vnd.schemaregistry.v1+json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        context, path = _ctx_from(self.path.split("?", 1)[0])
        bag = _SR_DATA["subjects"].get(context, {})
        if path == "/contexts":
            return self._json(200, _SR_DATA["contexts"])
        if path == "/config":
            if context == "team-a":
                return self._json(200, {"compatibilityLevel": "FULL"})
            if context == "empty-ctx":
                return self._json(200, {"compatibilityLevel": "BACKWARD"})
            return self._json(200, {"compatibilityLevel": _SR_DATA["global"]})
        if path == "/subjects":
            return self._json(200, list(bag.keys()))
        match = re.match(r"^/config/(.+)$", path)
        if match:
            subject = unquote(match.group(1))
            record = bag.get(subject)
            if not record:
                return self._json(404, {"error_code": 40401, "message": "Subject not found."})
            if record.get("compat") is None:
                return self._json(
                    404,
                    {
                        "error_code": 40408,
                        "message": (f"Subject '{subject}' does not have subject-level " "compatibility configured"),
                    },
                )
            return self._json(200, {"compatibilityLevel": record["compat"]})
        match = re.match(r"^/subjects/([^/]+)/versions/?$", path)
        if match:
            record = bag.get(unquote(match.group(1)))
            if not record:
                return self._json(404, {"error_code": 40401, "message": "Subject not found."})
            return self._json(200, record["versions"])
        match = re.match(r"^/subjects/([^/]+)/versions/latest$", path)
        if match:
            subject = unquote(match.group(1))
            record = bag.get(subject)
            if not record:
                return self._json(404, {"error_code": 40401, "message": "Subject not found."})
            body: dict[str, Any] = {
                "subject": subject,
                "version": record["versions"][-1],
                "id": abs(hash(subject)) % 10000,
                "schemaType": record["schemaType"],
                "schema": record["schema"],
            }
            if record["refs"]:
                body["references"] = [
                    {"name": ref["name"], "subject": ref["subject"], "version": ref["version"]}
                    for ref in record["refs"]
                ]
            return self._json(200, body)
        return self._json(404, {"error_code": 404, "message": "not found"})

    def log_message(self, *_args: Any) -> None:
        return


class MockSchemaRegistry:
    def __init__(self) -> None:
        self.port = _free_port()
        self.httpd = HTTPServer(("127.0.0.1", self.port), _MockSRHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=5)


# ---- MCP HTTP client ------------------------------------------------------


class McpHttp:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(timeout=TIMEOUT)
        self.session_id: Optional[str] = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
        }

    def close(self) -> None:
        self.client.close()

    def _headers(self, extra: Optional[dict[str, str]] = None) -> dict[str, str]:
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _parse(body: str) -> Any:
        if "data:" in body:
            chunks = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
            if not chunks:
                raise AssertionError(f"SSE body had no data lines: {body[:500]}")
            return json.loads(chunks[-1])
        return json.loads(body)

    def initialize(self) -> dict[str, Any]:
        response = self.client.post(
            self.url,
            headers=self._headers(),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {},
                    "clientInfo": {"name": "v32-feature-http", "version": "0"},
                },
            },
        )
        response.raise_for_status()
        self.session_id = response.headers.get("mcp-session-id") or response.headers.get("Mcp-Session-Id")
        payload = self._parse(response.text)
        self.client.post(
            self.url,
            headers=self._headers(),
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        return payload

    def call_tool(
        self,
        name: str,
        arguments: Optional[dict[str, Any]] = None,
        *,
        req_id: int = 10,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> Any:
        response = self.client.post(
            self.url,
            headers=self._headers(extra_headers),
            json={
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        response.raise_for_status()
        return self._parse(response.text)


def _tool_payload(rpc: dict[str, Any]) -> Any:
    result = rpc.get("result", rpc)
    if not isinstance(result, dict):
        return result
    structured = result.get("structuredContent")
    if structured is not None:
        return structured
    content = result.get("content")
    if isinstance(content, list) and content:
        text = content[0].get("text")
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return result


# ---- fixtures -------------------------------------------------------------


class FeatureHarness:
    def __init__(self) -> None:
        self.external_url = os.environ.get("MCP_URL", "").strip()
        self.registry: Optional[MockSchemaRegistry] = None
        self.server: Optional[subprocess.Popen] = None
        self.docker_id: Optional[str] = None
        self.mcp_url = ""
        self.owned = False
        self.image = os.environ.get(
            "MCP_IMAGE",
            "aywengo/kafka-schema-reg-mcp:3.2.0-rc2-admin",
        )

    def start(self) -> str:
        if self.external_url:
            base = self.external_url.rstrip("/")
            self.mcp_url = base if base.endswith("/mcp") else f"{base}/mcp"
            print(f"Using existing MCP at {self.mcp_url}")
            return self.mcp_url

        self.owned = True
        self.registry = MockSchemaRegistry()
        self.registry.start()
        try:
            return self._start_local_process()
        except Exception as local_err:  # noqa: BLE001
            print(f"Local remote-mcp-server failed ({local_err}); trying Docker image {self.image}")
            return self._start_docker()

    def _wait_ready(self, base: str, *, owned_proc: Optional[subprocess.Popen] = None) -> str:
        self.mcp_url = f"{base}/mcp"
        deadline = time.time() + 60
        last_err = ""
        while time.time() < deadline:
            if owned_proc is not None and owned_proc.poll() is not None:
                out = owned_proc.stdout.read() if owned_proc.stdout else ""
                raise RuntimeError(f"remote-mcp-server exited early:\n{out}")
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"{base}/ready")
                    if response.status_code == 200:
                        assert self.registry is not None
                        print(f"Started MCP at {self.mcp_url} (SR {self.registry.url})")
                        return self.mcp_url
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
            time.sleep(0.4)
        raise RuntimeError(f"MCP server did not become ready: {last_err}")

    def _start_local_process(self) -> str:
        assert self.registry is not None
        mcp_port = _free_port()
        env = os.environ.copy()
        env.update(
            {
                "MCP_TRANSPORT": "streamable-http",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": str(mcp_port),
                "ENABLE_AUTH": "false",
                "MCP_EDITION": "admin",
                "SCHEMA_REGISTRY_URL": self.registry.url,
                "VIEWONLY": "false",
                "TASKS_BACKEND": "memory",
            }
        )
        script = os.path.join(ROOT, "remote-mcp-server.py")
        self.server = subprocess.Popen(
            [sys.executable, script],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return self._wait_ready(f"http://127.0.0.1:{mcp_port}", owned_proc=self.server)

    def _start_docker(self) -> str:
        assert self.registry is not None
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
            self.server.wait(timeout=5)
            self.server = None
        mcp_port = _free_port()
        # Publish the mock SR to the Docker host gateway.
        sr_url = f"http://host.docker.internal:{self.registry.port}"
        cmd = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--add-host=host.docker.internal:host-gateway",
            "-p",
            f"127.0.0.1:{mcp_port}:8000",
            "-e",
            "ENABLE_AUTH=false",
            "-e",
            "MCP_EDITION=admin",
            "-e",
            "MCP_PORT=8000",
            "-e",
            "MCP_HOST=0.0.0.0",
            "-e",
            f"SCHEMA_REGISTRY_URL={sr_url}",
            "-e",
            "TASKS_BACKEND=memory",
            self.image,
            "python",
            "remote-mcp-server.py",
        ]
        created = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if created.returncode != 0:
            raise RuntimeError(f"docker run failed ({created.returncode}): {created.stderr or created.stdout}")
        self.docker_id = created.stdout.strip()
        try:
            return self._wait_ready(f"http://127.0.0.1:{mcp_port}")
        except Exception:
            logs = subprocess.run(
                ["docker", "logs", self.docker_id],
                capture_output=True,
                text=True,
                check=False,
            )
            raise RuntimeError(f"Docker MCP did not become ready.\nlogs:\n{logs.stdout}\n{logs.stderr}") from None

    def stop(self) -> None:
        if not self.owned:
            return
        if self.docker_id:
            subprocess.run(
                ["docker", "rm", "-f", self.docker_id],
                capture_output=True,
                text=True,
                check=False,
            )
            self.docker_id = None
        if self.server and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=5)
        if self.registry:
            self.registry.stop()


# ---- tests ----------------------------------------------------------------


def test_disaster_recovery(mcp: McpHttp) -> None:
    print("== guided_disaster_recovery ==")
    rpc = mcp.call_tool(
        "guided_disaster_recovery",
        {
            "registry": "prod",
            "backup_target": "s3://bucket/sr",
            "rpo": "under-1-hour",
            "rto": "under-4-hours",
            "scenarios": ["accidental-deletion", "corruption"],
            "include_runbook": True,
            "verify_restore": True,
        },
        req_id=20,
    )
    plan = _tool_payload(rpc)
    assert isinstance(plan, dict), plan
    assert plan.get("error") is None, plan
    assert plan.get("status") == "plan", plan
    assert plan.get("schedule") == "hourly", plan
    assert plan.get("strategy", {}).get("recovery") == "restore_to_prepared_registry", plan
    assert plan.get("objectives", {}).get("rpo") == "under-1-hour", plan
    runbook = plan.get("runbook") or ""
    assert "accidental" in runbook.lower(), runbook[:500]
    assert "corruption" in runbook.lower(), runbook[:500]
    print("PASS guided_disaster_recovery")


def test_registry_insights(mcp: McpHttp) -> None:
    print("== get_registry_insights ==")
    rpc = mcp.call_tool(
        "get_registry_insights",
        {"top_n": 5, "version_sprawl_threshold": 20},
        req_id=30,
    )
    report = _tool_payload(rpc)
    assert isinstance(report, dict), report
    assert report.get("error_code") is None, report
    findings = report.get("findings") or []
    codes = {item.get("code") for item in findings if isinstance(item, dict)}
    print("findings", sorted(codes))
    expected = {
        "VERSION_SPRAWL",
        "COMPATIBILITY_NONE",
        "DANGLING_REFERENCE",
        "EMPTY_CONTEXT",
    }
    missing = expected - codes
    assert not missing, f"missing {missing}; got {codes}; report={json.dumps(report)[:1500]}"
    assert report.get("limitations"), report
    print("PASS get_registry_insights")


def test_traceparent(mcp: McpHttp) -> None:
    print("== traceparent ==")
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    rpc = mcp.call_tool(
        "ping",
        {},
        req_id=40,
        extra_headers={"traceparent": traceparent, "tracestate": "vendor=v32"},
    )
    payload = _tool_payload(rpc)
    assert isinstance(payload, dict), payload
    assert payload.get("response") == "pong", payload
    assert payload.get("server_version"), payload
    print(f"PASS ping with traceparent (server_version={payload.get('server_version')})")


def main() -> int:
    harness = FeatureHarness()
    mcp: Optional[McpHttp] = None
    try:
        url = harness.start()
        mcp = McpHttp(url)
        info = mcp.initialize().get("result", {}).get("serverInfo", {})
        print("serverInfo", info)
        assert info.get("version"), info
        test_disaster_recovery(mcp)
        test_registry_insights(mcp)
        test_traceparent(mcp)
        print("ALL PASS")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if mcp is not None:
            mcp.close()
        harness.stop()


if __name__ == "__main__":
    sys.exit(main())
