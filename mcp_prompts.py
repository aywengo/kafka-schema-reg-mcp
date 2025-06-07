#!/usr/bin/env python3
"""
MCP Prompts for Kafka Schema Registry

This module contains all predefined prompts that help users interact with
Claude Desktop for schema management tasks. Prompts provide guided workflows,
examples, and best practices.
"""

def get_schema_getting_started_prompt():
    """Getting started with Schema Registry operations"""
    return """# Getting Started with Schema Registry Guide

This guide will help you get started with essential schema operations. Here are some common tasks:

## 📋 Basic Operations
1. **List all schemas**: "List all schema contexts and subjects"
2. **Register a schema**: "Register a new user schema with fields for id, name, and email"
3. **Get schema details**: "Show me the latest version of the user schema"
4. **Check compatibility**: "Check if adding an 'age' field to user schema is backward compatible"

## 🏗️ Context Management
- **Create contexts**: "Create development and production contexts"
- **List context schemas**: "Show all schemas in the development context"
- **Context isolation**: "Create a GDPR context for compliance schemas"

## 📊 Configuration & Monitoring
- **Check status**: "Test all registry connections"
- **View configuration**: "Show the global compatibility configuration"
- **Export for backup**: "Export all schemas from production context"

What would you like to do first?"""

def get_schema_registration_prompt():
    """Guide for registering new schemas"""
    return """# Schema Registration Guide

I'll help you register a new schema. Here's what you need to know:

## 🎯 Quick Registration
**Basic command**: "Register a [entity] schema with fields [field1], [field2], [field3]"

**Example**: "Register a user schema with fields id (int), name (string), and email (optional string)"

## 📝 Schema Types Supported
- **AVRO** (default): Most common, supports evolution
- **JSON**: Simple structure validation
- **PROTOBUF**: Protocol buffer schemas

## 🏗️ Context-Aware Registration
**With context**: "Register a user schema in the development context"
**Multi-registry**: "Register the order schema in the production registry"

## ⚙️ Advanced Options
- **Compatibility checking**: I'll automatically check compatibility before registration
- **Version control**: Each registration creates a new version
- **Validation**: Schema structure is validated before registration

## 📋 Common Schema Examples
1. **User schema**: id, name, email, created_at
2. **Order schema**: order_id, customer_id, amount, status, timestamp
3. **Event schema**: event_id, event_type, timestamp, payload

What type of schema would you like to register?"""

def get_context_management_prompt():
    """Guide for managing schema contexts"""
    return """# Schema Context Management

Contexts help organize schemas by environment, team, or purpose. Let me help you manage them:

## 🚀 Getting Started with Contexts
**List existing**: "List all schema contexts"
**Create new**: "Create a [environment] context" (e.g., development, production, staging)

## 🏢 Common Context Patterns
1. **By Environment**:
   - development → Testing and iteration
   - staging → Pre-production validation  
   - production → Live schemas

2. **By Team/Domain**:
   - user-service → User-related schemas
   - order-service → Order processing schemas
   - analytics → Analytics and reporting schemas

3. **By Compliance**:
   - gdpr → GDPR-compliant schemas
   - pci → Payment-related schemas
   - public → Public API schemas

## 🔧 Context Operations
- **View schemas**: "Show all schemas in the [context] context"
- **Register in context**: "Register [schema] in the [context] context"
- **Export context**: "Export all schemas from [context] for backup"
- **Clean up**: "Delete empty contexts that are no longer needed"

## 🔄 Schema Promotion Workflow
1. **Develop**: Register schema in development context
2. **Test**: Check compatibility with staging
3. **Promote**: Move to production context
4. **Monitor**: Export for documentation and compliance

Which context operation would you like to perform?"""

