# v3.0 Migration Guide

v3.0 moves the server to FastMCP 4 / MCP SDK 2 and replaces `SLIM_MODE` with
editions. The protocol change is backward compatible for clients that still use
the `2025-11-25` handshake. The tool surface change is not: a deployment now
exposes 38, 41 or 67 tools instead of all 75.

## Before you upgrade

1. Decide which edition each deployment should run: `viewer`, `editor` or
   `admin`. The default is `viewer`.
2. Check the tools your clients call against `docs/editions.md`. If a client
   needs a write tool, run at least the `editor` image; for configuration,
   deletion or migration, run `admin`.
3. Set `MCP_EDITION` explicitly in production. Do not rely on the image default
   if the workload needs write access.
4. Keep `VIEWONLY=true` on read-only registry connections. It is still enforced,
   now at the HTTP session boundary.

## Edition selection

| Old | New |
|---|---|
| `SLIM_MODE=true` | `MCP_EDITION=editor` (or `SLIM_MODE=true` as a temporary alias) |
| `SLIM_MODE=false` | `MCP_EDITION=admin` for the full pre-3.0 surface |
| no flag | `MCP_EDITION=viewer` (new default) |

`SLIM_MODE` is a deprecated alias for `editor`. Setting `MCP_EDITION` and
`SLIM_MODE` together is a startup error. The alias will be removed in 4.0.0.

### Docker tags

Plain tags (`:stable`, `:latest`, `:3.0.0`) point at the `viewer` edition.
Edition tags are suffixed: `:stable-viewer`, `:stable-editor`,
`:stable-admin` (and the same for `latest` and version tags). Pin the suffix
you need.

### Helm

`helm/values.yaml` now has `edition: viewer`. The image tag defaults to
`<appVersion>-<edition>` when `image.tag` is empty. If you previously set
`extraEnvVars: SLIM_MODE=true`, remove it and set `edition: editor` instead;
otherwise startup fails with the conflict error.

## Removed and renamed tools

Renamed (old name still works through a deprecation warning in 2.3.x, removed
in 3.0):

- `get_mcp_compliance_status_tool` → `get_mcp_compliance_status`
- `get_oauth_scopes_info_tool` → `get_oauth_scopes_info`

Removed in 3.0:

- `set_default_registry`
- `workflow_status`, `get_workflow_status`, `list_available_workflows`,
  `abort_workflow`
- `submit_elicitation_response`, `list_elicitation_requests`,
  `get_elicitation_request`, `get_elicitation_status`,
  `cancel_elicitation_request`

Use the `registry` argument on the tool call instead of
`set_default_registry`. Use `list_workflows`, `describe_workflow` and
`guided_schema_evolution` for workflow state. Interactive tools now use MCP
elicitation directly; the fallback request/response tools are gone.

## Protocol changes

- One process serves both `2026-07-28` and `2025-11-25`. The client negotiates;
  no configuration is needed.
- Interactive tools return `InputRequiredResult` on modern connections and call
  `ctx.elicit()` on legacy connections. Clients must be able to answer an
  elicitation request or handle a suspended result.
- Resumable state is signed with `REQUEST_STATE_KEY`. The value must be at least
  32 bytes. Helm generates or reuses a Secret; set the key yourself if you run
  outside Helm.
- Resource-not-found now returns JSON-RPC `-32602` instead of `-32002`.
- Missing tools return `-32602`; they are not registered outside their edition.

## Tasks

Long-running tools (`register_schema`, migrations, bulk operations) use the
`io.modelcontextprotocol/tasks` extension. The default backend is in-memory and
works for one replica. For more than one replica, set:

```bash
TASKS_BACKEND=redis
TASKS_BACKEND_URL=redis://valkey:6379/0
```

Helm refuses `tasks.backend=memory` when `replicaCount > 1` or autoscaling is
enabled.

## Resources and links

`_links` URIs now resolve to registered resources. The schemes are
`registry://`, `schema://` and `subject://`. A few links point at the
collection resource when the old path had no handler (for example migrations
and tasks). List results carry a short private cache hint; clients that do not
understand the hint ignore it.

## Rollback

v3.0 cannot serve the full 75-tool surface with one flag. To roll back, deploy
the last 2.x image and set `SLIM_MODE` as before. Schema Registry data and
schema IDs are unchanged; only the MCP surface and the state key are new.

## Checklist

- [ ] Set `MCP_EDITION` on every deployment.
- [ ] Replace `SLIM_MODE` with `MCP_EDITION` in Helm values and Compose files.
- [ ] Pin edition-suffixed image tags.
- [ ] Set or confirm `REQUEST_STATE_KEY` (32+ bytes).
- [ ] Choose `TASKS_BACKEND` for multi-replica deployments.
- [ ] Update clients that call removed workflow or elicitation tools.
- [ ] Run `pytest tests/test_editions.py tests/test_edition_matrix.py`.
