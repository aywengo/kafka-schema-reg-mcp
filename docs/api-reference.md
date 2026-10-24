# API Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server v3.0 REST API with **FastMCP 4.1+** and **MCP 2026-07-28**. The same process also serves `2025-11-25` clients. The MCP tool surface is edition-dependent; see [editions.md](editions.md).

> **Note**: This document describes the REST API endpoints provided by the Kafka Schema Registry MCP Server. For the MCP (Model Context Protocol) tools used with Claude Desktop, please refer to the [MCP Tools Reference](mcp-tools-reference.md).

## Base URL

```
http://localhost:38000
```

## Authentication

> **Important Distinction:**
> - `SCHEMA_REGISTRY_USER` and `SCHEMA_REGISTRY_PASSWORD` (and their multi-registry variants) are used by the MCP server to authenticate against the backend Kafka Schema Registry. They do NOT protect access to the MCP server itself.
> - To secure the MCP server API/tools, use `ENABLE_AUTH` and related `AUTH_*` variables to enable OAuth2 authentication for MCP clients.

The MCP server supports optional basic authentication when configured with environment variables:

```bash
export SCHEMA_REGISTRY_USER="your-username"
export SCHEMA_REGISTRY_PASSWORD="your-password"
```

When authentication is enabled, include credentials in requests:

```bash
curl -u username:password http://localhost:38000/...
```

### Environment Variables for Authentication

| Variable | Description | Applies To |
|----------|-------------|------------|
| `SCHEMA_REGISTRY_USER` | Username for backend Schema Registry | Schema Registry (backend) |
| `SCHEMA_REGISTRY_PASSWORD` | Password for backend Schema Registry | Schema Registry (backend) |
| `ENABLE_AUTH` | Enable OAuth2 authentication/authorization | MCP Server (frontend) |
| `AUTH_ISSUER_URL` | OAuth2 issuer URL | MCP Server (frontend) |
| `AUTH_VALID_SCOPES` | Comma-separated list of valid scopes | MCP Server (frontend) |
| `AUTH_DEFAULT_SCOPES` | Comma-separated list of default scopes | MCP Server (frontend) |
| `AUTH_REQUIRED_SCOPES` | Comma-separated list of required scopes | MCP Server (frontend) |
| `AUTH_CLIENT_REG_ENABLED` | Enable dynamic client registration | MCP Server (frontend) |
| `AUTH_REVOCATION_ENABLED` | Enable token revocation endpoint | MCP Server (frontend) |

---

## 📦 Schema Export Endpoints (New in v1.3.0)

The MCP server provides comprehensive export capabilities with 17 endpoints covering all export scenarios:

### **Export Formats**
- **JSON**: Structured export with complete metadata and configuration
- **Avro IDL**: Human-readable schema documentation format
- **ZIP Bundle**: Packaged exports with organized file structure

### **Export Scopes**
- **Single Schema**: Export specific schema versions
- **Subject Export**: All versions of a schema subject with metadata
- **Context Export**: Complete context with all subjects and configuration
- **Global Export**: Full registry backup with all contexts

### **Quick Reference**
| Endpoint | Method | Scope | Formats |
|----------|--------|-------|---------|
| `GET /export/schemas/{subject}` | GET | Single schema | JSON, Avro IDL |
| `POST /export/subjects/{subject}` | POST | Subject (all versions) | JSON |
| `POST /export/contexts/{context}` | POST | Context (all subjects) | JSON, ZIP Bundle |
| `POST /export/global` | POST | Global (all contexts) | JSON, ZIP Bundle |
| `GET /export/subjects` | GET | Subject listing | JSON |