def get_schema_export_prompt():
    """Guide for exporting schemas and documentation"""
    return """# Schema Export & Documentation

I can help you export schemas for backup, documentation, migration, or compliance:

## 📋 Export Options

### 🎯 Single Schema Export
**JSON format**: "Export the user schema as JSON"
**Avro IDL**: "Export the user schema as Avro IDL for documentation"
**Specific version**: "Export version 2 of the user schema"

### 📚 Subject Export (All Versions)
**Complete history**: "Export all versions of the user schema"
**With metadata**: "Export user schema with configuration and metadata"

### 🏗️ Context Export
**Environment backup**: "Export all schemas from production context"
**Team schemas**: "Export all user-service schemas"
**Compliance report**: "Export all GDPR schemas with full metadata"

### 🌐 Global Export
**Complete backup**: "Export all schemas from the registry"
**Multi-registry**: "Export all schemas from the development registry"

## 📊 Export Formats
- **JSON**: Machine-readable, easy to parse
- **Avro IDL**: Human-readable, great for documentation
- **Bundle**: ZIP format with all metadata

## 🎯 Common Use Cases
1. **Documentation**: "Generate human-readable documentation for all user schemas"
2. **Backup**: "Create a complete backup of production schemas"
3. **Migration**: "Export development schemas for promotion to production"
4. **Compliance**: "Generate audit report of all schemas with metadata"
5. **Code Generation**: "Export order schema as Avro IDL for Java client generation"

## 📝 Export Features
- **Metadata included**: Version history, compatibility settings, timestamps
- **Configuration included**: Compatibility levels, mode settings
- **Structured output**: Ready for documentation tools or migration

What would you like to export?"""

def get_multi_registry_prompt():
    """Guide for multi-registry operations"""
    return """# Multi-Registry Management

I can help you manage multiple Schema Registry instances for different environments:

## 🌐 Multi-Registry Overview
**List registries**: "Show me all available Schema Registry instances"
**Test connections**: "Test connections to all registries"
**Registry status**: "Check the health of all registry connections"

## 🔄 Cross-Registry Operations

### 📊 Comparison
**Compare all**: "Compare development and production registries"
**Find differences**: "Find schemas in development that are missing in production"
**Context comparison**: "Compare user-service context between dev and prod"

### 🚚 Migration
**Single schema**: "Migrate user schema from development to production"
**Context migration**: "Migrate all analytics schemas from staging to production"
**Bulk migration**: "Generate Docker configuration for migrating development context"

### 🔍 Discovery
**Schema inventory**: "List all schemas across all registries"
**Missing schemas**: "Find schemas that exist in dev but not in production"
**Version differences**: "Compare schema versions between registries"

## 🏗️ Environment Patterns
1. **Development → Staging → Production**: Standard promotion pipeline
2. **Regional deployments**: US-East, US-West, EU registries
3. **Team isolation**: Separate registries per team or service
4. **Disaster recovery**: Primary and backup registries

## ⚙️ Registry Configuration
- **Default registry**: "Set production as the default registry"
- **READONLY mode**: Some registries may be read-only for safety
- **Authentication**: Each registry can have different credentials

## 🚀 Workflow Examples
1. **Schema promotion**: Develop → Test → Deploy across environments
2. **Disaster recovery**: Compare and sync between primary and backup
3. **Multi-region**: Sync schemas across geographical deployments
4. **Team coordination**: Compare team registries before merging

Which multi-registry operation would you like to perform?"""

def get_schema_compatibility_prompt():
    """Guide for schema compatibility and evolution"""
    return """# Schema Compatibility & Evolution Guide

I'll help you understand and manage schema compatibility for safe evolution:

## 🔍 Compatibility Basics
**Check compatibility**: "Check if adding a field to user schema is backward compatible"
**View settings**: "Show the compatibility configuration for user schema"
**Global settings**: "Show the global compatibility configuration"

## 📊 Compatibility Levels
1. **BACKWARD** (default): New schema can read old data
2. **FORWARD**: Old schema can read new data  
3. **FULL**: Both backward and forward compatible
4. **NONE**: No compatibility checking

## ✅ Safe Schema Changes
### Backward Compatible:
- Add optional fields (with defaults)
- Remove fields
- Add enum values
- Widen field types (int → long)

### Forward Compatible:
- Remove optional fields
- Add fields
- Remove enum values
- Narrow field types (long → int)

## ⚠️ Breaking Changes
- Change field names
- Change field types (incompatibly)
- Remove required fields
- Change record names

## 🛠️ Configuration Management
**Set global**: "Set global compatibility to FULL for maximum safety"
**Subject-specific**: "Set user schema to BACKWARD compatibility"
**Context-specific**: "Configure production context for FULL compatibility"

## 🔄 Evolution Workflow
1. **Design change**: Plan your schema modification
2. **Check compatibility**: "Check if my updated user schema is compatible"
3. **Test in development**: Register in dev context first
4. **Validate**: Ensure existing consumers continue working
5. **Promote**: Move to production after validation

## 📋 Common Evolution Scenarios
1. **Add user preference**: "Check if adding 'preferences' field to user schema is safe"
2. **Deprecate field**: "How do I safely remove the 'deprecated_field' from order schema?"
3. **Type migration**: "Can I change user ID from int to string safely?"
4. **Enum expansion**: "Is it safe to add new status values to order schema?"

## 🎯 Best Practices
- Always check compatibility before registration
- Use optional fields with defaults for new additions
- Plan breaking changes with version coordination
- Test schema changes in development first

What compatibility question can I help you with?"""

