# MCP Tools Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server v2.0.0 with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance** **MCP Tools**, including all 70+ tools and their usage with Claude Desktop.

## 🏃 SLIM_MODE: Performance Optimization

**SLIM_MODE** is a performance optimization feature that reduces the number of exposed MCP tools from **70+ to ~11 essential tools**, significantly improving LLM response times and reducing token usage.

### **Enabling SLIM_MODE**
```bash
# Docker
docker run -e SLIM_MODE=true -e SCHEMA_REGISTRY_URL=http://localhost:8081 aywengo/kafka-schema-reg-mcp:stable

# Environment Variable
export SLIM_MODE=true

# Claude Desktop Configuration
"env": {
  "SLIM_MODE": "true",
  "SCHEMA_REGISTRY_URL": "http://localhost:8081"
}
```

### **Benefits of SLIM_MODE**
- 🚀 **Faster LLM Response**: ~85% reduction in tool processing overhead
- 💰 **Lower Token Usage**: Fewer tools to parse means reduced costs
- 🎯 **Focused Functionality**: Essential read-only operations for production
- 🔍 **Better Tool Discovery**: LLMs can more easily find the right tool
- 📊 **Resource-First Approach**: Uses MCP resources instead of tools for read-only operations

### **Tools Available in SLIM_MODE** (~11 tools)
✅ **Core Connectivity**
- `ping` - Server health check

✅ **Registry Management** (Read-only)
- `get_default_registry` - Get current default registry
- `set_default_registry` - Set default registry (single-registry mode only)
- **REMOVED**: `list_registries`, `get_registry_info`, `test_registry_connection`, `test_all_registries` - Use resources instead:
  - `registry://names` - List all configured registries
  - `registry://info/{name}` - Get detailed registry information
  - `registry://status/{name}` - Test specific registry connection
  - `registry://status` - Test all registry connections

✅ **Schema Operations**
- `get_schema` - Retrieve schema versions
- `get_schema_versions` - List all versions of a schema
- `register_schema` - Register new schemas
- `check_compatibility` - Check schema compatibility
- **REMOVED**: `list_subjects` - Use `registry://{name}/subjects` resource instead
- **REMOVED**: `list_contexts` - Use `registry://{name}/contexts` resource instead

✅ **Configuration Reading**
- `get_subject_config` - Get subject configuration  
- `get_subject_mode` - Get subject mode
- **REMOVED**: `get_mode` - Use `registry://mode` resource instead
- **REMOVED**: `get_global_config` - Use `registry://{name}/config` resource instead

✅ **Context Management**
- `create_context` - Create new contexts

✅ **Statistics** (Lightweight)
- `count_contexts` - Count contexts
- `count_schemas` - Count schemas
- `count_schema_versions` - Count schema versions
- **REMOVED**: `check_viewonly_mode` - Use `registry://mode/{name}` resource instead

### **Tools EXCLUDED in SLIM_MODE** (~50 tools)
❌ **Heavy Operations**
- All migration tools (`migrate_schema`, `migrate_context`, etc.)
- All batch operations (`clear_context_batch`, etc.)
- All export/import tools
- All interactive/elicitation tools (`*_interactive` variants)
- Delete operations (`delete_subject`, `delete_context`)
- Configuration updates (`update_*` tools)
- Task management tools
- Comparison tools
- Heavy statistics with async operations

### **When to Use SLIM_MODE**
- ✅ Production environments with read-heavy workloads
- ✅ When experiencing slow LLM responses
- ✅ Cost-sensitive deployments
- ✅ Simple schema viewing and compatibility checking
- ❌ Not suitable for: migrations, bulk operations, or administrative tasks

---

## 🔍 Registry Metadata Integration

**All test and statistics methods now automatically include comprehensive Schema Registry metadata** using the `/v1/metadata/*` endpoints. This provides enhanced traceability and debugging capabilities without requiring separate calls.

**Metadata Included:**
- **Version**: Schema Registry version (e.g., "7.6.0")
- **Commit ID**: Git commit hash of the registry build
- **Kafka Cluster ID**: Unique identifier for the Kafka cluster
- **Schema Registry Cluster ID**: Registry cluster identifier

**Enhanced Methods:**
- `get_registry_info` - **Primary method for complete registry information with metadata** *(Available in SLIM_MODE)*
- `test_registry_connection` - Connection testing with metadata *(Available in SLIM_MODE)*
- `test_all_registries` - Multi-registry testing with metadata *(Available in SLIM_MODE)*
- `count_schemas`, `count_contexts`, `count_schema_versions` - Statistics with registry context *(Available in SLIM_MODE)*
- `get_registry_statistics` - Comprehensive stats with metadata *(NOT in SLIM_MODE - heavy operation)*

## 🤖 MCP Integration Overview

The Kafka Schema Registry MCP Server provides **70+ comprehensive MCP tools** that enable natural language interaction with Kafka Schema Registry through Claude Desktop and other MCP clients, now with advanced async operations and multi-registry support.

