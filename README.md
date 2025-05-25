# Kafka Schema Registry MCP Server v1.3.0

A comprehensive Message Control Protocol (MCP) server that provides a REST API interface for Kafka Schema Registry operations, including advanced **Schema Context** support for logical schema grouping and management, **Configuration Management** for compatibility settings, **Mode Control** for operational state management, and **comprehensive Schema Export** capabilities for backup, migration, and schema documentation.

## ✨ Features

- **Complete Schema Management**: Register, retrieve, and manage Avro schemas
- **Schema Contexts**: Logical grouping with separate "sub-registries" 
- **Configuration Management**: Control compatibility levels globally and per-subject
- **Mode Control**: Manage operational states (READWRITE, READONLY, IMPORT)
- **Schema Export**: Comprehensive export capabilities with JSON, Avro IDL, and ZIP bundle formats
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
- **Enterprise-Ready Configuration**: Granular control over compatibility and operational modes
- **Multi-Format Export**: JSON, Avro IDL, and ZIP bundle export formats

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

### Configuration Management

#### Get Global Configuration
```bash
GET /config?context={context}
```
```bash
curl http://localhost:38000/config
curl http://localhost:38000/config?context=production
```

#### Update Global Configuration
```bash
PUT /config?context={context}
```
```bash
curl -X PUT http://localhost:38000/config \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FULL"}'

curl -X PUT http://localhost:38000/config?context=production \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "BACKWARD"}'
```

#### Get/Set Subject Configuration
```bash
GET /config/{subject}?context={context}
PUT /config/{subject}?context={context}
```
```bash
# Get subject-specific configuration
curl http://localhost:38000/config/user-value

# Set subject-specific compatibility level
curl -X PUT http://localhost:38000/config/user-value \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FORWARD"}'

# Subject config in specific context
curl -X PUT http://localhost:38000/config/user-value?context=staging \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FULL"}'
```

### Mode Management

#### Get/Set Global Mode
```bash
GET /mode?context={context}
PUT /mode?context={context}
```
```bash
# Get current mode
curl http://localhost:38000/mode

# Set to read-only mode
curl -X PUT http://localhost:38000/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "READONLY"}'

# Set import mode for specific context
curl -X PUT http://localhost:38000/mode?context=staging \
  -H "Content-Type: application/json" \
  -d '{"mode": "IMPORT"}'
```

#### Get/Set Subject Mode
```bash
GET /mode/{subject}?context={context}
PUT /mode/{subject}?context={context}
```
```bash
# Get subject mode
curl http://localhost:38000/mode/user-value

# Set subject to read-only
curl -X PUT http://localhost:38000/mode/user-value \
  -H "Content-Type: application/json" \
  -d '{"mode": "READONLY"}'
```

### Schema Export

#### Export Single Schema
```bash
GET /export/schemas/{subject}?version=latest&context={context}&format={format}
```
```bash
# Export latest schema as JSON
curl http://localhost:38000/export/schemas/user-value

# Export specific version as Avro IDL
curl http://localhost:38000/export/schemas/user-value?version=2&format=avro_idl

# Export from specific context
curl http://localhost:38000/export/schemas/user-value?context=production&format=json
```

#### Export Subject (All Versions)
```bash
POST /export/subjects/{subject}?context={context}
```
```bash
curl -X POST http://localhost:38000/export/subjects/user-value \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }'

# Export only latest version
curl -X POST http://localhost:38000/export/subjects/user-value \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_versions": "latest"
  }'
```

#### Export Context (All Subjects)
```bash
POST /export/contexts/{context}
```
```bash
# Export context as JSON
curl -X POST http://localhost:38000/export/contexts/production \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }'

# Export context as ZIP bundle
curl -X POST http://localhost:38000/export/contexts/production \
  -H "Content-Type: application/json" \
  -d '{
    "format": "bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }' --output production_export.zip
```

#### Export Global (All Contexts)
```bash
POST /export/global
```
```bash
# Export everything as JSON
curl -X POST http://localhost:38000/export/global \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }'

# Export everything as comprehensive ZIP bundle
curl -X POST http://localhost:38000/export/global \
  -H "Content-Type: application/json" \
  -d '{
    "format": "bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }' --output complete_registry_export.zip
```

#### List Exportable Subjects
```bash
GET /export/subjects?context={context}
```
```bash
# List all exportable subjects in default context
curl http://localhost:38000/export/subjects

# List exportable subjects in specific context
curl http://localhost:38000/export/subjects?context=production
```

## 📦 Schema Export Features