def get_troubleshooting_prompt():
    """Troubleshooting guide for common issues"""
    return """# Schema Registry Troubleshooting

This advanced troubleshooting guide helps you diagnose and resolve complex Schema Registry issues:

## 🔍 Quick Diagnostics
**Health check**: "Test all registry connections"
**Status overview**: "Show me the current registry status"
**Configuration check**: "Display the current registry configuration"

## 🚨 Common Issues & Solutions

### 🔌 Connection Problems
**Symptoms**: Registry unreachable, timeout errors
**Diagnosis**: "Test connection to [registry]"
**Solutions**:
- Check registry URL and network connectivity
- Verify authentication credentials
- Check firewall and security group settings

### 📋 Schema Registration Failures
**Symptoms**: "Schema registration failed" errors
**Diagnosis**: "Check compatibility of [subject] schema"
**Solutions**:
- Verify schema syntax (valid JSON/Avro)
- Check compatibility with existing versions
- Ensure proper permissions (write scope)

### 🔄 Compatibility Errors
**Symptoms**: "Schema incompatible" messages
**Diagnosis**: "Show compatibility configuration for [subject]"
**Solutions**:
- Review compatibility level settings
- Check what changes are causing conflicts
- Consider schema evolution strategy

### 🏗️ Context Issues
**Symptoms**: Schemas not found, wrong context
**Diagnosis**: "List all contexts" and "Show schemas in [context]"
**Solutions**:
- Verify context names and spelling
- Check if schema exists in different context
- Ensure context was created properly

### 🌐 Multi-Registry Problems
**Symptoms**: Registry not found, wrong target
**Diagnosis**: "List all registries" and "Test registry connections"
**Solutions**:
- Verify registry configuration
- Check default registry settings
- Confirm registry names match configuration

## 🛠️ Diagnostic Commands
1. **System health**: "Test all registries and show their status"
2. **Schema audit**: "List all schemas and their versions"
3. **Configuration review**: "Show all compatibility settings"
4. **Context inventory**: "List all contexts with schema counts"
5. **Task monitoring**: "Show all active tasks and their progress"

## 📊 Performance Issues
**Symptoms**: Slow operations, timeouts
**Diagnosis**: "Show active tasks and their progress"
**Solutions**:
- Monitor long-running operations
- Use async task monitoring for bulk operations
- Check registry resource usage

## 🔐 Permission Issues
**Symptoms**: "Access denied", "Insufficient permissions"
**Diagnosis**: "Show OAuth scopes and current permissions"
**Solutions**:
- Verify required scopes (read, write, admin)
- Check authentication configuration
- Review READONLY mode settings

## 📝 Data Issues
**Symptoms**: Missing schemas, unexpected versions
**Diagnosis**: "Export [subject] with full metadata"
**Solutions**:
- Check schema history and versions
- Verify context and registry locations
- Compare with expected schema structure

## 🆘 Getting Help
If you're still having issues:
1. **Export diagnostics**: "Generate a complete system status report"
2. **Check logs**: Review server logs for detailed error messages
3. **Test minimal case**: Try with a simple schema first
4. **Environment validation**: Ensure all components are properly configured

What issue are you experiencing? I'll help you diagnose and resolve it."""