### **Key Features:**
- ✅ **Natural Language Interface**: Interact using plain English commands
- ✅ **Claude Desktop Integration**: Seamless AI-assisted schema management  
- ✅ **70+ MCP Tools**: Complete schema operations without API knowledge (or ~20 in SLIM_MODE)
- ✅ **Context-Aware Operations**: All tools support schema contexts
- ✅ **Real-time Feedback**: Immediate results and validation
- ✅ **Production Safety**: VIEWONLY mode blocks modifications in production
- ✅ **Async Task Management**: Non-blocking operations with progress tracking
- ✅ **Multi-Registry Support**: Manage multiple Schema Registry instances
- ✅ **SLIM_MODE**: Reduce tools to ~20 for better LLM performance

### **Tool Categories:**
- **Schema Management** (4 tools): register, retrieve, versions, compatibility - *3 available in SLIM_MODE*
- **Context Management** (3 tools): list, create, delete contexts - *2 available in SLIM_MODE*
- **Subject Management** (2 tools): list, delete subjects - *1 available in SLIM_MODE*
- **Configuration Management** (5 tools): global and subject-specific settings - *2 read-only in SLIM_MODE*
- **Mode Management** (5 tools): operational mode control - *2 read-only in SLIM_MODE*
- **Export Tools** (4 tools): comprehensive schema export capabilities - *NOT in SLIM_MODE*
- **Multi-Registry Tools** (8 tools): cross-registry operations - *6 available in SLIM_MODE*
- **Batch Cleanup Tools** (2 tools): efficient context cleanup - *NOT in SLIM_MODE*
- **Migration Tools** (5 tools): schema and context migration - *NOT in SLIM_MODE*
- **Task Management Tools** (10 tools): progress tracking and monitoring - *NOT in SLIM_MODE*
- **Interactive/Elicitation Tools** (15+ tools): guided workflows and user interaction - *NOT in SLIM_MODE*
- **Workflow Tools** (9 tools): multi-step guided operations - *NOT in SLIM_MODE*
- **Utility Tools** (8+ tools): compliance, OAuth, statistics - *2 available in SLIM_MODE*

---

## 🔧 Schema Management Tools

### 1. register_schema ✅ *(Available in SLIM_MODE)*

Register a new schema version under a specified subject.

**Purpose**: Create new schemas or evolve existing ones with version control.

**Parameters:**
- `subject` (string): The subject name for the schema
- `schema_definition` (object): The schema definition as a dictionary
- `schema_type` (string, optional): Schema type (default: "AVRO")
- `context` (string, optional): Schema context name

**Claude Desktop Usage:**
```
Human: "Register a user schema with fields for id, name, and email in the development context"

Claude: I'll register that user schema in your development context.

[Uses register_schema MCP tool]
✅ Schema registered: user-events (ID: 1) in development context
```

**Advanced Example:**
```
Human: "Create an order schema in the production context with orderId, customerId, items array, total amount, and timestamp"

Claude: I'll create a comprehensive order schema for production.

[Uses register_schema MCP tool]
✅ Schema registered: order-events (ID: 15) in production context
   Fields: orderId (string), customerId (string), items (array), total (double), timestamp (long)
```

---

### 2. get_schema ✅ *(Available in SLIM_MODE)*

Retrieve a specific version of a schema.

**Purpose**: View schema definitions, inspect field structures, and analyze schema evolution.

**Parameters:**
- `subject` (string): The subject name
- `version` (string, optional): Schema version (default: "latest")
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Show me the latest version of the user-events schema in production"

Claude: I'll retrieve the latest user-events schema from production.

[Uses get_schema MCP tool]
📋 Schema: user-events v3 in production context
   Fields: userId (string), eventType (string), timestamp (long), metadata (map)
   Registered: 2024-05-25 14:30:15 UTC
```

**Version-Specific Example:**
```
Human: "Show me version 2 of the order schema to compare with the current version"

Claude: I'll get version 2 of the order schema for comparison.

[Uses get_schema MCP tool]
📋 Schema: order-events v2 (historical)
   Fields: orderId (string), customerId (string), amount (double)
   Note: Missing items array and timestamp (added in v3)
```

---

### 3. get_schema_versions ✅ *(Available in SLIM_MODE)*

Get all versions of a schema subject.

**Purpose**: Track schema evolution, identify version history, and plan upgrades.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What versions exist for the user-events schema?"

Claude: I'll check all available versions of the user-events schema.

[Uses get_schema_versions MCP tool]
📊 user-events versions: [1, 2, 3, 4]
   Current: v4 (latest)
   Evolution: 4 versions spanning 6 months
```

**Context-Specific Example:**
```
Human: "Show me version history for payment schemas in the production context"

Claude: I'll get the version history for payment schemas in production.

[Uses get_schema_versions MCP tool]
📊 payment-events versions in production: [1, 2, 3, 4, 5]
   Latest: v5 (current production version)
   Note: 5 versions showing steady evolution
```

