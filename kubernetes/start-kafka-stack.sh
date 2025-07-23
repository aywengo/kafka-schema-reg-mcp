#!/bin/bash

# Kafka Schema Registry MCP Server - Kind Kubernetes Deployment Script (Helm-based)
# This script creates a Kind cluster and deploys Kafka, Schema Registry, AKHQ, and MCP Server using Helm charts

set -euo pipefail

# Script configuration
CLUSTER_NAME="kafka-mcp-cluster"
NAMESPACE="kafka-system"
MCP_NAMESPACE="mcp-system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHARTS_DIR="${SCRIPT_DIR}/charts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed. Please install $1 and try again."
        exit 1
    fi
}

# Function to wait for deployment to be ready
wait_for_deployment() {
    local namespace=$1
    local deployment=$2
    local timeout=${3:-300}
    
    log_info "Waiting for deployment $deployment in namespace $namespace to be ready..."
    kubectl wait --for=condition=available \
        --timeout=${timeout}s \
        deployment/$deployment \
        -n $namespace
}

# Function to wait for Helm release
wait_for_helm_release() {
    local release_name=$1
    local namespace=$2
    local timeout=${3:-300}
    
    log_info "Waiting for Helm release $release_name in namespace $namespace to be ready..."
    local end_time=$((SECONDS + timeout))
    
    while [[ $SECONDS -lt $end_time ]]; do
        if helm status $release_name -n $namespace &> /dev/null; then
            local status=$(helm status $release_name -n $namespace -o json | jq -r '.info.status')
            if [[ "$status" == "deployed" ]]; then
                log_success "Helm release $release_name is ready"
                return 0
            fi
        fi
        sleep 5
    done
    
    log_error "Timeout waiting for Helm release $release_name"
    return 1
}

# Function to create Kind cluster
create_kind_cluster() {
    log_info "Creating Kind cluster: $CLUSTER_NAME"
    
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        log_warning "Kind cluster '$CLUSTER_NAME' already exists. Deleting and recreating..."
        kind delete cluster --name $CLUSTER_NAME
    fi

    cat <<EOF | kind create cluster --name $CLUSTER_NAME --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 39092
    hostPort: 39092
    protocol: TCP
  - containerPort: 38081
    hostPort: 38081
    protocol: TCP
  - containerPort: 38080
    hostPort: 38080
    protocol: TCP
  - containerPort: 38000
    hostPort: 38000
    protocol: TCP
EOF

    log_success "Kind cluster created successfully"
}

# Function to add Helm repositories
add_helm_repositories() {
    log_info "Adding Helm repositories..."
    
    # Add Strimzi repository
    helm repo add strimzi https://strimzi.io/charts/
    
    # Add AKHQ repository
    helm repo add akhq https://akhq.io/
    
    # Add Bitnami repository
    helm repo add bitnami https://charts.bitnami.com/bitnami
    
    # Add Kafka MCP repository (published chart)
    helm repo add kafka-mcp https://aywengo.github.io/kafka-schema-reg-mcp
    
    # Update repositories
    helm repo update
    
    log_success "Helm repositories added and updated"
}

# Function to install Strimzi Kafka operator
install_strimzi_operator() {
    log_info "Installing Strimzi Kafka operator using Helm..."
    
    # Create namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Strimzi operator using Helm
    helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
        --namespace $NAMESPACE \
        --values "${CHARTS_DIR}/strimzi-values.yaml" \
        --wait \
        --timeout=300s
    
    log_success "Strimzi operator installed successfully"
}

# Function to deploy Kafka cluster
deploy_kafka_cluster() {
    log_info "Deploying Kafka cluster using Strimzi Helm chart..."
    
    # Install Kafka cluster using local Helm chart
    helm upgrade --install kafka-cluster "${CHARTS_DIR}/kafka-cluster" \
        --namespace $NAMESPACE \
        --wait \
        --timeout=600s
    
    wait_for_helm_release "kafka-cluster" $NAMESPACE
    
    # Wait for Kafka to be ready
    log_info "Waiting for Kafka cluster to be ready (this may take several minutes)..."
    kubectl wait kafka/kafka-mcp --for=condition=Ready --timeout=600s -n $NAMESPACE
    
    log_success "Kafka cluster deployed successfully"
}

