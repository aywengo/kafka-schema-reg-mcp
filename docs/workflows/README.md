# Kafka Schema Registry Workflows

This directory contains documentation for advanced multi-step workflows available in the Kafka Schema Registry MCP server.

## Available Workflows

### 🔄 [Schema Evolution Assistant](./schema-evolution-assistant.md)
**Purpose**: Safely evolve schemas with breaking change analysis and migration strategies  
**Use Case**: When you need to modify existing schemas in production  
**Complexity**: Intermediate to Advanced  

**How to Start**:
- **Direct**: `guided_schema_evolution`
- **With context**: `guided_schema_evolution --subject "user-events" --current_schema "{...}"`
- **Auto-trigger**: Automatically starts when `register_schema_interactive` detects breaking changes
- **Via prompt**: Use the `schema-evolution` prompt for guided commands

---

### 🚀 Schema Migration Wizard
**Purpose**: Migrate schemas between registries or contexts  
**Use Case**: Moving schemas from dev to prod, or between different registry instances  
**Complexity**: Intermediate  

**How to Start**:
- **Direct**: `guided_schema_migration`
- **Via unified MCP**: Available as a tool in the main server

---

### 🏢 Context Reorganization
**Purpose**: Reorganize schemas across different contexts  
**Use Case**: Restructuring schema organization, team-based context management  
**Complexity**: Intermediate  

**How to Start**:
- **Direct**: `guided_context_reorganization`
- **Via unified MCP**: Available as a tool in the main server

---

### 🛡️ Disaster Recovery Setup
**Purpose**: Turn recovery objectives into a backup, recovery and verification plan  
**Use Case**: Disaster recovery planning, restore drills, failure runbooks  
**Complexity**: Advanced  
**Edition**: `admin`

**How to Start**:
- **Direct**: `guided_disaster_recovery`
- **With objectives**: `guided_disaster_recovery --backup_target "s3://schemas-dr" --rpo "under-1-hour" --rto "under-4-hours" --scenarios '["region-outage", "accidental-deletion"]'`

When `backup_target` is missing, the tool asks for it together with the RPO, the RTO
and one primary scenario. It returns a plan:

- `objectives`: the RPO, RTO and scenarios you chose.
- `strategy`: `backup_cadence` (the RPO sets it: hourly, daily or weekly), `recovery`
  (the RTO picks `warm_standby`, `restore_to_prepared_registry` or
  `restore_to_new_registry`) and `standby_required`. A real-time RPO always recovers
  from a warm standby, because restoring a scheduled export loses changes made since it.
- `warnings`: for example, a `schedule` slower than the RPO allows.
- `runbook`: Markdown with backup, recovery, one section per scenario and verification.
  Pass `include_runbook=false` to leave it out.