See the [Export Endpoints](#export-endpoints) section below for detailed documentation.

---

## Core Endpoints

### Health Check

#### GET `/`

Check if the MCP server is running and healthy.

**Response:**
```json
{
    "message": "Kafka Schema Registry MCP Server with Context Support"
}
```

**Example:**
```bash
curl http://localhost:38000/
```

---

## Context Management

### List Contexts

#### GET `/contexts`

Retrieve all available schema contexts.

**Response:**
```json
{
    "contexts": ["development", "staging", "production", "team-alpha"]
}
```

**Example:**
```bash
curl http://localhost:38000/contexts
```

### Create Context

#### POST `/contexts/{context}`

Create a new schema context.

**Parameters:**
- `context` (path): Context name

**Response:**
```json
{
    "message": "Context 'development' created successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:38000/contexts/development
```

### Delete Context

#### DELETE `/contexts/{context}`

Delete an existing schema context.

**Parameters:**
- `context` (path): Context name

**Response:**
```json
{
    "message": "Context 'development' deleted successfully"
}
```

**Error Responses:**
- `404`: Context not found
- `500`: Context contains schemas (some registries may not support deletion)

---

## Schema Management

### Register Schema

#### POST `/schemas`

Register a new schema version for a subject.

**Query Parameters:**
- `context` (optional): Schema context name

**Request Body:**
```json
{
    "subject": "string",
    "schema": {
        "type": "record",
        "name": "SchemaName",
        "fields": [...]
    },
    "schemaType": "AVRO",
    "context": "string"
}
```

**Response:**
```json
{
    "id": 1
}
```

**Examples:**

Basic registration:
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

With context (request body):
```bash
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO",
    "context": "development"
  }'
```

With context (query parameter):
```bash
curl -X POST http://localhost:38000/schemas?context=development \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO"
  }'
```

**Error Responses:**
- `400`: Invalid schema format
- `409`: Schema evolution conflict
- `500`: Registration failed

### Get Schema

#### GET `/schemas/{subject}`

Retrieve a specific schema version.

**Parameters:**
- `subject` (path): Schema subject name
- `version` (query, optional): Schema version (default: "latest")
- `context` (query, optional): Schema context

**Response:**
```json
{
    "subject": "user-value",
    "version": 1,
    "id": 1,
    "schema": "{\"type\":\"record\",\"name\":\"User\",\"fields\":[...]}"
}
```

**Examples:**

Get latest version:
```bash
curl http://localhost:38000/schemas/user-value
```

Get specific version:
```bash
curl http://localhost:38000/schemas/user-value?version=2
```

Get from specific context:
```bash
curl http://localhost:38000/schemas/user-value?context=production
```

**Error Responses:**
- `404`: Schema or version not found

### Get Schema Versions

#### GET `/schemas/{subject}/versions`

List all versions of a schema subject.

**Parameters:**
- `subject` (path): Schema subject name
- `context` (query, optional): Schema context

**Response:**
```json
[1, 2, 3, 4]
```

**Examples:**

Get all versions:
```bash
curl http://localhost:38000/schemas/user-value/versions
```

Get versions in context:
```bash
curl http://localhost:38000/schemas/user-value/versions?context=production
```

**Error Responses:**
- `404`: Subject not found

---

## Compatibility Checking

### Check Compatibility

#### POST `/compatibility`

Check if a schema is compatible with the latest version of a subject.

**Query Parameters:**
- `context` (optional): Schema context name

**Request Body:**
```json
{
    "subject": "string",
    "schema": {
        "type": "record",
        "name": "SchemaName",
        "fields": [...]
    },
    "schemaType": "AVRO",
    "context": "string"
}
```

**Response:**
```json
{
    "is_compatible": true
}
```

**Examples:**

Basic compatibility check:
```bash
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
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
    "schemaType": "AVRO"
  }'
```

With context:
```bash
curl -X POST http://localhost:38000/compatibility?context=production \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-value",
    "schema": {...},
    "schemaType": "AVRO"
  }'
```

**Error Responses:**
- `400`: Invalid schema format
- `404`: Subject not found
- `500`: Compatibility check failed

---

## Subject Management

### List Subjects

#### GET `/subjects`

List all subjects in the registry.

**Query Parameters:**
- `context` (optional): Filter by schema context

**Response:**
```json
["user-value", "order-events", "payment-processed"]
```

**Examples:**

List all subjects:
```bash
curl http://localhost:38000/subjects
```

List subjects in context:
```bash
curl http://localhost:38000/subjects?context=production
```

### Delete Subject

#### DELETE `/subjects/{subject}`

Delete a subject and all its versions.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Response:**
```json
[1, 2, 3]
```

**Examples:**

Delete subject:
```bash
curl -X DELETE http://localhost:38000/subjects/user-value
```

Delete from specific context:
```bash
curl -X DELETE http://localhost:38000/subjects/user-value?context=development
```

**Error Responses:**
- `404`: Subject not found
- `500`: Deletion failed

---

## Data Models

### Schema Request

```json
{
    "subject": "string",           // Required: Subject name
    "schema": {                    // Required: Avro schema object
        "type": "record",
        "name": "RecordName",
        "namespace": "optional.namespace",
        "fields": [
            {
                "name": "fieldName",
                "type": "fieldType",
                "doc": "optional documentation",
                "default": "optional default value"
            }
        ]
    },
    "schemaType": "AVRO",          // Optional: Default "AVRO"
    "context": "string"            // Optional: Context name
}
```

### Schema Response

```json
{
    "subject": "string",           // Subject name (may include context prefix)
    "version": 1,                  // Schema version number
    "id": 1,                       // Global schema ID
    "schema": "string"             // JSON-encoded schema
}
```

### Schema Registration Response

```json
{
    "id": 1                        // Assigned schema ID
}
```

### Compatibility Request

```json
{
    "subject": "string",           // Required: Subject name
    "schema": {                    // Required: Schema to check
        "type": "record",
        "name": "RecordName",
        "fields": [...]
    },
    "schemaType": "AVRO",          // Optional: Default "AVRO"
    "context": "string"            // Optional: Context name
}
```

### Compatibility Response

```json
{
    "is_compatible": true          // Compatibility result
}
```

### Context Response

```json
{
    "contexts": [                  // Array of context names
        "development",
        "staging",
        "production"
    ]
}
```

### Config Request

```json
{
    "compatibility": "string"      // Optional: Compatibility level
}
```

### Config Response

```json
{
    "compatibilityLevel": "string" // Current compatibility level
}
```

### Mode Request

```json
{
    "mode": "string"               // Required: Mode (IMPORT, READONLY, READWRITE)
}
```

### Mode Response

```json
{
    "mode": "string"               // Current mode
}
```

---

## Error Responses

### Standard Error Format

```json
{
    "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request format or data |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Schema evolution conflict |
| 500 | Internal Server Error | Server-side error |

### Common Error Scenarios

#### Schema Registration Errors

**Invalid Schema Format (400):**
```json
{
    "detail": "Invalid Avro schema format"
}
```

**Schema Evolution Conflict (409):**
```json
{
    "detail": "Schema evolution violates compatibility rules"
}
```

#### Context Errors

**Context Not Found (404):**
```json
{
    "detail": "Context 'unknown-context' not found"
}
```

**Context Deletion Failed (500):**
```json
{
    "detail": "Cannot delete context with existing schemas"
}
```

#### Subject Errors

**Subject Not Found (404):**
```json
{
    "detail": "Subject 'unknown-subject' not found"
}
```

**Version Not Found (404):**
```json
{
    "detail": "Version 999 not found for subject 'user-value'"
}
```

---

## Configuration Management

### Get Global Configuration

#### GET `/config`

Retrieve global Schema Registry configuration settings.

**Query Parameters:**
- `context` (optional): Schema context

**Response:**
```json
{
    "compatibilityLevel": "BACKWARD"
}
```

**Examples:**

Get global configuration:
```bash
curl http://localhost:38000/config
```

Get configuration for specific context:
```bash
curl http://localhost:38000/config?context=production
```

**Compatibility Levels:**
- `BACKWARD`: New schema can read data written with previous schema
- `FORWARD`: Previous schema can read data written with new schema
- `FULL`: Both backward and forward compatible
- `NONE`: No compatibility checking
- `BACKWARD_TRANSITIVE`: Backward compatible with all previous versions
- `FORWARD_TRANSITIVE`: Forward compatible with all future versions
- `FULL_TRANSITIVE`: Both backward and forward transitive compatible

### Update Global Configuration

#### PUT `/config`

Update global Schema Registry configuration settings.

**Query Parameters:**
- `context` (optional): Schema context

**Request Body:**
```json
{
    "compatibility": "BACKWARD"
}
```

**Response:**
```json
{
    "compatibility": "BACKWARD"
}
```

**Examples:**

Update global compatibility:
```bash
curl -X PUT http://localhost:38000/config \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FULL"}'
```

Update for specific context:
```bash
curl -X PUT http://localhost:38000/config?context=production \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "BACKWARD"}'
```

### Get Subject Configuration

#### GET `/config/{subject}`

Get configuration settings for a specific subject.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Response:**
```json
{
    "compatibilityLevel": "FORWARD"
}
```

**Examples:**

Get subject configuration:
```bash
curl http://localhost:38000/config/user-value
```

Get from specific context:
```bash
curl http://localhost:38000/config/user-value?context=production
```

**Error Responses:**
- `404`: Subject not found or no specific configuration set

### Update Subject Configuration

#### PUT `/config/{subject}`

Update configuration settings for a specific subject.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Request Body:**
```json
{
    "compatibility": "FORWARD"
}
```

**Response:**
```json
{
    "compatibility": "FORWARD"
}
```

**Examples:**

Set subject-specific configuration:
```bash
curl -X PUT http://localhost:38000/config/user-value \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FORWARD"}'
```

Set in specific context:
```bash
curl -X PUT http://localhost:38000/config/user-value?context=staging \
  -H "Content-Type: application/json" \
  -d '{"compatibility": "FULL"}'
```

### Add Subject Alias (MCP Tool)

- Tool: `add_subject_alias` (editor and admin, blocked in VIEWONLY)
- Params: `alias`, `existing_subject`, optional `context`, `registry`
- See: [Subject Aliasing](./subject-alias.md)

### Delete Subject Alias (MCP Tool)

- Tool: `delete_subject_alias` (editor and admin, blocked in VIEWONLY)
- Params: `alias`, optional `context`, `registry`
- See: [Subject Aliasing](./subject-alias.md)

### Delete Subject Configuration

#### DELETE `/config/{subject}`

Delete configuration settings for a specific subject, reverting to global configuration.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Response:**
```json
{
    "message": "Configuration for subject 'user-value' deleted successfully"
}
```

**Examples:**

Delete subject configuration:
```bash
curl -X DELETE http://localhost:38000/config/user-value
```

Delete from specific context:
```bash
curl -X DELETE http://localhost:38000/config/user-value?context=staging
```

---

## Mode Management

### Get Mode

#### GET `/mode`

Get the current operational mode of the Schema Registry.

**Query Parameters:**
- `context` (optional): Schema context

**Response:**
```json
{
    "mode": "READWRITE"
}
```

**Examples:**

Get global mode:
```bash
curl http://localhost:38000/mode
```

Get mode for specific context:
```bash
curl http://localhost:38000/mode?context=production
```

**Mode Types:**
- `READWRITE`: Normal operation mode (default)
- `READONLY`: Only read operations allowed
- `IMPORT`: Special mode for importing schemas from external sources

### Update Mode

#### PUT `/mode`

Update the operational mode of the Schema Registry.

**Query Parameters:**
- `context` (optional): Schema context

**Request Body:**
```json
{
    "mode": "READONLY"
}
```

**Response:**
```json
{
    "mode": "READONLY"
}
```

**Examples:**

Set to read-only mode:
```bash
curl -X PUT http://localhost:38000/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "READONLY"}'
```

Set import mode for context:
```bash
curl -X PUT http://localhost:38000/mode?context=staging \
  -H "Content-Type: application/json" \
  -d '{"mode": "IMPORT"}'
```

**Error Responses:**
- `422`: Invalid mode value
- `403`: Mode change not allowed

### Get Subject Mode

#### GET `/mode/{subject}`

Get the operational mode for a specific subject.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Response:**
```json
{
    "mode": "READWRITE"
}
```

**Examples:**

Get subject mode:
```bash
curl http://localhost:38000/mode/user-value
```

Get from specific context:
```bash
curl http://localhost:38000/mode/user-value?context=production
```

**Error Responses:**
- `404`: Subject not found or no specific mode set

### Update Subject Mode

#### PUT `/mode/{subject}`

Update the operational mode for a specific subject.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Request Body:**
```json
{
    "mode": "READONLY"
}
```

**Response:**
```json
{
    "mode": "READONLY"
}
```

**Examples:**

Set subject to read-only:
```bash
curl -X PUT http://localhost:38000/mode/user-value \
  -H "Content-Type: application/json" \
  -d '{"mode": "READONLY"}'
```

Set in specific context:
```bash
curl -X PUT http://localhost:38000/mode/user-value?context=production \
  -H "Content-Type: application/json" \
  -d '{"mode": "READWRITE"}'
```

### Delete Subject Mode

#### DELETE `/mode/{subject}`

Delete the mode setting for a specific subject, reverting to global mode.

**Parameters:**
- `subject` (path): Subject name
- `context` (query, optional): Schema context

**Response:**
```json
{
    "message": "Mode setting for subject 'user-value' deleted successfully"
}
```

**Examples:**

Delete subject mode:
```bash
curl -X DELETE http://localhost:38000/mode/user-value
```

Delete from specific context:
```bash
curl -X DELETE http://localhost:38000/mode/user-value?context=staging
```

---

## Advanced Usage Examples

### Multi-Context Schema Evolution

```bash
# 1. Register initial schema in development
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "amount", "type": "double"}
      ]
    },
    "context": "development"
  }'

