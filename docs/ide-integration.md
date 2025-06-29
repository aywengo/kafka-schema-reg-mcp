# IDE & AI Assistant Integration Guide

This guide provides comprehensive instructions for integrating the Kafka Schema Registry MCP Server v2.0.0 with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance** with popular development environments and AI-powered coding assistants, including enhanced authentication, async operations testing, and multi-registry support.

## 🔵 VS Code Integration

### Essential Extensions

Install these VS Code extensions for optimal development experience:

```bash
# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-vscode.vscode-json
code --install-extension humao.rest-client
code --install-extension ms-azuretools.vscode-docker
code --install-extension redhat.vscode-yaml
```

### Workspace Configuration

Create `.vscode/settings.json` in your project root:

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/test_integration.py"],
    "rest-client.environmentVariables": {
        "local": {
            "mcpServer": "http://localhost:38000",
            "schemaRegistry": "http://localhost:38081"
        },
        "staging": {
            "mcpServer": "http://staging.example.com:38000",
            "schemaRegistry": "http://staging.example.com:38081"
        },
        "production": {
            "mcpServer": "http://prod.example.com:38000",
            "schemaRegistry": "http://prod.example.com:38081"
        }
    },
    "files.associations": {
        "*.avsc": "json",
        "docker-compose*.yml": "yaml"
    },
    "editor.formatOnSave": true,
    "python.formatting.provider": "black"
}
```

### Interactive API Testing

Create `.vscode/requests.http` for testing your MCP server endpoints:

```http
@mcpServer = {{$dotenv %MCP_SERVER_URL}}
@context = development

### Health Check
GET {{mcpServer}}/
Accept: application/json

### List All Contexts
GET {{mcpServer}}/contexts
Accept: application/json

### Create Development Context
POST {{mcpServer}}/contexts/{{context}}
Content-Type: application/json

### Register User Schema
POST {{mcpServer}}/schemas
Content-Type: application/json

{
    "subject": "user-value",
    "schema": {
        "type": "record",
        "name": "User",
        "namespace": "com.example.schemas",
        "fields": [
            {
                "name": "id", 
                "type": "int",
                "doc": "Unique user identifier"
            },
            {
                "name": "name", 
                "type": "string",
                "doc": "Full name of the user"
            },
            {
                "name": "email", 
                "type": ["null", "string"], 
                "default": null,
                "doc": "User's email address"
            },
            {
                "name": "createdAt",
                "type": "long",
                "doc": "Timestamp when user was created"
            }
        ]
    },
    "schemaType": "AVRO",
    "context": "{{context}}"
}

### Get Schema with Version
GET {{mcpServer}}/schemas/user-value?context={{context}}&version=latest
Accept: application/json

### Get All Schema Versions
GET {{mcpServer}}/schemas/user-value/versions?context={{context}}
Accept: application/json

### Check Schema Compatibility
POST {{mcpServer}}/compatibility
Content-Type: application/json

{
    "subject": "user-value",
    "schema": {
        "type": "record",
        "name": "User",
        "namespace": "com.example.schemas",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "createdAt", "type": "long"},
            {
                "name": "lastLoginAt", 
                "type": ["null", "long"], 
                "default": null,
                "doc": "Timestamp of last login"
            }
        ]
    },
    "schemaType": "AVRO",
    "context": "{{context}}"
}

### List Subjects in Context
GET {{mcpServer}}/subjects?context={{context}}
Accept: application/json

### Delete Subject
DELETE {{mcpServer}}/subjects/user-value?context={{context}}
Accept: application/json

### === EXPORT FUNCTIONALITY TESTING ===

### Export Single Schema as JSON
GET {{mcpServer}}/export/schemas/user-value?context={{context}}&format=json
Accept: application/json

### Export Single Schema as Avro IDL
GET {{mcpServer}}/export/schemas/user-value?context={{context}}&format=avro_idl
Accept: text/plain

### Export Subject (All Versions)
POST {{mcpServer}}/export/subjects/user-value?context={{context}}
Content-Type: application/json

{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}

### Export Context as JSON
POST {{mcpServer}}/export/contexts/{{context}}
Content-Type: application/json

{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}

### Export Context as ZIP Bundle
POST {{mcpServer}}/export/contexts/{{context}}
Content-Type: application/json

