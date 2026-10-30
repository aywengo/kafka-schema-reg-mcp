# MCP Tools Reference

This document describes the Kafka Schema Registry MCP Server **3.0.0** on **FastMCP 4.1+** and **MCP 2026-07-28**. The same process also serves `2025-11-25` clients. The tool surface is generated from `tool_catalog.py`; this reference is generated from the live MCP schemas.

## Editions

Set `MCP_EDITION=viewer|editor|admin`; the default is `viewer`. `SLIM_MODE=true` is a deprecated alias for `editor`. The generated per-edition tables are in [editions.md](editions.md).

| Edition | Tools | Access |
|---|---|---|
| `viewer` | 39 | Read-only browsing, export, comparison, compatibility, statistics |
| `editor` | 42 | Viewer plus schema registration and evolution |
| `admin` | 67 | Full surface: configuration, deletion, contexts, migration, bulk operations, workflows |

Tools outside the active edition are not registered, so clients do not list them and cannot call them.

## Tools by edition

### Viewer (39 tools)

| Tool | Scope | Kind | Description |
|---|---|---|---|
| `check_compatibility` | `read` | read-only | Check if a schema is compatible with the latest version. |
| `check_compatibility_interactive` | `read` | read-only | Interactive compatibility checking with elicitation for resolution options. When compatibility issues are found, this tool will elicit resolution preferences from the user. |
| `compare_contexts_across_registries` | `read` | read-only | Compare contexts across two registries. |
| `compare_registries` | `read` | read-only | Compare two Schema Registry instances and show differences. |
| `count_contexts` | `read` | read-only | Count the number of contexts in a registry. |
| `count_schema_versions` | `read` | read-only | Count the number of versions for a specific schema. |
| `count_schemas` | `read` | read-only | Count the number of schemas in a context or registry. |
| `describe_workflow` | `read` | read-only | Get detailed information about a workflow definition |
| `export_context` | `read` | read-only | Export all subjects within a context. |
| `export_global` | `read` | read-only | Export all contexts and schemas from a registry. |
| `export_global_interactive` | `read` | read-only | Interactive global export with elicitation for export preferences. When export preferences are not specified, this tool will elicit the required configuration from the user. |
| `export_schema` | `read` | read-only | Export a single schema in the specified format. |
| `export_subject` | `read` | read-only | Export all versions of a subject. |
| `find_missing_schemas` | `read` | read-only | Find schemas that exist in source registry but not in target registry. |
| `generate_resource_templates` | `read` | read-only | Generate resource URI templates for your specific configuration. |
| `get_default_registry` | `read` | read-only | Get the current default registry. |
| `get_global_config` | `read` | read-only | Get global configuration settings. |
| `get_mcp_compliance_status` | `read` | read-only | Get MCP 2026-07-28 specification compliance status and configuration details. Returns information about JSON-RPC batching status, protocol version, header validation, and migration guidance. |
| `get_mode` | `read` | read-only | Get the current mode of the Schema Registry. |
| `get_oauth_scopes_info` | `read` | read-only | Get information about OAuth scopes and permissions. |
| `get_registry_info` | `read` | read-only | Get detailed information about a specific registry. |
| `get_registry_statistics` | `read` | read-only | Get comprehensive statistics about a registry. |
| `get_schema` | `read` | read-only | Get a specific version of a schema. |
| `get_schema_by_id` | `read` | read-only | Get a schema by its globally unique ID. |
| `get_schema_versions` | `read` | read-only | Get all versions of a schema for a subject. |
| `get_subject_config` | `read` | read-only | Get configuration settings for a specific subject. |
| `get_subject_mode` | `read` | read-only | Get the operational mode for a specific subject. |
| `get_subjects_by_schema_id` | `read` | read-only | Get subjects and versions associated with a schema ID. |
| `guided_schema_evolution` | `read` | read-only | Start the Schema Evolution Assistant workflow. This guided workflow helps you safely evolve schemas by analyzing changes, suggesting strategies, and coordinating consumer updates. |
| `list_available_resources` | `read` | read-only | List all available MCP resources and their usage patterns. |
| `list_contexts` | `read` | read-only | List all available schema contexts. |
| `list_registries` | `read` | read-only | List all configured Schema Registry instances. |
| `list_subjects` | `read` | read-only | List all subjects, optionally filtered by context. |
| `list_workflows` | `read` | read-only | List available multi-step workflows |
| `ping` | `read` | read-only | Respond to MCP ping requests with pong. This tool implements the standard MCP ping/pong protocol for server health checking. MCP proxies and clients use this to verify that the server is alive and responding. |
| `suggest_resource_for_tool` | `read` | read-only | Suggest the appropriate resource to use instead of a removed tool. |
| `test_all_registries` | `read` | read-only | Test connections to all configured registries. |
| `test_oauth_discovery_endpoints` | `read` | read-only | Test OAuth discovery endpoints to ensure proper MCP client compatibility. Validates: - /.well-known/oauth-authorization-server - /.well-known/oauth-protected-resource - /.well-known/jwks.json |
| `test_registry_connection` | `read` | read-only | Test connection to a specific registry. |

