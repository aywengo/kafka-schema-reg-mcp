#!/usr/bin/env python3
"""
MCP Prompts for Kafka Schema Registry

This module contains all predefined prompts that help users interact with
Claude Desktop for schema management tasks. Prompts provide guided workflows,
examples, and best practices.
"""


def get_schema_getting_started_prompt():
    """Getting started with Schema Registry operations"""
    return """# Getting Started with Schema Registry 🚀

## Quick Actions

### Essential Commands (Copy & Use)
```
"List all schema contexts"
"Show all schemas in production"
"Test all registry connections"
"Register a user schema with id, name, email fields"
"Export all schemas for backup"
```

## 🎯 First Steps

### 1. Check Your Environment
- **Command**: `"Test all registry connections"`
- **Why**: Ensures everything is connected properly

### 2. Explore What You Have
- **Command**: `"List all schema contexts and subjects"`
- **Why**: See your current schema landscape

### 3. Try a Simple Registration
- **Command**: `"Register a test schema with id and name fields in development"`
- **Why**: Verify write permissions and understand the flow

## 📋 Common Tasks

| Task | Command Example |
|------|----------------|
| View schemas | `"Show all schemas in development context"` |
| Register schema | `"Register user schema with id, name, email"` |
| Check compatibility | `"Is adding age field to user schema safe?"` |
| Export for backup | `"Export production schemas as JSON"` |
| Compare environments | `"Compare dev and prod registries"` |

## 💡 Pro Tips
- Start in `development` context for testing
- Always check compatibility before production changes
- Use contexts to organize by environment or team

**Ready?** Try: `"List all schema contexts"` to begin!"""


def get_schema_registration_prompt():
    """Guide for registering new schemas"""
    return """# Schema Registration Guide 📝

## Quick Registration

### 🎯 Copy & Paste Templates

**Basic User Schema:**
```
"Register a user schema with:
- id (long, required)
- name (string, required)
- email (string, optional)
- created_at (timestamp-millis)"
```

**Order Schema:**
```
"Register an order schema with:
- order_id (string)
- customer_id (long)
- amount (double)
- status (enum: PENDING, COMPLETED, CANCELLED)
- items (array of records with product_id, quantity, price)"
```

**Event Schema:**
```
"Register an event schema with:
- event_id (string)
- event_type (string)
- timestamp (long)
- payload (map of strings)"
```

## 🏗️ Advanced Registration

### With Context
```
"Register user schema in production context"
"Register order schema in development registry"
```

### With Namespace
```
"Register com.company.User schema with id and name fields"
```

### Complete Example
```
"Register a Product schema with:
- namespace: com.example.inventory
- fields:
  - sku (string, required)
  - name (string, required)
  - description (string, optional with default '')
  - price (decimal with precision 10,2)
  - in_stock (boolean, default true)
  - categories (array of strings)
in the production context"
```

## ⚡ Schema Types

| Type | When to Use | Example Field |
|------|------------|--------------|
| AVRO (default) | Most cases, supports evolution | All examples above |
| JSON | Simple validation, web APIs | `"Register JSON schema for REST endpoint"` |
| PROTOBUF | gRPC services, binary efficiency | `"Register protobuf User message"` |

## ✅ Validation Features
- Automatic syntax validation
- Compatibility checking
- Duplicate detection
- Field type validation

## 🚨 Common Errors & Solutions

**"Invalid schema"** → Check JSON syntax, missing commas
**"Incompatible schema"** → Add fields as optional with defaults
**"Subject not found"** → Create subject first or check context

**Next step?** Try registering a simple test schema!"""


