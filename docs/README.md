# Documentation Index

Welcome to the Kafka Schema Registry MCP Server v1.4.0 documentation! This folder contains comprehensive guides and references for the **True MCP Implementation** with **Claude Desktop Integration**.

## 🤖 **MCP Implementation Overview**

This project has been **completely transformed** from a REST API to a **true Message Control Protocol (MCP) server** that integrates seamlessly with Claude Desktop and other MCP clients. Users interact with schema management through **natural language commands** instead of API calls.

### **Key MCP Features:**
- ✅ **20 MCP Tools**: Complete schema operations via natural language
- ✅ **Claude Desktop Ready**: Direct AI integration for schema management
- ✅ **Natural Language Interface**: No curl commands or API knowledge required
- ✅ **Context-Aware Operations**: All tools support schema contexts
- ✅ **Export Capabilities**: JSON and Avro IDL formats with comprehensive metadata

---

## 📚 Available Documentation

### 🎯 **[Use Cases](use-cases.md)** - AI-Assisted Schema Management
Real-world scenarios using Claude Desktop integration:
- **Enterprise Use Cases**: Multi-environment management with AI assistance
- **Development Workflows**: AI-guided schema evolution and compatibility testing
- **Export & Documentation**: Human-readable schema documentation generation
- **Compliance & Governance**: AI-assisted regulatory compliance checking
- **Configuration Management**: Natural language configuration commands
- **Complete Development Lifecycle**: End-to-end workflows with Claude Desktop

### 🔧 **[MCP Tools Reference](mcp-tools-reference.md)** - Complete Tool Documentation
Comprehensive reference for all 20 MCP tools:
- **Schema Management Tools** (4): register, retrieve, versions, compatibility
- **Context Management Tools** (3): list, create, delete contexts
- **Subject Management Tools** (2): list, delete subjects  
- **Configuration Management Tools** (4): global and subject-specific settings
- **Mode Management Tools** (4): operational mode control
- **Export Tools** (4): comprehensive schema export capabilities
- **Natural Language Examples**: Claude Desktop usage patterns for each tool

### 📖 **[API Reference](api-reference.md)** - Legacy REST API Documentation
*Note: This document is maintained for reference but the **MCP Tools Reference** is the primary documentation for the current implementation.*

### 🔧 **[IDE Integration](ide-integration.md)**
Development environment setup guides (updated for MCP):
- **Claude Desktop Integration**: Primary interface for schema management
- **VS Code Integration**: Extensions and workspace configuration for MCP development
- **Cursor Integration**: AI-powered development with MCP server testing

### 🚀 **[Deployment Guide](deployment.md)**
Production deployment instructions covering:
- **Docker Deployment**: MCP server containerization and Claude Desktop configuration
- **Kubernetes**: Complete K8s manifests for MCP server deployment
- **Cloud Platforms**: AWS EKS, Google Cloud Run, Azure Container Instances
- **Security**: Authentication, network policies, MCP-specific considerations
- **Monitoring**: MCP server metrics and health monitoring
- **Claude Desktop Configuration**: Best practices and troubleshooting

---

## 🎉 What's New in v1.4.0 - True MCP Implementation

### **Complete MCP Transformation**
- **✅ 20 MCP Tools**: All schema operations via natural language
- **✅ Claude Desktop Ready**: Seamless AI integration
- **✅ No Pydantic Warnings**: Clean MCP protocol implementation
- **✅ Field Name Conflicts Resolved**: `schema` → `schema_definition` parameter updates
- **✅ Production Safety**: READONLY mode for safe production access

### **Enhanced Claude Desktop Integration**
- **Natural Language Commands**: "Register a user schema with fields for id, name, and email"
- **AI-Assisted Workflows**: Claude helps with compatibility checking and schema evolution
- **Context-Aware Operations**: "Export all production schemas in Avro IDL format"
- **Real-time Validation**: Immediate feedback on schema operations

### **Comprehensive Export Capabilities**
- **4 Export MCP Tools**: schema, subject, context, and global exports
- **Multiple Formats**: JSON for tooling, Avro IDL for documentation
- **AI-Enhanced Documentation**: Claude generates beautiful schema documentation
- **Complete Metadata**: Export timestamps, evolution history, configuration

