# Schema Generation Skill

**Skill Name:** `/schema-generate`
**Category:** Schema Development
**Description:** Generate production-ready Avro schemas from natural language descriptions

## Purpose

This skill helps you quickly generate Avro schemas using the project's schema templates with AI assistance. It ensures schemas follow best practices, include proper documentation, and are ready for registration.

## Usage

```
/schema-generate <schema-type> <name> <description>
```

### Parameters

- `<schema-type>`: Type of schema to generate (event, entity, command, aggregate)
- `<name>`: Name of the schema (e.g., UserRegistered, OrderEntity)
- `<description>`: Natural language description of fields and requirements

### Examples

```
/schema-generate event UserRegistered "user registration event with userId, email, registrationMethod (EMAIL/GOOGLE/FACEBOOK), timestamp"

/schema-generate entity Product "product entity with productId, name, price, inventory, status (DRAFT/ACTIVE/DISCONTINUED)"

/schema-generate command CreateOrder "create order command with customerId, items array, shippingAddress, paymentMethod"

/schema-generate aggregate Order "order aggregate managing line items with status, total, payment info"
```

## What This Skill Does

1. **Selects Template**: Chooses the appropriate template from `.claude-code/templates/`
2. **Parses Requirements**: Analyzes your natural language description
3. **Generates Schema**: Creates complete Avro schema with:
   - Proper field types and defaults
   - Required vs optional fields
   - Enums for constrained values
   - Nested records where appropriate
   - Complete documentation strings
4. **Validates Structure**: Ensures schema is valid Avro
5. **Suggests Improvements**: Recommends best practices
6. **Provides Context**: Shows where to register the schema

## Output

The skill generates:
- Complete Avro schema in JSON format
- Field-by-field documentation
- Compatibility notes
- Registration command for MCP server
- Related schemas suggestions

## Templates Used

- **Event Template** (`.claude-code/templates/event-schema.json`):
  - Standard event metadata (eventId, eventType, timestamp, version)
  - Event source tracking
  - Extensible metadata map

- **Entity Template** (`.claude-code/templates/entity-schema.json`):
  - Entity lifecycle fields (id, version, timestamps)
  - Status tracking with enums
  - Audit fields (createdBy, updatedBy)

- **Command Template** (`.claude-code/templates/command-schema.json`):
  - Command identification and tracking
  - Issuer information
  - Optimistic locking support

- **Aggregate Template** (`.claude-code/templates/aggregate-schema.json`):
  - Aggregate versioning for event sourcing
  - State snapshots
  - Child entity management

## Best Practices Applied

- ✅ Proper namespace conventions
- ✅ Required vs optional field distinction
- ✅ Default values where appropriate
- ✅ Comprehensive documentation
- ✅ Backward compatibility considerations
- ✅ Type safety (enums over strings)
- ✅ Consistent naming conventions

## Follow-up Actions

After generation, you can:
1. Review and customize the generated schema
2. Register it to a context (development, staging, production)
3. Check compatibility with existing schemas
4. Generate related schemas (events, commands, etc.)
5. Create test data based on the schema

## Related Skills

- `/schema-validate` - Validate generated schema
- `/schema-register` - Register schema to registry
- `/compatibility-check` - Check compatibility
- `/schema-evolve` - Evolve existing schema

## Notes

- All schemas include proper documentation by default
- Field types are inferred from your description
- Enums are created for constrained values
- Optional fields are wrapped in union types with null
- Generated schemas follow project's naming conventions
