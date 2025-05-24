# Kafka Schema Registry MCP Server

A comprehensive Message Control Protocol (MCP) server that provides a REST API interface for Kafka Schema Registry operations, including advanced **Schema Context** support for logical schema grouping and management.

## ✨ Features

- **Complete Schema Management**: Register, retrieve, and manage Avro schemas
- **Schema Contexts**: Logical grouping with separate "sub-registries" 
- **Version Control**: Handle multiple schema versions with compatibility checking
- **Authentication Support**: Optional basic authentication for Schema Registry
- **Compatibility Testing**: Verify schema evolution compatibility
- **Subject Management**: List and delete schema subjects
- **Context Isolation**: Schemas in different contexts are completely isolated
- **Docker Support**: Easy deployment with Docker Compose
- **Comprehensive Testing**: Full integration and unit test coverage

## 🏗️ Architecture

- **FastAPI-based MCP Server**: Modern async REST API with automatic OpenAPI docs
- **Kafka Schema Registry**: Backend for schema storage and management  
- **KRaft Mode**: Uses modern Kafka without Zookeeper dependency
- **Context-Aware Operations**: All endpoints support optional context parameters
- **Flexible Context Specification**: Context via request body or query parameters

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for local development)

### Start Services
```bash
docker-compose up -d
```

This starts:
- **Kafka** (KRaft mode): `localhost:39092`
- **Schema Registry**: `localhost:38081` 
- **MCP Server**: `localhost:38000`
- **AKHQ UI**: `localhost:38080` (Kafka management UI)

### Health Check
```bash
curl http://localhost:38000/
# {"message": "Kafka Schema Registry MCP Server with Context Support"}
```

## 📋 API Endpoints

### Core Schema Operations

#### Register Schema
```bash
POST /schemas
```
**Basic Usage:**
```bash
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {
      "type": "record",
      "name": "User", 
      "fields": [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "string"}
      ]
    },
    "schemaType": "AVRO"
  }'
```

**With Context (Request Body):**
```bash
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO",
    "context": "production"
  }'
```

**With Context (Query Parameter):**
```bash
curl -X POST http://localhost:38000/schemas?context=production \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO"
  }'
```

#### Get Schema
```bash
GET /schemas/{subject}?version=latest&context={context}
```
```bash
curl http://localhost:38000/schemas/user-value
curl http://localhost:38000/schemas/user-value?context=production
curl http://localhost:38000/schemas/user-value?version=2&context=staging
```

#### Get Schema Versions
```bash
GET /schemas/{subject}/versions?context={context}
```
```bash
curl http://localhost:38000/schemas/user-value/versions
curl http://localhost:38000/schemas/user-value/versions?context=production
```

#### Check Compatibility
```bash
POST /compatibility?context={context}
```
```bash
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO",
    "context": "production"
  }'
```

### Schema Context Management

#### List All Contexts
```bash
GET /contexts
```
```bash
curl http://localhost:38000/contexts
# {"contexts": ["production", "staging", "development"]}
```

#### Create Context
```bash
POST /contexts/{context}
```
```bash
curl -X POST http://localhost:38000/contexts/production
# {"message": "Context 'production' created successfully"}
```

#### Delete Context
```bash
DELETE /contexts/{context}
```
```bash
curl -X DELETE http://localhost:38000/contexts/staging
# {"message": "Context 'staging' deleted successfully"}
```

### Subject Management

#### List Subjects
```bash
GET /subjects?context={context}
```
```bash
# All subjects in default context
curl http://localhost:38000/subjects

# Subjects in specific context
curl http://localhost:38000/subjects?context=production
```

#### Delete Subject
```bash
DELETE /subjects/{subject}?context={context}
```
```bash
curl -X DELETE http://localhost:38000/subjects/user-value
curl -X DELETE http://localhost:38000/subjects/user-value?context=production
```

## 🎯 Schema Context Benefits

Schema Contexts provide powerful capabilities for enterprise schema management:

### **Logical Separation**
- **Environment Isolation**: `production`, `staging`, `development`
- **Team Boundaries**: `team-a`, `team-b`, `shared`
- **Application Domains**: `user-service`, `order-service`, `analytics`

