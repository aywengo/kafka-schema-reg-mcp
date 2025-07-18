#!/bin/bash

# Script to start test environment and run MCP development server
# Handles cleanup on interrupt

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
DOCKER_COMPOSE_FILE="tests/docker-compose.yml"
ENV_FILE="test_registry.env"
MCP_RUNNING=false
DOCKER_RUNNING=false

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

# Function to check if required files exist
check_requirements() {
    print_status "Checking requirements..."
    
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "Docker compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file not found: $ENV_FILE (will proceed without it)"
    fi
    
    if [ ! -f "kafka_schema_registry_unified_mcp.py" ]; then
        print_error "MCP server file not found: kafka_schema_registry_unified_mcp.py"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        print_error "Neither docker-compose nor docker compose is available"
        exit 1
    fi
    
    print_success "All requirements checked"
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        print_error "No valid docker compose command found"
        exit 1
    fi
}

# Function to start docker services
start_docker_services() {
    print_status "Starting Docker services..."
    
    local compose_cmd=$(get_docker_compose_cmd)
    local env_args=""
    
    # Add environment file if it exists
    if [ -f "$ENV_FILE" ]; then
        env_args="--env-file $ENV_FILE"
        print_status "Using environment file: $ENV_FILE"
    fi
    
    # Start services
    if $compose_cmd -f "$DOCKER_COMPOSE_FILE" $env_args up -d; then
        DOCKER_RUNNING=true
        print_success "Docker services started successfully"
        
        # Wait for services to be healthy
        print_status "Waiting for services to be healthy..."
        if $compose_cmd -f "$DOCKER_COMPOSE_FILE" $env_args logs -f --tail=0 &
        then
            local logs_pid=$!
            
            # Wait for a bit to let services start
            sleep 10
            
            # Kill the logs process
            kill $logs_pid 2>/dev/null || true
            
            print_success "Services are starting up..."
        fi
    else
        print_error "Failed to start Docker services"
        exit 1
    fi
}

# Function to stop docker services
stop_docker_services() {
    if [ "$DOCKER_RUNNING" = true ]; then
        print_status "Stopping Docker services..."
        
        local compose_cmd=$(get_docker_compose_cmd)
        local env_args=""
        
        if [ -f "$ENV_FILE" ]; then
            env_args="--env-file $ENV_FILE"
        fi
        
        # Stop and remove containers, networks, and volumes
        if $compose_cmd -f "$DOCKER_COMPOSE_FILE" $env_args down -v --remove-orphans; then
            print_success "Docker services stopped successfully"
        else
            print_warning "Some issues occurred while stopping Docker services"
        fi
        
        DOCKER_RUNNING=false
    fi
}

# Function to start MCP server
start_mcp_server() {
    print_status "Starting MCP development server..."
    
    # Load environment variables if file exists
    if [ -f "$ENV_FILE" ]; then
        print_status "Loading environment variables from $ENV_FILE"
        set -a  # automatically export all variables
        source "$ENV_FILE"
        set +a  # disable automatic export
    fi
    
    # Set ALLOW_LOCALHOST for testing environment
    export ALLOW_LOCALHOST=true
    
    # Start MCP server
    print_status "Running: mcp dev kafka_schema_registry_unified_mcp.py"
    mcp dev kafka_schema_registry_unified_mcp.py &
    local mcp_pid=$!
    MCP_RUNNING=true
    
    # Wait for MCP server
    wait $mcp_pid
    MCP_RUNNING=false
}

# Function to cleanup on exit
cleanup() {
    print_status "Cleaning up..."
    
    # Stop MCP server if running
    if [ "$MCP_RUNNING" = true ]; then
        print_status "Stopping MCP server..."
        # Kill all child processes
        jobs -p | xargs -r kill 2>/dev/null || true
        MCP_RUNNING=false
    fi
    
    # Stop Docker services
    stop_docker_services
    
    print_success "Cleanup completed"
}

# Function to verify schema registries are accessible
verify_schema_registries() {
    print_status "Verifying Schema Registry endpoints..."
    
    # Check development registry (port 38081)
    if curl -s -f http://localhost:38081/subjects >/dev/null 2>&1; then
        print_success "Development Schema Registry accessible at http://localhost:38081"
    else
        print_warning "Development Schema Registry at http://localhost:38081 not yet ready"
    fi
    
    # Check production registry (port 38082)  
    if curl -s -f http://localhost:38082/subjects >/dev/null 2>&1; then
        print_success "Production Schema Registry accessible at http://localhost:38082"
    else
        print_warning "Production Schema Registry at http://localhost:38082 not yet ready"
    fi
    
    # Additional wait if services aren't ready
    local retries=0
    local max_retries=12
    while [ $retries -lt $max_retries ]; do
        if curl -s -f http://localhost:38081/subjects >/dev/null 2>&1 && \
           curl -s -f http://localhost:38082/subjects >/dev/null 2>&1; then
            print_success "Both Schema Registries are ready!"
            break
        fi
        
        retries=$((retries + 1))
        print_status "Waiting for Schema Registries to be ready... (attempt $retries/$max_retries)"
        sleep 5
    done
    
    if [ $retries -eq $max_retries ]; then
        print_warning "Some Schema Registries may not be fully ready, but proceeding..."
    fi
}

# Function to display registry information
display_registry_info() {
    echo ""
    print_success "=== Test Environment Ready ==="
    echo -e "${BLUE}Available Schema Registries:${NC}"
    echo -e "  • ${GREEN}Development${NC}: http://localhost:38081"
    echo -e "  • ${GREEN}Production${NC}:  http://localhost:38082"
    echo ""
    echo -e "${BLUE}Web UI (AKHQ):${NC}"
    echo -e "  • ${GREEN}Management UI${NC}: http://localhost:38080"
    echo ""
    echo -e "${BLUE}MCP Server Configuration:${NC}"
    echo -e "  • Environment: ${ENV_FILE}"
    echo -e "  • Default Registry: development"
    echo "=================================="
    echo ""
}

# Function to handle interrupt signals
interrupt_handler() {
    print_warning "Interrupt received, initiating cleanup..."
    cleanup
    exit 0
}

# Main function
main() {
    print_status "Starting Kafka Schema Registry MCP Test Environment"
    echo "=================================================="
    
    # Set up signal handlers
    trap interrupt_handler SIGINT SIGTERM
    
    # Check requirements
    check_requirements
    
    # Start Docker services
    start_docker_services
    
    # Give services time to fully start
    print_status "Waiting 15 seconds for services to fully initialize..."
    sleep 15
    
    # Verify schema registries are accessible
    verify_schema_registries
    
    # Display registry information
    display_registry_info
    
    # Start MCP server
    start_mcp_server
    
    # If we reach here, MCP server exited normally
    print_status "MCP server has stopped"
    cleanup
}

# Run main function
main "$@" 