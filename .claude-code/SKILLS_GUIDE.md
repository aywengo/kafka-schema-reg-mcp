# Claude Code Skills Quick Start Guide

Welcome to Claude Code Skills for the Kafka Schema Registry MCP project! This guide will get you productive with skills in under 5 minutes.

## What Are Skills?

Skills are specialized, reusable workflows that automate common development tasks. Think of them as powerful shortcuts that combine multiple steps into a single command.

## The 5 Essential Skills

### 1. `/schema-generate` - Create Schemas Fast

**What it does:** Generates production-ready Avro schemas from plain English

**When to use:** Starting a new schema from scratch

**Quick example:**
```
/schema-generate event UserRegistered "user registration with userId, email, registrationMethod enum, timestamp"
```

**Output:** Complete Avro schema with proper types, documentation, and structure

---

### 2. `/schema-evolve` - Evolve Schemas Safely

**What it does:** Modifies existing schemas while checking compatibility

**When to use:** Adding fields, changing types, or updating schemas

**Quick example:**
```
/schema-evolve user-profile "add optional phoneNumber and preferences fields"
```

**Output:** Evolved schema + compatibility analysis + migration guidance

---

### 3. `/migration-plan` - Plan Deployments

**What it does:** Creates detailed migration plans between environments

**When to use:** Promoting schemas from dev → staging → production

**Quick example:**
```
/migration-plan development staging
```

**Output:** Step-by-step migration plan + rollback procedure + validation steps

---

### 4. `/context-compare` - Compare Schemas Between Environments

**What it does:** Compares schemas across different contexts to identify differences and plan synchronization

**When to use:** Before migrations, during environment audits, or investigating schema drift

**Quick examples:**
```
/context-compare development staging
/context-compare staging production --detailed
/context-compare development production --only-differences
```

**Output:** Detailed comparison report + difference analysis + synchronization recommendations

---

### 5. `/lint-and-test` - Ensure Quality

**What it does:** Runs linting and testing workflows automatically

**When to use:** Before every commit and push

**Quick examples:**
```
/lint-and-test quick        # Before commit (2-3 seconds)
/lint-and-test fix          # Auto-fix formatting issues
/lint-and-test pre-push     # Before pushing (10-15 seconds)
```

**Output:** Pass/fail status + auto-fixes + detailed error reports

---

## Your First 5 Minutes

### Minute 1: Generate a Schema
```
/schema-generate event UserLoggedIn "user login event with userId, loginTime, ipAddress, deviceType"
```

Review the generated schema. Notice:
- ✅ Proper Avro structure
- ✅ Field documentation
- ✅ Correct types
- ✅ Standard event metadata

---

### Minute 2: Evolve a Schema
```
/schema-evolve user-profile "add optional socialLoginProvider field with enum values: GOOGLE, FACEBOOK, GITHUB"
```

Review the compatibility analysis:
- ✅ Backward compatible? (Can old consumers read new data?)
- ✅ Forward compatible? (Can new consumers read old data?)
- ✅ Migration steps
- ✅ Rollback plan

---

### Minute 3: Plan a Migration
```
/migration-plan development staging
```

See the detailed plan:
- 📋 Schema inventory
- 🔍 Compatibility checks
- 📝 Step-by-step execution
- ⏮️ Rollback procedure
- ✅ Validation checklist

---

### Minute 4: Run Quality Checks
```
/lint-and-test quick
```

See instant feedback:
- ✅ Formatting correct?
- ✅ Imports sorted?
- ✅ Code style compliant?

If issues found:
```
/lint-and-test fix
```

Watch it auto-fix:
- 🔧 Formats with Black
- 🔧 Sorts imports with isort
- ✅ Ready to commit!

---

### Minute 5: Complete Workflow
```
# 1. Generate schema
/schema-generate entity Product "product with id, name, price, inventory, status"

# 2. Check quality
/lint-and-test quick

# 3. Commit
git add .
git commit -m "feat: add product entity schema"

# 4. Pre-push check
/lint-and-test pre-push

# 5. Push
git push
```

