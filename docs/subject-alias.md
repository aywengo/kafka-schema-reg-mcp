### Subject Aliasing (add_subject_alias)

Create an alias subject that points to an existing subject.

- Availability: Not available in SLIM_MODE or VIEWONLY mode
- Scope: Requires write scope (OAuth enabled environments)

Request semantics (Schema Registry API):

```bash
curl -X PUT \
  -u "USER:PASS" \
  -H "Content-Type: application/json" \
  -d '{"alias":"<existing-subject>"}' \
  "https://<schema-registry-host>/config/<alias>"
```

MCP Tool:

```json
{
  "tool": "add_subject_alias",
  "params": {
    "alias": "<new-alias>",
    "existing_subject": "<existing-subject>",
    "context": ".",
    "registry": "dev"
  }
}
```

Response (example):

```json
{
  "alias": "orders-latest",
  "target": "orders-value",
  "registry_mode": "multi",
  "_links": {
    "config": "subject://dev/orders-latest/config"
  }
}
```

Notes:
- If your registry version does not return JSON for alias PUT, the tool returns `{ "status": "ok" }` plus metadata.
- In VIEWONLY mode, the tool returns a structured error indicating modifications are blocked.

