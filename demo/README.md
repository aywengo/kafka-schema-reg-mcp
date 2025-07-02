# Kafka Schema Registry MCP with LLama Integration Demo

This demo extends the Kafka Schema Registry MCP server with local LLama integration, allowing you to interact with your Schema Registry using natural language through a private LLM running in Docker.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- At least 4GB RAM available for containers
- (Optional) NVIDIA GPU for faster LLama inference
- (Optional) Visual Studio Code for MCP integration

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/aywengo/kafka-schema-reg-mcp.git
cd kafka-schema-reg-mcp

# Navigate to the demo directory
cd demo

# Make the script executable
chmod +x run-llama-mcp.sh
```

### 2. Start All Services

```bash
# Start everything (Kafka, Schema Registry, MCP Server, LLama)
./run-llama-mcp.sh start
```

This will:
- ✅ Start Kafka and Schema Registry
- ✅ Launch the MCP server
- ✅ Run LLama via Ollama
- ✅ Start the MCP-LLama bridge service
- ✅ Pull the default LLama model (llama3.2:3b)

### 3. Choose Your Interface

#### Option A: Interactive CLI Client
```bash
# Interactive chat mode
python client-example.py

# Single command mode
python client-example.py --message "List all subjects in the schema registry"

# Check service health
python client-example.py --health
```

#### Option B: VSCode with MCP Integration

1. **Install Claude Dev Extension**:
   - Open VSCode
   - Install the "Claude Dev" extension from the marketplace
   - Or install any MCP-compatible extension

2. **Configure MCP Server Connection**:
   
   Create or update your VSCode settings (`settings.json`):
   ```json
   {
     "claudeDev.mcpServers": {
       "kafka-schema-registry": {
         "command": "docker",
         "args": [
           "exec", "-i", "mcp-server",
           "python", "-m", "kafka_schema_registry_mcp.server"
         ],
         "env": {
           "SCHEMA_REGISTRY_URL": "http://localhost:38081"
         }
       }
     }
   }
   ```

   **Alternative: Direct Connection**
   ```json
   {
     "claudeDev.mcpServers": {
       "kafka-schema-registry": {
         "command": "curl",
         "args": [
           "-X", "POST",
           "http://localhost:38000/tools/list_subjects",
           "-H", "Content-Type: application/json"
         ]
       }
     }
   }
   ```

3. **Use Natural Language in VSCode**:
   - Open the Claude Dev chat panel
   - Ask questions like: "List all subjects in the schema registry"
   - The extension will automatically use the MCP tools

4. **Benefits of VSCode Integration**:
   - 🔥 **Code Context**: Ask about schemas while viewing code
   - 📝 **Documentation**: Generate docs directly in your workspace
   - 🔄 **Workflow Integration**: Schema queries while developing
   - 💡 **IntelliSense**: Schema-aware code completion (with compatible extensions)

#### Option C: Direct API Integration
```bash
# Test the bridge API directly
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all subjects in the schema registry",
    "model": "llama3.2:3b",
    "use_mcp": true
  }'
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Client   │    │  MCP-LLama      │    │  Kafka Schema   │
│  (CLI/VSCode)   │◄──►│  Bridge         │◄──►│  Registry MCP   │
│  Natural Lang.  │    │  Service        │    │  Server         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  LLama/Ollama   │    │  Schema         │
                       │  Container      │    │  Registry       │
                       └─────────────────┘    └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │  Kafka Broker   │
                                              └─────────────────┘
