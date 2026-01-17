# Claude Code Skills for Kafka Schema Registry MCP

This directory contains custom skills designed specifically for the Kafka Schema Registry MCP Server project. These skills provide specialized workflows and automation for common development tasks.

## Available Skills

### 1. Schema Development Skills

#### `/schema-generate`
Generate production-ready Avro schemas from natural language descriptions.

```
/schema-generate event UserRegistered "user registration with userId, email, method"
/schema-generate entity Product "product with id, name, price, inventory"
/schema-generate command CreateOrder "create order with customer, items, payment"
/schema-generate aggregate Order "order managing line items and payments"
```

**Use when:**
- Starting a new schema from scratch
- Need to follow project templates
- Want AI assistance with schema design

---

#### `/schema-evolve`
Safely evolve existing schemas with automatic compatibility checking.

```
/schema-evolve user-profile "add optional phoneNumber field"
/schema-evolve order-event "add REFUNDED enum value"
/schema-evolve product-entity "rename description to productDescription"
```

**Use when:**
- Modifying existing schemas
- Ensuring backward compatibility
- Need migration guidance

---

### 2. Operations Skills

#### `/context-compare`
Compare schemas between contexts to identify differences and plan synchronization.

```
/context-compare development staging
/context-compare staging production --detailed
/context-compare development production --only-differences
```

**Use when:**
- Before deploying to higher environments
- Detecting schema drift between contexts
- Auditing environment synchronization
- Planning releases and promotions

---

#### `/migration-plan`
Generate comprehensive migration plans for moving schemas between contexts or registries.

```
/migration-plan development staging
/migration-plan staging production --with-rollback
/migration-plan registry-a registry-b --dry-run
```

**Use when:**
- Promoting schemas to higher environments
- Setting up disaster recovery
- Consolidating registries
- Need step-by-step migration process

---

### 3. Quality Assurance Skills

#### `/lint-and-test`
Run comprehensive linting and testing workflow with auto-fix capabilities.

```
/lint-and-test quick          # Quick lint check (2-3s)
/lint-and-test fix            # Auto-fix formatting (20-30s)
/lint-and-test ci             # CI mirror check (10-15s)
/lint-and-test test-quick     # Lint + quick tests (5 min)
/lint-and-test test-full      # Lint + full suite (15 min)
/lint-and-test pre-commit     # Pre-commit workflow
/lint-and-test pre-push       # Pre-push workflow
```

**Use when:**
- Before every commit
- Before every push
- Before creating pull requests
- When you have lint/test failures

---

## Skill Categories

### Schema Development
- **Purpose:** Create and evolve schemas efficiently
- **Skills:** schema-generate, schema-evolve
- **Output:** Production-ready Avro schemas

### Operations
- **Purpose:** Manage schema migrations and deployments
- **Skills:** migration-plan
- **Output:** Detailed migration plans with rollback procedures

### Quality Assurance
- **Purpose:** Ensure code quality and test coverage
- **Skills:** lint-and-test
- **Output:** Lint reports and test results

---

## Quick Start

### First Time Setup

1. **Generate your first schema:**
   ```
   /schema-generate event UserCreated "user creation event with userId, email, timestamp"
   ```

2. **Run lint check:**
   ```
   /lint-and-test quick
   ```

3. **Fix any issues:**
   ```
   /lint-and-test fix
   ```

### Daily Workflow

**Morning:**
```
/lint-and-test quick    # Verify clean starting point
```

**During Development:**
```
/schema-generate event OrderPlaced "order placement with orderId, items, total"
/schema-evolve user-profile "add loyaltyPoints field"
/lint-and-test quick    # After making changes
```

**Before Commit:**
```
/lint-and-test pre-commit
git commit -m "feat: add order placement schema"
```

**Before Push:**
```
/lint-and-test pre-push
git push origin your-branch
```

**Before Production:**
```
/migration-plan staging production --with-rollback
```

---

## Skill Invocation Methods

### Method 1: Direct Command
```
/schema-generate event UserRegistered "..."
```

### Method 2: Natural Language
```
"Generate a user registration event schema with userId, email, and timestamp"
```
I'll automatically invoke the appropriate skill.

### Method 3: Interactive
```
"I need to create a new schema"
```
I'll ask clarifying questions and invoke the right skill.

---

## Common Workflows

### Workflow 1: New Feature Development
```
1. /schema-generate event FeatureEvent "..."
2. Review and customize generated schema
3. /lint-and-test quick
4. Register schema to development context
5. /lint-and-test pre-commit
6. git commit
```

### Workflow 2: Schema Evolution
```
1. /schema-evolve existing-schema "add new field"
2. Review compatibility assessment
3. Test in development context
4. /lint-and-test test-quick
5. /lint-and-test pre-commit
6. git commit
```

### Workflow 3: Environment Promotion
```
1. /migration-plan development staging
2. Review migration plan
3. Execute migration during maintenance window
4. Validate migration success
5. /migration-plan staging production
6. Repeat for production
```

