# Schema Evolution Skill

**Skill Name:** `/schema-evolve`
**Category:** Schema Development
**Description:** Safely evolve existing schemas with automatic compatibility checking

## Purpose

This skill helps you evolve existing schemas while maintaining backward, forward, or full compatibility. It analyzes the current schema, suggests safe evolution strategies, and generates the new version.

## Usage

```
/schema-evolve <subject-name> <changes-description>
```

### Parameters

- `<subject-name>`: Name of the schema subject to evolve
- `<changes-description>`: Description of desired changes

### Examples

```
/schema-evolve user-profile "add optional phoneNumber and socialLoginProvider fields"

/schema-evolve order-event "add new enum value REFUNDED to orderStatus"

/schema-evolve product-entity "rename field 'description' to 'productDescription'"

/schema-evolve customer-aggregate "add nested address record with street, city, zipCode"
```

## What This Skill Does

1. **Retrieves Current Schema**: Fetches the latest version from the registry
2. **Analyzes Changes**: Understands what you want to modify
3. **Checks Compatibility**: Determines which evolution strategies are safe
4. **Suggests Approach**: Recommends the best way to make changes
5. **Generates New Version**: Creates evolved schema
6. **Validates Compatibility**: Confirms the new version is compatible
7. **Provides Migration Path**: Shows how to migrate data if needed

## Compatibility Modes

### BACKWARD (Default)
- ✅ Can delete fields
- ✅ Can add optional fields (with defaults)
- ❌ Cannot add required fields
- ❌ Cannot change field types

**Use when:** Consumers should read old data with new schema

### FORWARD
- ✅ Can add fields
- ✅ Can delete optional fields
- ❌ Cannot delete required fields
- ❌ Cannot change field types

**Use when:** New data should be readable by old consumers

### FULL
- ✅ Can add optional fields with defaults
- ✅ Can delete optional fields with defaults
- ❌ Very restrictive on changes
- ❌ Cannot change field types

**Use when:** Maximum compatibility required

### BACKWARD_TRANSITIVE
- All BACKWARD rules apply across all versions
- Most common for production systems

### NONE
- No compatibility checking
- Use only for development/testing contexts

## Safe Evolution Patterns

### Adding Fields (Safe)
```
✅ Add optional field with default:
{
  "name": "phoneNumber",
  "type": ["null", "string"],
  "default": null
}

❌ Add required field:
{
  "name": "phoneNumber",
  "type": "string"  // Will break backward compatibility
}
```

### Removing Fields (Conditionally Safe)
```
✅ Remove optional field (FORWARD compatible):
// Old consumers ignore unknown fields

❌ Remove required field (breaks compatibility):
// Old consumers expect this field
```

### Adding Enum Values (Safe)
```
✅ Add new enum value:
"symbols": ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "REFUNDED"]
           // REFUNDED is new

Note: Old consumers must handle unknown values gracefully
```

### Field Type Changes (Usually Unsafe)
```
❌ string → int (breaks compatibility)
❌ int → long (may work but risky)
✅ Use union types for flexibility:
   ["null", "string", "int"]  // Accepts multiple types
```

## Output

The skill provides:
- **Current Schema Analysis**: What the schema looks like now
- **Proposed Changes**: What will be modified
- **Compatibility Assessment**: Which modes are safe
- **Evolved Schema**: Complete new version
- **Migration Guide**: How to handle the evolution
- **Registration Command**: How to register new version
- **Rollback Plan**: How to revert if needed

## Evolution Workflow

```
1. Fetch current schema
   ↓
2. Analyze requested changes
   ↓
3. Check compatibility impact
   ↓
4. Generate evolved schema
   ↓
5. Validate new version
   ↓
6. Test compatibility
   ↓
7. Provide registration command
   ↓
8. Document migration path
```

## Common Evolution Scenarios

### Scenario 1: Add Optional Field
```
Current: User {id, name, email}
Request: "add optional phoneNumber"
Result: User {id, name, email, phoneNumber?}
Compatibility: BACKWARD ✅
```

### Scenario 2: Make Field Optional
```
Current: User {id, name, email (required)}
Request: "make email optional"
Result: User {id, name, email?}
Compatibility: FORWARD ✅ (with default)
```

### Scenario 3: Add Enum Value
```
Current: Status {ACTIVE, INACTIVE}
Request: "add SUSPENDED status"
Result: Status {ACTIVE, INACTIVE, SUSPENDED}
Compatibility: BACKWARD ✅ if consumers handle unknown
```

### Scenario 4: Rename Field (Risky)
```
Current: User {firstName}
Request: "rename firstName to givenName"
Approach: Add new field, deprecate old:
Result: User {firstName (deprecated), givenName}
Compatibility: BACKWARD ✅
Migration: Dual-write period, then remove old field
```

## Validation Checks

The skill performs:
- ✅ Avro schema syntax validation
- ✅ Compatibility rule checking
- ✅ Field type consistency
- ✅ Default value validation
- ✅ Documentation completeness
- ✅ Namespace consistency
- ✅ Reserved field name checking

## Error Handling

If evolution is unsafe:
1. **Identifies Issues**: Explains what breaks compatibility
2. **Suggests Alternatives**: Provides safe approaches
3. **Shows Examples**: Demonstrates how to make it work
4. **Offers Workarounds**: Multi-step evolution if needed

## Related Skills

- `/schema-generate` - Generate new schema
- `/compatibility-check` - Check compatibility between versions
- `/migration-plan` - Plan data migration
- `/schema-validate` - Validate schema structure

## Best Practices

1. **Always add defaults** to optional fields
2. **Never remove required fields** in one step
3. **Deprecate before deleting** fields
4. **Add, don't modify** field types
5. **Document breaking changes** clearly
6. **Test in development** context first
7. **Plan rollback strategy** before evolving
8. **Communicate changes** to consumers

## Notes

- Default compatibility mode is BACKWARD_TRANSITIVE
- Evolution is validated against ALL previous versions in transitive modes
- Use development context for testing evolutions
- Always document why fields were added/removed
- Consider consumer impact before evolving
