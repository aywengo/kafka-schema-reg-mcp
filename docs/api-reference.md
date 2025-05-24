# API Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server REST API.

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

This API reference provides comprehensive documentation for all endpoints and operations supported by the Kafka Schema Registry MCP Server. Use this as a reference when building integrations or working with the server programmatically. 