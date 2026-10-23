# Editions and tool catalog

v3.0 ships one codebase as three editions. `MCP_EDITION` selects the edition at
startup; the catalog is the source of truth and every table below is generated
from `tool_catalog.py`.

| Edition | Tools | Docker tag | Intended use |
|---|---|---|---|
| `viewer` | 38 | `:3.0.0-viewer` | Browse, export, compare, compatibility checks |
| `editor` | 41 | `:3.0.0-editor` | Viewer plus schema registration and evolution |
| `admin` | 67 | `:3.0.0-admin` | Full access, including configuration, deletion and migration |

The default is `viewer`. Set `MCP_EDITION=editor` or `MCP_EDITION=admin` to
expose more tools. The image can also bake a different default with
`MCP_EDITION_DEFAULT`.

`SLIM_MODE=true` is a deprecated alias for `MCP_EDITION=editor`. Setting both
`SLIM_MODE` and `MCP_EDITION` is an error, not a silent override.

## Viewer (38)

| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `ping` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `list_available_resources` | read | no | viewer |
| `suggest_resource_for_tool` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `compare_contexts_across_registries` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `describe_workflow` | read | no | viewer |


## Full editor set (41)

Includes every viewer tool.


| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `ping` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `list_available_resources` | read | no | viewer |
| `suggest_resource_for_tool` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `compare_contexts_across_registries` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `describe_workflow` | read | no | viewer |
| `register_schema` | write | yes | editor |
| `register_schema_interactive` | write | yes | editor |
| `guided_schema_evolution` | write | yes | editor |


## Full admin set (67)

Includes every editor tool.


| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `ping` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `list_available_resources` | read | no | viewer |
| `suggest_resource_for_tool` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `compare_contexts_across_registries` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `describe_workflow` | read | no | viewer |
| `register_schema` | write | yes | editor |
| `register_schema_interactive` | write | yes | editor |
| `guided_schema_evolution` | write | yes | editor |
| `create_context` | write | yes | admin |
| `create_context_interactive` | write | yes | admin |
| `delete_context` | admin | yes | admin |
| `delete_subject` | admin | yes | admin |
| `update_global_config` | write | yes | admin |
| `update_subject_config` | write | yes | admin |
| `update_mode` | write | yes | admin |
| `update_subject_mode` | write | yes | admin |
| `add_subject_alias` | admin | yes | admin |
| `delete_subject_alias` | admin | yes | admin |
| `migrate_schema` | admin | yes | admin |
| `migrate_context` | admin | yes | admin |
| `migrate_context_interactive` | admin | yes | admin |
| `migrate_schema_interactive` | admin | yes | admin |
| `clear_context_batch` | admin | yes | admin |
| `clear_multiple_contexts_batch` | admin | yes | admin |
| `bulk_operations_wizard` | admin | yes | admin |
| `bulk_schema_update` | admin | yes | admin |
| `bulk_schema_cleanup` | admin | yes | admin |
| `bulk_schema_migration` | admin | yes | admin |
| `bulk_configuration_update` | admin | yes | admin |
| `preview_bulk_operation` | admin | no | admin |
| `start_workflow` | admin | yes | admin |
| `guided_schema_migration` | admin | yes | admin |
| `guided_context_reorganization` | admin | yes | admin |
| `guided_disaster_recovery` | admin | yes | admin |


## Removing a tool

Tools are never registered when they are outside the active edition, so they do
not appear in `tools/list`, do not consume context, and cannot be called. A
client that calls a hidden tool gets `-32602 Unknown tool`.

## Resources and prompts

Resources are shared by all editions and remain read-only. Prompts are filtered
by `PROMPT_CATALOG`; the default set is available to every edition.
