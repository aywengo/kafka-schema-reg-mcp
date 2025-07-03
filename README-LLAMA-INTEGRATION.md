# Kafka Schema Registry MCP with LLama Integration

This repository includes a complete local LLama integration demo for the Kafka Schema Registry MCP server.

## 🚀 Quick Start

**All LLama integration files are organized in the `demo/` folder.**

```bash
# Clone and navigate to demo
git clone https://github.com/aywengo/kafka-schema-reg-mcp.git
cd kafka-schema-reg-mcp/demo

# Start the demo
chmod +x run-llama-mcp.sh
./run-llama-mcp.sh start

# Choose your interface:
# Option A: CLI client
python client-example.py

# Option B: Use with VSCode (see setup below)
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

## 💻 Interface Options

### Option A: Interactive CLI Client
```bash
python client-example.py
```
Perfect for quick queries and testing.

### Option B: VSCode Integration
Use Schema Registry directly in your development workflow:

1. **Install MCP Extension**: Install "Claude Dev" or similar MCP-compatible extension
2. **Configure Connection**: Add to your VSCode `settings.json`:
   ```json
   {
     "claudeDev.mcpServers": {
       "kafka-schema-registry": {
         "command": "docker",
         "args": ["exec", "-i", "mcp-server", "python", "-m", "kafka_schema_registry_mcp.server"],
         "env": {
           "SCHEMA_REGISTRY_URL": "http://localhost:38081"
         }
       }
     }
   }
   ```
3. **Start Chatting**: Use the extension chat to ask schema questions while coding

### Option C: Direct API
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List all subjects", "use_mcp": true}'
```

## 🏗️ Architecture

```
Your Questions → LLama (Ollama) → MCP Bridge → Schema Registry MCP → Kafka Schema Registry
     ↑                                                                          ↓
     └─────────────── Natural Language Responses ←─────────────────────────────┘
```

## 🔧 VSCode Benefits

- 🔥 **Code Context**: Ask about schemas while viewing your code
- 📝 **Documentation**: Generate schema docs directly in workspace
- 🔄 **Workflow Integration**: Schema queries during development
- 💡 **IntelliSense**: Schema-aware suggestions (with compatible extensions)

## 📖 Full Documentation

See [`demo/README.md`](demo/README.md) for complete documentation, including:

- Installation and setup instructions
- VSCode configuration examples
- Usage examples and commands
- Configuration options
- Troubleshooting guide
- API reference

## 🔧 Core MCP Server

This repository maintains full compatibility with the original MCP server functionality. The LLama integration is purely additive and runs alongside the existing server.

## 🚀 Getting Started

1. **Go to the demo folder**: `cd demo`
2. **Read the documentation**: `cat README.md`
3. **Start the demo**: `./run-llama-mcp.sh start`
4. **Choose your interface**:
   - **CLI**: `python client-example.py`
   - **VSCode**: Configure extension and chat in your editor
   - **API**: `curl http://localhost:8080/chat`

---

**Ready to try it? Head to the [`demo/`](demo/) folder! 🎉**