```

## 📁 Demo Files Structure

```
demo/
├── docker-compose-llama.yml    # Complete Docker setup with LLama integration
├── run-llama-mcp.sh           # Management script for all services
├── Dockerfile.bridge          # Bridge service container definition
├── requirements-bridge.txt    # Python dependencies for bridge
├── client-example.py          # Interactive CLI client
├── .env.template             # Configuration template
└── README.md                 # This file
```

## 🎯 What You Can Do

Ask LLama natural language questions about your Schema Registry:

### 📋 Basic Operations
- "List all subjects in the schema registry"
- "Show me the latest schema for user-events"
- "Get all versions of the payment-schema"

### 🔍 Schema Analysis
- "What fields are in the user-profile schema?"
- "Compare versions 1 and 2 of the order-events schema"
- "Find schemas containing a 'user_id' field"

### ✅ Compatibility & Validation
- "Check if this schema is compatible: {schema_json}"
- "What are the compatibility requirements?"
- "Test schema evolution compatibility"

### 📊 Management & Statistics
- "Show registry statistics"
- "Export all schemas from production context"
- "What's the current registry mode?"

## 🛠️ Service URLs

After starting with `./run-llama-mcp.sh start`:

| Service | URL | Description |
|---------|-----|-------------|
| 🤖 **LLama Bridge** | http://localhost:8080 | Main API for LLama + MCP |
| 🦙 **Ollama** | http://localhost:11434 | Direct LLama API |
| 🔧 **MCP Server** | http://localhost:38000 | Schema Registry MCP tools |
| 📊 **Schema Registry** | http://localhost:38081 | Confluent Schema Registry |
| 🎛️ **Kafka UI** | http://localhost:38080 | AKHQ web interface |
| 📁 **Kafka** | localhost:39092 | Kafka broker |

## 🔧 Configuration

### Environment Variables

```bash
# Set custom model
export DEFAULT_MODEL="llama3:8b"

# Start with custom model
./run-llama-mcp.sh start llama3:8b
```

### Custom Configuration

```bash
# Copy and customize the environment template
cp .env.template .env
# Edit .env file with your preferences
```

### Custom Models

```bash
# Pull a different model
./run-llama-mcp.sh pull-model codellama:7b

# Use in client
python client-example.py --model codellama:7b
```

### VSCode Configuration Examples

#### For Direct MCP Connection:
```json
{
  "claudeDev.mcpServers": {
    "kafka-schema-registry": {
      "command": "python",
      "args": ["-m", "mcp", "connect", "http://localhost:38000"],
      "env": {
        "MCP_SERVER_URL": "http://localhost:38000"
      }
    }
  }
}
```

#### For LLama Bridge Connection:
```json
{
  "claudeDev.apiEndpoint": "http://localhost:8080/chat",
  "claudeDev.mcpEnabled": true,
  "claudeDev.defaultModel": "llama3.2:3b"
}
```

## 📖 Usage Examples

### CLI Interactive Mode
```bash
python client-example.py
```

```
🤖 Starting interactive chat with llama3.2:3b
💡 Type 'help' for Schema Registry commands, 'quit' to exit
🔧 MCP tools are enabled - you can ask about schemas, subjects, etc.
------------------------------------------------------------

🧑 You: List all subjects in my schema registry

🤖 LLama: I'll check the subjects in your schema registry.

🔧 Used tools: list_subjects

The schema registry currently contains the following subjects:
- user-events-value
- order-events-value  
- payment-events-value

These are the active schema subjects registered in your Kafka Schema Registry.
```

### VSCode Integration Examples

1. **Schema Exploration While Coding**:
   ```
   In VSCode chat: "Show me the structure of the user-events schema and suggest how to deserialize it in Python"
   ```

2. **Schema Validation During Development**:
   ```
   In VSCode chat: "Check if my current JSON matches the user-profile schema requirements"
   ```

3. **Documentation Generation**:
   ```
   In VSCode chat: "Generate documentation for all schemas in the payments context"
   ```

### Single Command Mode
```bash
python client-example.py --message "Show me the structure of user-events schema"
```

### API Integration
```python
import httpx

async def ask_llama(question: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/chat",
            json={
                "message": question,
                "model": "llama3.2:3b",
                "use_mcp": True
            }
        )
        return response.json()

# Usage
result = await ask_llama("List all schema subjects")
print(result["response"])
```

## 🎮 Management Commands

⚠️ **Important**: Run all commands from the `demo/` directory

```bash
# Navigate to demo directory first
cd demo

# Start all services
./run-llama-mcp.sh start

# Stop all services  
./run-llama-mcp.sh stop

# Restart services
./run-llama-mcp.sh restart

# Check service status
./run-llama-mcp.sh status

# View logs
./run-llama-mcp.sh logs

# View specific service logs
./run-llama-mcp.sh logs ollama

# Clean up everything (removes volumes)
./run-llama-mcp.sh cleanup

# Pull specific model
./run-llama-mcp.sh pull-model llama3:8b
```

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check Docker status
docker info

# View detailed logs
./run-llama-mcp.sh logs

# Restart everything
./run-llama-mcp.sh restart
```