# 2. Evolve schema (add optional field)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"}
      ]
    },
    "context": "development"
  }'

# 3. Check compatibility with production
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"}
      ]
    },
    "context": "production"
  }'

# 4. If compatible, promote to production
curl -X POST http://localhost:38000/schemas?context=production \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"}
      ]
    }
  }'
```

### Batch Operations Script

```bash
#!/bin/bash

# Create multiple contexts
contexts=("development" "staging" "production" "team-alpha" "team-beta")
for context in "${contexts[@]}"; do
    echo "Creating context: $context"
    curl -X POST "http://localhost:38000/contexts/$context"
done

# Register schemas across contexts
subjects=("user-events" "order-events" "payment-events")
for subject in "${subjects[@]}"; do
    for context in "development" "staging"; do
        echo "Registering $subject in $context"
        curl -X POST "http://localhost:38000/schemas?context=$context" \
          -H "Content-Type: application/json" \
          -d "{
            \"subject\": \"$subject\",
            \"schema\": {
              \"type\": \"record\",
              \"name\": \"Event\",
              \"fields\": [
                {\"name\": \"id\", \"type\": \"string\"},
                {\"name\": \"timestamp\", \"type\": \"long\"}
              ]
            }
          }"
    done
done

# Generate compatibility report
echo "=== Compatibility Report ==="
for subject in "${subjects[@]}"; do
    echo "Subject: $subject"
    for context in "development" "staging" "production"; do
        result=$(curl -s "http://localhost:38000/schemas/$subject?context=$context")
        if echo "$result" | grep -q "detail"; then
            echo "  $context: NOT FOUND"
        else
            version=$(echo "$result" | jq -r .version)
            echo "  $context: Version $version"
        fi
    done
    echo ""
