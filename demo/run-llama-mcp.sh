#!/bin/bash

# Kafka Schema Registry MCP with LLama Integration Setup Script
# This script sets up and runs the complete stack including Kafka, Schema Registry, MCP Server, and LLama
# Run this script from the demo/ directory

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
    
    # Check if we're in the demo directory
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Cannot find $COMPOSE_FILE. Please run this script from the demo/ directory."
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
    
    # Create main bridge application if it doesn't exist
    if [ ! -f "$BRIDGE_DIR/main.py" ]; then
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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "http://mcp-server:8000")
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
        async with httpx.AsyncClient(timeout=10.0) as client:
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
        logger.info(f"Received chat request: {request.message[:100]}...")
        
        if request.use_mcp:
            # Simple approach: Ask LLama directly with MCP context
            mcp_context = await get_mcp_context()
            enhanced_prompt = f"""You are a helpful assistant with access to Kafka Schema Registry.

Available Schema Registry operations: {mcp_context}

User question: {request.message}

Please provide a helpful response. If the user is asking about schemas, subjects, or registry operations, provide relevant information."""
            
            response = await query_llama(enhanced_prompt, request.model)
            return ChatResponse(response=response, model=request.model, used_tools=["mcp_context"])
        
        # Simple LLama query without MCP
        response = await query_llama(request.message, request.model)
        return ChatResponse(response=response, model=request.model)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_mcp_context():
    """Get MCP context information"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get basic registry info
            response = await client.get(f"{MCP_SERVER_HOST}/health")
            if response.status_code == 200:
                return "Schema Registry is available for queries about subjects, schemas, versions, and compatibility."
    except Exception as e:
        logger.warning(f"Could not connect to MCP server: {e}")
    return "Schema Registry operations may be limited."

async def query_llama(prompt: str, model: str) -> str:
    """Query LLama via Ollama"""
    try:
        logger.info(f"Querying LLama with model {model}: {prompt[:100]}...")
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
            result = response.json()["response"]
            logger.info(f"LLama response received: {len(result)} characters")
            return result
    except Exception as e:
        logger.error(f"LLama query failed: {e}")
        return f"Error: Could not get response from LLama. {str(e)}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF
    fi
    
    print_success "Bridge service files verified/created"
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
    echo ""
    echo "Note: Run this script from the demo/ directory"
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
            print_status "Try running: python client-example.py"
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