### VSCode Connection Issues
```bash
# Verify MCP server is accessible
curl http://localhost:38000/health

# Check if bridge service is running
curl http://localhost:8080/health

# Test MCP tools directly
curl -X POST http://localhost:38000/tools/list_subjects \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Model Issues
```bash
# Check available models
docker exec ollama-mcp ollama list

# Pull model manually
docker exec ollama-mcp ollama pull llama3.2:3b

# Test Ollama directly
curl http://localhost:11434/api/version
```

### Bridge Service Issues
```bash
# Check bridge health
curl http://localhost:8080/health

# View bridge logs
./run-llama-mcp.sh logs mcp-bridge
```

### Wrong Directory Error
```bash
# If you see "Cannot find docker-compose-llama.yml"
# Make sure you're in the demo directory:
cd demo
./run-llama-mcp.sh start
```

### Performance Issues

**For better performance:**
- Use a smaller model: `llama3.2:1b` instead of `llama3.2:3b`
- Enable GPU support (requires NVIDIA GPU + drivers)
- Increase Docker memory limits

**GPU Support:**
```bash
# The docker-compose file includes GPU support
# Make sure you have nvidia-docker installed
# GPU will be automatically used if available
```

## 🔄 Development

### Custom Bridge Service
The bridge service code is created automatically in the `bridge/` directory by the setup script. You can modify `bridge/main.py` for custom integrations.

### Adding New MCP Tools
The MCP server supports the full Kafka Schema Registry API. Refer to the main MCP server documentation for adding new tools.

### Custom Models
You can use any Ollama-compatible model:

```bash
# List available models
docker exec ollama-mcp ollama list

# Try different models
python client-example.py --model codellama:7b
python client-example.py --model mistral:7b
```

### VSCode Extension Development
To create custom VSCode extensions that work with this setup:

```typescript
// Example VSCode extension code
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    const provider = new SchemaRegistryProvider();
    vscode.languages.registerCompletionItemProvider(
        { scheme: 'file', language: 'json' },
        provider
    );
}

class SchemaRegistryProvider implements vscode.CompletionItemProvider {
    async provideCompletionItems(): Promise<vscode.CompletionItem[]> {
        // Query schema registry via MCP bridge
        const response = await fetch('http://localhost:8080/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: 'List all subjects',
                use_mcp: true
            })
        });
        // Process response and return completion items
    }
}
```

## 📝 API Reference

### Bridge Service Endpoints

#### POST /chat
```json
{
  "message": "Your question about schema registry",
  "model": "llama3.2:3b",
  "use_mcp": true
}
```

#### GET /health
```json
{
  "status": "healthy",
  "ollama": "connected", 
  "mcp_server": "http://mcp-server:8000"
}
```

### MCP Server Endpoints

#### Direct MCP Tool Access
```bash
# List all available tools
curl http://localhost:38000/tools

# Execute specific tool
curl -X POST http://localhost:38000/tools/list_subjects \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 🎯 Quick Demo Commands

Once everything is running, try these commands:

### CLI Commands
```bash
# Basic registry info
python client-example.py --message "Show me registry statistics"

# List schemas
python client-example.py --message "List all subjects"

# Interactive mode for natural conversation
python client-example.py
```

### VSCode Commands
- Open Command Palette (`Ctrl+Shift+P`)
- Type "Claude: Ask about schema registry"
- Ask: "What subjects are available in my schema registry?"

### API Commands
```bash
# Health check
curl http://localhost:8080/health

# Ask a question
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List all subjects", "use_mcp": true}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes in the `demo/` folder
4. Test with `cd demo && ./run-llama-mcp.sh start`
5. Test both CLI and VSCode integrations
6. Submit a pull request

## 📄 License

Same as the main repository.

## ⚠️ Notes

- This demo is designed for **local development** and testing
- Always run commands from the `demo/` directory
- VSCode integration requires compatible MCP extensions
- For production use, consider security, scaling, and monitoring requirements
- LLama models can be resource-intensive; adjust model size based on your hardware
- The bridge service provides a simple integration layer - extend it for your specific needs

## 🌟 What's Next?

After trying the demo, you might want to:

- **Integrate with your existing Schema Registry** - Update connection settings in `.env`
- **Try different models** - Experiment with various LLama models for different use cases
- **Build custom VSCode extensions** - Create schema-aware development tools
- **Add authentication** - Implement security for production deployments
- **Scale the setup** - Deploy across multiple environments

**Happy exploring!** 🚀