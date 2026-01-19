# Migration Planning Skill

**Skill Name:** `/migration-plan`
**Category:** Operations
**Description:** Generate comprehensive migration plans for moving schemas between contexts or registries

## Purpose

This skill creates detailed, step-by-step migration plans for promoting schemas across environments (dev → staging → production) or migrating between Schema Registry instances.

## Usage

```
/migration-plan <source> <target> [options]
```

### Parameters

- `<source>`: Source context or registry (e.g., development, staging, registry-a)
- `<target>`: Target context or registry (e.g., staging, production, registry-b)
- `[options]`: Optional flags (--dry-run, --with-rollback, --validate-only)

### Examples

```
/migration-plan development staging

/migration-plan staging production --with-rollback

/migration-plan registry-primary registry-dr --dry-run

/migration-plan development production --validate-only
```

## What This Skill Does

1. **Analyzes Source**: Lists all schemas in source context/registry
2. **Analyzes Target**: Lists existing schemas in target
3. **Identifies Differences**: Finds new, updated, and conflicting schemas
4. **Checks Compatibility**: Validates all schemas against target compatibility rules
5. **Orders Dependencies**: Ensures schemas are migrated in correct order
6. **Generates Plan**: Creates detailed migration sequence
7. **Creates Rollback Plan**: Provides reversion steps
8. **Estimates Impact**: Calculates migration time and risk level

## Migration Plan Structure

The generated plan includes:

### 1. Executive Summary
- Total schemas to migrate
- Compatibility assessment
- Risk level (Low/Medium/High)
- Estimated migration time
- Recommended migration window

### 2. Pre-Migration Checklist
```markdown
□ Backup current target registry
□ Verify source schemas are validated
□ Check target registry health
□ Notify consuming applications
□ Prepare rollback procedure
□ Review compatibility settings
```

### 3. Schema Inventory
```
Source Schemas: 15
Target Schemas: 10
New Schemas: 7
Updated Schemas: 3
Conflicting Schemas: 0
```

### 4. Compatibility Analysis
```
✅ user-profile-v1: BACKWARD compatible
✅ order-event-v2: FORWARD compatible
⚠️  payment-entity-v3: Requires FULL compatibility
❌ customer-aggregate-v1: INCOMPATIBLE (action required)
```

### 5. Migration Sequence
```
Phase 1: Safe Migrations (No Dependencies)
  1. user-profile-v1
  2. product-entity-v1
  3. category-enum-v1

Phase 2: Dependent Migrations
  4. order-event-v1 (depends on: user-profile-v1)
  5. order-line-item-v1 (depends on: product-entity-v1)
  6. order-aggregate-v1 (depends on: order-event-v1, order-line-item-v1)

Phase 3: Complex Migrations (Manual Review)
  7. payment-entity-v3 (breaking change - requires data migration)
```

### 6. Execution Commands
```bash
# Phase 1: Safe Migrations
curl -X POST http://target:8081/schemas/user-profile-v1 \
  -H 'Content-Type: application/json' \
  -d @schemas/user-profile-v1.json

# Phase 2: Dependent Migrations
...

# Phase 3: Manual Migrations
# (requires manual intervention)
```

### 7. Validation Steps
```bash
# Verify each schema after migration
curl http://target:8081/subjects/user-profile-v1/versions/latest

# Check compatibility
curl -X POST http://target:8081/compatibility/subjects/user-profile-v1/versions/latest \
  -H 'Content-Type: application/json' \
  -d @test-schema.json
```

### 8. Rollback Plan
```
1. Stop consuming applications
2. Delete migrated schemas in reverse order
3. Restore from backup if needed
4. Restart applications
5. Verify rollback success
```

### 9. Post-Migration Validation
```markdown
□ All schemas registered successfully
□ Compatibility checks pass
□ Consumer applications functional
□ No error logs in registry
□ Performance metrics normal
□ Documentation updated
```

## Migration Strategies

### Strategy 1: Big Bang Migration
- Migrate all schemas at once
- Requires downtime
- Fastest but highest risk
- Use for: Small schema sets, dev → staging

### Strategy 2: Incremental Migration
- Migrate schemas in phases
- No/minimal downtime
- Safest approach
- Use for: Production migrations

### Strategy 3: Shadow Migration
- Dual-write to both registries
- Validate in parallel
- Zero-downtime
- Use for: Critical production systems

### Strategy 4: Blue-Green Migration
- Migrate to new registry
- Switch traffic when ready
- Easy rollback
- Use for: Multi-registry setups

## Risk Assessment