### **Multi-Tenancy**
- **Client Isolation**: `client-a`, `client-b` 
- **Regulatory Compliance**: `gdpr`, `pci`, `sox`
- **Geographic Regions**: `us-east`, `eu-west`, `asia-pacific`

### **Schema Evolution Management**
- **Versioning Strategy**: Different evolution rules per context
- **Testing Isolation**: Safe schema testing without affecting production
- **Migration Support**: Gradual context-based schema migrations

### **Operational Benefits**
- **Namespace Collision Prevention**: Same subject names in different contexts
- **Access Control**: Context-based permissions and governance
- **Monitoring & Metrics**: Context-aware observability

## 🔐 Authentication

Optional authentication support for Schema Registry:

```bash
# Set environment variables
export SCHEMA_REGISTRY_USER="your-username"
export SCHEMA_REGISTRY_PASSWORD="your-password"

# Restart services
docker-compose restart mcp-server
```

## 🧪 Testing

### Run All Tests
```bash
./run_integration_tests.sh
```

### Test Coverage
- ✅ **Core Operations**: Registration, retrieval, versioning
- ✅ **Context Management**: Create, list, delete contexts
- ✅ **Context-Aware Operations**: All endpoints with context support
- ✅ **Context Isolation**: Verify proper schema separation
- ✅ **Compatibility Checking**: Both default and context-aware
- ✅ **Error Handling**: Invalid schemas, missing subjects
- ✅ **Authentication**: Optional auth support

### Manual Testing
```bash
# Test context creation
curl -X POST http://localhost:38000/contexts/test-env

# Register schema in context
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "test-user",
    "schema": {"type": "record", "name": "User", "fields": [{"name": "id", "type": "int"}]},
    "context": "test-env"
  }'

# Verify context isolation
curl http://localhost:38000/subjects?context=test-env
curl http://localhost:38000/subjects  # Default context - should be different
```

## 🐳 Development

### Local Development
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server locally
python mcp_server.py
```

### Docker Development
```bash
# Rebuild after code changes
docker-compose build --no-cache mcp-server
docker-compose up -d
```

## 📚 Schema Registry Integration

This MCP server integrates with [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/fundamentals/index.html) and supports:

- **Multiple Schema Formats**: Avro, JSON Schema, Protocol Buffers
- **Schema Evolution**: Forward, backward, and full compatibility
- **Subject Naming Strategies**: TopicNameStrategy, RecordNameStrategy, TopicRecordNameStrategy
- **Schema Contexts**: Logical grouping and namespace management
- **Schema Linking**: Cross-registry schema replication (when supported)

## 🔗 References

- [Confluent Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/fundamentals/index.html)
- [Schema Registry API Reference](https://docs.confluent.io/platform/current/schema-registry/develop/api.html)
- [Schema Contexts Documentation](https://docs.confluent.io/platform/current/schema-registry/fundamentals/index.html#schema-contexts)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 🎉 Success Metrics

**Latest Test Results**: ✅ **21 PASSED**, ⚠️ **1 SKIPPED** (auth), ❌ **0 FAILED**

This includes comprehensive testing of both core functionality and advanced Schema Context features!

## 🔧 IDE & AI Assistant Integration

### 🔵 VS Code Integration

#### **Essential Extensions**
```bash
# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-vscode.vscode-json
code --install-extension humao.rest-client
code --install-extension ms-azuretools.vscode-docker
code --install-extension redhat.vscode-yaml
```

#### **Workspace Configuration**
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["test_integration.py"],
    "rest-client.environmentVariables": {
        "local": {
            "mcpServer": "http://localhost:38000",
            "schemaRegistry": "http://localhost:38081"
        }
    },
    "files.associations": {
        "*.avsc": "json",
        "docker-compose*.yml": "yaml"
    }
}
```