---

### 4. check_compatibility ✅ *(Available in SLIM_MODE)*

Check if a schema is compatible with existing versions.

**Purpose**: Validate schema evolution before registration, prevent breaking changes.

**Parameters:**
- `subject` (string): The subject name
- `schema_definition` (object): Schema definition to check
- `schema_type` (string, optional): Schema type (default: "AVRO")
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "I want to add an optional email field to the user schema. Check if this is backward compatible"

Claude: I'll check if adding an optional email field is backward compatible.

[Uses check_compatibility MCP tool]
✅ Compatibility: BACKWARD compatible
   Change: Adding optional field with default value - safe to deploy
   Impact: Existing consumers will continue working
```

**Breaking Change Detection:**
```
Human: "What if I change the userId field from string to integer - is that compatible?"

Claude: I'll check that type change for compatibility.

[Uses check_compatibility MCP tool]
❌ Compatibility: NOT compatible
   Issue: Type change from string to integer is BREAKING
   Risk: All existing consumers will fail
   Recommendation: Use a new field name instead
```

---

## 🗂️ Context Management Tools

### 5. list_contexts ✅ *(Available in SLIM_MODE)*

List all available schema contexts.

**Purpose**: Discover available environments, understand context organization.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "What schema contexts are available?"

Claude: I'll show you all available schema contexts.

[Uses list_contexts MCP tool]
📋 Available contexts:
   • development (active development)
   • staging (pre-production testing)  
   • production (live environment)
   • client-acme (tenant isolation)
```

---

### 6. create_context ✅ *(Available in SLIM_MODE)*

Create a new schema context.

**Purpose**: Set up new environments, tenant isolation, feature branches.

**Parameters:**
- `context` (string): Context name to create

**Claude Desktop Usage:**
```
Human: "Create a new context for our staging environment"

Claude: I'll create a staging context for you.

[Uses create_context MCP tool]
✅ Created context: staging
   Status: Ready for schema registration
   Usage: Isolated environment for pre-production testing
```

**Multi-Context Setup:**
```
Human: "Set up contexts for our three clients: ACME, Globex, and Wayne Enterprises"

Claude: I'll create isolated contexts for each of your clients.

[Uses create_context MCP tool multiple times]
✅ Created context: client-acme
✅ Created context: client-globex  
✅ Created context: client-wayne
   Purpose: Tenant isolation with independent schema evolution
```

---

### 7. delete_context ❌ *(NOT in SLIM_MODE)*

Delete a schema context.

**Purpose**: Clean up temporary environments, remove unused contexts.

**Parameters:**
- `context` (string): Context name to delete

**Note**: This tool is excluded from SLIM_MODE as it's a destructive operation. Use full mode for context deletion.

**Claude Desktop Usage:**
```
Human: "Delete the feature-user-preferences context since we merged that feature"

Claude: I'll clean up the feature context for you.

[Uses delete_context MCP tool]
✅ Deleted context: feature-user-preferences
♻️ Resources cleaned up
   Note: All schemas in this context have been removed
```

---

## 📄 Subject Management Tools

### 8. list_subjects ✅ *(Available in SLIM_MODE)*

List all subjects, optionally filtered by context.

**Purpose**: Discover available schemas, understand subject organization.

**Parameters:**
- `context` (string, optional): Filter by schema context

**Claude Desktop Usage:**
```
Human: "What schemas are available in production?"

Claude: I'll show you all production schemas.

[Uses list_subjects MCP tool]
📋 Production subjects:
   • user-events (user activity tracking)
   • order-events (order lifecycle)
   • payment-events (payment processing)
   • notification-events (user notifications)
   Total: 4 active schemas
```

**All Contexts:**
```
Human: "Show me all schemas across all contexts"

Claude: I'll list all schemas from every context.

[Uses list_subjects MCP tool]
📋 All subjects across contexts:
   Production: 4 schemas
   Development: 8 schemas  
   Staging: 6 schemas
   Client contexts: 12 schemas
   Total: 30 schemas across 6 contexts
```

---

### 9. delete_subject ❌ *(NOT in SLIM_MODE)*

Delete a subject and all its versions.

**Purpose**: Remove deprecated schemas, clean up test subjects.

**Parameters:**
- `subject` (string): Subject name to delete
- `context` (string, optional): Schema context

**Note**: This destructive operation is excluded from SLIM_MODE for safety.

**Claude Desktop Usage:**
```
Human: "Delete the test-user-schema since we don't need it anymore"

Claude: I'll delete the test user schema for you.

[Uses delete_subject MCP tool]
✅ Deleted subject: test-user-schema
   Versions removed: [1, 2, 3]
   Context: development
⚠️ Note: Deletion is permanent and cannot be undone
```

---

## ⚙️ Configuration Management Tools

### 10. get_global_config ✅ *(Available in SLIM_MODE)*

Get global configuration settings.

**Purpose**: View current compatibility levels, understand global policies.