### Editor-only (3 tools)

| Tool | Scope | Kind | Description |
|---|---|---|---|
| `add_subject_alias` | `write` | write | Create a subject alias to an existing subject (editor and admin editions; VIEWONLY blocks writes). |
| `register_schema` | `write` | write | Register a new schema version. |
| `register_schema_interactive` | `write` | write | Interactive schema registration with elicitation for missing field definitions. When schema_definition is incomplete or missing fields, this tool will elicit the required information from the user interactively. |

### Admin-only (25 tools)

| Tool | Scope | Kind | Description |
|---|---|---|---|
| `bulk_configuration_update` | `admin` | write | Update configuration settings across multiple schemas or contexts. Supports security policies, retention settings, and access controls. |
| `bulk_operations_wizard` | `admin` | read-only | Start the interactive Bulk Operations Wizard for admin tasks. Guides through safe execution of operations across multiple schemas. Supports schema updates, migrations, cleanup, and configuration changes. |
| `bulk_schema_cleanup` | `admin` | destructive | Clean up schemas in bulk with safety checks. Detects active consumers and provides options for handling them. Supports test schema cleanup, deprecated schema removal, and version purging. |
| `bulk_schema_migration` | `admin` | destructive | Migrate schemas between contexts or registries. Supports pattern-based selection and maintains schema IDs. Includes preview and rollback capabilities. |
| `bulk_schema_update` | `admin` | write | Update schemas in bulk with interactive guidance. Supports compatibility settings, naming conventions, and metadata updates. Pattern matching supported (e.g., test-*, deprecated-*). |
| `clear_context_batch` | `admin` | destructive | Clear all subjects in a context using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution. |
| `clear_multiple_contexts_batch` | `admin` | destructive | Clear multiple contexts in a registry using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution. |
| `create_context` | `write` | write | Create a new schema context. |
| `create_context_interactive` | `write` | write | Interactive context creation with elicitation for metadata. When context metadata is not provided, this tool will elicit organizational information from the user. |
| `delete_context` | `admin` | destructive | Delete a schema context. |
| `delete_subject` | `admin` | destructive | Delete a subject and all its versions. |
| `delete_subject_alias` | `admin` | destructive | Delete a subject alias (editor and admin editions; VIEWONLY blocks writes). |
| `guided_context_reorganization` | `admin` | read-only | Start the Context Reorganization workflow for reorganizing schemas across contexts |
| `guided_disaster_recovery` | `admin` | read-only | Start the Disaster Recovery Setup workflow |
| `guided_schema_migration` | `admin` | read-only | Start the Schema Migration Wizard workflow for guided schema migration |
| `migrate_context` | `admin` | destructive | Guide for migrating an entire context using Docker-based tools. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking. |
| `migrate_context_interactive` | `admin` | destructive | Interactive context migration with elicitation for missing preferences. When migration preferences are not specified, this tool will elicit the required configuration from the user. |
| `migrate_schema` | `admin` | destructive | Migrate a schema from one registry to another. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking. |
| `restore_bundle` | `admin` | destructive | Apply an export document to one registry. Dry-run unless apply is true. Preserves schema ids. Uses FastMCP background tasks API (SEP-1686) for async execution. |
| `migrate_schema_interactive` | `admin` | destructive | Interactive schema migration that asks for missing preferences. Modern clients get a multi-round-trip form; legacy clients get `elicitation/create`. Declining returns a structured error. |
| `preview_bulk_operation` | `admin` | read-only | Preview the changes a bulk operation would make without executing it. |
| `update_global_config` | `write` | write | Update global configuration settings. |
| `update_mode` | `write` | write | Update the mode of the Schema Registry. |
| `update_subject_config` | `write` | write | Update configuration settings for a specific subject. |
| `update_subject_mode` | `write` | write | Update the mode for a specific subject. |

