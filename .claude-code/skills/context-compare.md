# Context Comparison Skill

**Skill Name:** `/context-compare`
**Category:** Operations
**Description:** Compare schemas between contexts to identify differences and plan synchronization

## Purpose

This skill analyzes and compares schemas across different contexts (development, staging, production) to identify:
- Schemas present in one context but missing in another
- Schema version differences
- Compatibility mismatches
- Configuration drift
- Synchronization needs

## Usage

```
/context-compare <source-context> <target-context> [options]
```

### Parameters

- `<source-context>`: Source context to compare from (e.g., development, staging)
- `<target-context>`: Target context to compare to (e.g., staging, production)
- `[options]`: Optional flags (--detailed, --only-differences, --include-config)

### Examples

```
/context-compare development staging

/context-compare staging production --detailed

/context-compare development production --only-differences

/context-compare staging production --include-config
```

## What This Skill Does

1. **Retrieves Schemas**: Fetches all schemas from both contexts
2. **Identifies Differences**: Compares schema subjects, versions, and content
3. **Analyzes Compatibility**: Checks compatibility settings between contexts
4. **Generates Report**: Creates detailed comparison report
5. **Provides Recommendations**: Suggests synchronization actions
6. **Creates Action Plan**: Generates step-by-step sync plan if needed

## Comparison Report Structure

### 1. Executive Summary
```
Context Comparison: development → staging
Generated: 2026-01-17 10:30:00

Summary:
  Source Context (development): 15 schemas
  Target Context (staging): 12 schemas
  Schemas in both: 10 schemas
  Only in source: 5 schemas (NEW)
  Only in target: 2 schemas (ORPHANED)
  Version differences: 3 schemas
  Compatibility differences: 1 schema
```

### 2. Schemas Only in Source (New)
```
New schemas in development (not in staging):
  ✨ user-profile-v2
     - Version: 2
     - Created: 2026-01-15
     - Status: Ready for promotion

  ✨ order-event-v3
     - Version: 3
     - Created: 2026-01-16
     - Status: Ready for promotion

  ✨ payment-entity-v1
     - Version: 1
     - Created: 2026-01-17
     - Status: Needs testing

  ⚠️  experimental-feature-v1
     - Version: 1
     - Created: 2026-01-17
     - Status: Not ready (experimental)

  ⚠️  test-schema-v1
     - Version: 1
     - Created: 2026-01-16
     - Status: Test only (do not promote)
```

### 3. Schemas Only in Target (Orphaned)
```
Schemas in staging but not in development:
  🗑️  deprecated-schema-v1
     - Version: 1
     - Last Modified: 2025-12-01
     - Action: Consider cleanup

  🗑️  old-format-entity-v1
     - Version: 1
     - Last Modified: 2025-11-15
     - Action: Replaced by new-format-entity-v2
```

### 4. Version Differences
```
Schemas with different versions:
  📊 user-profile
     - development: v3 (3 versions)
     - staging: v2 (2 versions)
     - Difference: +1 version ahead in development
     - Status: Needs promotion

  📊 order-aggregate
     - development: v5 (5 versions)
     - staging: v4 (4 versions)
     - Difference: +1 version ahead in development
     - Status: Needs promotion

  📊 customer-entity
     - development: v2 (2 versions)
     - staging: v3 (3 versions)
     - Difference: -1 version behind in development
     - Status: ⚠️  ALERT - Staging ahead (investigate)
```

### 5. Compatibility Differences
```
Schemas with different compatibility settings:
  ⚙️  user-profile
     - development: BACKWARD
     - staging: BACKWARD_TRANSITIVE
     - Impact: More restrictive in staging
     - Action: Align settings before promotion

  ⚙️  order-event
     - development: FULL
     - staging: BACKWARD
     - Impact: Different compatibility guarantees
     - Action: Review and align
```

### 6. Schema Content Differences
```
Schemas with same version but different content:
  🔍 product-entity-v2
     - Same version number but content differs
     - Status: ⚠️  CRITICAL - Schema drift detected
     - Action: Investigate immediately

  Fields added in development:
    + loyaltyPoints (optional, default: 0)
    + preferences (optional record)

  Fields removed in development:
    - oldField (deprecated)
```

### 7. Compatibility Analysis
```
Compatibility check for promotion:
  ✅ user-profile-v3: BACKWARD compatible with staging v2
  ✅ order-aggregate-v5: BACKWARD compatible with staging v4
  ⚠️  payment-entity-v1: No baseline in staging (new schema)
  ❌ experimental-feature-v1: INCOMPATIBLE (breaking changes)
```