done
```

---

## Export Endpoints

### Export Single Schema

#### GET `/export/schemas/{subject}`

Export a single schema version with optional format conversion.

**Parameters:**
- `subject` (path): Schema subject name
- `version` (query, optional): Schema version (default: "latest")
- `context` (query, optional): Schema context
- `format` (query, optional): Export format ("json" or "avro_idl", default: "json")
- `include_metadata` (query, optional): Include export metadata (default: true)

**Response (JSON format):**
```json
{
    "subject": "user-events",
    "version": 1,
    "id": 123,
    "schema": "{\"type\":\"record\",\"name\":\"UserEvent\",...}",
    "schemaType": "AVRO",
    "metadata": {
        "exported_at": "2024-01-15T10:30:00Z",
        "registry_url": "http://localhost:38081",
        "context": "production"
    }
}
```

**Response (Avro IDL format):**
```idl
/**
 * Schema for user-events
 * Generated from Schema Registry subject: user-events
 */
@namespace("com.example.events")
protocol UserEventProtocol {

record UserEvent {
  string userId;
  string eventType;
  long timestamp;
}

}
```

**Examples:**
```bash
# Export latest schema as JSON
curl http://localhost:38000/export/schemas/user-events

# Export specific version as Avro IDL
curl http://localhost:38000/export/schemas/user-events?version=2&format=avro_idl