## Tool parameters

### Viewer tools

#### `check_compatibility`

Check if a schema is compatible with the latest version.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `schema_definition` | `object` | yes |  |
| `schema_type` | `string` | no | `AVRO` |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `check_compatibility_interactive`

Interactive compatibility checking with elicitation for resolution options. When compatibility issues are found, this tool will elicit resolution preferences from the user.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `schema_definition` | `object` | yes |  |
| `schema_type` | `string` | no | `AVRO` |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `compare_contexts_across_registries`

Compare contexts across two registries.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `source_context` | `string` | yes |  |
| `target_context` | `string` | no |  |

#### `compare_registries`

Compare two Schema Registry instances and show differences.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `include_contexts` | `boolean` | no | `true` |
| `include_configs` | `boolean` | no | `true` |

#### `count_contexts`

Count the number of contexts in a registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |

#### `count_schema_versions`

Count the number of versions for a specific schema.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `count_schemas`

Count the number of schemas in a context or registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `describe_workflow`

Get detailed information about a workflow definition

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `workflow_id` | `string` | yes |  |

#### `export_context`

Export all subjects within a context.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | yes |  |
| `registry` | `string` | no |  |
| `include_metadata` | `boolean` | no | `true` |
| `include_config` | `boolean` | no | `true` |
| `include_versions` | `string` | no | `all` |

#### `export_global`

Export all contexts and schemas from a registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |
| `include_metadata` | `boolean` | no | `true` |
| `include_config` | `boolean` | no | `true` |
| `include_versions` | `string` | no | `all` |

#### `export_global_interactive`

Interactive global export with elicitation for export preferences. When export preferences are not specified, this tool will elicit the required configuration from the user.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |
| `include_metadata` | `boolean` | no |  |
| `include_config` | `boolean` | no |  |
| `include_versions` | `string` | no |  |
| `format` | `string` | no |  |
| `compression` | `string` | no |  |
| `output_format` | `string` | no |  |
| `schemas_per_file` | `string` | no |  |

#### `export_schema`

Export a single schema in the specified format.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `version` | `string` | no | `latest` |
| `context` | `string` | no |  |
| `format` | `string` | no | `json` |
| `registry` | `string` | no |  |

#### `export_subject`

Export all versions of a subject.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `include_metadata` | `boolean` | no | `true` |
| `include_config` | `boolean` | no | `true` |
| `include_versions` | `string` | no | `all` |
| `registry` | `string` | no |  |

#### `find_missing_schemas`

Find schemas that exist in source registry but not in target registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `context` | `string` | no |  |

#### `generate_resource_templates`

Generate resource URI templates for your specific configuration.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry_name` | `string` | no |  |
| `context` | `string` | no |  |
| `subject` | `string` | no |  |

#### `get_default_registry`

Get the current default registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `get_global_config`

Get global configuration settings.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_mcp_compliance_status`

Get MCP 2026-07-28 specification compliance status and configuration details. Returns information about JSON-RPC batching status, protocol version, header validation, and migration guidance.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `get_mode`

Get the current mode of the Schema Registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_oauth_scopes_info`

Get information about OAuth scopes and permissions.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `get_registry_info`

Get detailed information about a specific registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |

#### `get_registry_statistics`

Get comprehensive statistics about a registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |
| `include_context_details` | `boolean` | no | `true` |

#### `get_schema`

Get a specific version of a schema.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `version` | `string` | no | `latest` |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_schema_by_id`

Get a schema by its globally unique ID.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `schema_id` | `integer` | yes |  |
| `registry` | `string` | no |  |

#### `get_schema_versions`

Get all versions of a schema for a subject.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_subject_config`

Get configuration settings for a specific subject.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_subject_mode`

Get the operational mode for a specific subject.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `get_subjects_by_schema_id`

Get subjects and versions associated with a schema ID.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `schema_id` | `integer` | yes |  |
| `registry` | `string` | no |  |

#### `guided_schema_evolution`

Start the Schema Evolution Assistant workflow. This guided workflow helps you safely evolve schemas by analyzing changes, suggesting strategies, and coordinating consumer updates.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | no |  |
| `current_schema` | `string` | no |  |
| `proposed_schema` | `string` | no |  |
| `strategy` | `string` | no |  |