### 8. Synchronization Recommendations
```
Recommended Actions:

Priority 1: CRITICAL (Do Now)
  1. Investigate schema drift in product-entity-v2
     - Same version, different content
     - Resolution: Determine source of truth

  2. Investigate staging ahead issue for customer-entity
     - Staging has v3, development has v2
     - Resolution: Review change history

Priority 2: HIGH (Plan for Next Release)
  3. Promote user-profile-v3 to staging
     - BACKWARD compatible
     - Well tested in development

  4. Promote order-aggregate-v5 to staging
     - BACKWARD compatible
     - Production ready

Priority 3: MEDIUM (Plan and Test)
  5. Promote payment-entity-v1 to staging
     - New schema, needs testing
     - Requires consumer updates

Priority 4: LOW (Cleanup)
  6. Remove orphaned schemas from staging
     - deprecated-schema-v1
     - old-format-entity-v1

  7. Align compatibility settings
     - user-profile: BACKWARD → BACKWARD_TRANSITIVE
     - order-event: FULL → BACKWARD

Priority 5: SKIP (Do Not Promote)
  8. experimental-feature-v1
     - Experimental, not production ready

  9. test-schema-v1
     - Test only, never promote
```

### 9. Sync Plan
```
Synchronization Plan: development → staging

Phase 1: Critical Issues (Do First)
  □ Fix schema drift in product-entity-v2
  □ Investigate customer-entity version mismatch

Phase 2: Safe Promotions (Low Risk)
  □ Promote user-profile-v3
  □ Promote order-aggregate-v5

Phase 3: New Schemas (Needs Testing)
  □ Promote payment-entity-v1
  □ Update consuming applications

Phase 4: Cleanup (Post-Promotion)
  □ Remove deprecated-schema-v1 from staging
  □ Remove old-format-entity-v1 from staging
  □ Align compatibility settings

Phase 5: Verification
  □ Validate all promotions
  □ Check compatibility settings
  □ Run integration tests
  □ Monitor for issues
```

## Output Formats

### Default Format (Markdown)
```markdown
# Context Comparison Report
## development → staging
...
```

### JSON Format (--format=json)
```json
{
  "source_context": "development",
  "target_context": "staging",
  "timestamp": "2026-01-17T10:30:00Z",
  "summary": {
    "source_schemas": 15,
    "target_schemas": 12,
    "common_schemas": 10,
    "only_in_source": 5,
    "only_in_target": 2,
    "version_differences": 3
  },
  "differences": [...],
  "recommendations": [...]
}
```

### CSV Format (--format=csv)
```csv
Subject,Source Version,Target Version,Status,Action
user-profile,v3,v2,Version Mismatch,Promote to staging
order-aggregate,v5,v4,Version Mismatch,Promote to staging
...
```

## Comparison Modes

### Quick Mode (Default)
- Summary statistics
- Major differences only
- High-level recommendations
- Fast execution

### Detailed Mode (--detailed)
- Full schema content comparison
- Field-by-field differences
- Compatibility analysis per schema
- Complete recommendations

### Diff-Only Mode (--only-differences)
- Only shows differences
- Hides identical schemas
- Focused view for quick review

### Config Mode (--include-config)
- Includes compatibility settings
- Schema registry configuration
- Context-level settings
- Global configuration differences

## Common Use Cases

### Use Case 1: Pre-Deployment Check
```
Scenario: Ready to deploy to staging
Command: /context-compare development staging --detailed
Output: Complete comparison with promotion plan
Action: Review and execute sync plan
```

### Use Case 2: Production Audit
```
Scenario: Verify production is in sync with staging
Command: /context-compare staging production --only-differences
Output: List of any differences found
Action: Investigate unexpected differences
```

### Use Case 3: Schema Drift Detection
```
Scenario: Detect configuration drift between environments
Command: /context-compare development production --include-config
Output: All differences including settings
Action: Align configurations
```

### Use Case 4: Release Planning
```
Scenario: Plan next release to production
Command: /context-compare staging production
Output: List of changes to promote
Action: Create release plan
```

## Alerts and Warnings

### Critical Alerts 🔴
```
⚠️  CRITICAL: Schema drift detected
    - product-entity-v2 has same version but different content
    - Action: Investigate immediately

⚠️  CRITICAL: Target ahead of source
    - customer-entity staging v3 > development v2
    - Action: Review change history
```

### High Priority Warnings 🟡
```
⚠️  WARNING: Compatibility mismatch
    - user-profile compatibility differs between contexts
    - Action: Align before promotion

⚠️  WARNING: Breaking change detected
    - experimental-feature-v1 incompatible with target
    - Action: Do not promote
```

### Info Notices 🔵
```
ℹ️  INFO: New schemas ready for promotion
    - 3 schemas tested and ready
    - Action: Include in next release

ℹ️  INFO: Orphaned schemas found
    - 2 schemas only in target
    - Action: Review for cleanup
```

## Detailed Comparison Features

### Field-Level Comparison
```
Schema: user-profile-v3

Fields added in development:
  + phoneNumber
    - Type: ["null", "string"]
    - Default: null
    - Status: ✅ BACKWARD compatible (optional)

  + preferences
    - Type: record { emailNotifications, smsNotifications, language }
    - Default: null
    - Status: ✅ BACKWARD compatible (optional with default)

Fields modified in development:
  ~ email
    - Old: string (required)
    - New: ["null", "string"] (optional)
    - Status: ⚠️  FORWARD compatible only (required → optional)

Fields removed in development:
  - oldField
    - Type: string
    - Status: ✅ BACKWARD compatible (field deletion allowed)
```