{
    "format": "bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}

### Export Global Registry
POST {{mcpServer}}/export/global
Content-Type: application/json

{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}

### List Exportable Subjects
GET {{mcpServer}}/export/subjects?context={{context}}
Accept: application/json

### Generate Documentation Export
POST {{mcpServer}}/export/contexts/{{context}}
Content-Type: application/json

{
    "format": "bundle",
    "include_metadata": true,
    "include_config": false,
    "include_versions": "latest"
}

### === ASYNC OPERATIONS TESTING (v1.7.0) ===

### Check Task Queue Status
GET {{mcpServer}}/tasks/status
Accept: application/json

### Get Task Progress
GET {{mcpServer}}/tasks/{{taskId}}/progress
Accept: application/json

### List Active Tasks
GET {{mcpServer}}/tasks/active
Accept: application/json

### Cancel Task
POST {{mcpServer}}/tasks/{{taskId}}/cancel
Content-Type: application/json

### === MIGRATION FUNCTIONALITY TESTING ===

### Migrate Schema Between Contexts
POST {{mcpServer}}/migrate/schema
Content-Type: application/json

{
    "subject": "user-value",
    "source_context": "development",
    "target_context": "staging",
    "version": "latest",
    "dry_run": false,
    "overwrite": false
}

### Migrate Entire Context
POST {{mcpServer}}/migrate/context
Content-Type: application/json

{
    "source_context": "development",
    "target_context": "staging",
    "dry_run": false,
    "overwrite": false,
    "include_config": true
}

### Dry Run Migration Preview
POST {{mcpServer}}/migrate/context
Content-Type: application/json

{
    "source_context": "development",
    "target_context": "staging",
    "dry_run": true,
    "include_config": true
}

### Multi-Registry Migration (Multi-Registry MCP Server)
POST {{mcpServer}}/migrate/cross-registry
Content-Type: application/json

{
    "source_registry": "primary",
    "target_registry": "disaster_recovery",
    "contexts": ["production", "staging"],
    "dry_run": false,
    "include_config": true
}

### Migration Status Check
GET {{mcpServer}}/migrate/status?task_id={{migration_task_id}}
Accept: application/json

### Migration History
GET {{mcpServer}}/migrate/history?context={{context}}&limit=10
Accept: application/json

### Debug Configuration

Create `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug MCP Server",
            "type": "python",
            "request": "launch",
            "program": "mcp_server.py",
            "console": "integratedTerminal",
            "env": {
                "SCHEMA_REGISTRY_URL": "http://localhost:8081",
                "PYTHONPATH": "${workspaceFolder}"
            },
            "args": []
        },
        {
            "name": "Debug Integration Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/test_integration.py",
                "-v",
                "--tb=short"
            ],
            "console": "integratedTerminal",
            "env": {
                "MCP_SERVER_URL": "http://localhost:38000",
                "SCHEMA_REGISTRY_URL": "http://localhost:38081"
            }
        },
        {
            "name": "Debug Unit Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/test_unit.py",
                "-v"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

### Tasks Configuration

Create `.vscode/tasks.json` for automated workflows:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Services",
            "type": "shell",
            "command": "docker-compose up -d",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            }
        },
        {
            "label": "Run Integration Tests",
            "type": "shell",
            "command": "./tests/run_integration_tests.sh",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            },
            "dependsOn": "Start Services"
        },
        {
            "label": "Stop Services",
            "type": "shell",
            "command": "docker-compose down",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        },
        {
            "label": "View Logs",
            "type": "shell",
            "command": "docker-compose logs -f",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Rebuild MCP Server",
            "type": "shell",
            "command": "docker-compose build --no-cache mcp-server && docker-compose restart mcp-server",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        },
        {
            "label": "Test Export Functionality",
            "type": "shell",
            "command": "pytest tests/test_integration.py -k export -v",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            },
            "dependsOn": "Start Services"
        },
        {
            "label": "Generate Schema Documentation",
            "type": "shell",
            "command": "mkdir -p docs/exports && curl -X POST http://localhost:38000/export/global -H 'Content-Type: application/json' -d '{\"format\": \"bundle\", \"include_metadata\": true, \"include_config\": true, \"include_versions\": \"all\"}' --output docs/exports/schema_docs_$(date +%Y%m%d).zip",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        },
        {
            "label": "Export Production Backup",
            "type": "shell",
            "command": "mkdir -p backups && curl -X POST http://localhost:38000/export/contexts/production -H 'Content-Type: application/json' -d '{\"format\": \"bundle\", \"include_metadata\": true, \"include_config\": true, \"include_versions\": \"all\"}' --output backups/production_backup_$(date +%Y%m%d_%H%M%S).zip",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        }
    ]
}
```

---

## 🤖 Claude Code Integration

### MCP Server as AI Context Provider

The Schema Registry MCP server enhances Claude's capabilities by providing real-time schema management context.

### Setup Instructions

1. **Install Claude Dev Extension**
```bash
code --install-extension claude-ai.claude-dev
```

2. **Configure MCP Integration**

Create `claude_config.json` in your project root:

```json
{
    "mcp_servers": {
        "kafka-schema-registry": {
            "url": "http://localhost:38000",
            "capabilities": [
                "schema_management",
                "context_management", 
                "compatibility_checking",
                "subject_management",
                "migration_operations",
                "export_functionality"
            ],
            "contexts": [
                "development",
                "staging", 
                "production"
            ]
        },
        "kafka-schema-registry-multi": {
            "url": "http://localhost:39000",
            "capabilities": [
                "multi_registry_management",
                "cross_registry_migration",
                "disaster_recovery",
                "registry_synchronization",
                "bulk_operations"
            ],
            "registries": [
                "primary",
                "disaster_recovery",
                "development"
            ]
        }
    },
    "workflows": {
        "schema_development": {
            "name": "Schema Development Workflow",
            "description": "End-to-end schema development and evolution process",
            "steps": [
                {
                    "name": "analyze_existing_schemas",
                    "description": "Analyze current schemas in target context",
                    "endpoint": "/subjects"
                },
                {
                    "name": "design_new_schema", 
                    "description": "Design new schema or evolution",
                    "type": "interactive"
                },
                {
                    "name": "check_compatibility",
                    "description": "Validate compatibility with existing schemas",
                    "endpoint": "/compatibility"
                },
                {
                    "name": "register_schema",
                    "description": "Register the new schema version",
                    "endpoint": "/schemas"
                },
                {
                    "name": "validate_integration",
                    "description": "Verify integration and test",
                    "type": "validation"
                }
            ]
        },
        "multi_environment_promotion": {
            "name": "Multi-Environment Schema Promotion",
            "description": "Promote schemas from development to production",
            "steps": [
                "validate_development_schema",
                "check_staging_compatibility", 
                "migrate_to_staging",
                "validate_staging_deployment",
                "check_production_compatibility",
                "migrate_to_production"
            ]
        },
        "disaster_recovery_setup": {
            "name": "Disaster Recovery Configuration",
            "description": "Set up and validate disaster recovery registry",
            "server": "kafka-schema-registry-multi",
            "steps": [
                "validate_primary_registry",
                "setup_dr_registry",
                "perform_initial_sync",
                "validate_sync_integrity",
                "setup_continuous_sync",
                "test_failover_scenario"
            ]
        },
        "migration_workflow": {
            "name": "Schema Migration Workflow",
            "description": "Migrate schemas between contexts or registries",
            "steps": [
                "analyze_migration_scope",
                "generate_migration_plan",
                "execute_dry_run",
                "validate_dry_run_results",
                "execute_migration",
                "validate_migration_success"
            ]
        }
    }
}
```

### Claude-Assisted Workflows

#### Schema Evolution Assistant

Use these prompts to leverage Claude for schema evolution:

```text
SCHEMA EVOLUTION PROMPT:

Using the Kafka Schema Registry MCP server at localhost:38000:

1. Analyze the current 'user-events' schema in the 'production' context
2. I need to add the following fields while maintaining backward compatibility:
   - userId: string (required)
   - sessionId: string (optional, default null) 
   - deviceInfo: record with deviceType and osVersion
3. Generate the evolved schema JSON
4. Check compatibility against the existing production schema
5. If compatible, provide the registration command
6. If not compatible, suggest alternative approaches

Context: We're adding user session tracking to improve analytics while ensuring existing consumers continue to work.

Current production schema endpoint: GET /schemas/user-events?context=production
Compatibility check endpoint: POST /compatibility
Registration endpoint: POST /schemas

Please walk through this step by step and provide curl commands for each step.
```

#### Migration Strategy Assistant

```text
MIGRATION STRATEGY PROMPT:

Using the Schema Registry MCP servers (single: localhost:38000, multi: localhost:39000):

Current situation:
- Development context: 25 schemas actively developed
- Staging context: 18 schemas (missing 7 latest developments) 
- Production context: 15 schemas (missing 10 latest developments)
- Need to promote stable schemas from dev → staging → production

Requirements:
1. Identify schemas ready for promotion (stable, tested, compatible)
2. Generate migration plan with dependency order
3. Perform dry-run migrations to validate
4. Execute actual migrations with validation
5. Set up automated promotion pipeline

Migration endpoints available:
- Context migration: POST /migrate/context  
- Schema migration: POST /migrate/schema
- Migration status: GET /migrate/status
- Migration history: GET /migrate/history

Please provide:
1. Analysis commands to assess current state
2. Migration plan with specific curl commands
3. Validation steps for each migration
4. Rollback procedures if needed
5. Automation script template

Context analysis: Start by comparing contexts and identifying differences.
```

#### Multi-Registry Disaster Recovery Assistant

```text
DISASTER RECOVERY SETUP PROMPT:

Using the Multi-Registry MCP server at localhost:39000:

Current setup:
- Primary registry: production schemas (localhost:8081)
- Need to establish disaster recovery registry (localhost:8082)
- Must maintain real-time synchronization
- Requirement for <5 minute RPO (Recovery Point Objective)

Tasks:
1. Analyze primary registry current state
2. Set up disaster recovery registry configuration
3. Perform initial bulk synchronization
4. Validate synchronization integrity
5. Set up continuous synchronization
6. Test failover and fallback procedures

Multi-registry endpoints:
- Registry health: GET /registries/{name}/health
- Cross-registry sync: POST /sync/registries
- Registry comparison: GET /compare/registries
- Failover test: POST /failover/test
- Bulk migration: POST /migrate/bulk

Please provide:
1. Current state analysis commands
2. DR setup and validation steps
3. Synchronization strategy with specific configurations
4. Failover testing procedure
5. Monitoring and alerting recommendations
6. Complete disaster recovery runbook

Start with registry health checks and current schema inventory.
```

#### Context Strategy Advisor

```text
CONTEXT STRATEGY PROMPT:

Help me design a comprehensive schema context strategy for our organization:

Current situation:
- 50+ microservices across 8 teams
- 3 environments: development, staging, production  
- 200+ different event types
- Compliance requirements: GDPR (EU), CCPA (California)
- Teams: Identity, Payments, Analytics, Notifications, Orders, Inventory, Support, Admin

Requirements:
1. Team autonomy for schema evolution
2. Environment isolation 
3. Compliance-specific schema variants
4. Shared schemas for cross-team integration
5. Clear promotion workflow with migration support
6. Automated backup and export strategy

Using the MCP server endpoints:
- Context management: /contexts
- Schema operations: /schemas
- Subject listing: /subjects
- Export capabilities: /export/*
- Migration operations: /migrate/*

Please provide:
1. Recommended context naming strategy
2. Context creation commands
3. Schema governance policies
4. Migration-based promotion workflow design
5. Export and backup strategies
6. Example implementations for 2-3 teams

Be specific and provide actual curl commands and context names.
```

#### Export Strategy Advisor

```text
EXPORT STRATEGY PROMPT:

Design a comprehensive export and backup strategy for our schema registry:

Current needs:
- Daily automated backups with migration capability
- Environment-specific exports for promotion via migration
- Documentation generation for developer onboarding
- Compliance reporting (quarterly GDPR, SOX audits)
- Disaster recovery capabilities with cross-registry migration

Using the v1.3.0+ export and migration endpoints:
- Single schema: GET /export/schemas/{subject}
- Subject export: POST /export/subjects/{subject}
- Context export: POST /export/contexts/{context}
- Global export: POST /export/global
- Context migration: POST /migrate/context
- Schema migration: POST /migrate/schema
- Cross-registry migration: POST /migrate/cross-registry (multi-registry server)

Export formats available:
- JSON: Structured data with metadata
- Avro IDL: Human-readable documentation
- ZIP Bundle: Organized file packages

Please provide:
1. Automated backup script design with migration capabilities
2. Documentation generation workflow
3. Environment promotion export + migration strategy
4. Compliance reporting automation
5. Disaster recovery export + migration procedures
6. Storage and retention policies
7. Migration-based deployment pipelines

Include specific curl commands, migration configurations, and script examples.
```

### Integration Patterns

#### 1. **Schema Design Assistant**
- Analyze existing schemas for patterns and conventions
- Generate compatible schema evolutions
- Suggest optimal field naming and types
- Validate Avro schema syntax and best practices

#### 2. **Context Strategy Advisor**  
- Design multi-environment deployment strategies
- Plan schema migration and promotion workflows
- Recommend governance policies and standards
- Create context-specific testing scenarios

#### 3. **Compatibility Analyzer**
- Automated compatibility checking across contexts
- Breaking change detection and impact analysis
- Evolution path recommendations
- Risk assessment for schema changes

#### 4. **Code Generation Assistant**
- Generate producer/consumer code from schemas
- Create test data generators
- Build migration scripts
- Generate documentation

#### 5. **Export and Backup Automation**
- Automated backup script generation
- Documentation export workflows
- Environment promotion pipelines
- Compliance reporting automation

#### 6. **Schema Documentation Generator**
- Convert JSON schemas to human-readable Avro IDL
- Generate comprehensive API documentation
- Create developer onboarding materials
- Build schema evolution guides

---

## 🧠 Claude Code Integration

### AI-Native Schema Development with Claude Code

Claude Code provides a specialized development environment that leverages the Schema Registry MCP server for intelligent, context-aware schema management and development workflows.

### Setup & Configuration

#### 1. Claude Code MCP Server Configuration

Create `claude-code-config.json` in your project root:

```json
{
    "mcp_servers": {
        "kafka-schema-registry": {
            "command": "python",
            "args": ["kafka_schema_registry_unified_mcp.py"],
            "env": {
                "SCHEMA_REGISTRY_URL": "http://localhost:8081",
                "MCP_SERVER_PORT": "38000",
                "DEFAULT_CONTEXT": "development"
            },
            "capabilities": [
                "schema_management",
                "context_management",
                "compatibility_checking",
                "migration_operations",
                "export_functionality",
                "multi_registry_support"
            ]
        },
        "kafka-schema-registry-multi": {
            "command": "python", 
            "args": ["remote-mcp-server.py"],
            "env": {
                "MULTI_REGISTRY_CONFIG": "multi_registry.env",
                "MCP_SERVER_PORT": "39000"
            },
            "capabilities": [
                "multi_registry_management",
                "cross_registry_migration",
                "disaster_recovery",
                "bulk_operations"
            ]
        }
    },
    "claude_code_settings": {
        "auto_completion": {
            "schema_fields": true,
            "context_aware": true,
            "compatibility_hints": true
        },
        "real_time_validation": {
            "avro_syntax": true,
            "compatibility_checking": true,
            "context_validation": true
        },
        "intelligent_suggestions": {
            "schema_evolution": true,
            "migration_planning": true,
            "best_practices": true
        }
    }
}
```

#### 2. Claude Code Workspace Configuration

Create `.claude-code/workspace.json`:

```json
{
    "workspace_type": "kafka_schema_management",
    "mcp_integration": {
        "enabled": true,
        "servers": ["kafka-schema-registry", "kafka-schema-registry-multi"],
        "auto_context_detection": true,
        "smart_completion": true
    },
    "ai_assistance": {
        "schema_generation": {
            "enabled": true,
            "templates": [
                "event_schema",
                "entity_schema", 
                "command_schema",
                "aggregate_schema"
            ],
            "validation_mode": "real_time"
        },
        "migration_assistance": {
            "enabled": true,
            "auto_planning": true,
            "compatibility_analysis": true,
            "rollback_planning": true
        },
        "documentation_generation": {
            "enabled": true,
            "formats": ["markdown", "avro_idl", "json_schema"],
            "auto_update": true
        }
    },
    "development_contexts": {
        "default": "development",
        "available": ["development", "staging", "production", "testing"],
        "context_isolation": true
    }
}
```

#### 3. Claude Code Schema Templates

Create `.claude-code/templates/` directory with schema templates:

**Event Schema Template** (`.claude-code/templates/event-schema.json`):
```json
{
    "template_name": "Event Schema",
    "description": "Template for domain event schemas",
    "schema_template": {
        "type": "record",
        "name": "{{EventName}}Event",
        "namespace": "{{namespace}}",
        "doc": "{{event_description}}",
        "fields": [
            {
                "name": "eventId",
                "type": "string",
                "doc": "Unique identifier for this event instance"
            },
            {
                "name": "eventType",
                "type": "string",
                "doc": "Type of event for routing and processing"
            },
            {
                "name": "timestamp",
                "type": "long",
                "doc": "Unix timestamp when event occurred"
            },
            {
                "name": "version",
                "type": "string",
                "default": "1.0",
                "doc": "Schema version for compatibility tracking"
            },
            {
                "name": "data",
                "type": "{{DataRecordType}}",
                "doc": "Event-specific payload data"
            },
            {
                "name": "metadata",
                "type": ["null", {
                    "type": "map",
                    "values": "string"
                }],
                "default": null,
                "doc": "Optional event metadata for extensibility"
            }
        ]
    },
    "ai_prompts": {
        "generation": "Generate an event schema for {{domain}} domain with {{EventName}} event type",
        "evolution": "Evolve this event schema to support {{new_requirements}} while maintaining backward compatibility",
        "validation": "Validate this event schema against existing schemas in {{context}} context"
    }
}
```

**Entity Schema Template** (`.claude-code/templates/entity-schema.json`):
```json
{
    "template_name": "Entity Schema",
    "description": "Template for business entity schemas",
    "schema_template": {
        "type": "record",
        "name": "{{EntityName}}",
        "namespace": "{{namespace}}",
        "doc": "{{entity_description}}",
        "fields": [
            {
                "name": "id",
                "type": "string",
                "doc": "Unique identifier for this {{EntityName}}"
            },
            {
                "name": "version",
                "type": "long",
                "doc": "Entity version for optimistic locking"
            },
            {
                "name": "createdAt",
                "type": "long",
                "doc": "Unix timestamp when entity was created"
            },
            {
                "name": "updatedAt",
                "type": "long",
                "doc": "Unix timestamp when entity was last updated"
            },
            {
                "name": "status",
                "type": {
                    "type": "enum",
                    "name": "{{EntityName}}Status",
                    "symbols": ["ACTIVE", "INACTIVE", "DELETED"]
                },
                "default": "ACTIVE",
                "doc": "Current status of the entity"
            }
        ]
    },
    "ai_prompts": {
        "generation": "Generate an entity schema for {{EntityName}} with fields: {{field_list}}",
        "relationships": "Add relationship fields to connect {{EntityName}} with {{related_entities}}",
        "constraints": "Add validation constraints for {{business_rules}}"
    }
}
```

### Claude Code AI-Enhanced Workflows

#### 1. Intelligent Schema Generation

Claude Code provides natural language schema generation with MCP server integration:

```javascript
// Claude Code AI Prompt Interface
// Type: Schema Generation
// Context: development

/*
AI PROMPT: "Create an e-commerce order processing schema with the following requirements:
- Order must have unique ID, customer info, and line items
- Support for multiple payment methods (credit, debit, paypal, crypto)
- Include order lifecycle status tracking
- Add audit fields for compliance
- Ensure backward compatibility with existing order schemas
- Use consistent naming conventions from our existing schemas"

CONTEXT ANALYSIS: Using MCP server to analyze existing schemas in 'development' context
TARGET: Register in development context, validate against staging context schemas
*/

// Claude Code will:
// 1. Analyze existing schemas via MCP server
// 2. Generate compatible schema following patterns
// 3. Validate against current schemas
// 4. Suggest registration commands
// 5. Provide migration path if needed
```

#### 2. Context-Aware Schema Evolution

```javascript
// Claude Code Evolution Assistant
// Context: production schema evolution

/*
EVOLUTION PROMPT: "I need to evolve the 'user-profile' schema in production to add:
- Social login provider tracking (google, facebook, twitter, github)
- Privacy preferences (analytics_opt_in, marketing_opt_in, data_sharing)
- Account tier information (free, premium, enterprise)

CONSTRAINTS:
- Must maintain backward compatibility
- Existing consumers should continue working
- Migration should be zero-downtime
- Need rollback plan"

ANALYSIS REQUEST: Check current production schema, validate evolution approach
*/

// Claude Code process:
// 1. Fetch current production schema via MCP
// 2. Analyze compatibility requirements  
// 3. Generate evolved schema with proper defaults
// 4. Create compatibility test plan
// 5. Generate migration strategy
// 6. Provide rollback procedures
```

#### 3. Cross-Context Migration Planning

```javascript
// Claude Code Migration Assistant
// Multi-context workflow

/*
MIGRATION PROMPT: "Plan migration of schema changes from development to production:

DEVELOPMENT CONTEXT: 15 new/updated schemas ready for promotion
STAGING CONTEXT: Need to validate and test before production
PRODUCTION CONTEXT: Zero-downtime deployment required

REQUIREMENTS:
- Batch migration of related schemas
- Dependency order validation
- Compatibility testing at each stage
- Automated rollback capability
- Full audit trail"

TARGET: Generate comprehensive migration plan with validation steps
*/

// Claude Code migration workflow:
// 1. Analyze schemas in development context
// 2. Check staging context compatibility
// 3. Generate dependency-ordered migration plan
// 4. Create validation test scripts
// 5. Provide execution timeline
// 6. Generate monitoring and rollback procedures
```

### Claude Code Custom Commands

Configure Claude Code with schema-specific commands in `.claude-code/commands/`:

**Schema Commands** (`.claude-code/commands/schema.json`):
```json
{
    "commands": [
        {
            "name": "schema:analyze",
            "description": "AI-powered schema analysis and recommendations",
            "type": "ai_enhanced",
            "workflow": [
                {
                    "step": "fetch_schema",
                    "mcp_endpoint": "/schemas/{subject}",
                    "parameters": ["subject", "context"]
                },
                {
                    "step": "analyze_structure",
                    "ai_task": "analyze schema structure and patterns"
                },
                {
                    "step": "suggest_improvements",
                    "ai_task": "suggest schema improvements and optimizations"
                },
                {
                    "step": "compatibility_check",
                    "mcp_endpoint": "/compatibility"
                }
            ]
        },
        {
            "name": "schema:generate",
            "description": "Generate schema from natural language description",
            "type": "ai_generation",
            "workflow": [
                {
                    "step": "analyze_requirements",
                    "ai_task": "extract schema requirements from description"
                },
                {
                    "step": "check_existing_patterns",
                    "mcp_endpoint": "/subjects",
                    "ai_task": "analyze existing schema patterns"
                },
                {
                    "step": "generate_schema",
                    "ai_task": "generate Avro schema following patterns"
                },
                {
                    "step": "validate_syntax",
                    "validation": "avro_schema_syntax"
                },
                {
                    "step": "check_compatibility",
                    "mcp_endpoint": "/compatibility"
                }
            ]
        },
        {
            "name": "schema:evolve",
            "description": "Evolve existing schema with AI guidance",
            "type": "ai_evolution",
            "workflow": [
                {
                    "step": "fetch_current_schema",
                    "mcp_endpoint": "/schemas/{subject}"
                },
                {
                    "step": "analyze_evolution_requirements",
                    "ai_task": "understand evolution requirements"
                },
                {
                    "step": "generate_evolved_schema",
                    "ai_task": "create evolved schema maintaining compatibility"
                },
                {
                    "step": "validate_compatibility",
                    "mcp_endpoint": "/compatibility"
                },
                {
                    "step": "suggest_migration_path",
                    "ai_task": "recommend deployment and migration strategy"
                }
            ]
        }
    ]
}
```

**Migration Commands** (`.claude-code/commands/migration.json`):
```json
{
    "commands": [
        {
            "name": "migration:plan", 
            "description": "AI-generated migration plan between contexts",
            "type": "ai_planning",
            "workflow": [
                {
                    "step": "analyze_source_context",
                    "mcp_endpoint": "/subjects",
                    "parameters": ["source_context"]
                },
                {
                    "step": "analyze_target_context", 
                    "mcp_endpoint": "/subjects",
                    "parameters": ["target_context"]
                },
                {
                    "step": "identify_differences",
                    "ai_task": "compare contexts and identify migration scope"
                },
                {
                    "step": "generate_migration_plan",
                    "ai_task": "create detailed migration plan with dependencies"
                },
                {
                    "step": "validate_plan",
                    "mcp_endpoint": "/migrate/context",
                    "parameters": ["dry_run=true"]
                }
            ]
        },
        {
            "name": "migration:execute",
            "description": "Execute migration with AI monitoring",
            "type": "ai_execution",
            "workflow": [
                {
                    "step": "pre_migration_validation",
                    "ai_task": "validate migration readiness"
                },
                {
                    "step": "execute_migration",
                    "mcp_endpoint": "/migrate/context"
                },
                {
                    "step": "monitor_progress",
                    "mcp_endpoint": "/migrate/status"
                },
                {
                    "step": "validate_results",
                    "ai_task": "verify migration success and integrity"
                },
                {
                    "step": "generate_report",
                    "ai_task": "create migration completion report"
                }
            ]
        }
    ]
}
```

**Export Commands** (`.claude-code/commands/export.json`):
```json
{
    "commands": [
        {
            "name": "export:smart",
            "description": "AI-optimized export strategy selection",
            "type": "ai_optimization",
            "workflow": [
                {
                    "step": "analyze_export_requirements",
                    "ai_task": "understand export purpose and requirements"
                },
                {
                    "step": "recommend_format",
                    "ai_task": "suggest optimal export format and settings"
                },
                {
                    "step": "execute_export",
                    "mcp_endpoint": "/export/{type}/{target}"
                },
                {
                    "step": "validate_export",
                    "ai_task": "verify export completeness and integrity"
                }
            ]
        },
        {
            "name": "documentation:generate",
            "description": "Generate comprehensive schema documentation",
            "type": "ai_documentation",
            "workflow": [
                {
                    "step": "analyze_schemas",
                    "mcp_endpoint": "/subjects"
                },
                {
                    "step": "generate_overviews",
                    "ai_task": "create schema overviews and relationships"
                },
                {
                    "step": "export_schemas",
                    "mcp_endpoint": "/export/contexts/{context}",
                    "parameters": ["format=bundle"]
                },
                {
                    "step": "generate_documentation",
                    "ai_task": "create comprehensive documentation package"
                }
            ]
        }
    ]
}
```

### Claude Code Integration Features

#### 1. Real-Time Schema Validation

Claude Code provides real-time validation as you type:

```json
// Real-time validation configuration
{
    "validation": {
        "avro_syntax": {
            "enabled": true,
            "real_time": true,
            "show_suggestions": true
        },
        "compatibility_checking": {
            "enabled": true,
            "check_against_contexts": ["development", "staging"],
            "warn_on_breaking_changes": true
        },
        "naming_conventions": {
            "enabled": true,
            "rules": [
                "camelCase_fields",
                "PascalCase_types",
                "consistent_namespaces"
            ]
        }
    }
}
```

#### 2. Intelligent Code Completion

Smart completion for schema fields, types, and values:

```javascript
// Claude Code completion examples:
{
    "type": "record",
    "name": "User", // Claude Code suggests: UserEvent, UserProfile, UserCommand
    "fields": [
        {
            "name": "id", // Suggests: userId, identifier, uniqueId based on context
            "type": "string" // Suggests: int, long based on field name patterns
        },
        // Claude Code suggests common fields based on schema analysis:
        // - timestamp, version, status for event schemas
        // - createdAt, updatedAt for entity schemas
        // - metadata for extensibility
    ]
}
```

#### 3. Context-Aware Suggestions

Claude Code analyzes your schemas and provides intelligent suggestions:

- **Field Additions**: Suggests missing fields based on similar schemas
- **Type Optimization**: Recommends better field types for your use cases
- **Compatibility Warnings**: Highlights potential breaking changes
- **Best Practices**: Suggests schema design improvements

#### 4. Migration Workflow Integration

Seamless integration with migration operations:

```javascript
// Claude Code migration interface
// Visual migration planner with drag-and-drop
// Real-time compatibility checking
// Dependency visualization
// Rollback planning assistance
```

### Claude Code Shortcuts & Snippets

Essential shortcuts for rapid schema development:

```json
{
    "shortcuts": {
        "Ctrl+Shift+S": "schema:analyze",
        "Ctrl+Shift+G": "schema:generate", 
        "Ctrl+Shift+E": "schema:evolve",
        "Ctrl+Shift+M": "migration:plan",
        "Ctrl+Shift+X": "export:smart",
        "Ctrl+Shift+V": "validate:compatibility",
        "Ctrl+Shift+D": "documentation:generate"
    },
    "snippets": {
        "event-schema": "Insert event schema template",
        "entity-schema": "Insert entity schema template",
        "migration-script": "Generate migration script",
        "compatibility-check": "Insert compatibility check",
        "export-config": "Insert export configuration"
    }
}
```

### Advanced Claude Code Features

#### 1. Visual Schema Designer

Claude Code provides a visual interface for schema design:

- **Drag-and-drop field creation**
- **Visual type selection**
- **Real-time compatibility checking**
- **Schema relationship visualization**
- **Migration path planning**

#### 2. AI-Powered Schema Analysis

Advanced analysis capabilities:

- **Pattern Recognition**: Identifies common patterns across schemas
- **Anomaly Detection**: Finds inconsistencies and potential issues
- **Optimization Suggestions**: Recommends performance improvements
- **Evolution Planning**: Suggests schema evolution strategies

#### 3. Collaborative Features

Team collaboration tools:

- **Schema Review Workflow**: AI-assisted code review for schemas
- **Change Impact Analysis**: Understand downstream effects of changes
- **Team Standards Enforcement**: Consistent naming and structure
- **Knowledge Sharing**: Automatic documentation and examples

---

## ⚡ Cursor Integration

### AI-Powered Schema Development

Cursor's advanced AI capabilities work seamlessly with the Schema Registry MCP server for intelligent, context-aware development.

### Setup & Configuration

#### 1. Project Integration

Add to your `.cursorrc`:

```json
{
    "mcp_endpoints": [
        {
            "name": "schema-registry",
            "url": "http://localhost:38000",
            "type": "rest_api",
            "description": "Kafka Schema Registry MCP Server with Context Support"
        }
    ],
    "ai_context": {
        "schema_registry": {
            "endpoints": [
                "/schemas",
                "/contexts", 
                "/subjects",
                "/compatibility"
            ],
            "context_awareness": true,
            "auto_completion": true
        }
    },
    "project_type": "kafka_schema_management",
    "ai_features": {
        "schema_validation": true,
        "compatibility_checking": true,
        "code_generation": true,
        "documentation_generation": true
    }
}
```

#### 2. Custom Commands

Create `.cursor/commands.json`:

```json
{
    "commands": [
        {
            "name": "schema:register",
            "description": "Register a new schema with AI assistance",
            "command": "curl -X POST http://localhost:38000/schemas",
            "ai_enhanced": true,
            "template": {
                "subject": "{{subject_name}}",
                "schema": "{{ai_generated_schema}}",
                "schemaType": "AVRO",
                "context": "{{target_context}}"
            }
        },
        {
            "name": "schema:evolve", 
            "description": "Evolve existing schema with compatibility checking",
            "ai_enhanced": true,
            "workflow": [
                "fetch_current_schema",
                "analyze_requirements", 
                "generate_evolution",
                "check_compatibility",
                "apply_changes"
            ]
        },
        {
            "name": "schema:migrate",
            "description": "Migrate schema between contexts with AI optimization",
            "ai_enhanced": true,
            "workflow": [
                "analyze_source_context",
                "validate_target_context",
                "generate_migration_plan",
                "execute_dry_run",
                "validate_dry_run_results",
                "execute_migration",
                "verify_migration_success"
            ],
            "endpoints": {
                "schema_migration": "POST /migrate/schema",
                "context_migration": "POST /migrate/context",
                "migration_status": "GET /migrate/status"
            }
        },
        {
            "name": "schema:promote",
            "description": "Promote schema between contexts using migration",
            "ai_enhanced": true,
            "workflow": [
                "validate_source_context",
                "check_target_compatibility",
                "execute_migration",
                "verify_deployment"
            ]
        },
        {
            "name": "multi-registry:sync",
            "description": "Synchronize schemas across multiple registries",
            "ai_enhanced": true,
            "server": "multi-registry",
            "workflow": [
                "analyze_registry_differences",
                "generate_sync_strategy",
                "execute_sync_plan",
                "validate_sync_integrity",
                "generate_sync_report"
            ],
            "endpoints": {
                "sync_registries": "POST /sync/registries",
                "compare_registries": "GET /compare/registries",
                "registry_health": "GET /registries/{name}/health"
            }
        },
        {
            "name": "disaster-recovery:setup",
            "description": "Set up disaster recovery with AI-guided configuration",
            "ai_enhanced": true,
            "server": "multi-registry",
            "workflow": [
                "analyze_primary_registry",
                "design_dr_strategy",
                "configure_dr_registry",
                "perform_initial_sync",
                "validate_dr_setup",
                "test_failover_scenario"
            ]
        },
        {
            "name": "schema:export",
            "description": "Export schemas with AI-assisted format selection",
            "ai_enhanced": true,
            "workflow": [
                "analyze_export_requirements",
                "select_optimal_format",
                "generate_export_request",
                "execute_export",
                "validate_export_integrity"
            ]
        },
        {
            "name": "schema:backup",
            "description": "Generate automated backup with AI optimization",
            "ai_enhanced": true,
            "workflow": [
                "assess_backup_scope",
                "optimize_backup_strategy",
                "execute_backup",
                "verify_backup_integrity",
                "generate_backup_report"
            ]
        },
        {
            "name": "schema:document",
            "description": "Generate comprehensive schema documentation",
            "ai_enhanced": true,
            "workflow": [
                "analyze_schema_complexity",
                "select_documentation_format",
                "generate_human_readable_docs",
                "create_developer_guides",
                "validate_documentation_completeness"
            ]
        },
        {
            "name": "migration:plan",
            "description": "Generate comprehensive migration plan with AI analysis",
            "ai_enhanced": true,
            "workflow": [
                "analyze_current_state",
                "identify_dependencies",
                "generate_migration_sequence",
                "estimate_migration_impact",
                "create_rollback_plan",
                "generate_migration_script"
            ]
        },
        {
            "name": "migration:validate",
            "description": "Validate migration plan and execution",
            "ai_enhanced": true,
            "workflow": [
                "validate_migration_plan",
                "check_compatibility_matrix",
                "verify_dependency_order",
                "simulate_migration_impact",
                "generate_validation_report"
            ]
        }
    ]
}
```

### AI-Enhanced Development Workflows

#### 1. Intelligent Schema Generation

```typescript
// Cursor AI Prompt Example:
// "Generate an Avro schema for e-commerce order events with these requirements:
// - Order ID (required string, UUID format)
// - Customer information (nested record: customerId, email, tier)
// - Line items (array of records: productId, quantity, unitPrice, discount)
// - Payment details (record: method, amount, currency, transactionId)
// - Timestamps (orderCreated, lastUpdated as long milliseconds)
// - Metadata (optional map for extensibility)
// - Ensure backward compatibility with existing order schemas
// - Follow company naming conventions (camelCase, descriptive names)"

interface OrderEvent {
    orderId: string;               // UUID format
    customer: {
        customerId: string;
        email: string;
        tier: 'bronze' | 'silver' | 'gold' | 'platinum';
    };
    lineItems: Array<{
        productId: string;
        quantity: number;
        unitPrice: number;
        discount?: number;
    }>;
    payment: {
        method: 'credit_card' | 'debit_card' | 'paypal' | 'bank_transfer';
        amount: number;
        currency: string;
        transactionId: string;
    };
    orderCreated: number;          // Unix timestamp in milliseconds
    lastUpdated: number;           // Unix timestamp in milliseconds
    metadata?: Record<string, string>;
}

// Cursor will automatically generate the corresponding Avro schema
// and provide registration commands
```

#### 2. Context-Aware Development

Cursor understands your schema context and provides intelligent suggestions:

```javascript
// When working in schema files, Cursor will:
// 1. Suggest field additions based on existing patterns
// 2. Warn about potential breaking changes
// 3. Recommend context-appropriate strategies
// 4. Generate test data that matches your schemas
// 5. Validate against existing schemas in real-time

// Example: Auto-completion for schema fields
const userSchema = {
    type: "record",
    name: "User",
    fields: [
        // Cursor suggests: commonly used fields in your context
        // Based on analysis of existing schemas
    ]
};
```

### Cursor Shortcuts & Snippets

Add these to your Cursor snippets for rapid development:

```json
{
    "Avro Schema Template": {
        "prefix": "avro-schema",
        "body": [
            "{",
            "  \"type\": \"record\",",
            "  \"name\": \"${1:RecordName}\",",
            "  \"namespace\": \"${2:com.example.schemas}\",",
            "  \"doc\": \"${3:Description of this schema}\",",
            "  \"fields\": [",
            "    {",
            "      \"name\": \"${4:fieldName}\",",
            "      \"type\": \"${5:string}\",",
            "      \"doc\": \"${6:Field description}\"${7:,}",
            "      ${8:\"default\": \"${9:defaultValue}\"}",
            "    }$0",
            "  ]",
            "}"
        ],
        "description": "Create a new Avro schema template"
    },
    
    "Register Schema with Context": {
        "prefix": "register-schema",
        "body": [
            "curl -X POST http://localhost:38000/schemas \\",
            "  -H \"Content-Type: application/json\" \\", 
            "  -d '{",
            "    \"subject\": \"${1:subject-name}\",",
            "    \"schema\": ${2:schema-object},",
            "    \"schemaType\": \"AVRO\",",
            "    \"context\": \"${3:development}\"",
            "  }'"
        ],
        "description": "Register a schema with context"
    },
    
    "Check Compatibility": {
        "prefix": "check-compat",
        "body": [
            "curl -X POST http://localhost:38000/compatibility \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"subject\": \"${1:subject-name}\",", 
            "    \"schema\": ${2:new-schema-object},",
            "    \"context\": \"${3:production}\"",
            "  }'"
        ],
        "description": "Check schema compatibility"
    },
    
    "Migrate Schema Between Contexts": {
        "prefix": "migrate-schema",
        "body": [
            "curl -X POST http://localhost:38000/migrate/schema \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"subject\": \"${1:subject-name}\",",
            "    \"source_context\": \"${2:development}\",",
            "    \"target_context\": \"${3:staging}\",",
            "    \"version\": \"${4:latest}\",",
            "    \"dry_run\": ${5:true},",
            "    \"overwrite\": ${6:false}",
            "  }'"
        ],
        "description": "Migrate schema between contexts"
    },
    
    "Migrate Entire Context": {
        "prefix": "migrate-context",
        "body": [
            "curl -X POST http://localhost:38000/migrate/context \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"source_context\": \"${1:development}\",",
            "    \"target_context\": \"${2:staging}\",",
            "    \"dry_run\": ${3:true},",
            "    \"overwrite\": ${4:false},",
            "    \"include_config\": ${5:true}",
            "  }'"
        ],
        "description": "Migrate entire context"
    },
    
    "Cross-Registry Migration": {
        "prefix": "cross-registry-migrate",
        "body": [
            "curl -X POST http://localhost:39000/migrate/cross-registry \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"source_registry\": \"${1:primary}\",",
            "    \"target_registry\": \"${2:disaster_recovery}\",",
            "    \"contexts\": [\"${3:production}\", \"${4:staging}\"],",
            "    \"dry_run\": ${5:false},",
            "    \"include_config\": ${6:true}",
            "  }'"
        ],
        "description": "Migrate schemas across registries"
    },
    
    "Multi-Registry Sync": {
        "prefix": "multi-registry-sync",
        "body": [
            "curl -X POST http://localhost:39000/sync/registries \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"source_registry\": \"${1:primary}\",",
            "    \"target_registry\": \"${2:disaster_recovery}\",",
            "    \"contexts\": [\"${3:production}\"],",
            "    \"dry_run\": ${4:false},",
            "    \"sync_mode\": \"${5:incremental}\"",
            "  }'"
        ],
        "description": "Synchronize schemas between registries"
    },
    
    "Registry Comparison": {
        "prefix": "compare-registries",
        "body": [
            "curl 'http://localhost:39000/compare/registries?source=${1:primary}&target=${2:disaster_recovery}&context=${3:production}' \\",
            "  | jq '.'"
        ],
        "description": "Compare schemas between registries"
    },
    
    "Migration Status Check": {
        "prefix": "migration-status",
        "body": [
            "curl 'http://localhost:38000/migrate/status?task_id=${1:migration-task-id}' \\",
            "  | jq '.'"
        ],
        "description": "Check migration task status"
    },
    
    "Multi-Context Schema Query": {
        "prefix": "multi-context-query",
        "body": [
            "# Query schemas across multiple contexts",
            "for context in development staging production; do",
            "  echo \"=== Context: $context ===\"",
            "  curl -s \"http://localhost:38000/subjects?context=$context\" | jq .",
            "  echo \"\"",
            "done"
        ],
        "description": "Query schemas across multiple contexts"
    },
    
    "Export Schema as JSON": {
        "prefix": "export-schema-json",
        "body": [
            "curl -X POST http://localhost:38000/export/subjects/${1:subject-name} \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"format\": \"json\",",
            "    \"include_metadata\": true,",
            "    \"include_config\": true,",
            "    \"include_versions\": \"${2:all}\"",
            "  }' --output ${3:export-filename}.json"
        ],
        "description": "Export schema subject as JSON"
    },
    
    "Export Context as Bundle": {
        "prefix": "export-context-bundle",
        "body": [
            "curl -X POST http://localhost:38000/export/contexts/${1:context-name} \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"format\": \"bundle\",",
            "    \"include_metadata\": true,",
            "    \"include_config\": true,",
            "    \"include_versions\": \"all\"",
            "  }' --output ${2:context-name}_export_$(date +%Y%m%d).zip"
        ],
        "description": "Export context as ZIP bundle"
    },
    
    "Global Registry Backup": {
        "prefix": "global-backup",
        "body": [
            "# Complete registry backup",
            "curl -X POST http://localhost:38000/export/global \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"format\": \"bundle\",",
            "    \"include_metadata\": true,",
            "    \"include_config\": true,",
            "    \"include_versions\": \"all\"",
            "  }' --output registry_backup_$(date +%Y%m%d_%H%M%S).zip"
        ],
        "description": "Complete registry backup"
    },
    
    "Migration Plan Generation": {
        "prefix": "migration-plan",
        "body": [
            "# Generate migration plan",
            "curl -X POST http://localhost:38000/migrate/context \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"source_context\": \"${1:development}\",",
            "    \"target_context\": \"${2:staging}\",",
            "    \"dry_run\": true,",
            "    \"include_config\": true",
            "  }' | jq '.migration_plan' > migration_plan_${3:$(date +%Y%m%d)}.json"
        ],
        "description": "Generate and save migration plan"
    },
    
    "Disaster Recovery Test": {
        "prefix": "dr-test",
        "body": [
            "# Test disaster recovery setup",
            "curl -X POST http://localhost:39000/failover/test \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"primary_registry\": \"${1:primary}\",",
            "    \"failover_registry\": \"${2:disaster_recovery}\",",
            "    \"test_contexts\": [\"${3:production}\"],",
            "    \"validate_schemas\": true",
            "  }' | jq '.'"
        ],
        "description": "Test disaster recovery failover"
    },
    
    "Generate Schema Documentation": {
        "prefix": "schema-docs",
        "body": [
            "# Generate schema documentation",
            "curl http://localhost:38000/export/schemas/${1:subject-name}?format=avro_idl \\",
            "  --output docs/${1:subject-name}_schema.avdl",
            "",
            "# Generate JSON version for tooling",
            "curl http://localhost:38000/export/schemas/${1:subject-name}?format=json \\",
            "  --output docs/${1:subject-name}_schema.json"
        ],
        "description": "Generate schema documentation in multiple formats"
    }
}
```

---

## 🚀 Development Best Practices

### Cross-IDE Workflows

- **Centralized Schema Management**: Use the MCP server as single source of truth across all development environments
- **Shared Configuration**: Maintain consistent `.http` files and environment variables across team members
- **Version Control**: Include all IDE configuration files in version control for team consistency

### AI Assistant Guidelines

- **Schema Validation**: Always validate AI-generated schemas using the compatibility endpoint before registration
- **Context Isolation**: Use development contexts for AI-assisted experimentation and testing
- **Incremental Evolution**: Test schema changes incrementally rather than making large changes at once
- **Documentation**: Generate comprehensive documentation for AI-suggested schema changes

### Debugging & Troubleshooting

- **Health Checks**: Always verify service health endpoints before investigating schema-specific issues
- **Log Analysis**: Use the enhanced test script diagnostics for comprehensive service status
- **Context Verification**: Ensure you're working in the correct schema context when debugging issues
- **Version Tracking**: Monitor schema versions and evolution history when troubleshooting compatibility issues

---

## 🔄 Multi-Registry Integration

### Multi-Registry MCP Server Setup

The project now supports multiple Schema Registry instances through the dedicated multi-registry MCP server, enabling cross-registry operations, disaster recovery, and distributed schema management.

### Configuration

Create `multi_registry.env` for multi-registry setup:

```env
# Primary Schema Registry
PRIMARY_SCHEMA_REGISTRY_URL=http://localhost:8081
PRIMARY_REGISTRY_NAME=primary

# Disaster Recovery Registry  
DR_SCHEMA_REGISTRY_URL=http://localhost:8082
DR_REGISTRY_NAME=disaster_recovery

# Development Registry
DEV_SCHEMA_REGISTRY_URL=http://localhost:8083
DEV_REGISTRY_NAME=development

# Multi-Registry MCP Server
MULTI_MCP_SERVER_PORT=39000
MULTI_MCP_SERVER_HOST=0.0.0.0

# Cross-Registry Migration Settings
MIGRATION_BATCH_SIZE=10
MIGRATION_TIMEOUT=300
ENABLE_CROSS_REGISTRY_MIGRATION=true
```

### VS Code Multi-Registry Configuration

Update `.vscode/settings.json` for multi-registry support:

```json
{
    "rest-client.environmentVariables": {
        "local": {
            "primaryMcp": "http://localhost:38000",
            "multiMcp": "http://localhost:39000",
            "primaryRegistry": "http://localhost:8081",
            "drRegistry": "http://localhost:8082",
            "devRegistry": "http://localhost:8083"
        },
        "staging": {
            "primaryMcp": "http://staging.example.com:38000",
            "multiMcp": "http://staging.example.com:39000",
            "primaryRegistry": "http://staging-primary.example.com:8081",
            "drRegistry": "http://staging-dr.example.com:8081"
        },
        "production": {
            "primaryMcp": "http://prod.example.com:38000", 
            "multiMcp": "http://prod.example.com:39000",
            "primaryRegistry": "http://prod-primary.example.com:8081",
            "drRegistry": "http://prod-dr.example.com:8081"
        }
    }
}
```

### Multi-Registry API Testing

Create `.vscode/multi-registry-requests.http`:

```http
@multiMcp = {{$dotenv %MULTI_MCP_SERVER_URL}}
@context = production

### List Available Registries
GET {{multiMcp}}/registries
Accept: application/json

### Registry Health Check
GET {{multiMcp}}/registries/primary/health
Accept: application/json

### Cross-Registry Schema Sync
POST {{multiMcp}}/sync/registries
Content-Type: application/json

{
    "source_registry": "primary",
    "target_registry": "disaster_recovery",
    "contexts": ["production", "staging"],
    "dry_run": false,
    "sync_mode": "incremental"
}

### Bulk Migration Between Registries
POST {{multiMcp}}/migrate/bulk
Content-Type: application/json

{
    "source_registry": "primary",
    "target_registry": "disaster_recovery", 
    "migration_plan": [
        {
            "context": "production",
            "subjects": ["user-events", "order-events", "payment-events"],
            "overwrite": false
        },
        {
            "context": "staging",
            "subjects": ["*"],
            "overwrite": true
        }
    ],
    "dry_run": false
}

### Registry Comparison Report
GET {{multiMcp}}/compare/registries?source=primary&target=disaster_recovery&context={{context}}
Accept: application/json

### Registry Failover Test
POST {{multiMcp}}/failover/test
Content-Type: application/json

{
    "primary_registry": "primary",
    "failover_registry": "disaster_recovery",
    "test_contexts": ["production"],
    "validate_schemas": true
}
```

### Multi-Registry Tasks Configuration

Add to `.vscode/tasks.json`:

```json
{
    "label": "Start Multi-Registry Environment",
    "type": "shell",
    "command": "docker-compose -f docker-compose.multi-registry.yml up -d",
    "group": "build",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    }
},
{
    "label": "Test Multi-Registry Migration",
    "type": "shell", 
    "command": "./tests/run_migration_integration_tests.sh",
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    },
    "dependsOn": "Start Multi-Registry Environment"
},
{
    "label": "Cross-Registry Sync",
    "type": "shell",
    "command": "curl -X POST http://localhost:39000/sync/registries -H 'Content-Type: application/json' -d '{\"source_registry\": \"primary\", \"target_registry\": \"disaster_recovery\", \"contexts\": [\"production\"], \"dry_run\": false}'",
    "group": "build",
    "presentation": {
        "echo": true,
        "reveal": "always"
    }
},
{
    "label": "Registry Comparison Report",
    "type": "shell",
    "command": "curl 'http://localhost:39000/compare/registries?source=primary&target=disaster_recovery&context=production' | jq '.' > docs/registry_comparison_$(date +%Y%m%d).json",
    "group": "build",
    "presentation": {
        "echo": true,
        "reveal": "always"
    }
}
```

---

## 🧪 Comprehensive Testing Integration

### Test Suite Overview

The project includes a comprehensive testing framework with multiple test categories and automated runners:

### Test Categories

1. **Migration Integration Tests** - Real schema migration testing with Docker registries
2. **Multi-Registry Tests** - Cross-registry operations and synchronization
3. **Performance Tests** - Load testing and performance validation
4. **Error Handling Tests** - Edge cases and failure scenarios
5. **Production Readiness Tests** - Full deployment validation
6. **Legacy Compatibility Tests** - Backward compatibility validation

### VS Code Test Configuration

Update `.vscode/launch.json` for comprehensive testing:

```json
{
    "name": "Debug Migration Tests",
    "type": "python",
    "request": "launch",
    "module": "pytest",
    "args": [
        "tests/test_migration_integration.py",
        "-v",
        "--tb=short",
        "--capture=no"
    ],
    "console": "integratedTerminal",
    "env": {
        "DOCKER_COMPOSE_FILE": "docker-compose.multi-registry.yml",
        "TEST_TIMEOUT": "300",
        "MIGRATION_TEST_MODE": "integration"
    }
},
{
    "name": "Debug Multi-Registry Tests", 
    "type": "python",
    "request": "launch",
    "module": "pytest",
    "args": [
        "tests/test_multi_registry_integration.py",
        "-v",
        "--tb=short"
    ],
    "console": "integratedTerminal",
    "env": {
        "MULTI_REGISTRY_CONFIG": "multi_registry.env",
        "TEST_REGISTRIES": "primary,disaster_recovery,development"
    }
},
{
    "name": "Run Comprehensive Test Suite",
    "type": "shell",
    "command": "./tests/run_comprehensive_tests.sh",
    "args": ["--category", "all", "--verbose"],
    "console": "integratedTerminal"
}
```

### Test Runner Tasks

Add comprehensive test tasks to `.vscode/tasks.json`:

```json
{
    "label": "Run Migration Tests",
    "type": "shell",
    "command": "./tests/run_migration_integration_tests.sh",
    "group": "test", 
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    },
    "options": {
        "env": {
            "TEST_TIMEOUT": "300",
            "VERBOSE": "true"
        }
    }
},
{
    "label": "Run Comprehensive Tests",
    "type": "shell",
    "command": "./tests/run_comprehensive_tests.sh",
    "args": ["--category", "all"],
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    }
},
{
    "label": "Quick Migration Fix Validation",
    "type": "shell",
    "command": "python tests/test_quick_migration_fix.py",
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always"
    }
},
{
    "label": "Validate Migration Source Code",
    "type": "shell", 
    "command": "python tests/validate_migration_fix.py",
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always"
    }
},
{
    "label": "Performance Test Suite",
    "type": "shell",
    "command": "./tests/run_comprehensive_tests.sh --category performance",
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    }
},
{
    "label": "Production Readiness Test",
    "type": "shell",
    "command": "./tests/run_comprehensive_tests.sh --category production",
    "group": "test", 
    "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
    }
}
```

---

This integration guide provides comprehensive setup instructions and best practices for maximizing productivity with modern development tools and AI assistants when working with the Kafka Schema Registry MCP server. 