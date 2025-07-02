#!/bin/bash

# Kafka Schema Registry MCP with LLama Integration Setup Script
# This script sets up and runs the complete stack including Kafka, Schema Registry, MCP Server, and LLama

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_MODEL="llama3.2:3b"
COMPOSE_FILE="docker-compose-llama.yml"
MODELS_DIR="./models"
LOGS_DIR="./logs"
BRIDGE_DIR="./bridge"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$MODELS_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$BRIDGE_DIR"
    
    print_success "Directories created"
}

# Function to check for GPU support
check_gpu_support() {
    print_status "Checking GPU support..."
    
    if command_exists nvidia-smi; then
        print_success "NVIDIA GPU detected"
        return 0
    else
        print_warning "No NVIDIA GPU detected. LLama will run on CPU (slower)"
        return 1
    fi
}

# Function to create bridge service files
create_bridge_service() {
    print_status "Creating MCP-LLama bridge service..."
    
    # Create Dockerfile for bridge service
    cat > "$BRIDGE_DIR/Dockerfile.bridge" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-bridge.txt .
RUN pip install --no-cache-dir -r requirements-bridge.txt

# Copy bridge application
COPY bridge/ ./

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the bridge service
CMD ["python", "main.py"]
EOF

    # Create requirements for bridge service
    cat > "$BRIDGE_DIR/requirements-bridge.txt" << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
pydantic==2.5.0
python-multipart==0.0.6
aiofiles==23.2.1
python-json-logger==2.0.7
EOF

    # Create main bridge application
    cat > "$BRIDGE_DIR/main.py" << 'EOF'
import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "http://localhost:8000")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:3b")

app = FastAPI(title="MCP-LLama Bridge", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = DEFAULT_MODEL
    use_mcp: bool = True

class ChatResponse(BaseModel):
    response: str
    model: str
    used_tools: list = []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Ollama connection
        async with httpx.AsyncClient() as client:
            ollama_response = await client.get(f"{OLLAMA_HOST}/api/version")
            ollama_healthy = ollama_response.status_code == 200
            
        return {
            "status": "healthy" if ollama_healthy else "degraded",
            "ollama": "connected" if ollama_healthy else "disconnected",
            "mcp_server": MCP_SERVER_HOST
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint that integrates LLama with MCP tools"""
    try:
        if request.use_mcp:
            # Get available MCP tools first
            tools_info = await get_mcp_tools()
            
            # Create enhanced prompt with tool information
            enhanced_prompt = create_tool_enhanced_prompt(request.message, tools_info)
            
            # Get LLama response
            llama_response = await query_llama(enhanced_prompt, request.model)
            
            # Check if LLama wants to use tools
            tool_calls = extract_tool_calls(llama_response)
            
            if tool_calls:
                # Execute tools and get final response
                final_response = await execute_tools_and_respond(
                    tool_calls, request.message, request.model
                )
                return ChatResponse(
                    response=final_response,
                    model=request.model,
                    used_tools=[call["tool"] for call in tool_calls]
                )
        
        # Simple LLama query without MCP
        response = await query_llama(request.message, request.model)
        return ChatResponse(response=response, model=request.model)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_mcp_tools():
    """Get available MCP tools"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MCP_SERVER_HOST}/tools")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Could not fetch MCP tools: {e}")
    return []

async def query_llama(prompt: str, model: str) -> str:
    """Query LLama via Ollama"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["response"]

def create_tool_enhanced_prompt(message: str, tools_info: list) -> str:
    """Create a prompt that includes available tools information"""
    tools_desc = "\n".join([
        f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}"
        for tool in tools_info
    ])
    
    return f"""You are an assistant that can help with Kafka Schema Registry operations.

Available tools:
{tools_desc}

To use a tool, respond with JSON in this format:
{{"use_tool": true, "tool": "tool_name", "arguments": {{"param": "value"}}}}

User message: {message}

Provide a helpful response. If the user's request can be fulfilled using available tools, use the appropriate tool."""

def extract_tool_calls(response: str) -> list:
    """Extract tool calls from LLama response"""
    try:
        # Try to parse as JSON
        parsed = json.loads(response.strip())
        if isinstance(parsed, dict) and parsed.get("use_tool"):
            return [parsed]
    except json.JSONDecodeError:
        pass
    return []

async def execute_tools_and_respond(tool_calls: list, original_message: str, model: str) -> str:
    """Execute MCP tools and get final response"""
    results = []
    
    for call in tool_calls:
        try:
            # Execute MCP tool
            result = await execute_mcp_tool(call["tool"], call.get("arguments", {}))
            results.append(f"Tool '{call['tool']}' result: {result}")
        except Exception as e:
            results.append(f"Tool '{call['tool']}' failed: {str(e)}")
    
    # Create follow-up prompt with results
    follow_up_prompt = f"""
Original request: {original_message}

Tool execution results:
{chr(10).join(results)}

Please provide a clear, human-readable summary of these results.
"""
    
    return await query_llama(follow_up_prompt, model)

async def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Execute an MCP tool"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_SERVER_HOST}/tools/{tool_name}",
            json=arguments
        )
        response.raise_for_status()
        return response.text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

    print_success "Bridge service files created"
}

