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

**Latest Test Results**: ✅ **21 PASSED**, ⚠️ **1 SKIPPED** (auth), ❌ **0 FAILED**

This includes comprehensive testing of both core functionality and advanced Schema Context features!