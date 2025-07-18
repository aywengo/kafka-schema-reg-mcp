# MCP IDE Integration Guide

This guide provides comprehensive configuration examples and setup instructions for integrating the Kafka Schema Registry MCP Server with popular IDEs using the MCP (Model Context Protocol) standard.

## 🎯 Overview

The Kafka Schema Registry MCP Server can be integrated with various IDEs through MCP clients, enabling AI-powered schema management directly within your development environment.

### Supported IDEs
- **🔵 VS Code** - via MCP extensions and plugins
- **⚡ Cursor** - via built-in MCP protocol support
- **🔴 JetBrains IDEs** - via MCP plugins (IntelliJ IDEA, PyCharm, WebStorm, etc.)

## 🔵 VS Code MCP Integration

### Prerequisites
- VS Code 1.85+ 
- Node.js 18+
- MCP extension for VS Code

### Extension Installation

```bash
# Install MCP extension for VS Code
code --install-extension mcp-client.vscode-mcp

# Alternative: Install from VS Code marketplace
# Search for "MCP Client" in Extensions
```

### Configuration Files

#### 1. VS Code Settings Configuration
Create or update `.vscode/settings.json`:

```json
{
    "mcp.servers": {
        "kafka-schema-registry": {
            "name": "Kafka Schema Registry",
            "description": "MCP server for Kafka Schema Registry management",
            "transport": "stdio",
            "command": "docker",
            "args": [
                "run", "--rm", "-i",
                "--network", "host",
                "-e", "SCHEMA_REGISTRY_URL=http://localhost:8081",
                "-e", "VIEWONLY=false",
                "aywengo/kafka-schema-reg-mcp:stable"
            ],
            "capabilities": [
                "tools",
                "resources",
                "prompts"
            ],
            "autoStart": true,
            "restartOnFailure": true
        }
    },
    "mcp.enableLogging": true,
    "mcp.logLevel": "info",
    "mcp.autoReconnect": true,
    "mcp.timeout": 30000
}
```

#### 2. Multi-Registry VS Code Configuration
For multiple Schema Registry instances:

```json
{
    "mcp.servers": {
        "kafka-schema-registry-multi": {
            "name": "Kafka Schema Registry (Multi)",
            "description": "Multi-registry MCP server for enterprise schema management",
            "transport": "stdio",
            "command": "docker",
            "args": [
                "run", "--rm", "-i",
                "--network", "host",
                "-e", "SCHEMA_REGISTRY_NAME_1=development",
                "-e", "SCHEMA_REGISTRY_URL_1=http://localhost:8081",
                "-e", "VIEWONLY_1=false",
                "-e", "SCHEMA_REGISTRY_NAME_2=staging", 
                "-e", "SCHEMA_REGISTRY_URL_2=http://localhost:8082",
                "-e", "VIEWONLY_2=false",
                "-e", "SCHEMA_REGISTRY_NAME_3=production",
                "-e", "SCHEMA_REGISTRY_URL_3=http://localhost:8083",
                "-e", "VIEWONLY_3=true",
                "aywengo/kafka-schema-reg-mcp:stable"
            ],
            "capabilities": [
                "tools",
                "resources", 
                "prompts"
            ],
            "autoStart": true
        }
    }
}
```

## ⚡ Cursor MCP Integration

Cursor has built-in MCP protocol support, making integration seamless.

### Configuration

#### 1. Cursor MCP Configuration
Create `.cursor/mcp-config.json`:

```json
{
    "version": "1.0",
    "servers": {
        "kafka-schema-registry": {
            "name": "Kafka Schema Registry MCP",
            "description": "Enterprise schema management with MCP protocol",
            "type": "stdio",
            "transport": {
                "type": "docker",
                "image": "aywengo/kafka-schema-reg-mcp:stable",
                "args": [],
                "environment": {
                    "SCHEMA_REGISTRY_URL": "http://localhost:8081",
                    "VIEWONLY": "false"
                },
                "network": "host"
            },
            "capabilities": {
                "tools": true,
                "resources": true,
                "prompts": true,
                "sampling": false
            },
            "timeout": 30000,
            "retries": 3,
            "autoRestart": true
        }
    },
    "defaultServer": "kafka-schema-registry",
    "ai": {
        "contextSize": 32000,
        "enableSchemaCompletion": true,
        "enableCompatibilityChecking": true,
        "autoSuggestSchemaEvolution": true,
        "enableMigrationAssistance": true
    }
}
```

## 🔴 JetBrains IDEs MCP Integration

JetBrains IDEs support MCP through plugins and custom integrations.

### Plugin Installation