### Low Risk ✅
- All schemas are backward compatible
- No breaking changes
- Well-tested in lower environments
- Clear rollback path

### Medium Risk ⚠️
- Some schemas have compatibility concerns
- Limited testing in target environment
- Dependencies between schemas
- Rollback possible but complex

### High Risk ❌
- Breaking changes present
- Untested schemas
- Complex dependencies
- No clear rollback path
- **Recommendation**: Do NOT proceed without review

## Dependency Resolution

The skill automatically:
1. Detects schema references (nested types, imports)
2. Orders schemas by dependency depth
3. Ensures parent schemas migrate before children
4. Identifies circular dependencies (error)
5. Creates migration waves

Example dependency graph:
```
order-aggregate-v1
  ├─ order-event-v1
  │   └─ user-profile-v1 ✅ (migrate first)
  └─ order-line-item-v1
      └─ product-entity-v1 ✅ (migrate first)
```

## Compatibility Modes Handling

### BACKWARD Mode
```
Target allows:
  ✅ Deleting fields
  ✅ Adding optional fields with defaults
Migration: Safe - newer consumers can read old data
```

### FORWARD Mode
```
Target allows:
  ✅ Adding fields
  ✅ Deleting optional fields
Migration: Safe - old consumers can read new data
```

### FULL Mode
```
Target allows:
  ✅ Adding optional fields with defaults
  ✅ Deleting optional fields with defaults
Migration: Very safe - bidirectional compatibility
```

### NONE Mode
```
Target allows:
  ⚠️ Any changes
Migration: Risky - no compatibility guarantees
```

## Output Formats

### Markdown Report (Default)
```markdown
# Migration Plan: development → production
## Summary
...
```

### JSON (--format=json)
```json
{
  "source": "development",
  "target": "production",
  "schemas": [...],
  "phases": [...],
  "risk_level": "medium"
}
```

### Shell Script (--format=script)
```bash
#!/bin/bash
# Migration script: development → production
# Generated: 2026-01-17
...
```

## Common Migration Scenarios

### Scenario 1: Dev → Staging
```
Context: First promotion of new features
Schemas: 5 new schemas
Risk: Low
Strategy: Big bang migration
Validation: Automated tests in staging
```

### Scenario 2: Staging → Production
```
Context: Validated features ready for production
Schemas: 3 schemas (all tested in staging)
Risk: Low-Medium
Strategy: Incremental migration during maintenance window
Validation: Canary deployment + monitoring
```

### Scenario 3: Production → DR Registry
```
Context: Disaster recovery setup
Schemas: All production schemas
Risk: Low (read-only DR)
Strategy: Shadow migration with continuous sync
Validation: Periodic integrity checks
```

### Scenario 4: Registry Consolidation
```
Context: Merging multiple registries
Schemas: 50+ schemas from 3 registries
Risk: High
Strategy: Multi-phase with extensive testing
Validation: Parallel running + gradual cutover
```

## Validation Checks

Before migration:
- ✅ Source registry is accessible
- ✅ Target registry is accessible and healthy
- ✅ All schemas are valid Avro
- ✅ No naming conflicts in target
- ✅ Target compatibility settings are known
- ✅ Required permissions are available

During migration:
- ✅ Each schema registers successfully
- ✅ Compatibility checks pass
- ✅ No errors in registry logs
- ✅ Schema IDs are assigned correctly

After migration:
- ✅ All schemas are queryable
- ✅ Version numbers are correct
- ✅ Compatibility mode is preserved
- ✅ Consuming applications work
- ✅ Performance is acceptable

## Error Handling

If migration fails:
1. **Pause Immediately**: Stop migrating additional schemas
2. **Identify Failure Point**: Which schema caused the issue
3. **Assess Impact**: What's already migrated
4. **Execute Rollback**: Use prepared rollback plan
5. **Root Cause Analysis**: Why did it fail
6. **Fix and Retry**: Correct issue and re-attempt

## Related Skills

- `/schema-evolve` - Evolve schemas before migration
- `/compatibility-check` - Check compatibility rules
- `/export-schemas` - Export schemas for backup
- `/validate-registry` - Validate registry health

## Best Practices

1. **Always test in lower environments first**
2. **Create backups before migration**
3. **Migrate during low-traffic windows**
4. **Notify stakeholders beforehand**
5. **Have rollback plan ready**
6. **Monitor during and after migration**
7. **Document what was migrated**
8. **Validate thoroughly post-migration**

## Notes

- Migration plans are saved to `migrations/` directory
- All plans include timestamps and metadata
- Rollback plans are generated automatically
- Use `--dry-run` to preview without executing
- Production migrations should be reviewed by team