# Function to pull LLama model
pull_model() {
    local model=${1:-$DEFAULT_MODEL}
    print_status "Pulling LLama model: $model"
    
    # Wait for Ollama to be ready
    print_status "Waiting for Ollama service to be ready..."
    sleep 10
    
    # Pull the model
    docker exec ollama-mcp ollama pull "$model" || {
        print_warning "Failed to pull model automatically. You can pull it later with:"
        print_warning "docker exec ollama-mcp ollama pull $model"
    }
}

# Function to start services
start_services() {
    print_status "Starting all services..."
    
    # Start services in the background
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_status "Waiting for services to be ready..."
    
    # Wait for core services
    sleep 30
    
    print_success "Services started successfully!"
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    print_status "Service URLs:"
    echo "🤖 LLama (Ollama):           http://localhost:11434"
    echo "🌉 MCP-LLama Bridge:        http://localhost:8080"
    echo "🔧 MCP Server:              http://localhost:38000"
    echo "📊 Schema Registry:         http://localhost:38081"
    echo "🎛️  Kafka UI (AKHQ):         http://localhost:38080"
    echo "📁 Kafka:                   localhost:39092"
}

# Function to stop services
stop_services() {
    print_status "Stopping all services..."
    docker-compose -f "$COMPOSE_FILE" down
    print_success "Services stopped"
}

# Function to clean up everything
cleanup() {
    print_status "Cleaning up all resources..."
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
    print_success "Cleanup completed"
}

# Function to show logs
show_logs() {
    local service=${1:-""}
    if [ -n "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Function to show help
show_help() {
    echo "Kafka Schema Registry MCP with LLama Integration"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show service status"
    echo "  logs [service]  Show logs (optionally for specific service)"
    echo "  cleanup         Stop services and remove volumes"
    echo "  pull-model      Pull LLama model"
    echo "  help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DEFAULT_MODEL   LLama model to use (default: llama3.2:3b)"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs ollama              # Show Ollama logs"
    echo "  $0 pull-model llama3:8b     # Pull specific model"
}

# Main script logic
main() {
    local command=${1:-"help"}
    
    case "$command" in
        "start")
            check_prerequisites
            create_directories
            check_gpu_support
            create_bridge_service
            start_services
            pull_model "${2:-$DEFAULT_MODEL}"
            show_status
            echo ""
            print_success "🚀 All services are up and running!"
            print_status "You can now interact with LLama through the bridge at http://localhost:8080"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 5
            start_services
            show_status
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "$2"
            ;;
        "cleanup")
            cleanup
            ;;
        "pull-model")
            pull_model "$2"
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"