#### For IntelliJ IDEA / PyCharm / WebStorm
```bash
# Install MCP plugin via JetBrains Marketplace
# Search for "MCP Protocol Client" in Plugin Marketplace
# Or install manually from GitHub releases
```

### Configuration Files

#### 1. JetBrains MCP Configuration
Create `.idea/mcp-config.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="MCPConfiguration">
    <servers>
      <server id="kafka-schema-registry" name="Kafka Schema Registry">
        <description>Enterprise schema registry management via MCP</description>
        <transport type="stdio">
          <command>docker</command>
          <args>
            <arg>run</arg>
            <arg>--rm</arg>
            <arg>-i</arg>
            <arg>--network</arg>
            <arg>host</arg>
            <arg>-e</arg>
            <arg>SCHEMA_REGISTRY_URL=http://localhost:8081</arg>
            <arg>-e</arg>
            <arg>VIEWONLY=false</arg>
            <arg>aywengo/kafka-schema-reg-mcp:stable</arg>
          </args>
        </transport>
        <capabilities>
          <capability>tools</capability>
          <capability>resources</capability>
          <capability>prompts</capability>
        </capabilities>
        <autoStart>true</autoStart>
        <timeout>30000</timeout>
      </server>
    </servers>
  </component>
</project>
```

## 🛠️ Configuration Management

### Environment Variables

Create a unified environment configuration file `.env.mcp`:

```bash
# Schema Registry Configuration
SCHEMA_REGISTRY_URL=http://localhost:8081
SCHEMA_REGISTRY_USER=
SCHEMA_REGISTRY_PASSWORD=
VIEWONLY=false

# Multi-Registry Configuration
SCHEMA_REGISTRY_NAME_1=development
SCHEMA_REGISTRY_URL_1=http://localhost:8081
VIEWONLY_1=false

SCHEMA_REGISTRY_NAME_2=staging
SCHEMA_REGISTRY_URL_2=http://localhost:8082
VIEWONLY_2=false

SCHEMA_REGISTRY_NAME_3=production
SCHEMA_REGISTRY_URL_3=http://localhost:8083
VIEWONLY_3=true

# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_LOG_LEVEL=info
MCP_ENABLE_CORS=true

# Authentication (optional)
ENABLE_AUTH=false
AUTH_ISSUER_URL=
AUTH_VALID_SCOPES=
```

## 🧪 Testing Your MCP Integration

### Basic Connection Test

Create `test-mcp-connection.py`:

```python
#!/usr/bin/env python3
"""Test MCP connection to Kafka Schema Registry server."""

import json
import subprocess
import sys
import time
from typing import Dict, Any

def test_mcp_connection(config_file: str) -> bool:
    """Test MCP connection using the configured server."""
    
    print(f"🔍 Testing MCP connection with config: {config_file}")
    
    try:
        # Test basic connectivity
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "http://localhost:8080/mcp/list_tools",
            "-H", "Content-Type: application/json",
            "-d", "{}"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            tools = response.get("tools", [])
            print(f"✅ MCP server connected successfully")
            print(f"📊 Available tools: {len(tools)}")
            return True
        else:
            print(f"❌ MCP connection failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing MCP connection: {e}")
        return False

def main():
    """Main test function."""
    
    print("🚀 MCP Integration Test Suite")
    print("=" * 50)
    
    # Test MCP connection
    mcp_ok = test_mcp_connection("config.json")
    
    print("\n📋 Test Results:")
    print(f"MCP Connection: {'✅ OK' if mcp_ok else '❌ FAILED'}")
    
    if mcp_ok:
        print("\n🎉 MCP integration is ready!")
        return 0
    else:
        print("\n⚠️  MCP test failed. Please check your configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## 🚀 Quick Start Commands

### Setup Commands

```bash
# Clone configuration examples
git clone https://github.com/aywengo/kafka-schema-reg-mcp
cd kafka-schema-reg-mcp/config-examples

# VS Code setup
cp vscode-mcp-settings.json .vscode/settings.json
code --install-extension mcp-client.vscode-mcp

# Cursor setup  
cp cursor-mcp-config.json .cursor/mcp-config.json

# JetBrains setup
cp jetbrains-mcp-config.xml .idea/mcp-config.xml
# Install MCP plugin from JetBrains Marketplace

# Test integration
python test-mcp-connection.py
```

## 🎉 Success! 

Once configured, you can:

- **Ask your AI assistant**: "List all schema subjects in the development context"
- **Schema evolution**: "Help me add a new field to the user schema while maintaining compatibility"
- **Migration assistance**: "Migrate the payment schema from staging to production"
- **Export operations**: "Export all schemas from the production context as documentation"

Your IDE now has full access to Kafka Schema Registry operations through the MCP protocol! 🚀 