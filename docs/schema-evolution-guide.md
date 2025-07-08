# Schema Evolution Assistant Guide

## Overview

The Schema Evolution Assistant is a multi-step workflow that guides you through safely evolving Kafka schemas. It analyzes proposed changes, detects breaking compatibility issues, and helps you choose the best migration strategy for your use case.

## When to Use the Schema Evolution Assistant

Use the Schema Evolution Assistant when you need to:

- **Make breaking changes** to an existing schema
- **Evolve schemas in production** with active consumers
- **Plan complex migrations** involving multiple schema changes
- **Coordinate schema updates** across teams
- **Ensure safe rollback** procedures

## Starting the Assistant

### Via MCP Tool

```json
// Start the Schema Evolution Assistant
{
  "tool": "guided_schema_evolution",
  "parameters": {
    "subject": "user-events",
    "current_schema": "{\"type\":\"record\",\"name\":\"User\",\"fields\":[...]}"
  }
}
```

### Via Interactive Registration

When using `register_schema_interactive`, the assistant will automatically trigger if breaking changes are detected.

## Workflow Steps

### Step 1: Change Analysis

The assistant begins by analyzing your schema changes:

- **Subject**: The schema subject name
- **Change Type**: What kind of changes you're making
  - `add_fields` - Adding new fields
  - `remove_fields` - Removing existing fields
  - `modify_fields` - Changing field types or properties
  - `rename_fields` - Renaming fields
  - `restructure_schema` - Major structural changes
  - `multiple_changes` - Combination of above
- **Change Description**: Detailed description of your changes
- **Current Consumers**: Number of active consumers (e.g., "10-50")
- **Production Impact**: Criticality of the system
  - `yes_critical` - Production critical system
  - `yes_non_critical` - Production but not critical
  - `no_staging` - Staging environment
  - `no_development` - Development environment

### Step 2: Breaking Changes Detection

The assistant analyzes your changes for compatibility issues:

- **Has Breaking Changes**: Whether breaking changes were detected
- **Current Compatibility**: Current registry compatibility mode
- **Risk Tolerance**: Your tolerance for risk
  - `very_low` - Minimal risk acceptable
  - `low` - Some risk acceptable with precautions
  - `medium` - Moderate risk acceptable
  - `high` - Higher risk acceptable

### Step 3: Compatibility Resolution (If Breaking Changes)

If breaking changes are detected, you'll need to choose a resolution approach:

- **`make_backward_compatible`** - Modify schema to maintain compatibility
- **`use_union_types`** - Use union types to support both formats
- **`add_defaults`** - Add default values to new required fields
- **`create_new_subject`** - Create a new schema subject
- **`force_with_coordination`** - Proceed with coordinated consumer updates

### Step 4: Evolution Strategy Selection

Choose your schema evolution approach:

#### Direct Update
- **Best for**: Non-breaking changes or coordinated deployments
- **Process**: Update schema directly
- **Risk**: Low for compatible changes, high for breaking changes

#### Multi-Version Migration
- **Best for**: Breaking changes with many consumers
- **Process**: Create intermediate schema versions
- **Risk**: Low, allows gradual migration

#### Dual Support
- **Best for**: Supporting old and new formats simultaneously
- **Process**: Implement logic to handle both schemas
- **Risk**: Medium, requires application changes

#### Gradual Migration
- **Best for**: Large-scale migrations
- **Process**: Phased approach with checkpoints
- **Risk**: Low, but takes longer

#### Blue-Green Deployment
- **Best for**: Critical systems with zero downtime
- **Process**: Parallel environments with switchover
- **Risk**: Low, but resource intensive

### Step 5: Strategy-Specific Configuration

Based on your chosen strategy, configure the details:

#### For Multi-Version Migration:
- **Intermediate Versions**: Number of transitional versions
- **Version Timeline**: Days between each version
- **Deprecation Strategy**: How to handle deprecated fields

#### For Dual Support:
- **Support Duration**: How long to support both formats
- **Field Mapping**: Mapping between old and new field names
- **Conversion Logic**: How to handle conversions

#### For Gradual Migration:
- **Phase Count**: Number of migration phases
- **Phase Criteria**: How to progress between phases
- **Rollback Checkpoints**: Whether to create checkpoints