# Function to deploy Schema Registry using Bitnami Helm chart
deploy_schema_registry() {
    log_info "Deploying Schema Registry using Bitnami Helm chart..."
    
    # Install Schema Registry using Helm
    helm upgrade --install schema-registry bitnami/schema-registry \
        --namespace $NAMESPACE \
        --values "${CHARTS_DIR}/schema-registry-values.yaml" \
        --wait \
        --timeout=300s
    
    wait_for_helm_release "schema-registry" $NAMESPACE
    
    log_success "Schema Registry deployed successfully"
}

# Function to deploy AKHQ using Helm chart
deploy_akhq() {
    log_info "Deploying AKHQ using Helm chart..."
    
    # Install AKHQ using Helm
    helm upgrade --install akhq akhq/akhq \
        --namespace $NAMESPACE \
        --values "${CHARTS_DIR}/akhq-values.yaml" \
        --wait \
        --timeout=300s
    
    wait_for_helm_release "akhq" $NAMESPACE
    
    log_success "AKHQ deployed successfully"
}

# Function to build and load MCP server image
build_and_load_mcp_image() {
    log_info "Building and loading MCP server image..."
    
    # Build the image from the project root
    cd "${SCRIPT_DIR}/.."
    docker build -t kafka-schema-reg-mcp:local .
    
    # Load image into Kind cluster
    kind load docker-image kafka-schema-reg-mcp:local --name $CLUSTER_NAME
    
    cd "${SCRIPT_DIR}"
    log_success "MCP server image built and loaded into Kind cluster"
}

# Function to deploy MCP server using published Helm chart
deploy_mcp_server() {
    log_info "Deploying MCP server using published Helm chart..."
    
    # Create MCP namespace
    kubectl create namespace $MCP_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Install MCP server using published Helm chart
    helm upgrade --install mcp-server kafka-mcp/kafka-schema-registry-mcp \
        --namespace $MCP_NAMESPACE \
        --values "${CHARTS_DIR}/mcp-server-values.yaml" \
        --wait \
        --timeout=300s
    
    wait_for_helm_release "mcp-server" $MCP_NAMESPACE
    
    log_success "MCP server deployed successfully"
}

# Function to display connection information
display_connection_info() {
    log_success "=============================================="
    log_success "Kafka Schema Registry MCP Stack is ready!"
    log_success "=============================================="
    echo
    log_info "Service endpoints (accessible from your host machine):"
    echo "  • Kafka Bootstrap Server: localhost:39092"
    echo "  • Schema Registry: http://localhost:38081"
    echo "  • AKHQ (Kafka UI): http://localhost:38080"
    echo "  • MCP Server: http://localhost:38000"
    echo
    log_info "Kubernetes cluster information:"
    echo "  • Cluster name: $CLUSTER_NAME"
    echo "  • Kafka namespace: $NAMESPACE"
    echo "  • MCP namespace: $MCP_NAMESPACE"
    echo
    log_info "Helm releases:"
    helm list --all-namespaces
    echo
    log_info "Useful commands:"
    echo "  • Check all pods: kubectl get pods --all-namespaces"
    echo "  • View MCP server logs: kubectl logs -f deployment/mcp-server-mcp-server -n $MCP_NAMESPACE"
    echo "  • View Schema Registry logs: kubectl logs -f deployment/schema-registry -n $NAMESPACE"
    echo "  • List Helm releases: helm list --all-namespaces"
    echo "  • Delete cluster: kind delete cluster --name $CLUSTER_NAME"
    echo
    log_info "Testing the deployment:"
    echo "  • Schema Registry health: curl http://localhost:38081/subjects"
    echo "  • MCP Server health: curl http://localhost:38000/health"
    echo
}

