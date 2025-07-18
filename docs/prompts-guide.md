# MCP Prompts Guide

Welcome to the comprehensive guide for **MCP Prompts** in the Kafka Schema Registry MCP Server! This document covers all available prompts that help you interact with Claude Desktop using natural language for schema management tasks.

## 🎯 What are MCP Prompts?

MCP Prompts are **predefined templates and guides** that appear in Claude Desktop to help you:
- **Get started quickly** with common schema operations
- **Learn best practices** for schema management
- **Follow structured workflows** for complex tasks
- **Troubleshoot issues** effectively
- **Understand advanced features** and patterns

## 🚀 Key Improvements (v2.0.5+)

Our prompts now feature:
- **📋 Quick Copy-Paste Commands** - Ready-to-use examples you can copy directly
- **🎯 Action-Oriented Format** - Less reading, more doing
- **📊 Tables and Visual Organization** - Easier to scan and find what you need
- **💡 Pro Tips** - Expert advice integrated throughout
- **🔧 Better Error Handling** - Common errors and immediate solutions
- **⚡ Performance Tips** - Guidance for large-scale operations

## 📋 Available Prompts

The Kafka Schema Registry MCP Server provides **10 comprehensive prompts** covering all aspects of schema management:

### 🚀 **quick-reference** (NEW!)
**Your cheat sheet** - Essential commands and templates for quick access.

**What it includes:**
- Most used commands in copy-paste format
- Common schema templates
- Daily operation commands
- Quick troubleshooting steps
- Pro tips summary

**Best for:** Quick lookups, daily operations, command reference

---

### 🚀 **schema-getting-started**
**Perfect for new users** - provides an overview of basic operations and common tasks.

**What it covers:**
- Quick actions section with copy-paste commands
- Essential first steps with explanations
- Common tasks in table format
- Pro tips for beginners
- Clear next steps

**Best for:** First-time users, onboarding new team members

---

### 📝 **schema-registration**
**Complete guide for registering schemas** with ready-to-use templates.

**What it covers:**
- Copy & paste schema templates
- Complete examples for common schemas
- Schema type comparison table
- Error solutions reference
- Advanced registration patterns

**Best for:** Developers registering new schemas, learning schema patterns

---

### 🏗️ **context-management**
**Master schema contexts** with clear strategies and examples.

**What it covers:**
- Quick context commands
- Three main context strategies with examples
- Operations reference table
- Schema promotion workflow
- Best practices checklist

**Best for:** DevOps teams, multi-environment setups, enterprise governance

---

### 📊 **schema-export**
**Streamlined export guide** with format comparison and use cases.

**What it covers:**
- Quick export commands for all scenarios
- Format comparison (JSON vs Avro IDL)
- Export scope examples
- Common use case table
- Advanced export patterns

**Best for:** Documentation generation, backup procedures, compliance auditing

---

### 🌐 **multi-registry**
**Multi-registry operations** with practical examples and workflows.

**What it covers:**
- Essential multi-registry commands
- Setup pattern examples
- Comparison and migration commands
- Common scenario workflows
- Management best practices

**Best for:** Multi-environment setups, disaster recovery, regional deployments

---

### 🔄 **schema-compatibility**
**Visual guide to schema evolution** with safe/unsafe change examples.

**What it covers:**
- Quick compatibility checks
- Safe changes with ✅ markers
- Breaking changes with ❌ warnings
- Compatibility levels table
- Evolution patterns step-by-step
- Error-to-solution mapping

**Best for:** Schema evolution, ensuring backward compatibility, production safety

---

### 🛠️ **troubleshooting**
**Rapid diagnostic guide** with symptom-to-solution mapping.

**What it covers:**
- Quick diagnostic commands
- Issue categories with symptoms and fixes
- Diagnostic command reference table
- Debug checklist
- Full report generation

**Best for:** Issue resolution, system maintenance, debugging problems

---

### 🔄 **schema-evolution** (NEW!)
**Safe schema evolution assistant** with guided workflows and strategy selection.

**What it covers:**
- Quick start commands for evolution workflows
- When to use the Schema Evolution Assistant
- Complete workflow explanation (8-step process)
- Common evolution scenarios with examples
- Evolution strategies comparison (Direct Update, Multi-Version Migration, Dual Support, Blue-Green)
- Best practices and troubleshooting
- Learning path from beginner to advanced

**Best for:** Production schema changes, breaking change management, complex evolution scenarios

---

### 🚀 **advanced-workflows**
**Enterprise patterns** with real-world examples and code snippets.

**What it covers:**
- CI/CD integration with YAML examples
- Enterprise governance patterns
- Performance optimization techniques
- Monitoring dashboard commands
- Complex workflow examples
- Disaster recovery procedures

**Best for:** Enterprise deployments, complex automation, team coordination

## 🎮 How to Use Prompts

### In Claude Desktop

1. **Quick Access Methods:**
   ```
   "Show me the quick reference"
   "Help me register a schema"
   "I need to troubleshoot an issue"
   "Show multi-registry commands"
   "Show me the schema evolution guide"
   "Help me safely evolve my schema"
   ```

2. **Direct Usage:**
   - Copy commands directly from prompts
   - Modify templates for your use case
   - Follow step-by-step workflows

3. **Interactive Help:**
   - Ask follow-up questions
   - Request specific examples
   - Get clarification on any step

### Example Workflows

**For New Users:**
```
Human: I'm new to this, where should I start?

Claude: Let me show you the getting started guide with quick actions you can try right away...
[Displays schema-getting-started prompt with copy-paste commands]
```

**For Schema Evolution:**
```
Human: I need to safely change my user schema in production

Claude: I'll show you the Schema Evolution Assistant guide with step-by-step workflows...
[Displays schema-evolution prompt with evolution strategies and examples]
```

**For Troubleshooting:**
```
Human: My schema registration is failing, help!

Claude: Let me show you the troubleshooting guide with diagnostic commands...
[Displays troubleshooting prompt with symptom-to-solution mapping]
```

## 💡 Best Practices for Using Prompts

1. **Start with quick-reference** for daily operations
2. **Use specific prompts** when diving into a topic
3. **Copy commands directly** and modify as needed
4. **Follow the workflows** step-by-step
5. **Use schema-evolution prompt** for any production schema changes
6. **Ask for clarification** on any confusing parts

## 🔄 Schema Evolution Integration

The **schema-evolution** prompt integrates seamlessly with the Schema Evolution Assistant workflow:

### **Direct Integration**
```
Human: "Show me the schema evolution guide"
→ Displays comprehensive evolution prompt
→ Copy commands to start workflows
→ Get guided through 8-step process
```

### **Natural Language Triggers**
```
Human: "Help me safely evolve my user schema"
→ Automatically starts Schema Evolution Assistant
→ Pre-populated with context from your request
→ Interactive workflow with step-by-step guidance
```

### **Workflow Entry Points**
- **Direct Tool Call**: `guided_schema_evolution`
- **Natural Language**: "Start schema evolution assistant"
- **Auto-Trigger**: When `register_schema_interactive` detects breaking changes
- **Via Prompts**: Use evolution guide for copy-paste commands

## 🔧 Prompt Customization

While these prompts cover most use cases, you can:
- Request modifications to existing prompts
- Ask for examples specific to your schemas
- Get help creating custom workflows
- Combine multiple prompts for complex scenarios

## 📚 Additional Resources

- **[API Reference](api-reference.md)** - Complete tool documentation
- **[Use Cases](use-cases.md)** - Real-world scenarios
- **[Examples](../examples/)** - Code samples and templates

---

**Need help?** Just ask: "Show me the quick reference" to get started!