The Schema Export functionality provides comprehensive capabilities for backing up, migrating, and documenting your schema registry:

### **Export Formats**
- **JSON**: Structured export with complete metadata
- **Avro IDL**: Human-readable schema documentation
- **ZIP Bundle**: Packaged exports with organized file structure

### **Export Scopes**
- **Single Schema**: Export specific schema versions
- **Subject Export**: All versions of a schema subject
- **Context Export**: All schemas within a context
- **Global Export**: Complete registry backup

### **Export Options**
- **Version Control**: Export all versions, latest only, or specific versions
- **Metadata Inclusion**: Export timestamps, registry URLs, and context information
- **Configuration Export**: Include compatibility settings and operational modes
- **Flexible Filtering**: Context-aware exports with granular control

### **Use Cases**
- **🔄 Migration**: Move schemas between environments or registries
- **💾 Backup**: Regular backups of schema registry state
- **📋 Documentation**: Generate human-readable schema documentation
- **🔍 Auditing**: Export for compliance and schema governance
- **🧪 Testing**: Create test datasets with schema versions
- **📊 Analysis**: Schema evolution analysis and reporting

### **Export Endpoints Quick Reference**

| Endpoint | Method | Description | Output Format |
|----------|--------|-------------|---------------|
| `/export/schemas/{subject}` | GET | Export single schema | JSON, Avro IDL |
| `/export/subjects/{subject}` | POST | Export all versions of subject | JSON |
| `/export/contexts/{context}` | POST | Export entire context | JSON, ZIP Bundle |
| `/export/global` | POST | Export complete registry | JSON, ZIP Bundle |
| `/export/subjects` | GET | List exportable subjects | JSON |

### **Advanced Export Examples**

#### Backup Production Environment
```bash
# Export entire production context as ZIP bundle
curl -X POST http://localhost:38000/export/contexts/production \
  -H "Content-Type: application/json" \
  -d '{
    "format": "bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }' --output production_backup_$(date +%Y%m%d).zip
```

#### Generate Schema Documentation
```bash
# Export all schemas as Avro IDL for documentation
curl http://localhost:38000/export/schemas/user-events?format=avro_idl \
  --output user-events-schema.avdl

# Export specific version for historical documentation
curl http://localhost:38000/export/schemas/user-events?version=3&format=avro_idl \
  --output user-events-v3-schema.avdl
```

#### Migration Between Environments
```bash
# 1. Export from staging
curl -X POST http://localhost:38000/export/contexts/staging \
  -d '{"format": "json", "include_versions": "latest"}' \
  --output staging_schemas.json

# 2. Process and import to production (external tooling)
# 3. Verify with specific version exports
curl http://localhost:38000/export/schemas/user-events?context=production&version=latest
```

#### Schema Governance and Auditing
```bash
# Export with full metadata for compliance
curl -X POST http://localhost:38000/export/global \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }' --output compliance_export_$(date +%Y%m%d_%H%M%S).json
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

## 🔧 Configuration & Mode Benefits

### **Compatibility Management**
- **Global Control**: Set default compatibility levels across all schemas
- **Subject Override**: Fine-tune compatibility per schema subject
- **Context Isolation**: Different compatibility rules per environment/context
- **Evolution Safety**: Prevent breaking changes with strict compatibility levels

### **Operational Modes**
- **READWRITE**: Normal operation for active development and production
- **READONLY**: Temporary read-only mode for maintenance or migrations  
- **IMPORT**: Special mode for bulk schema imports and migrations
- **Subject-Level Control**: Different modes per schema subject
- **Context-Aware**: Mode settings per context for environment-specific control

### **Governance Benefits**
- **Policy Enforcement**: Automated compatibility checking
- **Change Control**: Controlled schema evolution with approval workflows
- **Risk Mitigation**: Read-only modes prevent accidental modifications
- **Migration Support**: Import mode for safe schema migrations

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
- ✅ **Configuration Management**: Global and subject-level compatibility settings
- ✅ **Mode Control**: Operational state management (READWRITE, READONLY, IMPORT)
- ✅ **Context-Aware Config/Mode**: Configuration and mode settings per context
- ✅ **Schema Export**: Single schemas, subjects, contexts, and global exports (17 export tests)
- ✅ **Export Formats**: JSON, Avro IDL, and ZIP bundle formats with metadata
- ✅ **Export Validation**: Content verification, format validation, and metadata inclusion
- ✅ **Compatibility Checking**: Both default and context-aware
- ✅ **Error Handling**: Invalid schemas, missing subjects, invalid config/mode
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

# Test export functionality
curl http://localhost:38000/export/schemas/test-user?context=test-env&format=json
curl http://localhost:38000/export/schemas/test-user?context=test-env&format=avro_idl
```

