# IDE & AI Assistant Integration Guide

This guide provides comprehensive instructions for integrating the Kafka Schema Registry MCP Server with popular development environments and AI-powered coding assistants.

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
```

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
            "command": "./run_integration_tests.sh",
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
                "subject_management"
            ],
            "contexts": [
                "development",
                "staging", 
                "production"
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
                "promote_to_staging",
                "validate_staging_deployment",
                "check_production_compatibility",
                "promote_to_production"
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
5. Clear promotion workflow

Using the MCP server endpoints:
- Context management: /contexts
- Schema operations: /schemas
- Subject listing: /subjects

Please provide:
1. Recommended context naming strategy
2. Context creation commands
3. Schema governance policies
4. Promotion workflow design
5. Example implementations for 2-3 teams

Be specific and provide actual curl commands and context names.
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
            "name": "schema:promote",
            "description": "Promote schema between contexts",
            "ai_enhanced": true,
            "workflow": [
                "validate_source_context",
                "check_target_compatibility",
                "execute_promotion",
                "verify_deployment"
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

This integration guide provides comprehensive setup instructions and best practices for maximizing productivity with modern development tools and AI assistants when working with the Kafka Schema Registry MCP server. 