def get_context_management_prompt():
    """Guide for managing schema contexts"""
    return """# Schema Context Management 🏢

## Quick Context Commands

### 🚀 Essential Operations
```
"List all contexts"
"Create production context"
"Show schemas in development context"
"Delete empty test-context"
```

## 🎯 Context Strategies

### 1. Environment-Based (Recommended)
```
development/   → Active development
staging/       → Pre-production testing
production/    → Live schemas
```
**Create all**: `"Create development, staging, and production contexts"`

### 2. Team-Based
```
user-service/     → User team schemas
order-service/    → Order team schemas
analytics/        → Analytics team schemas
```
**Example**: `"Create user-service context for team isolation"`

### 3. Compliance-Based
```
gdpr/      → GDPR-compliant schemas
pci/       → Payment schemas
public/    → External API schemas
```
**Example**: `"Create gdpr context with description 'GDPR-compliant schemas only'"`

## 📋 Context Operations

| Operation | Command Example |
|-----------|----------------|
| List schemas | `"Show all schemas in production"` |
| Count schemas | `"How many schemas in development?"` |
| Register in context | `"Register user schema in staging context"` |
| Export context | `"Export all production schemas"` |
| Clear context | `"Delete all schemas from test context"` |
| Remove context | `"Delete empty development context"` |

## 🔄 Schema Promotion Flow
```
1. "Register schema in development"
2. "Test and validate"
3. "Check compatibility with staging"
4. "Migrate schema to staging"
5. "After QA, migrate to production"
```

## 💡 Best Practices
- Use consistent naming (lowercase, hyphens)
- Document context purpose
- Regular cleanup of test contexts
- Implement access controls per context

**Start with**: `"Create development and production contexts"`"""


def get_schema_export_prompt():
    """Guide for exporting schemas and documentation"""
    return """# Schema Export & Documentation 📤

## Quick Export Commands

### 🎯 Copy & Use
```
"Export user schema as JSON"
"Export all production schemas"
"Generate documentation for order schema"
"Create backup of entire registry"
```

## 📊 Export Formats

### JSON (Machine-Readable)
```
"Export user schema as JSON"
"Export all development schemas as JSON bundle"
```
**Use for**: Backups, migrations, CI/CD

### Avro IDL (Human-Readable)
```
"Export user schema as Avro IDL"
"Generate readable documentation for all schemas"
```
**Use for**: Documentation, code reviews, wikis

## 🎯 Export Scopes

### Single Schema
```
"Export latest user schema"
"Export version 3 of order schema"
"Export user schema with all metadata"
```

### By Context
```
"Export all production schemas"
"Export development context for backup"
"Export gdpr context with full history"
```

### Global Export
```
"Export entire registry for disaster recovery"
"Create complete backup with all contexts"
"Export all schemas across all registries"
```

## 📋 Common Use Cases

| Purpose | Command |
|---------|---------|
| **Daily Backup** | `"Export all production schemas with metadata"` |
| **Documentation** | `"Generate Avro IDL docs for all public schemas"` |
| **Migration** | `"Export development schemas for promotion"` |
| **Audit** | `"Export all schemas with version history"` |
| **DR Setup** | `"Export complete registry for backup site"` |

## 🚀 Advanced Exports

### With Filters
```
"Export only schemas modified this week"
"Export schemas matching 'user*' pattern"
```

### For Code Generation
```
"Export order schema as Avro IDL for Java generation"
"Export all event schemas for Python client"
```

### Compliance Reports
```
"Export GDPR schemas with metadata and ownership"
"Generate audit report of all schema changes"
```

## 💡 Pro Tips
- Schedule regular exports for backup
- Use IDL format for documentation
- Include metadata for compliance
- Version your exports

**Try now**: `"Export all development schemas as JSON"`"""


