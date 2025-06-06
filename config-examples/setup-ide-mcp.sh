#!/bin/bash

# Setup script for IDE MCP Integration with Kafka Schema Registry
# This script configures VS Code, Cursor, and JetBrains IDEs for MCP protocol integration

set -e

echo "🚀 Kafka Schema Registry MCP - IDE Integration Setup"
echo "======================================================"

# Check if we're in the right directory
if [ ! -f "config-examples/mcp-ide-integration.md" ]; then
    echo "❌ Please run this script from the kafka-schema-reg-mcp repository root"
    exit 1
fi

# Function to setup VS Code
setup_vscode() {
    echo "🔵 Setting up VS Code MCP integration..."
    
    # Create .vscode directory if it doesn't exist
    mkdir -p .vscode
    
    # Copy VS Code configurations
    cp config-examples/vscode-mcp-settings.json .vscode/settings.json
    cp config-examples/vscode-mcp-tasks.json .vscode/tasks.json
    
    echo "✅ VS Code configuration copied to .vscode/"
    echo "📝 Install MCP extension: code --install-extension mcp-client.vscode-mcp"
}

# Function to setup Cursor
setup_cursor() {
    echo "⚡ Setting up Cursor MCP integration..."
    
    # Create .cursor directory if it doesn't exist
    mkdir -p .cursor
    
    # Copy Cursor configuration
    cp config-examples/cursor-mcp-config.json .cursor/mcp-config.json
    
    echo "✅ Cursor configuration copied to .cursor/"
    echo "📝 Cursor has built-in MCP support - no additional extensions needed"
}

# Function to setup JetBrains IDEs
setup_jetbrains() {
    echo "🔴 Setting up JetBrains IDEs MCP integration..."
    
    # Create .idea directory if it doesn't exist
    mkdir -p .idea
    
    # Copy JetBrains configuration
    cp config-examples/jetbrains-mcp-config.xml .idea/mcp-config.xml
    
    echo "✅ JetBrains configuration copied to .idea/"
    echo "📝 Install MCP plugin from JetBrains Marketplace"
}

# Function to setup development environment
setup_environment() {
    echo "🐳 Setting up MCP development environment..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Start the MCP development environment
    echo "🚀 Starting Kafka Schema Registry + MCP services..."
    docker-compose -f config-examples/docker-compose.mcp.yml up -d
    
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Check service health
    echo "🔍 Checking service health..."
    
    # Check Schema Registry
    if curl -s http://localhost:8081/subjects > /dev/null; then
        echo "✅ Schema Registry (single) is running on http://localhost:8081"
    else
        echo "⚠️  Schema Registry might still be starting..."
    fi
    
    # Check MCP Server
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ MCP Server (single) is running on http://localhost:8080"
    else
        echo "⚠️  MCP Server might still be starting..."
    fi
    
    # Check Multi-Registry MCP Server
    if curl -s http://localhost:8081/health > /dev/null 2>&1; then
        echo "✅ MCP Server (multi) is running on http://localhost:8081"
    else
        echo "⚠️  Multi-Registry MCP Server might still be starting..."
    fi
    
    echo "🌐 AKHQ UI available at http://localhost:38080"
}

# Function to test MCP integration
test_integration() {
    echo "🧪 Testing MCP integration..."
    
    # Test basic MCP connectivity
    if command -v python3 > /dev/null; then
        python3 config-examples/test-mcp-connection.py
    else
        echo "⚠️  Python3 not available for testing. Please verify manually:"
        echo "   curl http://localhost:8080/health"
    fi
}

# Function to show next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup Complete! Next Steps:"
    echo "================================"
    echo ""
    echo "📖 Read the complete guide:"
    echo "   open config-examples/mcp-ide-integration.md"
    echo ""
    echo "🔵 VS Code:"
    echo "   1. Install MCP extension: code --install-extension mcp-client.vscode-mcp"
    echo "   2. Restart VS Code"
    echo "   3. Open Command Palette > 'MCP: Connect to Server'"
    echo ""
    echo "⚡ Cursor:"
    echo "   1. Restart Cursor"
    echo "   2. MCP integration should be automatically detected"
    echo "   3. Try asking: 'List all schema subjects'"
    echo ""
    echo "🔴 JetBrains IDEs:"
    echo "   1. Install MCP plugin from Marketplace"
    echo "   2. Restart IDE"
    echo "   3. Configure MCP server in Settings > Tools > MCP"
    echo ""
    echo "🐳 Services running:"
    echo "   - Schema Registry: http://localhost:8081"
    echo "   - MCP Server (Single): http://localhost:8080"
    echo "   - MCP Server (Multi): http://localhost:8081"
    echo "   - AKHQ UI: http://localhost:38080"
    echo ""
    echo "🛑 To stop services:"
    echo "   docker-compose -f config-examples/docker-compose.mcp.yml down"
}

# Main execution
main() {
    # Parse command line arguments
    SETUP_VSCODE=false
    SETUP_CURSOR=false
    SETUP_JETBRAINS=false
    SETUP_ENVIRONMENT=false
    SETUP_ALL=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --vscode)
                SETUP_VSCODE=true
                shift
                ;;
            --cursor)
                SETUP_CURSOR=true
                shift
                ;;
            --jetbrains)
                SETUP_JETBRAINS=true
                shift
                ;;
            --environment)
                SETUP_ENVIRONMENT=true
                shift
                ;;
            --all)
                SETUP_ALL=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --vscode      Setup VS Code MCP integration"
                echo "  --cursor      Setup Cursor MCP integration"
                echo "  --jetbrains   Setup JetBrains IDEs MCP integration"
                echo "  --environment Setup Docker development environment"
                echo "  --all         Setup everything"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # If no specific options, setup everything
    if [ "$SETUP_ALL" = true ] || ([ "$SETUP_VSCODE" = false ] && [ "$SETUP_CURSOR" = false ] && [ "$SETUP_JETBRAINS" = false ] && [ "$SETUP_ENVIRONMENT" = false ]); then
        SETUP_VSCODE=true
        SETUP_CURSOR=true
        SETUP_JETBRAINS=true
        SETUP_ENVIRONMENT=true
    fi
    
    # Execute setup functions
    if [ "$SETUP_VSCODE" = true ]; then
        setup_vscode
    fi
    
    if [ "$SETUP_CURSOR" = true ]; then
        setup_cursor
    fi
    
    if [ "$SETUP_JETBRAINS" = true ]; then
        setup_jetbrains
    fi
    
    if [ "$SETUP_ENVIRONMENT" = true ]; then
        setup_environment
    fi
    
    # Test integration if environment was set up
    if [ "$SETUP_ENVIRONMENT" = true ]; then
        sleep 5  # Give services more time to start
        test_integration
    fi
    
    show_next_steps
}

# Run main function with all arguments
main "$@" 