# Documentation Index

Welcome to the Kafka Schema Registry MCP Server v1.3.0 documentation! This folder contains comprehensive guides and references for all aspects of the project.

## 📚 Available Documentation

### 🎯 **[Use Cases](use-cases.md)**
Real-world scenarios and implementation examples covering:
- **Enterprise Use Cases**: Multi-environment management, multi-tenant SaaS, team boundaries
- **Development Workflows**: Schema evolution testing, feature branch development, export-driven migrations
- **Compliance & Governance**: Regulatory compliance, data lifecycle management, audit trails
- **Testing & QA**: A/B testing, chaos engineering, resilience testing
- **Analytics & Monitoring**: Schema analytics, governance reporting, export-based analysis
- **Performance & Scalability**: High-volume event processing, efficient export strategies
- **Integration Patterns**: Event-driven architecture, microservices coordination
- **Export & Migration**: Backup strategies, environment promotion, documentation generation

### 📖 **[API Reference](api-reference.md)**
Complete REST API documentation including:
- **Core Endpoints**: Health checks, schema management, context operations
- **Export Endpoints**: 17 export endpoints for schemas, subjects, contexts, and global exports
- **Request/Response Models**: Detailed data structures and examples
- **Export Formats**: JSON, Avro IDL, and ZIP bundle format specifications
- **Error Handling**: HTTP status codes and error scenarios
- **Authentication**: Optional basic auth configuration
- **Advanced Examples**: Multi-context workflows, batch operations, export strategies

### 🔧 **[IDE Integration](ide-integration.md)**
Development environment setup guides for:
- **VS Code Integration**: Extensions, workspace config, REST client, debugging, export testing
- **Claude Code Integration**: AI-assisted workflows, schema evolution prompts, export automation
- **Cursor Integration**: AI-powered development, schema generation, export workflows
- **Cross-IDE Workflows**: Best practices, shared configurations, export documentation

### 🚀 **[Deployment Guide](deployment.md)**
Production deployment instructions covering:
- **Docker Deployment**: Local development and production configurations
- **Kubernetes**: Complete K8s manifests, Helm charts, scaling
- **Cloud Platforms**: AWS EKS, Google Cloud Run, Azure Container Instances
- **Security**: Authentication, network policies, TLS configuration
- **Monitoring**: Prometheus metrics, Grafana dashboards, observability
- **Performance**: Resource optimization, autoscaling, troubleshooting
- **Export Infrastructure**: Backup strategies, storage optimization, automated exports

## 🎉 What's New in v1.3.0

### **Comprehensive Schema Export** 
The latest release introduces powerful export capabilities:
- **17 Export Endpoints**: Complete coverage for all export scenarios
- **Multiple Formats**: JSON, Avro IDL, and ZIP bundle exports
- **Multi-Scope Export**: Single schemas, subjects, contexts, or global exports
- **Metadata Integration**: Export timestamps, URLs, and context information
- **Production Ready**: 53 passing tests with comprehensive validation

### **Enhanced Documentation**
- **Export Use Cases**: Real-world backup, migration, and documentation scenarios
- **IDE Integration**: Export testing and automation workflows
- **API Reference**: Complete export endpoint documentation
- **Deployment Guide**: Export infrastructure and backup strategies

### **Test Coverage Achievement**
✅ **53 PASSED**, ⚠️ **1 SKIPPED** (auth), ❌ **0 FAILED**

## 🗺️ Documentation Navigation

### **Getting Started**
1. Start with the main [README](../README.md) for quick setup
2. Review [Use Cases](use-cases.md) to understand application scenarios
3. Check [API Reference](api-reference.md) for endpoint details

### **Development**
1. Follow [IDE Integration](ide-integration.md) for your preferred editor
2. Use [API Reference](api-reference.md) for implementation details
3. Reference [Use Cases](use-cases.md) for patterns and examples

### **Production**
1. Review [Deployment Guide](deployment.md) for your target platform
2. Implement monitoring using the observability sections
3. Apply security best practices from the security sections

## 🔗 Quick Links

- **Main Project**: [README](../README.md)
- **Source Code**: [mcp_server.py](../mcp_server.py)
- **Tests**: [tests/](../tests/)
- **Docker Setup**: [docker-compose.yml](../docker-compose.yml)

## 📝 Contributing to Documentation

When contributing to the documentation:

1. **Use Cases**: Add real-world scenarios with complete examples
2. **API Reference**: Include request/response examples and error cases
3. **IDE Integration**: Provide step-by-step setup instructions
4. **Deployment**: Include production-ready configurations and troubleshooting

## 🆘 Getting Help

If you need assistance:

1. Check the relevant documentation section first
2. Review the [Use Cases](use-cases.md) for similar scenarios
3. Consult the [API Reference](api-reference.md) for endpoint details
4. Check the [Deployment Guide](deployment.md) for infrastructure issues

---

**Happy Schema Managing!** 🎉 