# Export from production context
curl http://localhost:38000/export/schemas/user-events?context=production&format=json
```

### Export Subject (All Versions)

#### POST `/export/subjects/{subject}`

Export all versions of a schema subject with comprehensive metadata.

**Parameters:**
- `subject` (path): Schema subject name
- `context` (query, optional): Schema context

**Request Body:**
```json
{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}
```

**Request Options:**
- `format`: Export format ("json" only for subject exports)
- `include_metadata`: Include export metadata and timestamps
- `include_config`: Include subject-specific configuration
- `include_versions`: Version selection ("all", "latest", or specific version number)

**Response:**
```json
{
    "subject": "user-events",
    "versions": [
        {
            "subject": "user-events",
            "version": 1,
            "id": 123,
            "schema": "{\"type\":\"record\",...}",
            "schemaType": "AVRO",
            "metadata": {
                "exported_at": "2024-01-15T10:30:00Z",
                "registry_url": "http://localhost:38081",
                "context": "production"
            }
        }
    ],
    "config": {
        "compatibilityLevel": "BACKWARD"
    },
    "mode": {
        "mode": "READWRITE"
    }
}
```

**Examples:**
```bash
# Export all versions
curl -X POST http://localhost:38000/export/subjects/user-events \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }'

# Export only latest version
curl -X POST http://localhost:38000/export/subjects/user-events \
  -H "Content-Type: application/json" \
  -d '{"include_versions": "latest"}'
```

### Export Context (All Subjects)

#### POST `/export/contexts/{context}`

Export all schemas, configuration, and metadata for a specific context.

**Parameters:**
- `context` (path): Context name

**Request Body:**
```json
{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}
```

**Request Options:**
- `format`: Export format ("json" or "bundle")
- `include_metadata`: Include export metadata
- `include_config`: Include context configuration
- `include_versions`: Version selection for all subjects

**Response (JSON format):**
```json
{
    "context": "production",
    "exported_at": "2024-01-15T10:30:00Z",
    "subjects": [
        {
            "subject": "user-events",
            "versions": [...],
            "config": {...},
            "mode": {...}
        }
    ],
    "global_config": {
        "compatibilityLevel": "BACKWARD"
    },
    "global_mode": {
        "mode": "READWRITE"
    }
}
```

**Response (Bundle format):**
ZIP file containing:
```
production/
├── metadata.json              # Context metadata
├── subjects/
│   ├── user-events/
│   │   ├── metadata.json      # Subject metadata
│   │   ├── v1.json           # Schema version 1
│   │   ├── v1.avdl           # Avro IDL version 1
│   │   └── v2.json           # Schema version 2
│   └── order-events/
│       ├── metadata.json
│       └── v1.json
```

**Examples:**
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

### Export Global (Complete Registry)

#### POST `/export/global`

Export the complete schema registry including all contexts and global configuration.

**Request Body:**
```json
{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
}
```

**Response (JSON format):**
```json
{
    "exported_at": "2024-01-15T10:30:00Z",
    "contexts": [
        {
            "context": "production",
            "exported_at": "2024-01-15T10:30:00Z",
            "subjects": [...],
            "global_config": {...},
            "global_mode": {...}
        }
    ],
    "default_context": {
        "context": "",
        "subjects": [...],
        "global_config": {...},
        "global_mode": {...}
    },
    "global_config": {
        "compatibilityLevel": "BACKWARD"
    },
    "global_mode": {
        "mode": "READWRITE"
    }
}
```

**Response (Bundle format):**
```
schema_registry_export_20240115_103000.zip
├── global_metadata.json       # Global export metadata
├── contexts/
│   ├── production/
│   │   ├── metadata.json
│   │   └── subjects/
│   │       └── user-events/...
│   ├── staging/
│   │   ├── metadata.json
│   │   └── subjects/...
│   └── default/               # Default context
│       ├── metadata.json
│       └── subjects/...
```

**Examples:**
```bash
# Complete registry export as JSON
curl -X POST http://localhost:38000/export/global \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }'