The tool is a planner and calls nothing. You carry the plan out with the normal tools:
`export_global` or `export_context` for backups, `restore_bundle` to recover (dry run
first, then `apply=true`), and a restore into a scratch registry to verify. See
[`guided_disaster_recovery`](../mcp-tools-reference.md#guided_disaster_recovery) and
[`restore_bundle`](../mcp-tools-reference.md#restore_bundle) for the parameters.

## Workflow Entry Points

### 1. Direct MCP Tool Calls
Each workflow can be started directly using its MCP tool:
```bash
# Schema Evolution
guided_schema_evolution

# Schema Migration  
guided_schema_migration

# Context Reorganization
guided_context_reorganization

# Disaster Recovery
guided_disaster_recovery
```

### 2. Automatic Triggers
Some workflows start automatically based on conditions:
- **Schema Evolution Assistant**: Triggered when `register_schema_interactive` detects breaking changes
- **Migration Workflows**: Can be triggered from compatibility checking tools

### 3. Natural Language Prompts
Use the built-in prompts for guided experiences:
```bash
# Get the schema evolution prompt
"Show me the schema evolution guide"

# Start with natural language
"Help me safely evolve my user schema"
"Guide me through changing my order schema"
"I need to migrate schemas from dev to prod"
```

### 4. Interactive Tools Integration
Workflows integrate with existing interactive tools:
- `register_schema_interactive` → Schema Evolution Assistant (on breaking changes)
- `check_compatibility_interactive` → Evolution recommendations
- `migrate_schema` → Migration workflow options

## Workflow Features

### 🎯 **Multi-Step Guidance**
- Step-by-step progression through complex operations
- Context-aware recommendations based on your environment
- Built-in validation and error handling

### 🔍 **Intelligent Analysis**
- Automatic detection of breaking changes
- Impact assessment for schema modifications
- Consumer compatibility analysis

### 📋 **Strategic Planning**
- Multiple strategy options for each scenario
- Risk assessment and mitigation planning
- Timeline estimation and coordination

### 🤝 **Team Coordination**
- Consumer update planning
- Deployment window coordination
- Rollback procedure documentation

### 📊 **Progress Tracking**
- Real-time workflow progress monitoring
- Task status and completion tracking
- Detailed logging and audit trails

## Getting Started

### For Beginners
1. **Start Simple**: Use the Schema Evolution Assistant with a test schema
2. **Learn the Basics**: Understand compatibility rules and safe changes
3. **Practice**: Try adding optional fields before attempting breaking changes

### For Intermediate Users
1. **Plan Complex Changes**: Use the assistant for breaking changes
2. **Coordinate Teams**: Practice consumer update coordination
3. **Monitor Progress**: Learn to track and manage workflow execution

### For Advanced Users
1. **Multi-Schema Operations**: Handle complex restructuring scenarios
2. **Cross-Registry Migrations**: Manage enterprise-scale migrations
3. **Disaster Recovery**: Plan from RPO and RTO, then drill the restore into a scratch registry

## Best Practices

### 🛡️ **Safety First**
- Always start workflows in development/staging environments
- Use dry-run options when available
- Maintain rollback capabilities for all changes

### 📝 **Documentation**
- Document all workflow decisions and rationale
- Keep track of consumer coordination efforts
- Maintain audit trails for compliance

### 🔄 **Iterative Approach**
- Break complex changes into smaller, manageable steps
- Validate each step before proceeding
- Learn from each workflow execution

### 🤝 **Team Collaboration**
- Involve all stakeholders in workflow planning
- Coordinate deployment windows across teams
- Share workflow outcomes and lessons learned

## Troubleshooting

### Workflow Won't Start
```bash
# Check workflow system status
"Check if workflows are available"
"Show workflow status"
"Test multi-step elicitation system"
```

### Workflow Fails Mid-Execution
```bash
# Check current state
"Show active workflows"
"Get workflow progress for [workflow-id]"
"List active tasks"

# Recovery options
"Cancel workflow [workflow-id]"
"Resume workflow [workflow-id]"
"Show rollback options"
```

### Integration Issues
```bash
# Verify integrations
"Test all registry connections"
"Check my permissions"
"Show current registry mode"
```

## Contributing

When adding new workflows:

1. **Create Documentation**: Add detailed workflow documentation in this directory
2. **Update README**: Add your workflow to the list above
3. **Add Prompts**: Create user-friendly prompts in `mcp_prompts.py`
4. **Integration**: Ensure integration with existing tools where appropriate
5. **Testing**: Add comprehensive tests for workflow scenarios

## Related Documentation

- [Schema Evolution Guide](../schema-evolution-guide.md) - Detailed evolution strategies
- [MCP Tools Reference](../mcp-tools-reference.md) - Complete tool documentation
- [Multi-Step Elicitation](../multi_step_elicitation.md) - Technical workflow details
- [IDE Integration](../ide-integration.md) - IDE-specific workflow setup

---

**Need Help?** 
- Use the troubleshooting prompt: `"Show me troubleshooting guide"`
- Check workflow status: `"Show active workflows"`
- Get quick help: `"Show me quick reference"` 