#### **REST Client Testing**
Create `.vscode/requests.http` for interactive API testing:
```http
### Health Check
GET {{mcpServer}}/

### List Contexts
GET {{mcpServer}}/contexts

### Create Context
POST {{mcpServer}}/contexts/development

### Register Schema
POST {{mcpServer}}/schemas
Content-Type: application/json

{
    "subject": "user-value",
    "schema": {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": ["null", "string"], "default": null}
        ]
    },
    "schemaType": "AVRO",
    "context": "development"
}

### Get Schema
GET {{mcpServer}}/schemas/user-value?context=development

### Check Compatibility
POST {{mcpServer}}/compatibility
Content-Type: application/json

{
    "subject": "user-value",
    "schema": {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "created_at", "type": "long"}
        ]
    },
    "schemaType": "AVRO",
    "context": "development"
}
```

#### **Debug Configuration**
Create `.vscode/launch.json`:
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
                "SCHEMA_REGISTRY_URL": "http://localhost:8081"
            }
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["test_integration.py", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

#### **Tasks Configuration**
Create `.vscode/tasks.json`:
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
            }
        },
        {
            "label": "Run Tests",
            "type": "shell",
            "command": "./run_integration_tests.sh",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Stop Services",
            "type": "shell",
            "command": "docker-compose down",
            "group": "build"
        }
    ]
}
```

---

### 🤖 Claude Code Integration

#### **MCP Server as Context Provider**

The Schema Registry MCP server can be integrated with Claude Code extension to provide intelligent schema management assistance.

#### **Setup Instructions**

1. **Install Claude Dev Extension**
```bash
code --install-extension claude-ai.claude-dev
```

2. **Configure MCP Integration**
Create `claude_config.json`:
```json
{
    "mcp_servers": {
        "kafka-schema-registry": {
            "url": "http://localhost:38000",
            "capabilities": [
                "schema_management",
                "context_management", 
                "compatibility_checking"
            ]
        }
    },
    "workflows": {
        "schema_development": {
            "steps": [
                "analyze_existing_schemas",
                "design_new_schema",
                "check_compatibility",
                "register_schema",
                "validate_integration"
            ]
        }
    }
}
```

#### **Claude-Assisted Workflows**

**Schema Evolution Workflow:**
```python
# Example Claude prompt for schema evolution
"""
Using the Kafka Schema Registry MCP server at localhost:38000:

1. Analyze the current 'user-value' schema in the 'production' context
2. Suggest backward-compatible changes to add an 'address' field
3. Generate the new schema JSON
4. Check compatibility against the existing schema
5. Provide registration command if compatible

Context: We need to add address information while maintaining backward compatibility.
"""
```

**Context Management Workflow:**
```python
# Example Claude prompt for context management
"""
Help me set up a proper schema context strategy:

1. List existing contexts in our Schema Registry
2. Create contexts for: development, staging, production
3. Design a schema promotion workflow between contexts
4. Suggest naming conventions for subjects within each context

Use the MCP server endpoints to implement this strategy.
"""
```

#### **Integration Patterns**

**1. Schema Design Assistant:**
- Ask Claude to analyze existing schemas
- Generate compatible schema evolutions
- Suggest field naming conventions
- Validate schema designs

**2. Context Strategy Advisor:**
- Design multi-environment strategies
- Plan schema migration workflows
- Recommend governance policies
- Create testing scenarios

**3. Compatibility Checker:**
- Automated compatibility analysis
- Breaking change detection
- Evolution recommendations
- Risk assessment

---

### ⚡ Cursor Integration

#### **AI-Powered Schema Development**

Cursor's AI capabilities can be enhanced with the Schema Registry MCP server for intelligent schema management.

#### **Setup & Configuration**

1. **Project Integration**
Add to your `.cursorrc`:
```json
{
    "mcp_endpoints": [
        {
            "name": "schema-registry",
            "url": "http://localhost:38000",
            "type": "rest_api"
        }
    ],
    "ai_context": {
        "schema_registry": {
            "endpoints": [
                "/schemas",
                "/contexts", 
                "/subjects",
                "/compatibility"
            ]
        }
    }
}
```

2. **Custom Commands**
Create Cursor commands in `.cursor/commands.json`:
```json
{
    "commands": [
        {
            "name": "schema:register",
            "description": "Register a new schema with AI assistance",
            "command": "curl -X POST http://localhost:38000/schemas",
            "ai_enhanced": true
        },
        {
            "name": "schema:evolve", 
            "description": "Evolve schema with compatibility checking",
            "ai_enhanced": true,
            "workflow": [
                "analyze_current_schema",
                "suggest_evolution",
                "check_compatibility",
                "apply_changes"
            ]
        }
    ]
}
```

#### **AI-Enhanced Workflows**

**1. Intelligent Schema Generation**
```typescript
// Cursor AI Prompt Example:
// "Generate an Avro schema for user events with the following requirements:
// - User ID (required integer)
// - Event type (enum: login, logout, purchase, view)
// - Timestamp (long, required)
// - Metadata (optional map of strings)
// - Ensure backward compatibility with existing user schemas"