# Complete registry backup as ZIP
curl -X POST http://localhost:38000/export/global \
  -H "Content-Type: application/json" \
  -d '{
    "format": "bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all"
  }' --output complete_backup_$(date +%Y%m%d).zip
```

### List Exportable Subjects

#### GET `/export/subjects`

List all subjects available for export with metadata.

**Parameters:**
- `context` (query, optional): Filter by context

**Response:**
```json
{
    "context": "production",
    "subjects": [
        {
            "subject": "user-events",
            "full_subject": ":.production:user-events",
            "version_count": 3,
            "latest_version": 3,
            "context": "production"
        }
    ],
    "total_subjects": 1
}
```

**Examples:**
```bash
# List all exportable subjects
curl http://localhost:38000/export/subjects

# List subjects in specific context
curl http://localhost:38000/export/subjects?context=production
```

---

## Export Data Models

### ExportRequest

```json
{
    "format": "json|bundle",
    "include_metadata": true,
    "include_config": true,
    "include_versions": "all|latest|<version_number>"
}
```

### ExportedSchema

```json
{
    "subject": "string",
    "version": 1,
    "id": 123,
    "schema": "string",
    "schemaType": "AVRO",
    "metadata": {
        "exported_at": "2024-01-15T10:30:00Z",
        "registry_url": "http://localhost:38081",
        "context": "production"
    }
}
```

### SubjectExport

```json
{
    "subject": "string",
    "versions": [ExportedSchema],
    "config": {
        "compatibilityLevel": "BACKWARD"
    },
    "mode": {
        "mode": "READWRITE"
    }
}
```

### ContextExport

```json
{
    "context": "string",
    "exported_at": "2024-01-15T10:30:00Z",
    "subjects": [SubjectExport],
    "global_config": {
        "compatibilityLevel": "BACKWARD"
    },
    "global_mode": {
        "mode": "READWRITE"
    }
}
```

### GlobalExport

```json
{
    "exported_at": "2024-01-15T10:30:00Z",
    "contexts": [ContextExport],
    "default_context": ContextExport,
    "global_config": {
        "compatibilityLevel": "BACKWARD"
    },
    "global_mode": {
        "mode": "READWRITE"
    }
}
```

---

## 📊 MCP Tools and Resources

The v3.0.0 server exposes an edition-dependent MCP surface. The full parameter reference is in [mcp-tools-reference.md](mcp-tools-reference.md).

| Edition | Tools | Access |
|---|---|---|
| `viewer` | 39 | Read-only browsing, export, comparison, compatibility, statistics |
| `editor` | 42 | Viewer plus schema registration and evolution |
| `admin` | 66 | Full surface: configuration, deletion, contexts, migration, bulk operations, workflows |

### Tool inventory

| Tool | Edition | Scope | Kind | Description |
|---|---|---|---|---|
| `check_compatibility` | `viewer` | `read` | read-only | Check if a schema is compatible with the latest version. |
| `check_compatibility_interactive` | `viewer` | `read` | read-only | Interactive compatibility checking with elicitation for resolution options. When compatibility issues are found, this tool will elicit resolution preferences from the user. |
| `compare_contexts_across_registries` | `viewer` | `read` | read-only | Compare contexts across two registries. |
| `compare_registries` | `viewer` | `read` | read-only | Compare two Schema Registry instances and show differences. |
| `count_contexts` | `viewer` | `read` | read-only | Count the number of contexts in a registry. |
| `count_schema_versions` | `viewer` | `read` | read-only | Count the number of versions for a specific schema. |
| `count_schemas` | `viewer` | `read` | read-only | Count the number of schemas in a context or registry. |
| `describe_workflow` | `viewer` | `read` | read-only | Get detailed information about a workflow definition |
| `export_context` | `viewer` | `read` | read-only | Export all subjects within a context. |
| `export_global` | `viewer` | `read` | read-only | Export all contexts and schemas from a registry. |
| `export_global_interactive` | `viewer` | `read` | read-only | Interactive global export with elicitation for export preferences. When export preferences are not specified, this tool will elicit the required configuration from the user. |
| `export_schema` | `viewer` | `read` | read-only | Export a single schema in the specified format. |
| `export_subject` | `viewer` | `read` | read-only | Export all versions of a subject. |
| `find_missing_schemas` | `viewer` | `read` | read-only | Find schemas that exist in source registry but not in target registry. |
| `generate_resource_templates` | `viewer` | `read` | read-only | Generate resource URI templates for your specific configuration. |
| `get_default_registry` | `viewer` | `read` | read-only | Get the current default registry. |
| `get_global_config` | `viewer` | `read` | read-only | Get global configuration settings. |
| `get_mcp_compliance_status` | `viewer` | `read` | read-only | Get MCP 2026-07-28 specification compliance status and configuration details. Returns information about JSON-RPC batching status, protocol version, header validation, and migration guidance. |
| `get_mode` | `viewer` | `read` | read-only | Get the current mode of the Schema Registry. |
| `get_oauth_scopes_info` | `viewer` | `read` | read-only | Get information about OAuth scopes and permissions. |
| `get_registry_info` | `viewer` | `read` | read-only | Get detailed information about a specific registry. |
| `get_registry_statistics` | `viewer` | `read` | read-only | Get comprehensive statistics about a registry. |
| `get_schema` | `viewer` | `read` | read-only | Get a specific version of a schema. |
| `get_schema_by_id` | `viewer` | `read` | read-only | Get a schema by its globally unique ID. |
| `get_schema_versions` | `viewer` | `read` | read-only | Get all versions of a schema for a subject. |
| `get_subject_config` | `viewer` | `read` | read-only | Get configuration settings for a specific subject. |
| `get_subject_mode` | `viewer` | `read` | read-only | Get the operational mode for a specific subject. |
| `get_subjects_by_schema_id` | `viewer` | `read` | read-only | Get subjects and versions associated with a schema ID. |
| `guided_schema_evolution` | `viewer` | `read` | read-only | Start the Schema Evolution Assistant workflow. This guided workflow helps you safely evolve schemas by analyzing changes, suggesting strategies, and coordinating consumer updates. |
| `list_available_resources` | `viewer` | `read` | read-only | List all available MCP resources and their usage patterns. |
| `list_contexts` | `viewer` | `read` | read-only | List all available schema contexts. |
| `list_registries` | `viewer` | `read` | read-only | List all configured Schema Registry instances. |
| `list_subjects` | `viewer` | `read` | read-only | List all subjects, optionally filtered by context. |
| `list_workflows` | `viewer` | `read` | read-only | List available multi-step workflows |
| `ping` | `viewer` | `read` | read-only | Respond to MCP ping requests with pong. This tool implements the standard MCP ping/pong protocol for server health checking. MCP proxies and clients use this to verify that the server is alive and responding. |
| `suggest_resource_for_tool` | `viewer` | `read` | read-only | Suggest the appropriate resource to use instead of a removed tool. |
| `test_all_registries` | `viewer` | `read` | read-only | Test connections to all configured registries. |
| `test_oauth_discovery_endpoints` | `viewer` | `read` | read-only | Test OAuth discovery endpoints to ensure proper MCP client compatibility. Validates: - /.well-known/oauth-authorization-server - /.well-known/oauth-protected-resource - /.well-known/jwks.json |
| `test_registry_connection` | `viewer` | `read` | read-only | Test connection to a specific registry. |
| `add_subject_alias` | `editor` | `write` | write | Create a subject alias to an existing subject (editor and admin editions; VIEWONLY blocks writes). |
| `register_schema` | `editor` | `write` | write | Register a new schema version. |
| `register_schema_interactive` | `editor` | `write` | write | Interactive schema registration with elicitation for missing field definitions. When schema_definition is incomplete or missing fields, this tool will elicit the required information from the user interactively. |
| `bulk_configuration_update` | `admin` | `admin` | write | Update configuration settings across multiple schemas or contexts. Supports security policies, retention settings, and access controls. |
| `bulk_operations_wizard` | `admin` | `admin` | read-only | Start the interactive Bulk Operations Wizard for admin tasks. Guides through safe execution of operations across multiple schemas. Supports schema updates, migrations, cleanup, and configuration changes. |
| `bulk_schema_cleanup` | `admin` | `admin` | destructive | Clean up schemas in bulk with safety checks. Detects active consumers and provides options for handling them. Supports test schema cleanup, deprecated schema removal, and version purging. |
| `bulk_schema_migration` | `admin` | `admin` | destructive | Migrate schemas between contexts or registries. Supports pattern-based selection and maintains schema IDs. Includes preview and rollback capabilities. |
| `bulk_schema_update` | `admin` | `admin` | write | Update schemas in bulk with interactive guidance. Supports compatibility settings, naming conventions, and metadata updates. Pattern matching supported (e.g., test-*, deprecated-*). |
| `clear_context_batch` | `admin` | `admin` | destructive | Clear all subjects in a context using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution. |
| `clear_multiple_contexts_batch` | `admin` | `admin` | destructive | Clear multiple contexts in a registry using application-level batch operations. ⚠️ APPLICATION-LEVEL BATCHING: Uses individual requests per MCP 2026-07-28 compliance. Uses FastMCP background tasks API (SEP-1686) for async execution. |
| `create_context` | `admin` | `write` | write | Create a new schema context. |
| `create_context_interactive` | `admin` | `write` | write | Interactive context creation with elicitation for metadata. When context metadata is not provided, this tool will elicit organizational information from the user. |
| `delete_context` | `admin` | `admin` | destructive | Delete a schema context. |
| `delete_subject` | `admin` | `admin` | destructive | Delete a subject and all its versions. |
| `delete_subject_alias` | `admin` | `admin` | destructive | Delete a subject alias (editor and admin editions; VIEWONLY blocks writes). |
| `guided_context_reorganization` | `admin` | `admin` | read-only | Start the Context Reorganization workflow for reorganizing schemas across contexts |
| `guided_disaster_recovery` | `admin` | `admin` | read-only | Start the Disaster Recovery Setup workflow |
| `guided_schema_migration` | `admin` | `admin` | read-only | Start the Schema Migration Wizard workflow for guided schema migration |
| `migrate_context` | `admin` | `admin` | destructive | Guide for migrating an entire context using Docker-based tools. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking. |
| `migrate_context_interactive` | `admin` | `admin` | destructive | Interactive context migration with elicitation for missing preferences. When migration preferences are not specified, this tool will elicit the required configuration from the user. |
| `migrate_schema` | `admin` | `admin` | destructive | Migrate a schema from one registry to another. Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking. |
| `migrate_schema_interactive` | `admin` | `admin` | destructive | Interactive schema migration that asks for missing preferences. Modern clients get a multi-round-trip form; legacy clients get ``elicitation/create``. Declining returns a structured error. |
| `preview_bulk_operation` | `admin` | `admin` | read-only | Preview the changes a bulk operation would make without executing it. |
| `update_global_config` | `admin` | `write` | write | Update global configuration settings. |
| `update_mode` | `admin` | `write` | write | Update the mode of the Schema Registry. |
| `update_subject_config` | `admin` | `write` | write | Update configuration settings for a specific subject. |
| `update_subject_mode` | `admin` | `write` | write | Update the mode for a specific subject. |

### Resources

The server exposes 4 concrete resources and 17 resource templates. Resources are available in every edition.

| URI or template | Type | Description |
|---|---|---|
| `registry://names` | resource | Get list of all configured registry names. |
| `registry://info` | resource | Get detailed server configuration and capabilities. |
| `registry://status` | resource | Get connection status for all registries. |
| `registry://mode` | resource | Get operational mode for all registries. |
| `registry://info/{name}` | template | Get detailed information about a specific registry. |
| `registry://status/{name}` | template | Get connection status for a specific registry. |
| `registry://mode/{name}` | template | Get operational mode for a specific registry. |
| `registry://{name}/subjects` | template | Get all subjects for a specific registry, optionally filtered by context. |
| `registry://{name}/contexts/{context}/subjects` | template | Get all subjects in a named context for a specific registry. |
| `registry://{name}/contexts` | template | Get all contexts for a specific registry. |
| `registry://{name}/config` | template | Get global configuration for a specific registry, optionally filtered by context. |
| `schema://{name}/{context}/{subject}` | template | Get schema content for a specific subject in a specific context and registry. |
| `schema://{name}/{subject}` | template | Get schema content for a specific subject in the default context of a registry. |
| `schema://{name}/{context}/{subject}/versions` | template | Get all versions of a schema for a specific subject in a specific context and registry. |
| `schema://{name}/{subject}/versions` | template | Get all versions of a schema for a specific subject in the default context of a registry. |
| `subject://{name}/{context}/{subject}/config` | template | Get configuration settings for a specific subject with explicit context. |
| `subject://{name}/{subject}/config` | template | Get configuration settings for a specific subject in the default context. |
| `subject://{name}/{context}/{subject}/mode` | template | Get the mode for a specific subject with explicit context. |
| `subject://{name}/{subject}/mode` | template | Get the mode for a specific subject in the default context. |
| `registry://{name}/migrations` | template | List persisted migration records (none are persisted by this server). |
| `registry://{name}/tasks` | template | Describe how background tasks are exposed. |