def get_multi_registry_prompt():
    """Guide for multi-registry operations"""
    return """# Multi-Registry Management 🌐

## Quick Multi-Registry Commands

### 🎯 Essential Operations
```
"List all registries"
"Test all registry connections"
"Compare dev and prod registries"
"Migrate user schema from dev to prod"
"Set production as default registry"
```

## 🏗️ Registry Setup Examples

### Development Pipeline
```
dev-registry     → Development (read-write)
staging-registry → Staging (read-write)
prod-registry    → Production (VIEWONLY)
```

### Regional Deployment
```
us-east-registry → Primary US East
us-west-registry → US West replica
eu-registry      → European region
```

## 📊 Comparison Operations

### Find Differences
```
"Compare development and production registries"
"Find schemas in dev missing from prod"
"Show version differences for user schema"
```

### Detailed Analysis
```
"Compare user-service context between registries"
"List all schemas unique to development"
"Show configuration differences"
```

## 🚚 Migration Workflows

### Single Schema
```
"Migrate user schema from dev to prod"
"Copy order schema v2 from staging to production"
```

### Bulk Migration
```
"Migrate all analytics schemas to production"
"Copy entire development context to staging"
"Generate migration plan for disaster recovery"
```

### Safe Migration Steps
1. `"Compare source and target registries"`
2. `"Check compatibility in target"`
3. `"Migrate with dry-run first"`
4. `"Verify migration success"`

## 🔧 Registry Management

| Task | Command |
|------|---------|
| Set default | `"Set production as default registry"` |
| Check health | `"Test connection to staging registry"` |
| View config | `"Show production registry configuration"` |
| Count schemas | `"How many schemas in each registry?"` |

## 🎯 Common Scenarios

### Promotion Pipeline
```
1. "Develop in dev-registry"
2. "Test compatibility with staging"
3. "Migrate to staging-registry"
4. "Validate in staging"
5. "Promote to prod-registry"
```

### Disaster Recovery
```
1. "Compare primary and backup registries"
2. "Find missing schemas in backup"
3. "Sync all schemas to backup"
4. "Verify backup completeness"
```

## 💡 Best Practices
- Keep production in VIEWONLY mode
- Regular registry synchronization
- Monitor registry drift
- Document registry purposes

**Start with**: `"List all registries and their status"`"""


def get_schema_compatibility_prompt():
    """Guide for schema compatibility and evolution"""
    return """# Schema Compatibility Guide 🔄

## Quick Compatibility Checks

### 🎯 Common Checks
```
"Is adding email field to user schema safe?"
"Check compatibility before adding age field"
"Can I remove the legacy_field safely?"
"What's the compatibility setting for user schema?"
```

## ✅ Safe Changes (Backward Compatible)

### Always Safe:
- ✅ Add optional field with default
- ✅ Add new enum value
- ✅ Widen types (int → long)
- ✅ Add aliases

### Examples:
```
"Add optional phone field with default empty string"
"Add CANCELLED to order status enum"
"Change user_id from int to long"
```

## ❌ Breaking Changes

### Never Safe Without Coordination:
- ❌ Rename fields
- ❌ Change types incompatibly
- ❌ Remove required fields
- ❌ Change namespace

### Examples That Break:
```
"Rename username to user_name"  ❌
"Change ID from long to string" ❌
"Remove required email field"   ❌
```

## 📊 Compatibility Levels

| Level | What It Means | Use When |
|-------|--------------|----------|
| **BACKWARD** | New schema reads old data | Default, most common |
| **FORWARD** | Old schema reads new data | Careful planning needed |
| **FULL** | Both ways compatible | Maximum safety |
| **NONE** | No checking | Development only |

### Setting Compatibility:
```
"Set user schema to BACKWARD compatibility"
"Set global compatibility to FULL"
"Use NONE compatibility in development context"
```

## 🔄 Evolution Patterns

### Adding a Field Safely:
```
1. "Check current user schema"
2. "Add optional 'preferences' field with default {}"
3. "Check compatibility"
4. "Register if compatible"
```

### Deprecating a Field:
```
1. "Mark field as deprecated in documentation"
2. "Stop writing to field"
3. "Wait for consumers to update"
4. "Remove field in major version"
```

### Type Migration:
```
1. "Add new field with new type"
2. "Write to both fields"
3. "Migrate readers to new field"
4. "Remove old field later"
```

## 🚨 Compatibility Errors

| Error | Solution |
|-------|----------|
| "Field removed" | Add back as optional |
| "Type changed" | Use union types or aliases |
| "Required field added" | Make optional with default |
| "Namespace changed" | Add alias for old namespace |

## 💡 Best Practices
- Always check before registering
- Use optional fields for new additions
- Plan breaking changes carefully
- Test in development first

**Try**: `"Check if adding age field to user schema is safe"`"""