### Workflow 4: Pre-Commit
```
1. Make code changes
2. /lint-and-test quick
3. If issues → /lint-and-test fix
4. git diff (review changes)
5. /lint-and-test quick (verify)
6. git commit
```

### Workflow 5: Pre-Push
```
1. /lint-and-test ci
2. If fails → fix issues
3. /lint-and-test test-quick (optional)
4. git push
```

---

## Skill Output Locations

### Generated Files

**Schemas:**
- Generated schemas are displayed in output
- Save to appropriate location for registration
- Include in git commits

**Migration Plans:**
- Saved to `migrations/` directory (auto-created)
- Include timestamps and metadata
- Version controlled

**Test Reports:**
- Saved to `tests/reports/` directory
- Not version controlled (in .gitignore)
- Useful for debugging

**Lint Reports:**
- Displayed in terminal output
- Auto-fixes applied directly to files
- Review with `git diff`

---

## Skill Configuration

### Environment Variables

Skills respect these environment variables:

```bash
# Schema Registry
SCHEMA_REGISTRY_URL=http://localhost:8081
DEFAULT_CONTEXT=development

# MCP Server
MCP_SERVER_PORT=38000

# Testing
SLIM_MODE=false
```

### Project Configuration

Skills read from:
- `.claude-code/config.json` - Main configuration
- `.claude-code/workspace.json` - Workspace settings
- `.claude-code/templates/` - Schema templates
- `pyproject.toml` - Lint configurations

---

## Best Practices

### Schema Generation
1. ✅ Use descriptive names for schemas
2. ✅ Include field-level documentation in descriptions
3. ✅ Specify enum values when applicable
4. ✅ Indicate required vs optional fields
5. ✅ Review generated schema before registering

### Schema Evolution
1. ✅ Always check compatibility first
2. ✅ Test in development context
3. ✅ Add defaults to optional fields
4. ✅ Document breaking changes
5. ✅ Plan rollback strategy

### Migration Planning
1. ✅ Use `--dry-run` first
2. ✅ Review plan before executing
3. ✅ Backup before production migration
4. ✅ Migrate during maintenance windows
5. ✅ Validate after migration

### Linting and Testing
1. ✅ Run quick lint frequently (it's fast!)
2. ✅ Fix lint issues immediately
3. ✅ Never push with lint failures
4. ✅ Run tests before pull requests
5. ✅ Keep virtual environment activated

---

## Troubleshooting

### Skill Not Found
```
Error: Unknown skill /schema-generate
Fix: Ensure you're using the correct syntax with forward slash
```

### Permission Errors
```
Error: Permission denied
Fix: Check file permissions on skill files
      chmod +x .claude-code/skills/*.md
```

### Template Not Found
```
Error: Template 'event' not found
Fix: Verify templates exist in .claude-code/templates/
      ls .claude-code/templates/
```

### Lint Check Fails
```
Error: Black would reformat files
Fix: /lint-and-test fix
```

### Test Failures
```
Error: Docker not running
Fix: Start Docker Desktop
```

---

## Extending Skills

### Creating New Skills

1. Create new skill file in `.claude-code/skills/`
2. Follow the naming convention: `skill-name.md`
3. Include these sections:
   - Skill Name and Description
   - Purpose
   - Usage and Examples
   - What This Skill Does
   - Output
   - Related Skills
   - Best Practices

4. Update this README.md

### Skill File Template

```markdown
# Your Skill Name

**Skill Name:** `/your-skill`
**Category:** Category Name
**Description:** Brief description

## Purpose
Why this skill exists

## Usage
How to invoke it with examples

## What This Skill Does
Step-by-step what happens

## Output
What the skill produces

## Related Skills
Links to related skills

## Best Practices
Tips for using this skill
```

---

## Related Documentation

- **GETTING_STARTED.md** - Contributor guide
- **AGENTS.md** - Development guidelines
- **TESTING_SETUP_GUIDE.md** - Testing documentation
- **.claude-code/README.md** - Claude Code usage guide
- **docs/api-reference.md** - API documentation

---

## Support

For issues or questions:
- Check skill documentation above
- Review GETTING_STARTED.md
- See AGENTS.md for development guidelines
- Check project documentation in `docs/`

---

## Version

Skills version: 1.0.0
Last updated: 2026-01-17
Compatible with: Claude Code, Kafka Schema Registry MCP v2.1.5

---

## Summary

You now have 4 powerful skills at your disposal:

1. **`/schema-generate`** - Create schemas from descriptions
2. **`/schema-evolve`** - Safely evolve existing schemas
3. **`/migration-plan`** - Plan schema migrations
4. **`/lint-and-test`** - Ensure code quality

These skills are designed to work together to provide a seamless development experience for the Kafka Schema Registry MCP project.

**Start using them now!** Try `/schema-generate event UserRegistered "..."` to create your first schema.