**Parameters:**
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the current global compatibility configuration?"

Claude: I'll check the global compatibility settings.

[Uses get_global_config MCP tool]
⚙️ Global configuration:
   Compatibility Level: BACKWARD
   Policy: New schemas must be backward compatible
   Context: Applied globally unless overridden
```

---

### 11. update_global_config ❌ *(NOT in SLIM_MODE)*

Update global configuration settings.

**Purpose**: Change compatibility requirements, enforce policies.

**Parameters:**
- `compatibility` (string): Compatibility level (BACKWARD, FORWARD, FULL, NONE)
- `context` (string, optional): Schema context

**Note**: Configuration updates are excluded from SLIM_MODE. Use full mode for configuration changes.

**Claude Desktop Usage:**
```
Human: "Set the production context to FULL compatibility for maximum safety"

Claude: I'll set production to the strictest compatibility mode.

[Uses update_global_config MCP tool]
✅ Updated global config for production context
   Compatibility: FULL (strictest mode)
   Impact: Both forward and backward compatibility required
   Safety: Maximum protection against breaking changes
```

---

### 12. get_subject_config ✅ *(Available in SLIM_MODE)*

Get configuration for a specific subject.

**Purpose:** View subject-specific compatibility overrides.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the compatibility setting for the payment-events schema?"

Claude: I'll check the payment-events compatibility configuration.

[Uses get_subject_config MCP tool]
⚙️ payment-events configuration:
   Compatibility: FULL (overrides global BACKWARD)
   Reason: Critical payment data requires strict compatibility
   Last updated: 2024-05-20 by ops-team
```

---

### 13. update_subject_config ❌ *(NOT in SLIM_MODE)*

Update configuration for a specific subject.

**Purpose**: Override global settings for specific schemas, apply custom policies.

**Parameters:**
- `subject` (string): The subject name
- `compatibility` (string): Compatibility level
- `context` (string, optional): Schema context

**Note**: Configuration updates are excluded from SLIM_MODE.

**Claude Desktop Usage:**
```
Human: "Set the payment schemas to require FULL compatibility since they're critical"

Claude: I'll apply strict compatibility rules to payment schemas.

[Uses update_subject_config MCP tool]
✅ Updated payment-events configuration
   Compatibility: FULL (strictest mode)
   Override: Supersedes global BACKWARD setting
   Reason: Critical payment data protection
```

---

## 🎛️ Mode Management Tools

### 14. ~~get_mode~~ ❌ *(REMOVED - Use registry://mode resource)*

**Replaced by:** `registry://mode` resource

Get the current operational mode.

**Migration:** Use the `registry://mode` resource instead of this tool for better performance.

**Claude Desktop Usage:**
```
Human: "What's the current operational mode of the schema registry?"

Claude: I'll check the current operational mode.

[Uses registry://mode resource]
🎛️ Current mode: READWRITE
   Status: Normal operations - registration and reads enabled
   Context: Global setting
```

---

### 15. update_mode ❌ *(NOT in SLIM_MODE)*

Update the operational mode.

**Purpose**: Control schema registration during maintenance, enable read-only modes.

**Parameters:**
- `mode` (string): Mode to set (READWRITE, READONLY, IMPORT)
- `context` (string, optional): Schema context

**Note**: Mode updates are excluded from SLIM_MODE.

**Claude Desktop Usage:**
```
Human: "Switch to read-only mode during our maintenance window"

Claude: I'll switch the registry to read-only mode for maintenance.

[Uses update_mode MCP tool]
✅ Mode changed: READONLY
   Effect: Schema registration disabled, reads still allowed
   Duration: Until manually changed back to READWRITE
⏰ Ready for maintenance operations
```

---

### 16. get_subject_mode ✅ *(Available in SLIM_MODE)*

Get the mode for a specific subject.

**Purpose**: Check subject-specific operational restrictions.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Check if the user-events subject has any mode restrictions"

Claude: I'll check the operational mode for user-events.

[Uses get_subject_mode MCP tool]
🎛️ user-events mode: READWRITE
   Status: Normal operations enabled
   Override: No subject-specific restrictions
```

---

### 17. update_subject_mode ❌ *(NOT in SLIM_MODE)*

Update the mode for a specific subject.

**Purpose**: Restrict specific schemas during migrations, enable subject-level controls.

**Parameters:**
- `subject` (string): The subject name
- `mode` (string): Mode to set
- `context` (string, optional): Schema context

**Note**: Mode updates are excluded from SLIM_MODE.

**Claude Desktop Usage:**
```
Human: "Set the legacy-events schema to read-only since we're deprecating it"

Claude: I'll set legacy-events to read-only mode.

[Uses update_subject_mode MCP tool]
✅ legacy-events mode: READONLY
   Effect: No new versions allowed, existing versions readable
   Purpose: Deprecation in progress