def get_troubleshooting_prompt():
    """Troubleshooting guide for common issues"""
    return """# Troubleshooting Guide 🔧

## Quick Diagnostics

### 🚨 First Steps
```
"Test all registry connections"
"Show current registry status"
"List active tasks"
"Check my permissions"
```

## Common Issues & Solutions

### 🔌 Connection Errors

**Symptoms**: "Connection refused", timeouts
**Quick fixes**:
```
"Test connection to production registry"
"Show registry configuration"
"Check if registry URL is correct"
```

**Solutions**:
- Verify URL includes http:// or https://
- Check network/firewall settings
- Verify credentials if auth enabled

### 📝 Registration Failures

**Symptoms**: "Failed to register schema"
**Quick fixes**:
```
"Validate my schema syntax"
"Check compatibility for user schema"
"Show current compatibility settings"
```

**Common causes**:
- Invalid JSON/Avro syntax (missing comma, quotes)
- Incompatible changes (see compatibility guide)
- Insufficient permissions (need write scope)

### 🏗️ Context/Subject Not Found

**Symptoms**: "Subject not found", "Context does not exist"
**Quick fixes**:
```
"List all contexts"
"Show all subjects in development"
"Create missing context"
```

**Solutions**:
- Check spelling (case-sensitive)
- Verify context exists: `"List all contexts"`
- Create if missing: `"Create development context"`

### 🔐 Permission Denied

**Symptoms**: "Access denied", "Insufficient permissions"
**Quick fixes**:
```
"Check my current permissions"
"Show OAuth scopes"
"Is this registry in VIEWONLY mode?"
```

**Solutions**:
- Verify OAuth scopes (need write for registration)
- Check VIEWONLY mode settings
- Contact admin for permission updates

### ⏱️ Performance Issues

**Symptoms**: Slow operations, timeouts
**Quick fixes**:
```
"Show active tasks"
"List running operations"
"Check registry statistics"
```

**Solutions**:
- Use async operations for bulk tasks
- Monitor with: `"Show task progress"`
- Cancel if needed: `"Cancel task [ID]"`

## 🛠️ Diagnostic Commands

| Issue Type | Diagnostic Command |
|------------|-------------------|
| Connection | `"Test connection to [registry]"` |
| Schema | `"Validate schema syntax"` |
| Compatibility | `"Check why schema is incompatible"` |
| Permissions | `"Show my current permissions"` |
| Performance | `"Show registry statistics"` |

## 📋 Debug Checklist

1. ✓ Registry URL correct and accessible
2. ✓ Credentials valid (if auth enabled)
3. ✓ Schema syntax valid
4. ✓ Compatibility level appropriate
5. ✓ Context/subject names correct
6. ✓ Sufficient permissions
7. ✓ Not in VIEWONLY mode

## 🆘 Still Stuck?

### Generate Full Report:
```
"Generate complete diagnostic report"
"Export system status for debugging"
"Show all error details"
```

### Check Logs:
- Server logs for detailed errors
- Task logs for operation failures
- Network logs for connectivity

**Need help?** Start with: `"Test all registry connections"`"""