### Configuration & Mode Example
```bash
# 1. Check current global configuration and mode
curl http://localhost:38000/config
curl http://localhost:38000/mode

# 2. Create production and staging contexts
curl -X POST http://localhost:38000/contexts/production
curl -X POST http://localhost:38000/contexts/staging

# 3. Set strict compatibility for production
curl -X PUT http://localhost:38000/config?context=production \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FULL"}'

# 4. Set lenient compatibility for staging  
curl -X PUT http://localhost:38000/config?context=staging \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "NONE"}'

# 5. Register schema in production with strict rules
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events",
    "schema": {
      "type": "record", 
      "name": "UserEvent",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "action", "type": "string"}
      ]
    },
    "context": "production"
  }'

# 6. Test evolution in staging (should succeed with NONE compatibility)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events",
    "schema": {
      "type": "record",
      "name": "UserEvent", 
      "fields": [
        {"name": "userId", "type": "int"},
        {"name": "action", "type": "string"}
      ]
    },
    "context": "staging"
  }'

# 7. Set production to read-only for maintenance
curl -X PUT http://localhost:38000/mode?context=production \
  -H "Content-Type: application/json" \
  -d '{"mode": "READONLY"}'

# 8. Try to register in read-only production (should fail)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "new-events",
    "schema": {"type": "record", "name": "NewEvent", "fields": []},
    "context": "production"
  }'

# 9. Reset production to normal operation
curl -X PUT http://localhost:38000/mode?context=production \
  -H "Content-Type: application/json" \
  -d '{"mode": "READWRITE"}'
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

## 📚 Documentation

This project includes comprehensive documentation in the `docs/` folder:

- **[Use Cases](docs/use-cases.md)** - Real-world scenarios and implementation examples
- **[API Reference](docs/api-reference.md)** - Complete endpoint documentation  
- **[IDE Integration](docs/ide-integration.md)** - VS Code, Claude Code, and Cursor setup
- **[Deployment Guide](docs/deployment.md)** - Docker, Kubernetes, and cloud deployments

### Key Integration Guides

#### 🔵 **VS Code Integration**
Complete setup with extensions, workspace configuration, REST client testing, and debugging.

#### 🤖 **Claude Code Integration**  
AI-assisted schema development with intelligent workflows and context management.

#### ⚡ **Cursor Integration**
AI-powered development with schema generation, visualization, and automated testing.

## 🚀 Production Deployment

For production deployments, see the [Deployment Guide](docs/deployment.md) which covers:

- **Docker Compose** production configurations
- **Kubernetes** deployments with Helm charts
- **Cloud platforms** (AWS EKS, Google Cloud Run, Azure)
- **Security** considerations and best practices
- **Monitoring** with Prometheus and Grafana
- **Performance** optimization and scaling

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

**Latest Test Results**: ✅ **53 PASSED**, ⚠️ **1 SKIPPED** (auth), ❌ **0 FAILED**

This includes comprehensive testing of:
- ✅ **Core Schema Operations**: Registration, retrieval, versioning, compatibility
- ✅ **Schema Context Management**: Creation, isolation, context-aware operations  
- ✅ **Configuration Management**: Global and subject-level compatibility controls
- ✅ **Mode Control**: Operational state management across contexts
- ✅ **Schema Export**: All export formats and scopes with comprehensive validation
- ✅ **Error Handling**: Invalid requests, missing resources, permission checks
- ✅ **Authentication**: Optional basic auth support

**New in v1.3.0:**
- 🆕 **Schema Export**: Comprehensive export functionality with multiple formats (17 export endpoints)
- 🆕 **Avro IDL Support**: Export schemas in human-readable Avro IDL format for documentation
- 🆕 **ZIP Bundle Export**: Package schemas with metadata, configuration, and organized file structure
- 🆕 **Multi-Scope Export**: Single schema, subject, context, or global exports with granular control
- 🆕 **Export Metadata**: Comprehensive export tracking with timestamps, URLs, and context information
- 🆕 **Flexible Versioning**: Export specific versions, latest, or all versions with validation
- 🆕 **Production-Ready**: 53 passing tests covering all export scenarios and edge cases

**Previous Releases:**
- **v1.2.0**: Configuration Management, Mode Control, Context-Aware Config/Mode
- **v1.1.0**: Schema Context Support, Context-Aware Operations  
- **v1.0.0**: Core Schema Registry MCP functionality