# Numbered Environment Variable Configuration Guide

## 🎯 **Enhanced Multi-Registry Configuration**

The Kafka Schema Registry MCP Server now supports a **cleaner, more intuitive configuration approach** using numbered environment variables. This eliminates complex JSON configurations and provides **per-registry READONLY mode** control.

---

## 📋 **Configuration Modes**

### **Mode 1: Single Registry (Backward Compatible)**

For single Schema Registry instance, use the traditional environment variables:

```bash
# Single registry configuration
export SCHEMA_REGISTRY_URL="http://localhost:8081"
export SCHEMA_REGISTRY_USER="admin"
export SCHEMA_REGISTRY_PASSWORD="password123"
export READONLY="false"
```

### **Mode 2: Multiple Registries (Up to 8 instances)**

For multiple Schema Registry instances, use numbered environment variables:

```bash
# Registry 1 - Development
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-schema-registry:8081"
export SCHEMA_REGISTRY_USER_1="dev-user"
export SCHEMA_REGISTRY_PASSWORD_1="dev-password"
export READONLY_1="false"

# Registry 2 - Staging  
export SCHEMA_REGISTRY_NAME_2="staging"
export SCHEMA_REGISTRY_URL_2="http://staging-schema-registry:8081"
export SCHEMA_REGISTRY_USER_2="staging-user"
export SCHEMA_REGISTRY_PASSWORD_2="staging-password"
export READONLY_2="false"

# Registry 3 - Production (Read-only for safety)
export SCHEMA_REGISTRY_NAME_3="production"
export SCHEMA_REGISTRY_URL_3="http://prod-schema-registry:8081"
export SCHEMA_REGISTRY_USER_3="prod-user"
export SCHEMA_REGISTRY_PASSWORD_3="prod-password"
export READONLY_3="true"
```

---

## 🔧 **Environment Variable Reference**

### **Required Variables (per registry)**
| Variable | Description | Example |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_NAME_X` | Registry alias/name | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint | `http://prod-registry:8081` |

### **Optional Variables (per registry)**
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCHEMA_REGISTRY_USER_X` | Username for authentication | *(empty)* | `admin` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password for authentication | *(empty)* | `password123` |
| `READONLY_X` | Enable read-only mode for this registry | `false` | `true` |

**Where X = 1, 2, 3, ... up to 8**

---

## 🔒 **Per-Registry READONLY Mode**

### **Production Safety Example**

```bash
# Development - Full access
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-registry:8081"
export READONLY_1="false"

# Production - Read-only for safety
export SCHEMA_REGISTRY_NAME_2="production"
export SCHEMA_REGISTRY_URL_2="http://prod-registry:8081"
export READONLY_2="true"
```

When `READONLY_X="true"` for a specific registry:

**🚫 Blocked Operations:** Schema registration, context creation, configuration changes
**✅ Allowed Operations:** Schema browsing, compatibility checking, export operations

---

## 🎨 **Claude Desktop Usage Examples**

### **Multi-Registry Mode**
```
"List all my Schema Registry instances"
"Compare development and production registries"
"Migrate user-events schema from staging to production"
"Register a schema in the development registry"
```

### **Per-Registry READONLY Examples**
```
Human: "Register a schema in production"
→ Claude: "Operation blocked: Registry 'production' is running in READONLY mode."
```

---

## 🚀 **Getting Started**

1. **Choose your mode**: Single or multi-registry
2. **Set environment variables**: Use numbered approach for multiple registries
3. **Configure Claude Desktop**: Use provided examples
4. **Test**: Use natural language commands

**Maximum supported registries: 8** 