### Step 6: Consumer Coordination

Plan how to coordinate with consumers:

- **Notification Method**:
  - `automatic_alerts` - Automated notifications
  - `email_notification` - Email to consumer teams
  - `api_deprecation_headers` - HTTP headers in responses
  - `documentation_only` - Update documentation
  - `multi_channel` - Multiple notification methods

- **Consumer Testing**:
  - `sandbox_environment` - Test in sandbox first
  - `canary_consumers` - Test with subset of consumers
  - `parallel_testing` - Run old and new in parallel
  - `consumer_managed` - Consumers test independently

- **Support Period**: How long to support the old schema

### Step 7: Rollback Planning

Define your rollback strategy:

- **Rollback Trigger**:
  - `error_rate_threshold` - Based on error metrics
  - `consumer_reports` - Based on consumer feedback
  - `manual_decision` - Manual intervention
  - `automated_monitoring` - Automated detection

- **Rollback Time**: Maximum time for rollback decision
- **Data Handling**: How to handle data during rollback
- **Rollback Testing**: Whether to test rollback procedures

### Step 8: Final Confirmation

Review and confirm your evolution plan:

- **Generate Migration Guide**: Create documentation for consumers
- **Create Runbook**: Generate operational runbook
- **Schedule Dry Run**: Test the migration first
- **Monitor Execution**: Enable monitoring during migration

## Example Scenarios

### Scenario 1: Adding Optional Fields

**Situation**: Adding an optional email field to user schema

**Recommended Path**:
1. Change Type: `add_fields`
2. No breaking changes detected
3. Strategy: `direct_update`
4. Simple notification to consumers

### Scenario 2: Removing Required Field

**Situation**: Removing a required field that consumers depend on

**Recommended Path**:
1. Change Type: `remove_fields`
2. Breaking changes detected
3. Resolution: `use_union_types` or `multi_version_migration`
4. Strategy: `multi_version_migration`
5. Create 2 intermediate versions over 30 days
6. Coordinate with all consumers
7. Set up error rate monitoring for rollback

### Scenario 3: Type Change

**Situation**: Changing field type from int to long

**Recommended Path**:
1. Change Type: `modify_fields`
2. Breaking changes detected (for some systems)
3. Resolution: `dual_support`
4. Configure field mapping and conversion
5. Support both formats for 1 month
6. Gradual consumer migration

## Best Practices

### 1. Always Test First
- Use dry run functionality
- Test in staging environment
- Validate with sample consumers

### 2. Communication is Key
- Notify consumers early
- Provide clear migration guides
- Set realistic timelines

### 3. Monitor Actively
- Watch error rates during migration
- Track consumer adoption
- Be ready to rollback

### 4. Document Everything
- Record decisions made
- Document field mappings
- Keep migration guides updated

### 5. Plan for Rollback
- Always have a rollback plan
- Test rollback procedures
- Define clear rollback criteria

## Troubleshooting

### Common Issues

#### "Workflow Not Starting"
- Ensure you have write permissions (not viewonly mode)
- Check that the schema exists
- Verify MCP connection is active

#### "Compatibility Check Failed"
- Review the specific compatibility errors
- Consider using union types for flexibility
- Check if creating a new subject is more appropriate

#### "Migration Taking Too Long"
- Review consumer adoption metrics
- Consider extending timelines
- Provide additional support to lagging consumers

## Integration with CI/CD

The Schema Evolution Assistant can be integrated into your CI/CD pipeline:

```bash
# Example: Check for breaking changes in CI
mcp_result=$(mcp call guided_schema_evolution \
  --subject "user-events" \
  --current_schema "@current.avsc" \
  --proposed_schema "@proposed.avsc")

if [[ $mcp_result == *"breaking_changes"* ]]; then
  echo "Breaking changes detected! Manual review required."
  exit 1
fi
```

## Related Tools

- `register_schema_interactive` - Interactive schema registration
- `check_compatibility_interactive` - Interactive compatibility checking
- `migrate_schema` - Direct schema migration
- `compare_registries` - Compare schemas across registries

## Conclusion

The Schema Evolution Assistant provides a safe, guided approach to evolving schemas in production. By following the workflow and best practices, you can minimize risk and ensure smooth schema evolution across your Kafka infrastructure. 