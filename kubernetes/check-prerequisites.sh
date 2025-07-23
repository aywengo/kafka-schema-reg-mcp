#!/bin/bash

# Prerequisites Checker for Kafka Schema Registry MCP Stack on Kind
# This script verifies that all required tools are installed and configured properly

set -euo pipefail

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

# Check if command exists and is executable
check_command() {
    local cmd=$1
    local min_version=${2:-""}
    local install_hint=${3:-""}
    
    if command -v "$cmd" &> /dev/null; then
        local version=$(eval "$cmd --version 2>/dev/null | head -n1 || echo 'Version unknown'")
        log_success "$cmd is installed: $version"
        return 0
    else
        log_error "$cmd is not installed or not in PATH"
        if [[ -n "$install_hint" ]]; then
            echo "  Install hint: $install_hint"
        fi
        return 1
    fi
}

# Check Docker daemon
check_docker_daemon() {
    if docker info &> /dev/null; then
        log_success "Docker daemon is running"
        
        # Check Docker memory limit
        local memory_limit=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
        if [[ $memory_limit -gt 4000000000 ]]; then
            log_success "Docker has sufficient memory: $(echo "scale=1; $memory_limit/1000000000" | bc 2>/dev/null || echo ">=4")GB"
        else
            log_warning "Docker memory limit might be too low for Kafka stack"
            echo "  Consider increasing Docker memory to at least 4GB in Docker Desktop settings"
        fi
        return 0
    else
        log_error "Docker daemon is not running"
        echo "  Please start Docker and try again"
        return 1
    fi
}

# Check Kind cluster availability
check_kind_setup() {
    if kind get clusters &> /dev/null; then
        local clusters=$(kind get clusters 2>/dev/null || echo "")
        if [[ -n "$clusters" ]]; then
            log_info "Existing Kind clusters found:"
            echo "$clusters" | sed 's/^/    /'
        else
            log_info "No existing Kind clusters found (this is fine)"
        fi
    fi
    
    # Check if kubectl can connect to any cluster
    if kubectl cluster-info &> /dev/null; then
        local current_context=$(kubectl config current-context 2>/dev/null || echo "unknown")
        log_info "kubectl is currently connected to cluster: $current_context"
    else
        log_info "kubectl is not connected to any cluster (this is fine, we'll create one)"
    fi
    
    return 0
}

# Check available system resources
check_system_resources() {
    log_info "Checking system resources..."
    
    # Check available memory
    if command -v free &> /dev/null; then
        local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
        if [[ $mem_gb -ge 4 ]]; then
            log_success "System has sufficient memory: ${mem_gb}GB"
        else
            log_warning "System memory might be limited: ${mem_gb}GB (recommended: 4GB+)"
        fi
    elif command -v vm_stat &> /dev/null; then
        # macOS
        local pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        local mem_gb=$((pages * 4096 / 1024 / 1024 / 1024))
        if [[ $mem_gb -ge 4 ]]; then
            log_success "System has sufficient memory: ~${mem_gb}GB available"
        else
            log_warning "Available memory might be limited (recommended: 4GB+)"
        fi
    else
        log_info "Cannot determine available memory (this is fine)"
    fi
    
    # Check available disk space
    local current_dir=$(pwd)
    local disk_space=$(df -h "$current_dir" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $disk_space =~ ^[0-9]+$ ]] && [[ $disk_space -ge 10 ]]; then
        log_success "Sufficient disk space available: ${disk_space}GB"
    else
        log_warning "Disk space might be limited (recommended: 10GB+)"
    fi
}

# Check network connectivity
check_network() {
    log_info "Checking network connectivity..."
    
    local urls=(
        "https://github.com"
        "https://docker.io"
        "https://strimzi.io"
        "https://quay.io"
    )
    
    local failed=0
    for url in "${urls[@]}"; do
        if curl -s --max-time 5 --head "$url" &> /dev/null; then
            log_success "Can reach $url"
        else
            log_warning "Cannot reach $url (this might cause issues during deployment)"
            ((failed++))
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        log_success "Network connectivity check passed"
    else
        log_warning "$failed network checks failed - deployment might be slower or fail"
    fi
}

# Main function
main() {
    echo "=================================================="
    echo "Kafka Schema Registry MCP Stack - Prerequisites Check"
    echo "=================================================="
    echo
    
    local errors=0
    local warnings=0
    
    log_info "Checking required tools..."
    echo
    
    # Check Docker
    if ! check_command "docker" "" "brew install docker (macOS) or https://docs.docker.com/get-docker/"; then
        ((errors++))
    else
        if ! check_docker_daemon; then
            ((errors++))
        fi
    fi
    echo
    
    # Check Kind
    if ! check_command "kind" "" "brew install kind (macOS) or https://kind.sigs.k8s.io/docs/user/quick-start/#installation"; then
        ((errors++))
    fi
    echo
    
    # Check kubectl
    if ! check_command "kubectl" "" "brew install kubectl (macOS) or https://kubernetes.io/docs/tasks/tools/"; then
        ((errors++))
    fi
    echo
    
    # Check Helm
    if ! check_command "helm" "" "brew install helm (macOS) or https://helm.sh/docs/intro/install/"; then
        ((errors++))
    fi
    echo
    
    # Check jq
    if ! check_command "jq" "" "brew install jq (macOS) or https://stedolan.github.io/jq/download/"; then
        ((errors++))
    fi
    echo
    
    # Optional tools
    log_info "Checking optional tools..."
    check_command "curl" "" "Usually pre-installed" || log_info "curl not found - some examples might not work"
    check_command "bc" "" "brew install bc (macOS)" || log_info "bc not found - memory calculations might not work"
    echo
    
    # Check Kind and kubectl setup
    log_info "Checking Kubernetes setup..."
    check_kind_setup
    echo
    
    # Check system resources
    check_system_resources
    echo
    
    # Check network
    check_network
    echo
    
    # Final summary
    echo "=================================================="
    if [[ $errors -eq 0 ]]; then
        log_success "Prerequisites check PASSED!"
        echo
        log_info "You're ready to deploy the Kafka Schema Registry MCP stack:"
        echo "  ./start-kafka-stack.sh"
    else
        log_error "Prerequisites check FAILED!"
        echo
        log_error "Please install the missing tools and try again."
        echo "  $errors required tools are missing"
    fi
    echo "=================================================="
    
    return $errors
}

# Run the check
main "$@" 