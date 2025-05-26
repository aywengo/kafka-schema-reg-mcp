# MCP Tools Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server v1.4.0 **MCP Tools**, including all 20 tools and their usage with Claude Desktop.

## 🤖 MCP Integration Overview

The Kafka Schema Registry MCP Server provides **20 comprehensive MCP tools** that enable natural language interaction with Kafka Schema Registry through Claude Desktop and other MCP clients.

### **Key Features:**
- ✅ **Natural Language Interface**: Interact using plain English commands
- ✅ **Claude Desktop Integration**: Seamless AI-assisted schema management  
- ✅ **20 MCP Tools**: Complete schema operations without API knowledge
- ✅ **Context-Aware Operations**: All tools support schema contexts
- ✅ **Real-time Feedback**: Immediate results and validation
- ✅ **Production Safety**: READONLY mode blocks modifications in production

### **Tool Categories:**
- **Schema Management** (4 tools): register, retrieve, versions, compatibility
- **Context Management** (3 tools): list, create, delete contexts
- **Subject Management** (2 tools): list, delete subjects
- **Configuration Management** (4 tools): global and subject-specific settings
- **Mode Management** (4 tools): operational mode control
- **Export Tools** (4 tools): comprehensive schema export capabilities

---

## 🔧 Schema Management Tools

### 1. register_schema

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

### 2. get_schema

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

### 3. get_schema_versions

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

### 4. check_compatibility

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

### 5. list_contexts

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

### 6. create_context

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

### 7. delete_context

Delete a schema context.

**Purpose**: Clean up temporary environments, remove unused contexts.

**Parameters:**
- `context` (string): Context name to delete

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

### 8. list_subjects

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

### 9. delete_subject

Delete a subject and all its versions.

**Purpose**: Remove deprecated schemas, clean up test subjects.

**Parameters:**
- `subject` (string): Subject name to delete
- `context` (string, optional): Schema context

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

### 10. get_global_config

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

### 11. update_global_config

Update global configuration settings.

**Purpose**: Change compatibility requirements, enforce policies.

**Parameters:**
- `compatibility` (string): Compatibility level (BACKWARD, FORWARD, FULL, NONE)
- `context` (string, optional): Schema context

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

### 12. get_subject_config

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

### 13. update_subject_config

Update configuration for a specific subject.

**Purpose**: Override global settings for specific schemas, apply custom policies.

**Parameters:**
- `subject` (string): The subject name
- `compatibility` (string): Compatibility level
- `context` (string, optional): Schema context

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

### 14. get_mode

Get the current operational mode.

**Purpose**: Check if schema registration is enabled, understand operational state.

**Parameters:**
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the current operational mode of the schema registry?"

Claude: I'll check the current operational mode.

[Uses get_mode MCP tool]
🎛️ Current mode: READWRITE
   Status: Normal operations - registration and reads enabled
   Context: Global setting
```

---

### 15. update_mode

Update the operational mode.

**Purpose**: Control schema registration during maintenance, enable read-only modes.

**Parameters:**
- `mode` (string): Mode to set (READWRITE, READONLY, IMPORT)
- `context` (string, optional): Schema context

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

### 16. get_subject_mode

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

### 17. update_subject_mode

Update the mode for a specific subject.

**Purpose**: Restrict specific schemas during migrations, enable subject-level controls.

**Parameters:**
- `subject` (string): The subject name
- `mode` (string): Mode to set
- `context` (string, optional): Schema context

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

## 📤 Export Tools

### 18. export_schema

Export a single schema in specified format.

**Purpose**: Generate documentation, backup specific schemas, create readable formats.

**Parameters:**
- `subject` (string): The subject name
- `version` (string, optional): Schema version (default: "latest")
- `context` (string, optional): Schema context
- `format` (string, optional): Export format ("json" or "avro_idl")

**Claude Desktop Usage:**
```
Human: "Export the user-events schema as Avro IDL for our documentation"

Claude: I'll export the user-events schema in human-readable Avro IDL format.

[Uses export_schema MCP tool]
📤 Exported user-events as Avro IDL:

@namespace("com.company.events")
/** User activity tracking schema */
record UserEvent {
  /** Unique user identifier */
  string userId;
  /** Type of activity performed */
  string eventType;
  /** Event timestamp in milliseconds */
  long timestamp;
  /** Optional event metadata */
  map<string> metadata = {};
}
```

---

### 19. export_subject

Export all versions of a subject.

**Purpose**: Complete subject backup, version history analysis, migration preparation.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include subject configuration
- `include_versions` (string, optional): Which versions ("all" or "latest")

**Claude Desktop Usage:**
```
Human: "Export the complete history of the order-events schema including all metadata"

