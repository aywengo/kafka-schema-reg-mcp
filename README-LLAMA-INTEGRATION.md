# Kafka Schema Registry MCP with LLama Integration

This branch includes a complete local LLama integration demo for the Kafka Schema Registry MCP server.

## 🚀 Quick Start

**All LLama integration files have been organized in the `demo/` folder.**

```bash
# Clone and navigate to demo
git clone https://github.com/aywengo/kafka-schema-reg-mcp.git
cd kafka-schema-reg-mcp
git checkout local-llama-integration
cd demo

# Start the demo
chmod +x run-llama-mcp.sh
./run-llama-mcp.sh start

# Test the integration
python client-example.py
```

## 📁 What's in the Demo Folder

The `demo/` folder contains a complete working example of LLama integration:

- **`docker-compose-llama.yml`** - Complete Docker setup with LLama, Kafka, Schema Registry
- **`run-llama-mcp.sh`** - One-command setup and management script
- **`client-example.py`** - Interactive CLI client for natural language queries
- **`README.md`** - Complete documentation and usage guide
- **Bridge service files** - Integration layer between LLama and MCP

## 🎯 What You Can Do

Ask natural language questions about your Schema Registry:

- "List all subjects in the schema registry"
- "Show me the structure of the user-events schema"  
- "Check if this schema is compatible with the latest version"
- "Export all schemas from the production context"

## 🏗️ Architecture

```
Your Questions → LLama (Ollama) → MCP Bridge → Schema Registry MCP → Kafka Schema Registry
     ↑                                                                          ↓
     └─────────────── Natural Language Responses ←─────────────────────────────┘
```

## 📖 Full Documentation

See [`demo/README.md`](demo/README.md) for complete documentation, including:

- Installation and setup instructions
- Usage examples and commands
- Configuration options
- Troubleshooting guide
- API reference

## 🔧 Core MCP Server

This branch maintains full compatibility with the original MCP server functionality. The LLama integration is purely additive and runs alongside the existing server.

## 🚀 Getting Started

1. **Go to the demo folder**: `cd demo`
2. **Read the documentation**: `cat README.md`
3. **Start the demo**: `./run-llama-mcp.sh start`
4. **Start chatting**: `python client-example.py`

---

**Ready to try it? Head to the [`demo/`](demo/) folder! 🎉**