### Version History Comparison
```
Schema: order-aggregate

Development version history:
  v5 - 2026-01-16: Added cancellation support
  v4 - 2026-01-10: Added refund tracking
  v3 - 2025-12-15: Added shipping details
  v2 - 2025-11-20: Added customer info
  v1 - 2025-10-01: Initial version

Staging version history:
  v4 - 2026-01-10: Added refund tracking
  v3 - 2025-12-15: Added shipping details
  v2 - 2025-11-20: Added customer info
  v1 - 2025-10-01: Initial version

Difference: v5 in development (cancellation support)
Status: Ready to promote
```

### Compatibility Settings Comparison
```
Context-wide compatibility settings:

development:
  - Default: BACKWARD
  - user-profile: BACKWARD (default)
  - order-event: FULL (overridden)
  - payment-entity: BACKWARD (default)

staging:
  - Default: BACKWARD_TRANSITIVE
  - user-profile: BACKWARD_TRANSITIVE (default)
  - order-event: BACKWARD (overridden)
  - payment-entity: BACKWARD_TRANSITIVE (default)

Recommendations:
  1. Align default compatibility to BACKWARD_TRANSITIVE
  2. Review order-event override (FULL → BACKWARD)
  3. Ensure settings match in production
```

## Integration with Other Skills

### With `/migration-plan`
```
# First compare contexts
/context-compare development staging

# Then plan migration for differences
/migration-plan development staging

# Creates migration plan based on comparison results
```

### With `/schema-evolve`
```
# Compare contexts
/context-compare staging production

# Evolve schema to fix compatibility
/schema-evolve user-profile "align with production requirements"

# Re-compare to verify
/context-compare staging production
```

### With `/lint-and-test`
```
# Compare contexts
/context-compare development staging

# Test changes before promotion
/lint-and-test test-quick

# Promote with confidence
```

## Best Practices

### Before Deployment
1. ✅ Always compare before promoting
2. ✅ Review all differences carefully
3. ✅ Check for schema drift
4. ✅ Verify compatibility settings
5. ✅ Plan promotion order

### Regular Audits
1. ✅ Compare staging ↔ production weekly
2. ✅ Compare development ↔ staging daily
3. ✅ Investigate unexpected differences
4. ✅ Clean up orphaned schemas
5. ✅ Maintain consistency

### Drift Detection
1. ✅ Alert on same-version content differences
2. ✅ Investigate target-ahead-of-source scenarios
3. ✅ Monitor compatibility setting changes
4. ✅ Track schema lifecycle

## Error Handling

### Context Not Found
```
Error: Context 'development' not found
Available contexts: staging, production, testing
Action: Use correct context name
```

### No Schemas Found
```
Warning: No schemas found in context 'development'
Action: Verify context is configured correctly
```

### Connection Failed
```
Error: Cannot connect to Schema Registry for context 'staging'
Action: Check registry URL and credentials
```

### Permission Denied
```
Error: Insufficient permissions to read context 'production'
Action: Request read access or use VIEWONLY mode
```

## Related Skills

- `/migration-plan` - Plan migration based on comparison
- `/schema-evolve` - Evolve schemas to fix compatibility
- `/context-sync` - Synchronize contexts automatically
- `/schema-validate` - Validate schema compatibility

## Advanced Features

### Pattern Matching
```
# Compare only specific subjects
/context-compare development staging --pattern "user-*"

# Exclude test schemas
/context-compare development staging --exclude "test-*"
```

### Custom Filters
```
# Only show incompatible schemas
/context-compare development staging --filter incompatible

# Only show version mismatches
/context-compare development staging --filter version-mismatch
```

### Historical Comparison
```
# Compare current development with staging from 7 days ago
/context-compare development staging --baseline 7d

# Compare with specific timestamp
/context-compare development staging --baseline 2026-01-10T00:00:00Z
```

## Output Customization

### Summary Only
```
/context-compare development staging --summary-only
```

### Verbose Mode
```
/context-compare development staging --verbose
```

### Export Report
```
/context-compare development staging --export comparison-report.md
```

## Notes

- Comparison is read-only and safe to run anytime
- Use detailed mode for comprehensive analysis
- Always investigate schema drift (same version, different content)
- Target-ahead-of-source requires immediate investigation
- Orphaned schemas may be safe to delete after review
- Compatibility setting differences can cause promotion failures
- Run comparison before every deployment
- Save comparison reports for audit trails

## Example Workflow

```bash
# 1. Compare contexts before deployment
/context-compare development staging --detailed

# 2. Review the comparison report
# (check for critical issues)

# 3. Fix any schema drift or compatibility issues
/schema-evolve problematic-schema "fix compatibility"

# 4. Re-compare to verify fixes
/context-compare development staging

# 5. Plan migration
/migration-plan development staging

# 6. Execute migration during maintenance window

# 7. Verify synchronization
/context-compare development staging --only-differences
# (should show no differences)
```