Claude: I'll export all versions and metadata for order-events.

[Uses export_subject MCP tool]
📦 Exported order-events subject:
   Versions: 5 versions (v1 through v5)
   Metadata: Registration dates, compatibility levels, evolution notes
   Configuration: FULL compatibility override
   Size: Complete evolution history from 2024-01-15 to present
```

---

### 20. export_context

Export all subjects within a context.

**Purpose**: Environment backup, context migration, compliance reporting.

**Parameters:**
- `context` (string): The context name
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include configuration data
- `include_versions` (string, optional): Which versions to include

**Claude Desktop Usage:**
```
Human: "Export the entire production context for our quarterly backup"

Claude: I'll create a comprehensive backup of the production context.

[Uses export_context MCP tool]
📦 Exported production context:
   Subjects: 15 schemas exported
   Versions: All historical versions included
   Configuration: Global and subject-specific settings
   Metadata: Complete audit trail and timestamps
   Ready for: Backup storage and compliance reporting
```

---

### 21. export_global

Export all contexts and schemas from the registry.

**Purpose**: Complete registry backup, disaster recovery, migration to new registry.

**Parameters:**
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include configuration data
- `include_versions` (string, optional): Which versions to include

**Claude Desktop Usage:**
```
Human: "Create a complete backup of our entire schema registry"

Claude: I'll create a comprehensive backup of the entire registry.

[Uses export_global MCP tool]
📦 Global registry export:
   Contexts: 6 contexts exported
   Subjects: 47 total schemas
   Versions: 156 schema versions
   Configuration: All compatibility and mode settings
   Size: Complete registry state for disaster recovery
   Format: Structured JSON with organized metadata
```

---

## 📊 MCP Resources

In addition to tools, the MCP server provides **2 resources** for real-time information:

### registry://status
Get current Schema Registry connection status and health information.

### registry://info  
Get detailed Schema Registry configuration, capabilities, and server information.

**Usage in Claude Desktop:**
```
Human: "Check the status of our Schema Registry connection"

Claude: I'll check the Schema Registry status for you.

[Uses registry://status resource]
✅ Schema Registry Status: Connected
   URL: http://localhost:8081
   Response Time: 45ms
   Health: All systems operational
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

## 🔒 READONLY Mode (Production Safety)

The MCP server includes a **production safety feature** that can be enabled by setting the `READONLY=true` environment variable. When enabled, all modification operations are blocked while read and export operations remain fully functional.

### **Environment Setup**
```bash
# Enable READONLY mode for production safety
export READONLY=true

# Or in Docker/Claude Desktop
"env": {
  "READONLY": "true",
  "SCHEMA_REGISTRY_URL": "http://localhost:8081"
}
```

### **Blocked Operations in READONLY Mode**
When READONLY mode is enabled, the following tools will return an error:
- 🚫 `register_schema` - Cannot register new schemas
- 🚫 `create_context` / `delete_context` - Cannot modify contexts
- 🚫 `delete_subject` - Cannot delete subjects
- 🚫 `update_global_config` / `update_subject_config` - Cannot modify configuration
- 🚫 `update_mode` / `update_subject_mode` - Cannot change operational modes

### **Allowed Operations in READONLY Mode**
These tools continue to work normally:
- ✅ All `get_*` tools - Read schema information and configuration
- ✅ All `list_*` tools - Browse available schemas and contexts
- ✅ `check_compatibility` - Test schema compatibility (no modifications)
- ✅ All `export_*` tools - Generate backups and documentation

### **Claude Desktop Usage in READONLY Mode**
```
Human: "Register a new user schema with id and name fields"

Claude: I attempted to register the schema, but the operation was blocked because the MCP server is running in READONLY mode for production safety. 

Error: Operation blocked: MCP server is running in READONLY mode. Set READONLY=false to enable modification operations.

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

---

This MCP Tools Reference enables natural language schema management through Claude Desktop, eliminating the need for complex API calls and technical syntax. The 20 comprehensive tools provide complete control over schema lifecycle, evolution, and governance through intuitive conversation, with optional READONLY mode for production safety. 