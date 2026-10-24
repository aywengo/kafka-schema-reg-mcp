# Elicitation and MRTR Workflows

## Overview

The Kafka Schema Registry MCP Server supports interactive workflows on both
protocol eras:

- **`2026-07-28` connections** use multi-round-trip (MRTR). A guard tool returns
  `InputRequiredResult` with one or more input requests. The client retries the
  same tool call with the answers and the sealed `requestState`.
- **`2025-11-25` connections** use the in-request `elicitation/create`
  handshake through `ctx.elicit`.

The server chooses the path from the negotiated protocol version. There is no
mock or default-value fallback: if the client declines or cannot answer, the
tool returns a structured error or a plan instead of silently writing data.

## Guard tools

These tools ask for missing information:

| Tool | Edition | Asks for |
|---|---|---|
| `register_schema_interactive` | editor | Missing schema fields, types, nullability and defaults |
| `migrate_schema_interactive` | admin | Source/target registry, context and migration preferences |
| `migrate_context_interactive` | admin | Context, registry and conflict-resolution preferences |
| `check_compatibility_interactive` | viewer | Resolution strategy when schemas are incompatible |
| `create_context_interactive` | admin | Context description, owner, environment and tags |
| `export_global_interactive` | viewer | Export format and inclusion options |

The admin planners (`guided_schema_evolution`, `guided_schema_migration`,
`guided_context_reorganization`, `guided_disaster_recovery` and
`bulk_operations_wizard`) use the same guard mechanism but only read state and
return a plan. They do not mutate the registry.

## Modern client flow

1. Call the tool with the arguments you already know.
2. The server returns an `InputRequiredResult`:

   ```json
   {
     "inputRequests": {
       "form": {
         "method": "elicitation/create",
         "params": {
           "message": "Provide the missing migration preferences",
           "requestedSchema": {
             "type": "object",
             "properties": {
               "dry_run": {"type": "boolean", "default": true}
             }
           }
         }
       }
     },
     "requestState": "..."
   }
   ```

3. Show the form to the user.
4. Retry the same tool call with `inputResponses` and the returned
   `requestState`.
5. The server validates the answers and continues the operation.

FastMCP clients handle this loop automatically. A direct JSON-RPC client must
implement it.

## Legacy client flow

On `2025-11-25`, the same tool calls `ctx.elicit` inside the request. The client
receives a normal `elicitation/create` request and replies with:

- `accept` and the form values,
- `decline`, or
- `cancel`.

The server converts optional `null` values to the schema default before
validation. Declining a destructive operation returns a structured error and
does not perform the write.

## Example: interactive schema registration

```python
result = await mcp.call_tool(
    "register_schema_interactive",
    {
        "subject": "user-events",
        "schema_type": "AVRO",
        # schema_definition is optional; the tool asks for missing fields
    },
)
```

If the proposed schema is incompatible, the tool returns
`status: "compatibility_error"` with the registry messages. It does not start a
second legacy workflow.

## Example: guided schema evolution

```python
result = await mcp.call_tool(
    "guided_schema_evolution",
    {
        "subject": "user-profile",
        "current_schema": '{"type":"record","name":"User","fields":[...]}',
        "proposed_schema": '{"type":"record","name":"User","fields":[...]}',
        "strategy": "BACKWARD",
    },
)
```

The result is a plan: compatibility findings, a recommended strategy and the
next tools to call. Apply the plan with the normal registry tools.

## Error handling

- **Declined**: the tool returns a structured `declined` or guidance result.
- **Unsupported client**: no mock values are substituted. Use a client that
  supports MRTR or `elicitation/create`.
- **Invalid answers**: validation errors identify the field that failed.
- **Expired state**: retry the original tool call to start a new round.

## Testing

Use the FastMCP client with explicit protocol modes:

```python
from fastmcp import Client

async with Client(server, mode="auto") as client:
    # 2026-07-28 MRTR path
    ...

async with Client(server, mode="legacy") as client:
    # 2025-11-25 elicitation/create path
    ...
```

The edition matrix tests cover both modes for viewer, editor and admin.

## Related documentation

- [MCP tools reference](mcp-tools-reference.md)
- [v3.0 migration guide](v3-migration-guide.md)
- [MCP specification](https://modelcontextprotocol.io)
