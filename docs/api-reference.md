# API Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server v1.7.0 REST API, including comprehensive export capabilities.

> **Note**: This document describes the REST API endpoints provided by the Kafka Schema Registry MCP Server. For the MCP (Message Control Protocol) tools used with Claude Desktop, please refer to the [MCP Tools Reference](mcp-tools-reference.md).

## Base URL

```
http://localhost:38000
```

## Authentication

The MCP server supports optional basic authentication when configured with environment variables:

```bash
export SCHEMA_REGISTRY_USER="your-username"  
export SCHEMA_REGISTRY_PASSWORD="your-password"
```

When authentication is enabled, include credentials in requests:

```bash
curl -u username:password http://localhost:38000/...
```

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

**Example:**
```bash
curl -X DELETE http://localhost:38000/contexts/development
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

This API reference provides comprehensive documentation for all endpoints and operations supported by the Kafka Schema Registry MCP Server v1.3.0. Use this as a reference when building integrations or working with the server programmatically. 