**Congratulations!** You've just completed a full development cycle with skills.

---

## Daily Workflow Cheat Sheet

### Morning Setup
```bash
source .venv/bin/activate   # Activate environment
/lint-and-test quick        # Verify clean state
```

### Creating Schemas
```bash
/schema-generate <type> <name> "<description>"
# Review output
# Save schema
# Test locally
```

### Evolving Schemas
```bash
/schema-evolve <subject> "<changes>"
# Review compatibility
# Test evolution
# Document changes
```

### Before Commit
```bash
/lint-and-test quick
# If fails: /lint-and-test fix
git diff                    # Review auto-fixes
/lint-and-test quick        # Verify fixes
git commit -m "..."
```

### Before Push
```bash
/lint-and-test pre-push
# Must pass!
git push
```

### Before Production
```bash
/migration-plan staging production
# Review plan carefully
# Execute during maintenance window
# Validate migration
```

---

## Skill Invocation Methods

### Method 1: Direct Command (Recommended)
```
/schema-generate event UserCreated "..."
```
✅ Fastest and most explicit

### Method 2: Natural Language
```
"Generate a user creation event schema with userId, email, and timestamp"
```
✅ I'll automatically invoke `/schema-generate`

### Method 3: Interactive
```
"I need help creating a schema"
```
✅ I'll ask clarifying questions then invoke the right skill

---

## Common Scenarios

### Scenario 1: New Feature Development
```
Developer: "I'm building a new order processing feature"

Step 1: Generate event schemas
/schema-generate event OrderCreated "order created with orderId, customerId, items, total"
/schema-generate event OrderConfirmed "order confirmed with orderId, confirmationTime"
/schema-generate event OrderShipped "order shipped with orderId, trackingNumber, carrier"

Step 2: Generate entity schema
/schema-generate entity Order "order entity with id, customer, items, status, total"

Step 3: Generate command schemas
/schema-generate command CreateOrder "create order with customerId, items, shippingAddress"
/schema-generate command ConfirmOrder "confirm order with orderId, paymentInfo"

Step 4: Quality check
/lint-and-test quick

Step 5: Commit
git commit -m "feat: add order processing schemas"
```

---

### Scenario 2: Schema Evolution
```
Developer: "Need to add customer preferences to user profile"

Step 1: Evolve schema
/schema-evolve user-profile "add preferences record with emailNotifications bool, smsNotifications bool, language string"

Step 2: Review compatibility
# Check output for compatibility assessment

Step 3: Test in development
# Register to development context
# Test with sample data

Step 4: Quality check
/lint-and-test quick

Step 5: Commit
git commit -m "feat: add user preferences to profile schema"
```

---

### Scenario 3: Production Promotion
```
DevOps: "Ready to promote schemas to production"

Step 1: Plan staging migration
/migration-plan development staging

Step 2: Review plan
# Check compatibility
# Review rollback procedure

Step 3: Execute staging migration
# Follow plan steps
# Validate success

Step 4: Plan production migration
/migration-plan staging production

Step 5: Schedule maintenance window
# Execute during low-traffic period
# Monitor closely
# Validate thoroughly
```

---

### Scenario 4: Pre-Commit Quality Check
```
Developer: "Ready to commit my changes"

Step 1: Quick lint
/lint-and-test quick

Output: ❌ Black would reformat 3 files

Step 2: Auto-fix
/lint-and-test fix

Output: ✅ Reformatted files, fixed imports

Step 3: Review changes
git diff

Step 4: Verify fixes
/lint-and-test quick

Output: ✅ All checks passed!

Step 5: Commit
git commit -m "feat: add new schema"
```

---

## Pro Tips

### Tip 1: Use Skills Frequently
Skills are fast! Don't hesitate to run them often:
```
/lint-and-test quick    # Takes 2-3 seconds
/lint-and-test quick    # Run after EVERY change
/lint-and-test quick    # Seriously, it's that fast
```