```

---

## 📤 Export Tools ❌ *(ALL NOT in SLIM_MODE)*

The following export tools are excluded from SLIM_MODE to reduce complexity:

### 18. export_schema ❌

Export a single schema in specified format.

**Note**: Export operations are excluded from SLIM_MODE as they can generate large responses.

---

### 19. export_subject ❌

Export all versions of a subject.

**Note**: Export operations are excluded from SLIM_MODE.

---

### 20. export_context ❌

Export all subjects within a context.

**Note**: Export operations are excluded from SLIM_MODE.

---

### 21. export_global ❌

Export all contexts and schemas from the registry.

**Note**: Export operations are excluded from SLIM_MODE. These are considered heavy operations that can generate large responses. Use full mode for export functionality.

---

## 📊 MCP Resources

In addition to tools, the MCP server provides **7 resources** for real-time information. All resources remain available in SLIM_MODE:

## 📊 Global Resources ✅ *(All Available in SLIM_MODE)*

### registry://status
Get current Schema Registry connection status and health information.

### registry://info  
Get detailed Schema Registry configuration, capabilities, and server information.

### registry://mode
Get information about the current registry mode and how it was detected.

### registry://names
Get a list of all configured schema registry names with status information.

## 🎯 Registry-Specific Resources ✅ *(All Available in SLIM_MODE)*

### registry://status/{name}
Get the connection status and health information for a specific registry.

### registry://info/{name}
Get detailed configuration and metadata information for a specific registry.

### registry://mode/{name}
Get mode and operational configuration information for a specific registry.

### registry://{name}/subjects ✅
Get all subjects for a specific registry, optionally filtered by context.

### registry://{name}/contexts ✅
Get all contexts for a specific registry.

### registry://{name}/config ✅
Get global configuration for a specific registry, optionally filtered by context.

## 📋 Schema Resources ✅ *(All Available in SLIM_MODE)*

### schema://{name}/{context}/{subject_name}
Get schema content for a specific subject in a specific context and registry.

### schema://{name}/{subject_name}
Get schema content for a specific subject in the default context of a registry.

**Usage Examples in Claude Desktop:**

**Global Resources:**
```
Human: "Check the status of our Schema Registry connection"

Claude: I'll check the Schema Registry status for you.