# Function to cleanup on exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        log_error "Script failed. You may want to clean up manually:"
        log_error "  kind delete cluster --name $CLUSTER_NAME"
    fi
}

# Main deployment function
main() {
    log_info "Starting Kafka Schema Registry MCP Stack deployment on Kind using Helm..."
    echo
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    check_command "kind"
    check_command "kubectl"
    check_command "docker"
    check_command "helm"
    check_command "jq"
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Deployment steps
    create_kind_cluster
    add_helm_repositories
    install_strimzi_operator
    deploy_kafka_cluster
    deploy_schema_registry
    deploy_akhq
    build_and_load_mcp_image
    deploy_mcp_server
    
    # Show connection information
    display_connection_info
}

# Function to uninstall all Helm releases
uninstall_helm_releases() {
    log_info "Uninstalling Helm releases..."
    
    # Uninstall in reverse order
    helm uninstall mcp-server -n $MCP_NAMESPACE 2>/dev/null || true
    helm uninstall akhq -n $NAMESPACE 2>/dev/null || true
    helm uninstall schema-registry -n $NAMESPACE 2>/dev/null || true
    helm uninstall kafka-cluster -n $NAMESPACE 2>/dev/null || true
    helm uninstall strimzi-kafka-operator -n $NAMESPACE 2>/dev/null || true
    
    log_success "Helm releases uninstalled"
}

