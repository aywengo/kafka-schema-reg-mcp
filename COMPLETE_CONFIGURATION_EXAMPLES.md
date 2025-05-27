# Complete Configuration Examples

## 🎯 **Kafka Schema Registry MCP Server - Configuration Guide**

This guide covers all configuration options for the enhanced Multi-Registry MCP Server with numbered environment variables support.

---

## 📋 **Mode 1: Single Registry (Backward Compatible)**

### **Basic Single Registry**
```bash
# Environment Variables
export SCHEMA_REGISTRY_URL="http://localhost:8081"
export SCHEMA_REGISTRY_USER="admin"
export SCHEMA_REGISTRY_PASSWORD="admin-password"
export READONLY="false"
```

### **Claude Desktop Configuration**
```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://localhost:8081",
        "SCHEMA_REGISTRY_USER": "admin",
        "SCHEMA_REGISTRY_PASSWORD": "admin-password",
        "READONLY": "false"
      }
    }
  }
}
```

### **Single Registry - Production Mode (READONLY)**
```json
{
  "mcpServers": {
    "kafka-schema-registry-readonly": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://prod-schema-registry:8081",
        "SCHEMA_REGISTRY_USER": "prod-viewer",
        "SCHEMA_REGISTRY_PASSWORD": "prod-password",
        "READONLY": "true"
      }
    }
  }
}
```

---

## 📋 **Mode 2: Multi-Registry (Numbered Environment Variables)**

### **Development Setup (3 Registries)**
```bash
# Development Registry
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-schema-registry:8081"
export SCHEMA_REGISTRY_USER_1="dev-user"
export SCHEMA_REGISTRY_PASSWORD_1="dev-password"
export READONLY_1="false"

# Staging Registry  
export SCHEMA_REGISTRY_NAME_2="staging"
export SCHEMA_REGISTRY_URL_2="http://staging-schema-registry:8081"
export SCHEMA_REGISTRY_USER_2="staging-user"
export SCHEMA_REGISTRY_PASSWORD_2="staging-password"
export READONLY_2="false"

# Production Registry (Read-only for safety)
export SCHEMA_REGISTRY_NAME_3="production"
export SCHEMA_REGISTRY_URL_3="http://prod-schema-registry:8081"
export SCHEMA_REGISTRY_USER_3="prod-user"
export SCHEMA_REGISTRY_PASSWORD_3="prod-password"
export READONLY_3="true"
```

### **Claude Desktop - Development Workflow**
```json
{
  "mcpServers": {
    "kafka-schema-registry-multi": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://localhost:8081",
        "SCHEMA_REGISTRY_USER_1": "",
        "SCHEMA_REGISTRY_PASSWORD_1": "",
        "READONLY_1": "false",
        
        "SCHEMA_REGISTRY_NAME_2": "staging",
        "SCHEMA_REGISTRY_URL_2": "http://localhost:8082",
        "SCHEMA_REGISTRY_USER_2": "",
        "SCHEMA_REGISTRY_PASSWORD_2": "",
        "READONLY_2": "false",
        
        "SCHEMA_REGISTRY_NAME_3": "production",
        "SCHEMA_REGISTRY_URL_3": "http://localhost:8083",
        "SCHEMA_REGISTRY_USER_3": "prod-user",
        "SCHEMA_REGISTRY_PASSWORD_3": "prod-password",
        "READONLY_3": "true"
      }
    }
  }
}
```