[Uses registry://status resource]
✅ Schema Registry Status: Connected
   URL: http://localhost:8081
   Response Time: 45ms
   Health: All systems operational
```

**Registry Names:**
```
Human: "Show me all available registries"

Claude: I'll list all configured registries for you.

[Uses registry://names resource]
📋 Available Registries:
   • production (default) ✅ Connected
   • staging ✅ Connected  
   • development ⚠️ Connection failed
   • testing ✅ Connected
   Total: 4 registries (3 connected, 1 failed)
```

**Registry Mode Information:**
```
Human: "What mode is the server running in?"

Claude: I'll check the server mode and configuration.

[Uses registry://mode resource]
🔧 Server Mode: MULTI-REGISTRY
   Detection: Auto-detected from REGISTRIES_CONFIG
   Structured Output: 100% Complete
   Elicitation: Enabled
   MCP Protocol: 2025-06-18 Compliant
```

**Registry-Specific Resources:**
```
Human: "Check the status of the production registry specifically"

Claude: I'll check the production registry status.

[Uses registry://status/production resource]
✅ Production Registry Status:
   URL: https://prod.schema-registry.com
   Status: Connected (120ms)
   Mode: READWRITE
   Viewonly: false
   Health: Operational
```

**Schema Content Access:**
```
Human: "Show me the user schema from production"

Claude: I'll retrieve the user schema from production.

[Uses schema://production/user resource]
📋 User Schema (Latest Version):
   Subject: user
   Registry: production
   Context: default
   Version: 3
   Schema Type: AVRO
   
   Schema Content:
   {
     "type": "record",
     "name": "User",
     "fields": [
       {"name": "id", "type": "long"},
       {"name": "name", "type": "string"},
       {"name": "email", "type": "string"}
     ]
   }
```

**Context-Specific Schema Access:**
```
Human: "Get the user schema from the analytics context in staging"

Claude: I'll retrieve the user schema from the analytics context.

[Uses schema://staging/analytics/user resource]
📋 User Schema (Analytics Context):
   Subject: user
   Registry: staging
   Context: analytics
   Version: 2
   Schema Type: AVRO
   
   Schema Content:
   {
     "type": "record",
     "name": "AnalyticsUser",
     "fields": [
       {"name": "user_id", "type": "long"},
       {"name": "username", "type": "string"},
       {"name": "last_activity", "type": "long"}
     ]
   }
```

---

## 💡 Natural Language Interaction Tips

### **Effective Commands:**
- **Be Specific**: "Register a user schema in production context" vs "Create schema"
- **Include Context**: "Show staging schemas" vs "Show schemas"  
- **Specify Format**: "Export as Avro IDL" vs "Export schema"
- **Ask for Help**: "What compatibility levels are available?"

### **Complex Workflows:**
- **Multi-Step Operations**: "Check compatibility, then register if safe"
- **Conditional Logic**: "Register in staging only if compatible with production"
- **Bulk Operations**: "Export all schemas from development context"

### **Best Practices:**
- ✅ Use clear, descriptive schema and context names
- ✅ Always check compatibility before production changes
- ✅ Export schemas before major changes for backup
- ✅ Clean up temporary contexts after feature completion
- ✅ Use context isolation for different environments

---

## 🔒 VIEWONLY Mode (Production Safety)

The MCP server includes a **production safety feature** that can be enabled by setting the `VIEWONLY=true` environment variable. When enabled, all modification operations are blocked while read and export operations remain fully functional.

### **Environment Setup**
```bash
# Enable VIEWONLY mode for production safety
export VIEWONLY=true

# Or in Docker/Claude Desktop
"env": {
  "VIEWONLY": "true",
  "SCHEMA_REGISTRY_URL": "http://localhost:8081"
}
```

### **Blocked Operations in VIEWONLY Mode**
When VIEWONLY mode is enabled, the following tools will return an error:
- 🚫 `register_schema` - Cannot register new schemas
- 🚫 `create_context` / `delete_context` - Cannot modify contexts
- 🚫 `delete_subject` - Cannot delete subjects
- 🚫 `update_global_config` / `update_subject_config` - Cannot modify configuration
- 🚫 `update_mode` / `update_subject_mode` - Cannot change operational modes

### **Allowed Operations in VIEWONLY Mode**
These tools continue to work normally:
- ✅ All `get_*` tools - Read schema information and configuration
- ✅ All `list_*` tools - Browse available schemas and contexts
- ✅ `check_compatibility` - Test schema compatibility (no modifications)
- ✅ All `export_*` tools - Generate backups and documentation

### **Claude Desktop Usage in VIEWONLY Mode**
```
Human: "Register a new user schema with id and name fields"

Claude: I attempted to register the schema, but the operation was blocked because the MCP server is running in VIEWONLY mode for production safety. 

Error: Operation blocked: MCP server is running in VIEWONLY mode. Set VIEWONLY=false to enable modification operations.

However, I can help you with read-only operations like:
- Viewing existing schemas
- Checking compatibility
- Exporting schemas for documentation
- Browsing contexts and subjects

Would you like me to show you the current schemas instead?
```

### **Benefits**
- 🛡️ **Production Safety**: Prevents accidental modifications to critical schemas
- 📊 **Full Visibility**: Complete read access for monitoring and analysis
- 📤 **Backup Capability**: All export operations remain available
- 🔍 **Compatibility Testing**: Can still validate schema changes without applying them

### **Combining VIEWONLY and SLIM_MODE**
```bash
# Maximum safety and performance for production
export VIEWONLY=true
export SLIM_MODE=true
```

This combination provides:
- 🛡️ **No Modifications**: VIEWONLY blocks all writes
- 🚀 **Fast Performance**: SLIM_MODE reduces tool overhead
- 🎯 **Production Ready**: Ideal for read-only production access

---

## 🌐 Multi-Registry Management Tools

### 22. ~~list_registries~~ ❌ *(REMOVED - Use registry://names resource)*

**Replaced by:** `registry://names` resource

List all configured Schema Registry instances.

**Migration:** Use the `registry://names` resource instead of this tool for better performance.

**Claude Desktop Usage:**
```
Human: "Show me all configured schema registries"

Claude: I'll list all configured registries with their status.

[Uses registry://names resource]
📋 Available Registries:
   • production (default) ✅ Connected
   • staging ✅ Connected  
   • development ⚠️ Connection failed
   • testing ✅ Connected
   Total: 4 registries (3 connected, 1 failed)
```

---

### 23. ~~get_registry_info~~ ❌ *(REMOVED - Use registry://info/{name} resource)*

**Replaced by:** `registry://info/{name}` resource

Get detailed information about a specific registry including connection status, configuration, and server metadata.

**Migration:** Use the `registry://info/{name}` resource instead of this tool for better performance.

**Claude Desktop Usage:**
```
Human: "Show me details about the production registry"

Claude: I'll get detailed information about the production registry.

[Uses registry://info/production resource]
📋 Production Registry Details:
   URL: https://prod.schema-registry.com
   Status: Connected (120ms)
   Version: 7.6.0
   Mode: READWRITE
   Viewonly: false
   Cluster ID: prod-cluster-001
```

---

### 24. ~~test_registry_connection~~ ❌ *(REMOVED - Use registry://status/{name} resource)*

**Replaced by:** `registry://status/{name}` resource

Test connection to a specific registry and return comprehensive information including metadata.

**Migration:** Use the `registry://status/{name}` resource instead of this tool for better performance.

**Claude Desktop Usage:**
```
Human: "Test the connection to the staging registry"

Claude: I'll test the connection to the staging registry.

[Uses registry://status/staging resource]
✅ Staging Registry Status:
   URL: https://staging.schema-registry.com
   Status: Connected (85ms)
   Health: All systems operational
   Last Check: 2024-01-15T10:30:00Z
```
{
    "status": "connected",
    "url": "http://localhost:8081",
    "response_time_ms": 45.2,
    "registry_mode": "single",
    "version": "7.6.0",
    "commit_id": "02d9aa023a8d034d480a718242df2a880e0be1f7",
    "kafka_cluster_id": "MkVlNjdqWVF0Q056MWFrUA",
    "schema_registry_cluster_id": "schema-registry",
    "scope": {
        "path": [],
        "clusters": {
            "kafka-cluster": "MkVlNjdqWVF0Q056MWFrUA",
            "schema-registry-cluster": "schema-registry"
        }
    }
}
```

**Example Usage:**
```bash
[Uses test_registry_connection MCP tool]
```

---

### 25. ~~test_all_registries~~ ❌ *(REMOVED - Use registry://status resource)*

**Replaced by:** `registry://status` resource

Test connections to all configured registries with comprehensive metadata.

**Migration:** Use the `registry://status` resource instead of this tool for better performance.

**Claude Desktop Usage:**
```
Human: "Test connections to all registries"

Claude: I'll test connections to all configured registries.

[Uses registry://status resource]
✅ Registry Connection Status:
   • production: Connected (120ms)
   • staging: Connected (85ms)  
   • development: Connection failed
   • testing: Connected (95ms)
   Summary: 3/4 registries connected
```

---

### 26. set_default_registry ✅ *(Available in SLIM_MODE - Single-Registry Mode Only)*

Set the default registry for operations.

**Purpose**: Change the active registry for subsequent operations.

**Availability**: 
- ✅ Available in SLIM_MODE when using single-registry configuration
- ❌ Not available in SLIM_MODE when using multi-registry configuration
- ✅ Always available in full mode

**Parameters:**
- `registry_name` (string): Registry name to set as default

---

### 27. get_default_registry ✅ *(Available in SLIM_MODE)*

Get the current default registry.

**Purpose**: Check which registry is currently active.

**Parameters:** None

---

## 🚀 Migration Tools ❌ *(ALL NOT in SLIM_MODE)*

All migration tools are excluded from SLIM_MODE as they are heavy, long-running operations:

### 28. migrate_schema ❌

Migrate a schema from one registry to another. Returns task ID for async operation.

**Purpose**: Schema promotion, environment synchronization, registry migration.

**Note**: Migration operations require full mode. These are complex, potentially long-running operations that benefit from full task management support.

---

### 29. migrate_context ❌

Generate ready-to-run Docker commands for migrating an entire context using the [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator) tool.

**Purpose**: Generate Docker commands for bulk schema migration, environment promotion, disaster recovery.

**Note**: Migration operations require full mode.

---

### 30. list_migrations ❌

Show migration history.

**Purpose**: Track migration operations, audit changes, view history.

**Note**: Migration operations require full mode.

---

### 31. get_migration_status ❌

Check migration progress.

**Purpose**: Monitor ongoing migrations, get detailed status, troubleshoot issues.

**Note**: Migration operations require full mode.

---

## 🧹 Batch Cleanup Tools ❌ *(ALL NOT in SLIM_MODE)*

Batch operations are excluded from SLIM_MODE:

### 32. clear_context_batch ❌

Efficiently remove all subjects from a context. Returns task ID for async operation.

**Purpose**: Clean up test environments, remove feature branches, reset contexts.

**Note**: These destructive batch operations require full mode for safety and proper task tracking.

---

### 33. clear_multiple_contexts_batch ❌

Clean multiple contexts in batch mode. Returns task ID for async operation.

**Purpose**: Bulk environment cleanup, multi-context reset, test cleanup.

**Note**: These destructive batch operations require full mode for safety and proper task tracking.

---

## 📊 Task Management & Progress Tracking Tools ❌ *(ALL NOT in SLIM_MODE)*

All task management tools are excluded from SLIM_MODE as they're primarily used with heavy operations:

### 34. get_task_progress ❌
### 35. get_migration_progress ❌
### 36. get_cleanup_progress ❌
### 37. get_comparison_progress ❌
### 38. list_all_active_tasks ❌
### 39. list_migration_tasks ❌
### 40. list_cleanup_tasks ❌
### 41. list_comparison_tasks ❌
### 42. cancel_task ❌
### 43. get_operation_info_tool ❌
### 44. watch_task_progress ❌

**Note**: Task management is not needed in SLIM_MODE since all included operations are synchronous and lightweight.

---

## Schema Statistics and Counting Tools

The following tools provide comprehensive statistics and counting capabilities for Schema Registry instances.

### Count Contexts ✅ *(Available in SLIM_MODE)*
```python
@mcp.tool()
def count_contexts(registry: Optional[str] = None) -> Dict[str, Any]:
    """Count the number of contexts in a registry.
    
    Args:
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - total_contexts: Total number of contexts
        - contexts: List of context names
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count contexts in default registry
result = count_contexts()
print(f"Found {result['total_contexts']} contexts: {result['contexts']}")

# Count contexts in specific registry
result = count_contexts(registry="production")
print(f"Found {result['total_contexts']} contexts in production")
```

### Count Schemas ✅ *(Available in SLIM_MODE)*
```python
@mcp.tool()
def count_schemas(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """Count the number of schemas in a context or registry.
    
    Args:
        context: Optional context name. If not provided, counts all contexts.
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - context: Context name (if specified)
        - total_schemas: Total number of schemas
        - schemas: List of schema names
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count all schemas in default registry
result = count_schemas()
print(f"Found {result['total_schemas']} schemas")

# Count schemas in specific context
result = count_schemas(context="production")
print(f"Found {result['total_schemas']} schemas in production context")

# Count schemas in specific registry and context
result = count_schemas(context="staging", registry="development")
print(f"Found {result['total_schemas']} schemas in staging context of development registry")
```

### Count Schema Versions ✅ *(Available in SLIM_MODE)*
```python
@mcp.tool()
def count_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """Count the number of versions for a specific schema.
    
    Args:
        subject: Schema subject name
        context: Optional context name. If not provided, uses default context.
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - context: Context name
        - subject: Schema subject name
        - total_versions: Total number of versions
        - versions: List of version numbers
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count versions of a schema in default context
result = count_schema_versions(subject="user-value")
print(f"Found {result['total_versions']} versions of user-value schema")

# Count versions in specific context
result = count_schema_versions(subject="order-value", context="production")
print(f"Found {result['total_versions']} versions in production context")

# Count versions in specific registry and context
result = count_schema_versions(
    subject="payment-value",
    context="staging",
    registry="development"
)
print(f"Found {result['total_versions']} versions in staging context of development registry")
```

### Get Registry Statistics ❌ *(NOT in SLIM_MODE)*
```python
@mcp.tool()
def get_registry_statistics(
    registry: Optional[str] = None,
    include_context_details: bool = True
) -> Dict[str, Any]:
    """Get comprehensive statistics about a registry.
    
    Args:
        registry: Optional registry name. If not provided, uses default registry.
        include_context_details: Whether to include detailed context information.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - total_contexts: Total number of contexts
        - total_schemas: Total number of schemas
        - total_versions: Total number of schema versions
        - avg_versions_per_schema: Average versions per schema
        - contexts: Optional detailed context information
        - timestamp: Current timestamp
    """
```

**Note**: This heavy statistics operation with potential async processing is excluded from SLIM_MODE. Use the individual counting tools instead.

Example usage:
```python
# Get basic statistics
result = get_registry_statistics(include_context_details=False)
print(f"Registry has {result['total_contexts']} contexts")
print(f"Total schemas: {result['total_schemas']}")
print(f"Total versions: {result['total_versions']}")
print(f"Average versions per schema: {result['avg_versions_per_schema']:.2f}")

# Get detailed statistics with context information
result = get_registry_statistics(include_context_details=True)
for context in result['contexts']:
    print(f"\nContext: {context['name']}")
    print(f"Schemas: {context['total_schemas']}")
    print(f"Versions: {context['total_versions']}")
```

### Error Handling
All counting tools handle errors gracefully and return appropriate error messages:

```python
# Example error response
{
    "error": "Registry not found: production",
    "timestamp": "2024-03-14T12:34:56Z"
}
```

Common error scenarios:
- Registry not found
- Context not found
- Schema subject not found
- Connection errors
- Authentication failures

### Best Practices
1. Use `get_registry_statistics` for comprehensive overview (when not in SLIM_MODE)
2. Use specific counting tools for targeted information
3. Include context names for precise counting
4. Handle potential errors in responses
5. Use timestamps for tracking data freshness

---

## 💡 SLIM_MODE Usage Tips

### **Effective SLIM_MODE Usage:**
- ✅ **Read Operations**: Perfect for viewing schemas and checking compatibility
- ✅ **Basic Registration**: Can still register new schemas when needed
- ✅ **Multi-Registry**: Full support for multiple registry management
- ✅ **Production Safety**: Combines well with VIEWONLY mode

### **When to Switch to Full Mode:**
- ❌ **Migrations**: Use full mode for schema/context migrations
- ❌ **Bulk Operations**: Use full mode for batch cleanup
- ❌ **Export/Import**: Use full mode for comprehensive exports
- ❌ **Configuration Changes**: Use full mode to update settings

### **Switching Modes:**
```bash
# Enable SLIM_MODE
export SLIM_MODE=true

# Disable SLIM_MODE (full mode)
export SLIM_MODE=false

# Check current mode
echo $SLIM_MODE
```

---

This MCP Tools Reference enables natural language schema management through Claude Desktop, eliminating the need for complex API calls and technical syntax. The 48 comprehensive tools provide complete control over schema lifecycle, evolution, and governance through intuitive conversation, with optional VIEWONLY mode for production safety and SLIM_MODE for optimized performance.