#### `list_available_resources`

List all available MCP resources and their usage patterns.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `list_contexts`

List all available schema contexts.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |

#### `list_registries`

List all configured Schema Registry instances.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `list_subjects`

List all subjects, optionally filtered by context.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `list_workflows`

List available multi-step workflows

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `ping`

Respond to MCP ping requests with pong. This tool implements the standard MCP ping/pong protocol for server health checking. MCP proxies and clients use this to verify that the server is alive and responding.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `suggest_resource_for_tool`

Suggest the appropriate resource to use instead of a removed tool.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `tool_name` | `string` | yes |  |

#### `test_all_registries`

Test connections to all configured registries.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

No parameters.

#### `test_oauth_discovery_endpoints`

Test OAuth discovery endpoints to ensure proper MCP client compatibility. Validates: - /.well-known/oauth-authorization-server - /.well-known/oauth-protected-resource - /.well-known/jwks.json

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `server_url` | `string` | no | `http://localhost:8000` |

#### `test_registry_connection`

Test connection to a specific registry.

- Edition: `viewer`
- Scope: `read`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |

### Editor-only tools

#### `add_subject_alias`

Create a subject alias to an existing subject (editor and admin editions; VIEWONLY blocks writes).

- Edition: `editor`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `alias` | `string` | yes |  |
| `existing_subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `register_schema`

Register a new schema version.

- Edition: `editor`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `schema_definition` | `object` | yes |  |
| `schema_type` | `string` | no | `AVRO` |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `register_schema_interactive`

Interactive schema registration with elicitation for missing field definitions. When schema_definition is incomplete or missing fields, this tool will elicit the required information from the user interactively.

- Edition: `editor`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `schema_definition` | `object` | no |  |
| `schema_type` | `string` | no | `AVRO` |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

### Admin-only tools

#### `bulk_configuration_update`

Update configuration settings across multiple schemas or contexts. Supports security policies, retention settings, and access controls.

- Edition: `admin`
- Scope: `admin`
- Kind: write
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `config_type` | `string` | no | `security` |
| `target_type` | `string` | no | `schemas` |
| `pattern` | `string` | no |  |
| `settings` | `object` | no |  |
| `dry_run` | `boolean` | no | `true` |

#### `bulk_operations_wizard`

Start the interactive Bulk Operations Wizard for admin tasks. Guides through safe execution of operations across multiple schemas. Supports schema updates, migrations, cleanup, and configuration changes.

- Edition: `admin`
- Scope: `admin`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `operation_type` | `string` | no |  |
| `dry_run` | `boolean` | no | `true` |

#### `bulk_schema_cleanup`

Clean up schemas in bulk with safety checks. Detects active consumers and provides options for handling them. Supports test schema cleanup, deprecated schema removal, and version purging.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `cleanup_type` | `string` | no | `test` |
| `pattern` | `string` | no |  |
| `keep_versions` | `integer` | no | `3` |
| `check_consumers` | `boolean` | no | `true` |
| `force` | `boolean` | no | `false` |

#### `bulk_schema_migration`

Migrate schemas between contexts or registries. Supports pattern-based selection and maintains schema IDs. Includes preview and rollback capabilities.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_context` | `string` | no |  |
| `target_context` | `string` | no |  |
| `source_registry` | `string` | no |  |
| `target_registry` | `string` | no |  |
| `schema_pattern` | `string` | no |  |
| `preserve_ids` | `boolean` | no | `true` |
| `dry_run` | `boolean` | no | `true` |

#### `bulk_schema_update`

Update schemas in bulk with interactive guidance. Supports compatibility settings, naming conventions, and metadata updates. Pattern matching supported (e.g., test-*, deprecated-*).

- Edition: `admin`
- Scope: `admin`
- Kind: write
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `pattern` | `string` | no |  |
| `update_type` | `string` | no | `compatibility` |
| `dry_run` | `boolean` | no | `true` |
| `batch_size` | `integer` | no | `10` |

#### `clear_context_batch`

Clear all subjects in a context using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | yes |  |
| `registry` | `string` | no |  |
| `delete_context_after` | `boolean` | no | `true` |
| `dry_run` | `boolean` | no | `true` |

#### `clear_multiple_contexts_batch`

Clear multiple contexts in a registry using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `contexts` | `array` | yes |  |
| `registry` | `string` | no |  |
| `delete_contexts_after` | `boolean` | no | `true` |
| `dry_run` | `boolean` | no | `true` |