# Script options
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_info "Stopping Kafka Schema Registry MCP Stack..."
        uninstall_helm_releases
        kind delete cluster --name $CLUSTER_NAME
        log_success "Cluster deleted successfully"
        ;;
    status)
        log_info "Checking cluster status..."
        if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
            echo "=== Kubernetes Pods ==="
            kubectl get pods --all-namespaces
            echo
            echo "=== Helm Releases ==="
            helm list --all-namespaces
        else
            log_warning "Cluster '$CLUSTER_NAME' is not running"
        fi
        ;;
    logs)
        service=${2:-mcp-server}
        case $service in
            mcp|mcp-server)
                kubectl logs -f deployment/mcp-server-mcp-server -n $MCP_NAMESPACE
                ;;
            kafka)
                kubectl logs -f kafka-mcp-kafka-0 -n $NAMESPACE
                ;;
            schema-registry|sr)
                kubectl logs -f deployment/schema-registry -n $NAMESPACE
                ;;
            akhq)
                kubectl logs -f deployment/akhq -n $NAMESPACE
                ;;
            *)
                log_error "Unknown service: $service"
                log_info "Available services: mcp-server, kafka, schema-registry, akhq"
                exit 1
                ;;
        esac
        ;;
            restart)
        service=${2:-mcp-server}
        case $service in
            mcp|mcp-server)
                log_info "Restarting MCP server..."
                kubectl rollout restart deployment/mcp-server-mcp-server -n $MCP_NAMESPACE
                kubectl rollout status deployment/mcp-server-mcp-server -n $MCP_NAMESPACE
                log_success "MCP server restarted successfully"
                ;;
            kafka)
                log_info "Restarting Kafka cluster..."
                kubectl annotate kafka kafka-mcp strimzi.io/manual-rolling-update=true -n $NAMESPACE
                kubectl wait kafka/kafka-mcp --for=condition=Ready --timeout=600s -n $NAMESPACE
                log_success "Kafka cluster restarted successfully"
                ;;
            schema-registry|sr)
                log_info "Restarting Schema Registry..."
                kubectl rollout restart deployment/schema-registry -n $NAMESPACE
                kubectl rollout status deployment/schema-registry -n $NAMESPACE
                log_success "Schema Registry restarted successfully"
                ;;
            akhq)
                log_info "Restarting AKHQ..."
                kubectl rollout restart deployment/akhq -n $NAMESPACE
                kubectl rollout status deployment/akhq -n $NAMESPACE
                log_success "AKHQ restarted successfully"
                ;;
            *)
                log_error "Unknown service: $service. Available: mcp-server, kafka, schema-registry, akhq"
                exit 1
                ;;
        esac
        ;;
            upgrade)
        service=${2:-all}
        case $service in
            mcp|mcp-server)
                log_info "Upgrading MCP server..."
                build_and_load_mcp_image
                helm upgrade mcp-server kafka-mcp/kafka-schema-registry-mcp \
                    --namespace $MCP_NAMESPACE \
                    --values "${CHARTS_DIR}/mcp-server-values.yaml"
                log_success "MCP server upgraded successfully"
                ;;
            kafka)
                log_info "Upgrading Kafka cluster..."
                helm upgrade kafka-cluster "${CHARTS_DIR}/kafka-cluster" -n $NAMESPACE
                log_success "Kafka cluster upgraded successfully"
                ;;
            schema-registry|sr)
                log_info "Upgrading Schema Registry..."
                helm upgrade schema-registry bitnami/schema-registry \
                    --namespace $NAMESPACE \
                    --values "${CHARTS_DIR}/schema-registry-values.yaml"
                log_success "Schema Registry upgraded successfully"
                ;;
            akhq)
                log_info "Upgrading AKHQ..."
                helm upgrade akhq akhq/akhq \
                    --namespace $NAMESPACE \
                    --values "${CHARTS_DIR}/akhq-values.yaml"
                log_success "AKHQ upgraded successfully"
                ;;
            all)
                log_info "Upgrading all services..."
                helm repo update
                build_and_load_mcp_image
                helm upgrade mcp-server kafka-mcp/kafka-schema-registry-mcp \
                    --namespace $MCP_NAMESPACE \
                    --values "${CHARTS_DIR}/mcp-server-values.yaml"
                helm upgrade kafka-cluster "${CHARTS_DIR}/kafka-cluster" -n $NAMESPACE
                helm upgrade schema-registry bitnami/schema-registry \
                    --namespace $NAMESPACE \
                    --values "${CHARTS_DIR}/schema-registry-values.yaml"
                helm upgrade akhq akhq/akhq \
                    --namespace $NAMESPACE \
                    --values "${CHARTS_DIR}/akhq-values.yaml"
                log_success "All services upgraded successfully"
                ;;
            *)
                log_error "Unknown service: $service. Available: mcp-server, kafka, schema-registry, akhq, all"
                exit 1
                ;;
        esac
        ;;
    helm-status)
        log_info "Helm release status:"
        helm list --all-namespaces
        ;;
    help|--help|-h)
        echo "Kafka Schema Registry MCP Stack - Kind Deployment Script (Helm-based)"
        echo
        echo "Usage: $0 [COMMAND] [SERVICE]"
        echo
        echo "Commands:"
        echo "  start         Start the complete stack (default)"
        echo "  stop          Stop and delete the Kind cluster"
        echo "  status        Show the status of all pods and Helm releases"
        echo "  logs          Show logs for a service [mcp-server|kafka|schema-registry|akhq]"
        echo "  restart       Restart a service [mcp-server|kafka|schema-registry|akhq]"
        echo "  upgrade       Upgrade a service [mcp-server|kafka|schema-registry|akhq|all]"
        echo "  helm-status   Show Helm release status"
        echo "  help          Show this help message"
        echo
        echo "Examples:"
        echo "  $0 start                    # Start the complete stack"
        echo "  $0 logs mcp-server         # View MCP server logs"
        echo "  $0 restart schema-registry # Restart Schema Registry"
        echo "  $0 upgrade all             # Upgrade all services"
        echo
        ;;
    *)
        log_error "Unknown command: $1"
        log_info "Use '$0 help' to see available commands"
        exit 1
        ;;
esac 