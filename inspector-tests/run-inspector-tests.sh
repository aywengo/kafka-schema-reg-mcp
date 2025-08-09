#!/bin/bash

# Script to run MCP Inspector tests for Kafka Schema Registry MCP Server
# Tests against released Docker images

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_VERSION="${DOCKER_VERSION:-stable}"
SKIP_ENV_SETUP="${SKIP_ENV_SETUP:-false}"
CLEANUP_AFTER="${CLEANUP_AFTER:-true}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if Schema Registry is running
check_schema_registry() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    print_status "Checking Schema Registry on port $port..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            print_status "Schema Registry is ready on port $port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "Schema Registry failed to start on port $port"
    return 1
}

# Function to start test environment
start_test_environment() {
    local mode=${1:-multi}  # multi | single
    if [ "$SKIP_ENV_SETUP" = "true" ]; then
        print_warning "Skipping environment setup (SKIP_ENV_SETUP=true)"
        return 0
    fi
    
    print_status "Starting test environment..."
    cd "$PROJECT_ROOT/tests"
    
    if [ -f "./start_test_environment.sh" ]; then
        if [[ "$mode" == "single" || "$mode" == "dev" ]]; then
            ./start_test_environment.sh dev
            # Wait for DEV registry only
            check_schema_registry 38081
        else
            ./start_test_environment.sh multi
            # Wait for registries defined in tests/docker-compose.yml
            # DEV registry
            check_schema_registry 38081
            # PROD registry
            check_schema_registry 38082
        fi
    else
        print_error "Test environment setup script not found!"
        exit 1
    fi
}

# Function to stop test environment
stop_test_environment() {
    if [ "$CLEANUP_AFTER" = "false" ]; then
        print_warning "Keeping test environment running (CLEANUP_AFTER=false)"
        return 0
    fi
    
    print_status "Stopping test environment..."
    cd "$PROJECT_ROOT/tests"
    
    if [ -f "./stop_test_environment.sh" ]; then
        ./stop_test_environment.sh clean
    fi
}

# Function to run inspector tests
run_inspector_tests() {
    local config_file=$1
    local test_name=$2
    
    print_status "Running Inspector test: $test_name"
    print_status "Using Docker image: aywengo/kafka-schema-reg-mcp:$DOCKER_VERSION"
    
    cd "$SCRIPT_DIR"
    
    # Create a temp config file and ensure readable permissions
    local temp_config
    temp_config="$SCRIPT_DIR/config/.temp.inspector-config.json"
    trap 'rm -f "$temp_config"' EXIT

    # Update config file to use the specified Docker version
    sed "s/:stable/:$DOCKER_VERSION/g" "$config_file" > "$temp_config"
    chmod 644 "$temp_config"

    print_status "Generated temp config: $temp_config"

    # Validate jq availability
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq is required to parse Inspector config. Please install jq."
        exit 1
    fi

    # Extract server config (first entry)
    local server_key
    server_key=$(jq -r '.mcpServers | keys[0]' "$temp_config")
    if [ -z "$server_key" ] || [ "$server_key" = "null" ]; then
        print_error "Invalid Inspector config: no mcpServers entry found"
        exit 1
    fi

    local server_command
    server_command=$(jq -r ".mcpServers[\"$server_key\"].command" "$temp_config")
    if [ -z "$server_command" ] || [ "$server_command" = "null" ]; then
        print_error "Invalid Inspector config: missing command"
        exit 1
    fi

    # Build args array from JSON
    local -a raw_args
    while IFS=$'\n' read -r line; do
        raw_args+=("$line")
    done < <(jq -r ".mcpServers[\"$server_key\"].args[]" "$temp_config")

    # Guard: args must contain at least the image as the last token
    local raw_len=${#raw_args[@]}
    if [ "$raw_len" -lt 1 ]; then
        print_error "Invalid Inspector config: args array is empty"
        exit 1
    fi

    # Separate image (last arg) from options
    local image_arg_idx=$((raw_len - 1))
    local image_arg="${raw_args[$image_arg_idx]}"

    # Filter out any placeholder env (-e KEY) from raw args before the image
    local -a base_opts
    local idx=0
    local limit=$image_arg_idx
    while [ $idx -lt $limit ]; do
        if [ "${raw_args[$idx]}" = "-e" ]; then
            # skip "-e" and following key token
            idx=$((idx + 2))
            continue
        fi
        base_opts+=("${raw_args[$idx]}")
        idx=$((idx + 1))
    done

    # Ensure we connect to the compose network so the container can reach registries by service name
    local -a docker_network_opts
    local has_network=false
    for opt in "${base_opts[@]}"; do
        if [ "$opt" = "--network" ]; then
            has_network=true
            break
        fi
    done
    if [ "$has_network" = false ]; then
        docker_network_opts=("--network" "kafka-test-network")
    fi

    # Build env pairs (-e KEY=VALUE) and map URLs to compose service names
    local -a env_pairs
    local env_len
    env_len=$(jq -r ".mcpServers[\"$server_key\"].env | length" "$temp_config")
    if [ "$env_len" != "0" ]; then
        while IFS=$'\t' read -r key value; do
            local final_value="$value"
            case "$key" in
                SCHEMA_REGISTRY_URL|SCHEMA_REGISTRY_URL_1)
                    final_value="http://schema-registry-dev:8081"
                    ;;
                SCHEMA_REGISTRY_URL_2)
                    final_value="http://schema-registry-prod:8082"
                    ;;
            esac
            env_pairs+=("-e" "${key}=${final_value}")
        done < <(jq -r ".mcpServers[\"$server_key\"].env | to_entries[] | [.key, (.value|tostring)] | @tsv" "$temp_config")
    fi

    # Compose final args: options + network + env pairs + image
    local -a final_args
    final_args=("${base_opts[@]}" "${docker_network_opts[@]}" "${env_pairs[@]}" "$image_arg")

    print_status "Launching Inspector with server: $server_command ${final_args[*]}"
    npx @mcpjam/inspector "$server_command" "${final_args[@]}"
}

# Main execution
main() {
    print_status "Starting MCP Inspector tests for Kafka Schema Registry MCP"
    print_status "Docker version: $DOCKER_VERSION"

    # Desired config name (maps to config/inspector-config-<name>.json)
    local selected_name="${1:-stable}"
    local config_path="$SCRIPT_DIR/config/inspector-config-${selected_name}.json"

    # Validate config exists
    if [ ! -f "$config_path" ]; then
        print_error "Config file not found: $config_path"
        print_warning "Available configs:"
        ls -1 "$SCRIPT_DIR/config" | sed 's/^/  - /'
        exit 1
    fi

    # Decide environment mode based on name
    local env_mode="single"
    if echo "$selected_name" | grep -qi "multi"; then
        env_mode="multi"
    fi

    # Change to inspector-tests directory
    cd "$SCRIPT_DIR"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing npm dependencies..."
        npm install
    fi
    
    # Start test environment based on mode
    start_test_environment "$env_mode"

    # Run the selected test
    run_inspector_tests "$config_path" "$selected_name"

    # Stop test environment
    stop_test_environment
    
    print_status "Inspector tests completed!"
}

# Run main function
main "$@"