def get_advanced_workflows_prompt():
    """Guide for complex Schema Registry workflows"""
    return """# Advanced Workflows 🚀

## CI/CD Integration

### 🔄 Automated Schema Pipeline
```yaml
# Example CI/CD Commands
1. "Register schema in development"
2. "Run compatibility check"
3. "If compatible, tag for staging"
4. "Migrate to staging registry"
5. "After tests, promote to production"
```

### GitHub Actions Example:
```
"Export schema for CI validation"
"Check compatibility via API"
"Migrate if all tests pass"
```

## 🏢 Enterprise Patterns

### Multi-Team Coordination
```
Team A: "Register in team-a context"
Team B: "Register in team-b context"
Platform: "Migrate to shared context after review"
```

### Compliance Workflow
```
1. "Create gdpr-schemas context"
2. "Set strict compatibility rules"
3. "Register with metadata tags"
4. "Export for audit quarterly"
5. "Generate compliance report"
```

## 📊 Monitoring & Analytics

### Schema Metrics Dashboard
```
"Count schemas per context"
"Show schema growth trends"
"List most-versioned schemas"
"Find unused schemas"
"Generate usage statistics"
```

### Health Monitoring
```
"Test all registries hourly"
"Alert on compatibility breaks"
"Monitor schema drift"
"Track registration failures"
```

## 🚀 Performance Optimization

### Bulk Operations
```
# Parallel Processing
"Start async export of all contexts"
"Monitor progress with task ID"
"Process results when complete"

# Batch Registration
"Register 50 schemas from file"
"Track progress in real-time"
"Rollback on any failure"
```

### Caching Strategy
```
"Export frequently-used schemas"
"Cache in local development"
"Refresh cache on changes"
```

## 🔄 Disaster Recovery

### Automated Backup
```bash
# Daily backup script
"Export all production schemas"
"Compress and timestamp"
"Store in backup location"
"Verify backup integrity"
```

### Recovery Process
```
1. "Compare primary and backup"
2. "Identify missing schemas"
3. "Restore from backup"
4. "Verify restoration"
5. "Update documentation"
```

## 🧪 Testing Strategies

### Schema Contract Testing
```
"Create test context"
"Register producer schema"
"Validate consumer compatibility"
"Clean up after tests"
```

### Canary Deployments
```
"Register in canary context"
"Test with subset of traffic"
"Monitor for issues"
"Promote or rollback"
```

## 📋 Complex Scenarios

### Blue-Green Deployment
```
Blue: "Current production schemas"
Green: "Register new versions"
Switch: "Atomically switch traffic"
Rollback: "Revert if issues"
```

### Schema Versioning Strategy
```
v1: "Original schema"
v1.1: "Backward compatible additions"
v2: "Breaking changes with migration"
v2.1: "Further iterations"
```

## 💡 Pro Tips
- Automate repetitive tasks
- Use contexts for isolation
- Monitor everything
- Plan for failure scenarios
- Document your workflows

**Advanced example**: Try setting up a complete CI/CD pipeline!"""


