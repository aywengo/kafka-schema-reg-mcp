#!/bin/bash

# Kafka Schema Registry MCP Server - Helm Chart Publisher
# This script helps you publish your Helm chart to various repositories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CHART_DIR="$PROJECT_DIR/helm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo ""
    print_color $BLUE "=============================================="
    print_color $BLUE "$1"
    print_color $BLUE "=============================================="
    echo ""
}

# Function to validate chart
validate_chart() {
    print_header "VALIDATING HELM CHART"
    
    cd "$CHART_DIR"
    
    print_color $YELLOW "🔍 Linting Helm chart..."
    helm lint .
    
    print_color $YELLOW "🔍 Validating template rendering..."
    helm template test . --debug > /dev/null
    
    print_color $YELLOW "🔍 Checking dependencies..."
    helm dependency update
    
    print_color $GREEN "✅ Chart validation completed successfully!"
}

# Function to package chart locally
package_chart() {
    local version=$1
    print_header "PACKAGING HELM CHART (Version: $version)"
    
    cd "$PROJECT_DIR"
    
    # Update chart version
    if [[ -n "$version" ]]; then
        print_color $YELLOW "📝 Updating chart version to $version..."
        sed -i.bak "s/^version:.*/version: $version/" "$CHART_DIR/Chart.yaml"
        sed -i.bak "s/^appVersion:.*/appVersion: \"$version\"/" "$CHART_DIR/Chart.yaml"
        rm -f "$CHART_DIR/Chart.yaml.bak"
    fi
    
    # Create packages directory
    mkdir -p packages
    
    # Package the chart
    print_color $YELLOW "📦 Packaging chart..."
    helm package helm/ --destination packages/
    
    print_color $GREEN "✅ Chart packaged successfully in packages/ directory"
    ls -la packages/
}

# Function to publish to GitHub Pages
publish_github_pages() {
    print_header "PUBLISHING TO GITHUB PAGES"
    
    print_color $YELLOW "📚 Setting up GitHub Pages repository..."
    
    cat << 'EOF'
To publish to GitHub Pages, follow these steps:

1. Enable GitHub Pages in your repository:
   - Go to Settings → Pages
   - Source: GitHub Actions
   - Save the configuration

2. Push your changes and create a release:
   git add .
   git commit -m "Add Helm chart and GitHub Actions workflow"
   git push origin main
   
3. Create a release tag:
   git tag v1.8.0
   git push origin v1.8.0

4. The GitHub Action will automatically:
   - Package your chart
   - Create a GitHub release
   - Publish to GitHub Pages

5. Your chart will be available at:
   https://aywengo.github.io/kafka-schema-reg-mcp

6. Users can add your repo:
   helm repo add kafka-mcp https://aywengo.github.io/kafka-schema-reg-mcp
   helm repo update
   helm install my-release kafka-mcp/kafka-schema-registry-mcp

EOF
}

# Function to publish to OCI registry
publish_oci() {
    local registry=$1
    local version=$2
    
    print_header "PUBLISHING TO OCI REGISTRY ($registry)"
    
    cd "$PROJECT_DIR"
    
    # Login to registry (user needs to do this manually)
    print_color $YELLOW "🔐 Please ensure you're logged in to $registry"
    print_color $YELLOW "Example: helm registry login $registry"
    
    # Package if not already done
    if [[ ! -d "packages" ]]; then
        package_chart "$version"
    fi
    
    # Push to OCI registry
    local chart_file=$(ls packages/kafka-schema-registry-mcp-*.tgz | head -1)
    if [[ -f "$chart_file" ]]; then
        print_color $YELLOW "📤 Pushing chart to OCI registry..."
        helm push "$chart_file" "oci://$registry"
        print_color $GREEN "✅ Chart published to oci://$registry"
        
        print_color $BLUE "Users can install with:"
        print_color $BLUE "helm install my-release oci://$registry/kafka-schema-registry-mcp --version $version"
    else
        print_color $RED "❌ No chart package found!"
        exit 1
    fi
}