#### `create_context`

Create a new schema context.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | yes |  |
| `registry` | `string` | no |  |

#### `create_context_interactive`

Interactive context creation with elicitation for metadata. When context metadata is not provided, this tool will elicit organizational information from the user.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | yes |  |
| `registry` | `string` | no |  |
| `description` | `string` | no |  |
| `owner` | `string` | no |  |
| `environment` | `string` | no |  |
| `tags` | `array` | no |  |

#### `delete_context`

Delete a schema context.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `context` | `string` | yes |  |
| `registry` | `string` | no |  |

#### `delete_subject`

Delete a subject and all its versions.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |
| `permanent` | `boolean` | no | `false` |

#### `delete_subject_alias`

Delete a subject alias (editor and admin editions; VIEWONLY blocks writes).

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `alias` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `guided_context_reorganization`

Start the Context Reorganization workflow for reorganizing schemas across contexts

- Edition: `admin`
- Scope: `admin`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |
| `source_context` | `string` | no |  |
| `target_context` | `string` | no |  |
| `dry_run` | `boolean` | no |  |

#### `guided_disaster_recovery`

Start the Disaster Recovery Setup workflow

- Edition: `admin`
- Scope: `admin`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `registry` | `string` | no |  |
| `backup_target` | `string` | no |  |
| `schedule` | `string` | no |  |
| `verify_restore` | `boolean` | no |  |

#### `guided_schema_migration`

Start the Schema Migration Wizard workflow for guided schema migration

- Edition: `admin`
- Scope: `admin`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | no |  |
| `target_registry` | `string` | no |  |
| `subject` | `string` | no |  |
| `dry_run` | `boolean` | no |  |

#### `migrate_context`

Guide for migrating an entire context using Docker-based tools. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `context` | `string` | no |  |
| `target_context` | `string` | no |  |
| `preserve_ids` | `boolean` | no | `true` |
| `dry_run` | `boolean` | no | `true` |
| `migrate_all_versions` | `boolean` | no | `true` |

#### `migrate_context_interactive`

Interactive context migration with elicitation for missing preferences. When migration preferences are not specified, this tool will elicit the required configuration from the user.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `context` | `string` | no |  |
| `target_context` | `string` | no |  |
| `preserve_ids` | `boolean` | no |  |
| `dry_run` | `boolean` | no |  |
| `migrate_all_versions` | `boolean` | no |  |

#### `migrate_schema`

Migrate a schema from one registry to another. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `dry_run` | `boolean` | no | `false` |
| `preserve_ids` | `boolean` | no | `true` |
| `source_context` | `string` | no | `.` |
| `target_context` | `string` | no | `.` |
| `versions` | `array` | no |  |
| `migrate_all_versions` | `boolean` | no | `false` |

#### `restore_bundle`

Apply an `export_global`, `export_context`, or `export_subject` document to one registry. Dry-run unless `apply` is true. Preserves schema ids. `migrate_schema` remains the live-to-live copy between two registries.

Restore opens IMPORT on the whole registry with `force=true`, so a registry that already has schemas can keep ids. `accept_new_ids` is only the retry when that mode change still fails. A `context` filter limits which versions are written. It does not narrow the IMPORT window to `PUT /contexts/{ctx}/mode`. The version post creates a context; restore does not call `POST /contexts/{name}`.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task:  Yes.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `bundle` | `object` | yes | Export document. A string or a bare schema is rejected. |
| `target` | `string` | yes | Registry to write. |
| `apply` | `boolean` | no | `false` |
| `accept_new_ids` | `boolean` | no | `false`. Retry after IMPORT mode cannot be set. |
| `context` | `string` | no | Limit the document to one context. |
| `subject` | `string` | no | Limit the document to one subject. Requires `context`. |

#### `migrate_schema_interactive`

Interactive schema migration that asks for missing preferences. Modern clients get a multi-round-trip form; legacy clients get `elicitation/create`. Declining returns a structured error.

- Edition: `admin`
- Scope: `admin`
- Kind: destructive
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `source_registry` | `string` | yes |  |
| `target_registry` | `string` | yes |  |
| `source_context` | `string` | no | `.` |
| `target_context` | `string` | no | `.` |
| `versions` | `array` | no |  |
| `migrate_all_versions` | `boolean` | no |  |
| `preserve_ids` | `boolean` | no |  |
| `dry_run` | `boolean` | no |  |