def get_advanced_workflows_prompt():
    """Guide for complex Schema Registry workflows"""
    return """# Advanced Schema Registry Workflows

I can help you implement sophisticated schema management workflows:

## 🚀 CI/CD Integration Workflows

### 📋 Schema Validation Pipeline
1. **Development**: "Register schema in development context"
2. **Validation**: "Check compatibility before promotion"
3. **Testing**: "Export schemas for integration testing"
4. **Promotion**: "Migrate schemas from dev to staging"
5. **Production**: "Deploy to production with safety checks"

### 🔄 Automated Promotion
**Command sequence**:
- "Check if user schema in development is compatible with staging"
- "If compatible, migrate user schema from development to staging"
- "Export staging schemas for production readiness review"

## 🏢 Enterprise Governance Workflows

### 📊 Compliance Auditing
1. **Inventory**: "Generate complete schema inventory across all registries"
2. **Classification**: "Export all GDPR-related schemas with metadata"
3. **Validation**: "Check all schemas meet compliance requirements"
4. **Reporting**: "Generate audit report with version history"

### 🔐 Access Control & Safety
**Production protection**:
- "Set production registry to READONLY mode during maintenance"
- "Configure production context with FULL compatibility requirement"
- "Monitor all schema changes with task tracking"

## 🌐 Multi-Environment Orchestration

### 🔄 Environment Synchronization
**Regional deployment**:
- "Compare US-East and US-West registries for schema drift"
- "Find schemas missing in backup registry"
- "Generate migration plan for disaster recovery"

### 🚚 Bulk Operations
**Context migration**:
- "Generate Docker configuration for migrating user-service context"
- "Batch cleanup of deprecated contexts"
- "Bulk export of all development schemas"

## 📈 Monitoring & Analytics Workflows

### 📊 Schema Analytics
1. **Usage tracking**: "Count schemas per context across all registries"
2. **Growth monitoring**: "Show schema version growth over time"
3. **Health monitoring**: "Test all registry connections and report status"
4. **Performance tracking**: "Monitor long-running operations with task queue"

### 🔍 Drift Detection
**Continuous monitoring**:
- "Compare development and production registries weekly"
- "Alert on schema incompatibilities"
- "Track schema evolution patterns"

## 🛠️ Development Team Workflows

### 👥 Team Collaboration
**Feature development**:
1. **Branch schemas**: "Create feature-branch context for schema experimentation"
2. **Collaboration**: "Export schemas for team review and feedback"
3. **Integration**: "Merge compatible schemas back to main development"
4. **Documentation**: "Generate human-readable schema documentation"

### 🧪 Testing & Validation
**Schema testing pipeline**:
- "Register test schemas in isolated context"
- "Validate against existing consumer contracts"
- "Check backward compatibility with production"
- "Clean up test contexts after validation"

## 🎯 Performance Optimization Workflows

### ⚡ Async Operations
**Large-scale operations**:
- "Start background task for complete registry statistics"
- "Monitor progress of context migration"
- "Cancel long-running operations if needed"

### 📦 Batch Processing
**Efficient bulk operations**:
- "Process multiple contexts in parallel"
- "Batch export with progress monitoring"
- "Optimize large-scale comparisons"

## 🚦 Workflow Orchestration Examples

### 📋 Complete Release Workflow
```
1. "Create release-v2.1 context for new feature schemas"
2. "Register updated schemas in release context"
3. "Check compatibility with current production schemas"
4. "Export release schemas for integration testing"
5. "Migrate compatible schemas to staging"
6. "Validate in staging environment"
7. "Promote to production with safety checks"
8. "Archive release context after successful deployment"
```

### 🔄 Disaster Recovery Workflow
```
1. "Test connection to backup registry"
2. "Compare primary and backup registries"
3. "Find missing schemas in backup"
4. "Generate migration plan for complete sync"
5. "Execute migration with progress monitoring"
6. "Validate backup registry completeness"
```

Which advanced workflow would you like to implement?"""

# Prompt registry mapping prompt names to their functions
PROMPT_REGISTRY = {
    "schema-getting-started": get_schema_getting_started_prompt,
    "schema-registration": get_schema_registration_prompt,
    "context-management": get_context_management_prompt,
    "schema-export": get_schema_export_prompt,
    "multi-registry": get_multi_registry_prompt,
    "schema-compatibility": get_schema_compatibility_prompt,
    "troubleshooting": get_troubleshooting_prompt,
    "advanced-workflows": get_advanced_workflows_prompt,
}

def get_all_prompt_names():
    """Get list of all available prompt names."""
    return list(PROMPT_REGISTRY.keys())

def get_prompt_content(prompt_name: str):
    """Get the content for a specific prompt."""
    if prompt_name in PROMPT_REGISTRY:
        return PROMPT_REGISTRY[prompt_name]()
    else:
        return f"Prompt '{prompt_name}' not found. Available prompts: {', '.join(get_all_prompt_names())}"

def get_prompt_summary():
    """Get a summary of all available prompts."""
    return {
        "total_prompts": len(PROMPT_REGISTRY),
        "available_prompts": get_all_prompt_names(),
        "categories": {
            "getting_started": ["schema-getting-started"],
            "basic_operations": ["schema-registration", "context-management"],
            "advanced_features": ["schema-export", "multi-registry", "schema-compatibility"],
            "support": ["troubleshooting", "advanced-workflows"]
        }
    } 