### Prompts

The server exposes 10 prompts.

| Prompt | Description |
|---|---|
| `schema-getting-started` | Getting started with Schema Registry operations |
| `schema-registration` | Guide for registering new schemas |
| `context-management` | Guide for managing schema contexts |
| `schema-export` | Guide for exporting schemas and documentation |
| `multi-registry` | Guide for multi-registry operations |
| `schema-compatibility` | Guide for schema compatibility and evolution |
| `troubleshooting` | Troubleshooting guide for common issues |
| `advanced-workflows` | Guide for complex Schema Registry workflows |
| `schema-evolution` | Guide for safe schema evolution with the Schema Evolution Assistant |
| `quick-reference` | Get a quick reference card of most common commands. |

---

## Task Management Note

> **Important:** Custom task management tools (`get_task_status`, `get_task_progress`, `list_active_tasks`, `cancel_task`, `list_statistics_tasks`, `get_statistics_task_progress`) and migration status tools (`list_migrations`, `get_migration_status`) have been removed. Task status tracking is now handled by FastMCP's built-in Docket system. Use FastMCP's native task tracking instead.

---

This API reference provides comprehensive documentation for all endpoints and operations supported by the Kafka Schema Registry MCP Server v3.0.0. Use this as a reference when building integrations or working with the server programmatically.