# Function to setup Artifact Hub
setup_artifact_hub() {
    print_header "ARTIFACT HUB SETUP"
    
    cat << 'EOF'
To submit your chart to Artifact Hub:

1. Create an artifacthub-repo.yml file in your repository root:
EOF

    cat > "$PROJECT_DIR/artifacthub-repo.yml" << 'EOF'
# Artifact Hub repository metadata file
repositoryID: kafka-schema-registry-mcp
kind: helm
name: Kafka Schema Registry MCP Server
displayName: Kafka Schema Registry MCP Server
description: True MCP server for Kafka Schema Registry with OAuth2 authentication
url: https://aywengo.github.io/kafka-schema-reg-mcp
logoURL: https://github.com/aywengo/kafka-schema-reg-mcp/raw/main/docs/assets/logo.png
links:
  - name: GitHub
    url: https://github.com/aywengo/kafka-schema-reg-mcp
  - name: Documentation
    url: https://github.com/aywengo/kafka-schema-reg-mcp/tree/main/docs
maintainers:
  - name: aywengo
    email: your-email@example.com
EOF

    print_color $GREEN "✅ Created artifacthub-repo.yml"
    
    cat << 'EOF'

2. Submit to Artifact Hub:
   - Go to https://artifacthub.io/control-panel
   - Add your repository: https://aywengo.github.io/kafka-schema-reg-mcp
   - Artifact Hub will automatically index your charts

3. Your chart will be discoverable at:
   https://artifacthub.io/packages/helm/kafka-schema-registry-mcp/kafka-schema-registry-mcp

EOF
}

# Function to publish to custom repository
publish_custom() {
    local repo_url=$1
    local version=$2
    
    print_header "PUBLISHING TO CUSTOM REPOSITORY"
    
    cat << EOF
To publish to a custom Helm repository ($repo_url):

1. Package your chart (if not done):
   $(package_chart "$version")

2. Generate/update repository index:
   helm repo index packages/ --url $repo_url

3. Upload files to your web server:
   - Upload packages/*.tgz files
   - Upload index.yaml file

4. Users can add your repo:
   helm repo add kafka-mcp $repo_url
   helm repo update
   helm install my-release kafka-mcp/kafka-schema-registry-mcp

EOF
}

# Main menu
show_menu() {
    print_header "KAFKA SCHEMA REGISTRY MCP HELM CHART PUBLISHER"
    
    echo "Choose publishing method:"
    echo ""
    echo "1) 🐙 GitHub Pages (Recommended - Free)"
    echo "2) 📦 OCI Registry (Docker Hub, GHCR, etc.)"
    echo "3) 🏛️ Artifact Hub Submission"
    echo "4) 🌐 Custom Repository"
    echo "5) 🧪 Validate Chart Only"
    echo "6) 📦 Package Chart Locally"
    echo "7) ❓ Help & Information"
    echo "8) 🚪 Exit"
    echo ""
}

# Help function
show_help() {
    print_header "HELP & INFORMATION"
    
    cat << 'EOF'
PUBLISHING OPTIONS:

1. GitHub Pages (Recommended):
   - Free hosting via GitHub
   - Automatic updates with GitHub Actions
   - Best for open-source projects
   - URL: https://username.github.io/repository-name

2. OCI Registry:
   - Store charts in container registries
   - Supports: Docker Hub, GHCR, Harbor, etc.
   - Good for private/enterprise use
   - Example: oci://registry.example.com/charts

3. Artifact Hub:
   - Public chart discovery platform
   - Automatic indexing from GitHub Pages
   - Increases chart visibility
   - URL: https://artifacthub.io

4. Custom Repository:
   - Host on your own web server
   - Full control over infrastructure
   - Good for private/enterprise use

REQUIREMENTS:
- Helm 3.x installed
- Git repository with proper permissions
- For OCI: Registry credentials
- For GitHub Pages: Repository with Pages enabled

CHART STRUCTURE:
helm/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values
├── templates/          # Kubernetes templates
└── README.md          # Chart documentation

EOF
}

# Main script logic
main() {
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_color $RED "❌ Helm is not installed!"
        print_color $YELLOW "Please install Helm: https://helm.sh/docs/intro/install/"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -d "$CHART_DIR" ]]; then
        print_color $RED "❌ Helm chart directory not found!"
        print_color $YELLOW "Expected: $CHART_DIR"
        exit 1
    fi
    
    while true; do
        show_menu
        read -p "Select option [1-8]: " choice
        
        case $choice in
            1)
                validate_chart
                publish_github_pages
                ;;
            2)
                validate_chart
                read -p "Enter OCI registry URL (e.g., ghcr.io/username): " registry
                read -p "Enter chart version (e.g., 1.8.0): " version
                publish_oci "$registry" "$version"
                ;;
            3)
                setup_artifact_hub
                ;;
            4)
                read -p "Enter custom repository URL: " repo_url
                read -p "Enter chart version (e.g., 1.8.0): " version
                publish_custom "$repo_url" "$version"
                ;;
            5)
                validate_chart
                ;;
            6)
                read -p "Enter chart version (e.g., 1.8.0) or press Enter for current: " version
                package_chart "$version"
                ;;
            7)
                show_help
                ;;
            8)
                print_color $GREEN "👋 Goodbye!"
                exit 0
                ;;
            *)
                print_color $RED "❌ Invalid option. Please select 1-8."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@" 