### Tip 2: Let Skills Auto-Fix
Don't manually fix formatting:
```
❌ Manual: Fix each import, adjust line lengths, reformat...
✅ Skill: /lint-and-test fix (done in 20 seconds)
```

### Tip 3: Chain Skills in Workflows
```
/schema-generate event UserCreated "..."
/schema-evolve user-profile "..."
/lint-and-test fix
/migration-plan development staging
```

### Tip 4: Use Natural Language
```
Instead of remembering exact syntax:
"Generate an order event schema with orderId, items, and total"

I'll invoke: /schema-generate event Order "..."
```

### Tip 5: Always Review Skill Output
Skills generate comprehensive output:
- ✅ Read the compatibility analysis
- ✅ Review migration plans before executing
- ✅ Check auto-fixes with `git diff`
- ✅ Understand what changed and why

---

## Troubleshooting

### "Skill not found"
**Problem:** `/schema-generate` returns error

**Solution:** Ensure you're using the correct command with `/`
```
❌ schema-generate
✅ /schema-generate
```

---

### "Template not found"
**Problem:** Can't find event template

**Solution:** Verify templates exist
```bash
ls .claude-code/templates/
# Should show: event-schema.json, entity-schema.json, etc.
```

---

### "Lint check fails"
**Problem:** `/lint-and-test quick` shows errors

**Solution:** Auto-fix them
```
/lint-and-test fix
git diff  # Review changes
```

---

### "Docker not running"
**Problem:** Tests fail with Docker error

**Solution:** Start Docker Desktop
```bash
# Verify Docker is running
docker ps
```

---

## Next Steps

Now that you know the basics:

1. **Practice with Real Schemas**
   - Generate schemas for your actual use cases
   - Evolve them as requirements change
   - Plan real migrations

2. **Integrate into Your Workflow**
   - Use `/lint-and-test` before every commit
   - Use `/migration-plan` before deployments
   - Use schema skills for all schema work

3. **Read Detailed Documentation**
   - `.claude-code/skills/README.md` - Complete skills reference
   - `.claude-code/skills/<skill-name>.md` - Individual skill docs
   - `GETTING_STARTED.md` - Full contributor guide

4. **Customize and Extend**
   - Create your own skills
   - Modify templates
   - Adjust workflows

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SKILLS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SCHEMA DEVELOPMENT                                         │
│    /schema-generate <type> <name> "<description>"          │
│    /schema-evolve <subject> "<changes>"                    │
│                                                             │
│  OPERATIONS                                                 │
│    /migration-plan <source> <target>                       │
│                                                             │
│  QUALITY ASSURANCE                                          │
│    /lint-and-test quick      # Pre-commit (2-3s)           │
│    /lint-and-test fix        # Auto-fix (20-30s)           │
│    /lint-and-test pre-push   # Pre-push (10-15s)           │
│                                                             │
│  WORKFLOW                                                   │
│    1. /schema-generate ...   # Create schema               │
│    2. /lint-and-test quick   # Check quality               │
│    3. git commit             # Commit changes              │
│    4. /lint-and-test pre-push # Pre-push check             │
│    5. git push               # Push to remote              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary

You now have **5 powerful skills** that will supercharge your development workflow:

1. **`/schema-generate`** - Create schemas in seconds
2. **`/schema-evolve`** - Evolve schemas safely
3. **`/migration-plan`** - Plan deployments confidently
4. **`/context-compare`** - Compare schemas between environments
5. **`/lint-and-test`** - Ensure quality automatically

**Start using them today!** Try:
```
/schema-generate event YourFirstEvent "describe your event here"
```

**Questions?** Check:
- `.claude-code/skills/README.md` - Complete reference
- `GETTING_STARTED.md` - Contributor guide
- `AGENTS.md` - Development guidelines

**Happy coding with Claude Code Skills! 🚀**

---

**Version:** 1.0.0
**Last Updated:** 2026-01-17
**Author:** Claude Code Configuration Team
