# Editions and tool catalog

v3.0 ships one codebase as three editions. `MCP_EDITION` selects the edition at
startup; the catalog is the source of truth and every table below is generated
from `tool_catalog.py`.

| Edition | Tools | Docker tag | Intended use |
|---|---|---|---|
| `viewer` | 39 | `:3.0.0-viewer` | Browse, export, compare, compatibility checks |
| `editor` | 42 | `:3.0.0-editor` | Viewer plus schema registration and evolution |
| `admin` | 67 | `:3.0.0-admin` | Full access, including configuration, deletion and migration |

The default is `viewer`. Set `MCP_EDITION=editor` or `MCP_EDITION=admin` to
expose more tools. The image can also bake a different default with
`MCP_EDITION_DEFAULT`.

`SLIM_MODE=true` is a deprecated alias for `MCP_EDITION=editor`. Setting both
`SLIM_MODE` and `MCP_EDITION` is an error, not a silent override.

## Viewer (39)

| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `compare_contexts_across_registries` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `describe_workflow` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `guided_schema_evolution` | read | no | viewer |
| `list_available_resources` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `ping` | read | no | viewer |
| `suggest_resource_for_tool` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |

## Full editor set (42)

Includes every viewer tool.

| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `add_subject_alias` | write | yes | editor |
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `compare_contexts_across_registries` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `describe_workflow` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `guided_schema_evolution` | read | no | viewer |
| `list_available_resources` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `ping` | read | no | viewer |
| `register_schema` | write | yes | editor |
| `register_schema_interactive` | write | yes | editor |
| `suggest_resource_for_tool` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |

## Full admin set (67)

Includes every viewer tool.

| Tool | Scope | Mutates | Edition |
|---|---|---|---|
| `add_subject_alias` | write | yes | editor |
| `bulk_configuration_update` | admin | yes | admin |
| `bulk_operations_wizard` | admin | no | admin |
| `bulk_schema_cleanup` | admin | yes | admin |
| `bulk_schema_migration` | admin | yes | admin |
| `bulk_schema_update` | admin | yes | admin |
| `check_compatibility` | read | no | viewer |
| `check_compatibility_interactive` | read | no | viewer |
| `clear_context_batch` | admin | yes | admin |
| `clear_multiple_contexts_batch` | admin | yes | admin |
| `compare_contexts_across_registries` | read | no | viewer |
| `compare_registries` | read | no | viewer |
| `count_contexts` | read | no | viewer |
| `count_schema_versions` | read | no | viewer |
| `count_schemas` | read | no | viewer |
| `create_context` | write | yes | admin |
| `create_context_interactive` | write | yes | admin |
| `delete_context` | admin | yes | admin |
| `delete_subject` | admin | yes | admin |
| `delete_subject_alias` | admin | yes | admin |
| `describe_workflow` | read | no | viewer |
| `export_context` | read | no | viewer |
| `export_global` | read | no | viewer |
| `export_global_interactive` | read | no | viewer |
| `export_schema` | read | no | viewer |
| `export_subject` | read | no | viewer |
| `find_missing_schemas` | read | no | viewer |
| `generate_resource_templates` | read | no | viewer |
| `get_default_registry` | read | no | viewer |
| `get_global_config` | read | no | viewer |
| `get_mcp_compliance_status` | read | no | viewer |
| `get_mode` | read | no | viewer |
| `get_oauth_scopes_info` | read | no | viewer |
| `get_registry_info` | read | no | viewer |
| `get_registry_statistics` | read | no | viewer |
| `get_schema` | read | no | viewer |
| `get_schema_by_id` | read | no | viewer |
| `get_schema_versions` | read | no | viewer |
| `get_subject_config` | read | no | viewer |
| `get_subject_mode` | read | no | viewer |
| `get_subjects_by_schema_id` | read | no | viewer |
| `guided_context_reorganization` | admin | no | admin |
| `guided_disaster_recovery` | admin | no | admin |
| `guided_schema_evolution` | read | no | viewer |
| `guided_schema_migration` | admin | no | admin |
| `list_available_resources` | read | no | viewer |
| `list_contexts` | read | no | viewer |
| `list_registries` | read | no | viewer |
| `list_subjects` | read | no | viewer |
| `list_workflows` | read | no | viewer |
| `migrate_context` | admin | yes | admin |
| `migrate_context_interactive` | admin | yes | admin |
| `migrate_schema` | admin | yes | admin |
| `migrate_schema_interactive` | admin | yes | admin |
| `ping` | read | no | viewer |
| `preview_bulk_operation` | admin | no | admin |
| `register_schema` | write | yes | editor |
| `register_schema_interactive` | write | yes | editor |
| `restore_bundle` | admin | yes | admin |
| `suggest_resource_for_tool` | read | no | viewer |
| `test_all_registries` | read | no | viewer |
| `test_oauth_discovery_endpoints` | read | no | viewer |
| `test_registry_connection` | read | no | viewer |
| `update_global_config` | write | yes | admin |
| `update_mode` | write | yes | admin |
| `update_subject_config` | write | yes | admin |
| `update_subject_mode` | write | yes | admin |