### **Production Ready**
- **✅ 20/21 Integration Tests Passing** (1 skipped as expected)
- **✅ Docker Build & Test Suite**: Comprehensive validation
- **✅ GitHub Actions**: Automated CI/CD with multi-platform builds
- **✅ Security Scanning**: Trivy vulnerability scanning

---

## 🗺️ Documentation Navigation

### **Getting Started with MCP**
1. Start with the main [README](../README.md) for Claude Desktop setup
2. Review [Use Cases](use-cases.md) to see AI-assisted schema management
3. Check [MCP Tools Reference](mcp-tools-reference.md) for complete tool documentation

### **Claude Desktop Integration**
1. Follow the main [README](../README.md) for Claude Desktop configuration
2. Use [Use Cases](use-cases.md) for natural language interaction patterns
3. Reference [MCP Tools Reference](mcp-tools-reference.md) for specific tool usage

### **Development & Testing**
1. Review [MCP Tools Reference](mcp-tools-reference.md) for tool development
2. Use the test scripts: `tests/test_mcp_server.py`, `tests/advanced_mcp_test.py`
3. Run integration tests: `./tests/run_integration_tests.sh`

### **Production Deployment**
1. Review [Deployment Guide](deployment.md) for your target platform
2. Configure Claude Desktop using provided examples
3. Implement monitoring for MCP server health

---

## 🤖 Claude Desktop Usage Examples

### **Basic Schema Operations**
```
Human: "List all schema contexts"
Human: "Register a user schema with id, name, and email fields in development"
Human: "Check if adding an age field to the user schema is backward compatible"
Human: "Export the user schema as Avro IDL for documentation"
```

### **Advanced Workflows**
```
Human: "Create a production context and register our order schema with strict FULL compatibility"
Human: "Export all development schemas, check their compatibility with production, then promote the compatible ones"
Human: "Generate a compliance report by exporting all schemas from the GDPR context with full metadata"
```

### **Configuration Management**
```
Human: "Set the production context to FULL compatibility mode for maximum safety"
Human: "Switch to read-only mode during maintenance, then back to normal operations"
Human: "Show me the configuration differences between our development and production contexts"
```

---

## 🔗 Quick Links

### **MCP Implementation**
- **Main Project**: [README](../README.md) - Claude Desktop setup
- **MCP Server**: [kafka_schema_registry_mcp.py](../kafka_schema_registry_mcp.py)
- **Test Scripts**: [test_mcp_server.py](../tests/test_mcp_server.py), [advanced_mcp_test.py](../tests/advanced_mcp_test.py)
- **Integration Tests**: [run_integration_tests.sh](../tests/run_integration_tests.sh)

### **Configuration Examples**
- **Claude Desktop Docker**: [claude_desktop_docker_config.json](../claude_desktop_docker_config.json)
- **Claude Desktop Local**: [claude_desktop_config.json](../claude_desktop_config.json)
- **Docker Compose**: [docker-compose.yml](../docker-compose.yml)

### **Legacy Documentation**
- **Original REST API**: [API Reference](api-reference.md) *(maintained for reference)*
- **Legacy Server**: [mcp_server.py](../mcp_server.py) *(legacy FastAPI implementation)*

---

## 📝 Contributing to Documentation

When contributing to the MCP implementation documentation:

1. **Use Cases**: Add natural language interaction examples with Claude Desktop
2. **MCP Tools Reference**: Include comprehensive tool examples and usage patterns
3. **Deployment**: Provide MCP-specific configuration and troubleshooting
4. **Claude Desktop Integration**: Document best practices for AI-assisted workflows

---

## 🆘 Getting Help

If you need assistance with the MCP implementation:

1. Check [Use Cases](use-cases.md) for Claude Desktop interaction examples
2. Review [MCP Tools Reference](mcp-tools-reference.md) for tool-specific documentation
3. Consult [Deployment Guide](deployment.md) for Claude Desktop configuration
4. Test your setup with the provided test scripts

### **Quick Debug Commands**
```bash
# Test MCP server directly
python test_mcp_server.py

# Test with Schema Registry integration
python advanced_mcp_test.py

# Run comprehensive integration tests
./run_integration_tests.sh

# Test Docker image
./test_docker_image.sh
```

---

**Happy Schema Managing with AI! 🤖🎉** 