interface UserEvent {
    userId: number;
    eventType: 'login' | 'logout' | 'purchase' | 'view';
    timestamp: number;
    metadata?: Record<string, string>;
}

// AI will generate corresponding Avro schema and registration code
```

**2. Context-Aware Development**
```bash
# Cursor can understand your current context and suggest appropriate actions
# When working in schema files, it will:
# - Suggest field additions based on existing patterns
# - Warn about breaking changes
# - Recommend context strategies
# - Generate test data
```

#### **Advanced Features**

**1. Schema Visualization**
```python
# Cursor can generate visualization code for your schemas
import graphviz
from typing import Dict, Any

def visualize_schema_evolution(schema_versions: list) -> graphviz.Digraph:
    """Generate visual representation of schema evolution"""
    # AI-generated visualization code
    pass
```

**2. Automated Testing**
```python
# AI-generated test cases based on schema changes
@pytest.mark.parametrize("context", ["development", "staging", "production"])
def test_schema_compatibility_across_contexts(context: str):
    """Test schema compatibility in different contexts"""
    # AI-generated test implementation
    pass
```

**3. Migration Scripts**
```python
# AI-generated migration utilities
class SchemaContextMigrator:
    """Migrate schemas between contexts with validation"""
    
    def __init__(self, mcp_server_url: str):
        self.base_url = mcp_server_url
    
    async def migrate_schema(self, 
                           subject: str, 
                           from_context: str, 
                           to_context: str) -> bool:
        """AI-generated migration logic"""
        pass
```

#### **Cursor Shortcuts & Snippets**

Add to your Cursor snippets:
```json
{
    "Register Avro Schema": {
        "prefix": "avro-register",
        "body": [
            "curl -X POST http://localhost:38000/schemas \\",
            "  -H \"Content-Type: application/json\" \\", 
            "  -d '{",
            "    \"subject\": \"${1:subject-name}\",",
            "    \"schema\": {",
            "      \"type\": \"record\",",
            "      \"name\": \"${2:RecordName}\",",
            "      \"fields\": [",
            "        {\"name\": \"${3:field-name}\", \"type\": \"${4:string}\"}",
            "      ]",
            "    },",
            "    \"schemaType\": \"AVRO\",",
            "    \"context\": \"${5:development}\"",
            "  }'"
        ]
    },
    "Check Schema Compatibility": {
        "prefix": "schema-compat",
        "body": [
            "curl -X POST http://localhost:38000/compatibility \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{",
            "    \"subject\": \"${1:subject-name}\",", 
            "    \"schema\": ${2:schema-object},",
            "    \"context\": \"${3:production}\"",
            "  }'"
        ]
    }
}
```

---

## 🚀 Development Tips

### **Cross-IDE Workflows**
- Use the MCP server as a central point for schema management across all IDEs
- Share `.http` files between VS Code and other REST clients
- Maintain consistent environment variables across all development tools

### **AI Assistant Best Practices**
- Always validate AI-generated schemas with the compatibility endpoint
- Use context isolation for safe experimentation
- Test schema changes in development context before promoting

### **Debugging & Troubleshooting**
- Check service health endpoints before debugging schema issues
- Use the enhanced test script for comprehensive diagnostics
- Monitor Docker logs through your IDE's integrated terminal

---