### **Enterprise Setup (8 Registries - Maximum)**
```json
{
  "mcpServers": {
    "kafka-schema-registry-enterprise": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://dev-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_1": "dev-user",
        "SCHEMA_REGISTRY_PASSWORD_1": "dev-password",
        "READONLY_1": "false",
        
        "SCHEMA_REGISTRY_NAME_2": "feature-branch",
        "SCHEMA_REGISTRY_URL_2": "http://feature-schema-registry:8081", 
        "SCHEMA_REGISTRY_USER_2": "feature-user",
        "SCHEMA_REGISTRY_PASSWORD_2": "feature-password",
        "READONLY_2": "false",
        
        "SCHEMA_REGISTRY_NAME_3": "staging",
        "SCHEMA_REGISTRY_URL_3": "http://staging-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_3": "staging-user",
        "SCHEMA_REGISTRY_PASSWORD_3": "staging-password",
        "READONLY_3": "false",
        
        "SCHEMA_REGISTRY_NAME_4": "pre-production",
        "SCHEMA_REGISTRY_URL_4": "http://preprod-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_4": "preprod-user",
        "SCHEMA_REGISTRY_PASSWORD_4": "preprod-password",
        "READONLY_4": "false",
        
        "SCHEMA_REGISTRY_NAME_5": "production-us-east",
        "SCHEMA_REGISTRY_URL_5": "http://prod-us-east-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_5": "prod-user",
        "SCHEMA_REGISTRY_PASSWORD_5": "prod-password",
        "READONLY_5": "true",
        
        "SCHEMA_REGISTRY_NAME_6": "production-us-west",
        "SCHEMA_REGISTRY_URL_6": "http://prod-us-west-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_6": "prod-user",
        "SCHEMA_REGISTRY_PASSWORD_6": "prod-password",
        "READONLY_6": "true",
        
        "SCHEMA_REGISTRY_NAME_7": "disaster-recovery",
        "SCHEMA_REGISTRY_URL_7": "http://dr-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_7": "dr-user",
        "SCHEMA_REGISTRY_PASSWORD_7": "dr-password",
        "READONLY_7": "true",
        
        "SCHEMA_REGISTRY_NAME_8": "compliance-archive",
        "SCHEMA_REGISTRY_URL_8": "http://compliance-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_8": "compliance-user",
        "SCHEMA_REGISTRY_PASSWORD_8": "compliance-password",
        "READONLY_8": "true"
      }
    }
  }
}
```

---

## 🔒 **Security and READONLY Configurations**

### **Production Safety Configuration**
```json
{
  "mcpServers": {
    "kafka-schema-registry-production": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "production",
        "SCHEMA_REGISTRY_URL_1": "http://prod-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_1": "readonly-user",
        "SCHEMA_REGISTRY_PASSWORD_1": "readonly-password",
        "READONLY_1": "true",
        
        "SCHEMA_REGISTRY_NAME_2": "disaster-recovery",
        "SCHEMA_REGISTRY_URL_2": "http://dr-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_2": "readonly-user",
        "SCHEMA_REGISTRY_PASSWORD_2": "readonly-password", 
        "READONLY_2": "true"
      }
    }
  }
}
```

### **Mixed Environment Access**
```json
{
  "mcpServers": {
    "kafka-schema-registry-mixed": {
      "command": "python",
      "args": ["kafka_schema_registry_multi_mcp.py"],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://dev-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_1": "dev-admin",
        "SCHEMA_REGISTRY_PASSWORD_1": "dev-admin-password",
        "READONLY_1": "false",
        
        "SCHEMA_REGISTRY_NAME_2": "production",
        "SCHEMA_REGISTRY_URL_2": "http://prod-schema-registry:8081",
        "SCHEMA_REGISTRY_USER_2": "prod-viewer",
        "SCHEMA_REGISTRY_PASSWORD_2": "prod-view-password",
        "READONLY_2": "true"
      }
    }
  }
}
```

---

## 🎨 **Usage Examples by Configuration**

### **Single Registry Mode**
```
Human: "List all schema subjects"
Human: "Register a new user schema"
Human: "Export all schemas"
Human: "Check compatibility of my updated schema"
```

### **Multi-Registry Development Workflow**
```
Human: "List all my Schema Registry instances"
Human: "Compare development and staging registries"
Human: "Migrate user-events schema from dev to staging"
Human: "Test all registry connections"
Human: "Register a schema in development registry"
Human: "Find schemas missing in production"
```

### **Enterprise Operations**
```
Human: "Compare all production regions for consistency"
Human: "Sync schemas from production-us-east to disaster-recovery"
Human: "Generate migration report from staging to production"
Human: "List migration history"
Human: "Set up scheduled sync between prod regions"
```

### **Production Safety Examples**
```
Human: "Register a schema in production"
→ Claude: "❌ Operation blocked: Registry 'production' is running in READONLY mode." 