def get_schema_evolution_prompt():
    """Guide for safe schema evolution with the Schema Evolution Assistant"""
    return """# Schema Evolution Assistant 🔄

## Quick Start Commands

### 🚀 Start the Assistant
```
"Start schema evolution assistant"
"Guide me through evolving user schema"
"Help me safely change my order schema"
```

### With Pre-filled Information
```
"Evolve user-events schema - I need to add email field"
"Change order schema from string ID to long ID safely"
"Help migrate payment schema to new structure"
```

## 🎯 When to Use the Assistant

### ✅ Always Use For:
- **Breaking Changes**: Removing fields, changing types, renaming
- **Production Schemas**: Any change to live, critical schemas
- **Complex Changes**: Multiple modifications at once
- **Team Coordination**: Changes affecting multiple consumers

### Examples:
```
"I need to remove deprecated_field from user schema"
"Change user_id from string to long in production"
"Add required email field to existing user schema"
"Restructure nested address object in customer schema"
```

## 🛠️ What the Assistant Does

### 1. **Change Analysis** 🔍
- Detects all field additions, removals, type changes
- Identifies breaking vs. safe changes
- Analyzes impact on existing consumers
- Provides detailed compatibility assessment

### 2. **Strategy Planning** 📋
- **Direct Update**: For safe, backward-compatible changes
- **Multi-Version Migration**: Gradual transition with intermediate versions
- **Dual Support**: Support both old and new schemas simultaneously
- **Blue-Green Deployment**: Zero-downtime migrations

### 3. **Consumer Coordination** 🤝
- Plans consumer update sequences
- Suggests testing approaches
- Coordinates deployment windows
- Provides rollback procedures

### 4. **Safe Execution** ⚡
- Step-by-step implementation guidance
- Real-time compatibility validation
- Automated rollback triggers
- Post-deployment monitoring

## 📋 Common Evolution Scenarios

### Adding Fields Safely
```
"Add optional phone field to user schema"
→ Assistant guides: field type, default value, compatibility check

"Add required email field to existing schema"
→ Assistant plans: migration strategy, consumer updates, rollback plan
```

### Removing Fields
```
"Remove deprecated legacy_id field"
→ Assistant checks: consumer usage, deprecation timeline, safe removal

"Clean up unused fields from order schema"
→ Assistant validates: no active readers, safe to remove
```

### Type Changes
```
"Change user_id from string to long"
→ Assistant plans: dual-field approach, consumer migration, cleanup

"Convert price from float to decimal"
→ Assistant suggests: precision handling, data migration strategy
```

### Complex Restructuring
```
"Split address field into street, city, zip"
→ Assistant designs: multi-phase migration, intermediate schemas

"Merge user and profile schemas"
→ Assistant coordinates: cross-schema migration, consumer updates
```

## 🔄 Evolution Strategies Explained

### 🎯 Direct Update
**Best for**: Non-breaking changes, coordinated deployments
**Process**: Update schema directly
**Example**: Adding optional fields with defaults

### 🔄 Multi-Version Migration
**Best for**: Breaking changes with many consumers
**Process**: Create intermediate schema versions for gradual migration
**Timeline**: Usually 2-4 weeks depending on consumer count

### 🔀 Dual Support
**Best for**: Supporting old and new formats simultaneously
**Process**: Implement logic to handle both schemas
**Use case**: Long-term backward compatibility needs

### 📈 Blue-Green Deployment
**Best for**: Critical systems requiring zero downtime
**Process**: Parallel environments with atomic switchover
**Complexity**: High, but maximum safety

## 💡 Best Practices Built-In

### 🛡️ Safety First
- Always analyze before implementing
- Validate compatibility at each step
- Maintain rollback capabilities
- Monitor post-deployment health

### 📊 Data-Driven Decisions
- Use compatibility matrices for planning
- Analyze consumer usage patterns
- Consider performance implications
- Plan for future evolution needs

### 🤝 Team Coordination
- Involve all stakeholders in planning
- Document evolution decisions
- Coordinate deployment windows
- Establish clear rollback procedures

## 🚨 Troubleshooting

### Assistant Won't Start
```
"Check if workflows are available"
"Test multi-step elicitation system"
"Show workflow status"
```

### Evolution Fails
```
"Show current evolution task status"
"Check compatibility errors"
"Review rollback options"
```

### Consumer Issues
```
"Check consumer compatibility after evolution"
"Monitor schema evolution progress"
"Get evolution task details"
```

## 🎓 Learning Path

### Beginner: Start Simple
```
1. "Add optional field to test schema"
2. "Practice with development context"
3. "Learn compatibility rules"
```

### Intermediate: Coordinate Changes
```
1. "Plan breaking change with assistant"
2. "Coordinate consumer updates"
3. "Execute with monitoring"
```

### Advanced: Complex Migrations
```
1. "Multi-schema restructuring"
2. "Cross-registry migrations"
3. "Zero-downtime deployments"
```

## 🚀 Getting Started

### First Time Users
```
"Start schema evolution assistant for user schema"
```

### Experienced Users
```
"Evolve order schema - removing legacy fields, adding payment_method enum"
```

**Pro Tip**: The assistant learns from your preferences and gets better at suggesting strategies over time!

**Ready to evolve safely?** Try: `"Start schema evolution assistant"`"""


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
    "schema-evolution": get_schema_evolution_prompt,
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
            "advanced_features": [
                "schema-export",
                "multi-registry",
                "schema-compatibility",
                "schema-evolution",
            ],
            "support": ["troubleshooting", "advanced-workflows"],
        },
    }


# Quick reference card for users
def get_quick_reference():
    """Get a quick reference card of most common commands."""
    return """# Quick Reference Card 📋

## 🚀 Most Used Commands

### Setup & Status
```
"Test all connections"
"List all contexts"
"Show all schemas"
```

### Schema Operations
```
"Register user schema with id, name, email"
"Check if adding field X is safe"
"Start schema evolution assistant"
"Export schema Y as JSON"
```

### Multi-Registry
```
"Compare dev and prod"
"Migrate schema from dev to prod"
"Set production as default"
```

### Troubleshooting
```
"Why did registration fail?"
"Check my permissions"
"Show active tasks"
```

## 🎯 Copy-Paste Templates

### New User Schema
```
"Register user schema with:
- id (long)
- name (string)
- email (string, optional)
- created_at (timestamp-millis)"
```

### Environment Setup
```
"Create development, staging, and production contexts"
```

### Daily Backup
```
"Export all production schemas with metadata"
```

## 💡 Pro Tips
- Start in development context
- Always check compatibility
- Use contexts for organization
- Export regularly for backup

**Need more?** Ask: "Show me the getting started guide"
"""


# Add quick reference to the registry
PROMPT_REGISTRY["quick-reference"] = get_quick_reference