#### `preview_bulk_operation`

Preview the changes a bulk operation would make without executing it.

- Edition: `admin`
- Scope: `admin`
- Kind: read-only
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `operation_type` | `string` | yes |  |
| `items` | `array` | yes |  |
| `parameters` | `object` | no |  |

#### `update_global_config`

Update global configuration settings.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `compatibility` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `update_mode`

Update the mode of the Schema Registry.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `mode` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `update_subject_config`

Update configuration settings for a specific subject.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `compatibility` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

#### `update_subject_mode`

Update the mode for a specific subject.

- Edition: `admin`
- Scope: `write`
- Kind: write
- Background task: No.

| Parameter | Type | Required | Default / values |
|---|---|---|---|
| `subject` | `string` | yes |  |
| `mode` | `string` | yes |  |
| `context` | `string` | no |  |
| `registry` | `string` | no |  |

## Resources

The server exposes 4 concrete resources and 17 resource templates. Resources are available in every edition.

### Concrete resources

| URI | Name | Description |
|---|---|---|
| `registry://names` | `registry_names_resource` | Get list of all configured registry names. |
| `registry://info` | `registry_info_resource` | Get detailed server configuration and capabilities. |
| `registry://status` | `registry_status_resource` | Get connection status for all registries. |
| `registry://mode` | `registry_mode_resource` | Get operational mode for all registries. |

### Resource templates

| URI template | Name | Description |
|---|---|---|
| `registry://info/{name}` | `registry_info_specific_resource` | Get detailed information about a specific registry. |
| `registry://status/{name}` | `registry_status_specific_resource` | Get connection status for a specific registry. |
| `registry://mode/{name}` | `registry_mode_specific_resource` | Get operational mode for a specific registry. |
| `registry://{name}/subjects` | `registry_subjects_resource` | Get all subjects for a specific registry, optionally filtered by context. |
| `registry://{name}/contexts/{context}/subjects` | `registry_context_subjects_resource` | Get all subjects in a named context for a specific registry. |
| `registry://{name}/contexts` | `registry_contexts_resource` | Get all contexts for a specific registry. |
| `registry://{name}/config` | `registry_config_resource` | Get global configuration for a specific registry, optionally filtered by context. |
| `schema://{name}/{context}/{subject}` | `schema_content_resource` | Get schema content for a specific subject in a specific context and registry. |
| `schema://{name}/{subject}` | `schema_content_default_context_resource` | Get schema content for a specific subject in the default context of a registry. |
| `schema://{name}/{context}/{subject}/versions` | `schema_versions_resource` | Get all versions of a schema for a specific subject in a specific context and registry. |
| `schema://{name}/{subject}/versions` | `schema_versions_default_context_resource` | Get all versions of a schema for a specific subject in the default context of a registry. |
| `subject://{name}/{context}/{subject}/config` | `subject_config_resource` | Get configuration settings for a specific subject with explicit context. |
| `subject://{name}/{subject}/config` | `subject_config_default_context_resource` | Get configuration settings for a specific subject in the default context. |
| `subject://{name}/{context}/{subject}/mode` | `subject_mode_resource` | Get the mode for a specific subject with explicit context. |
| `subject://{name}/{subject}/mode` | `subject_mode_default_context_resource` | Get the mode for a specific subject in the default context. |
| `registry://{name}/migrations` | `migrations_collection_resource` | List persisted migration records (none are persisted by this server). |
| `registry://{name}/tasks` | `tasks_collection_resource` | Describe how background tasks are exposed. |

## Prompts

The server exposes 10 prompts.

| Prompt | Description |
|---|---|
| `schema-getting-started` | Getting started with Schema Registry operations |
| `schema-registration` | Guide for registering new schemas |
| `context-management` | Guide for managing schema contexts |
| `schema-export` | Guide for exporting schemas and documentation |
| `multi-registry` | Guide for multi-registry operations |
| `schema-compatibility` | Guide for schema compatibility and evolution |
| `troubleshooting` | Troubleshooting guide for common issues |
| `advanced-workflows` | Guide for complex Schema Registry workflows |
| `schema-evolution` | Guide for safe schema evolution with the Schema Evolution Assistant |
| `quick-reference` | Get a quick reference card of most common commands. |

## Related documentation

- [Editions and per-edition tool tables](editions.md)
- [v3.0 migration guide](v3-migration-guide.md)
- [REST API reference](api-reference.md)
