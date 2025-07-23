# Kubernetes Deployment for Kafka Schema Registry MCP Stack (Helm-based)

This directory contains Helm charts and scripts to deploy the complete Kafka Schema Registry MCP stack on a local Kubernetes cluster using Kind (Kubernetes in Docker).

## Overview

The deployment uses production-ready Helm charts and includes:

- **Strimzi Kafka Operator** - For managing Kafka clusters
- **Kafka Cluster** - Single-node Kafka deployed via Strimzi
- **Bitnami Schema Registry** - Confluent Schema Registry from Bitnami Helm chart
- **AKHQ** - Web UI for Kafka cluster and schema management from official AKHQ Helm chart
- **MCP Server** - Your Kafka Schema Registry MCP server using a custom Helm chart

## Prerequisites

Before running the deployment script, ensure you have the following tools installed:

### Required Tools

1. **Docker** - For building images and running Kind
   ```bash
   # macOS
   brew install docker
   
   # Or download from https://docs.docker.com/get-docker/
   ```

2. **Kind** - Kubernetes in Docker
   ```bash
   # macOS
   brew install kind
   
   # Linux
   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
   chmod +x ./kind
   sudo mv ./kind /usr/local/bin/kind
   ```

3. **kubectl** - Kubernetes CLI
   ```bash
   # macOS
   brew install kubectl
   
   # Linux
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

4. **Helm** - Kubernetes package manager
   ```bash
   # macOS
   brew install helm
   
   # Linux
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   ```

5. **jq** - JSON processor (for status checking)
   ```bash
   # macOS
   brew install jq
   
   # Linux
   sudo apt-get install jq  # Debian/Ubuntu
   sudo yum install jq      # CentOS/RHEL
   ```

### Verify Installation

```bash
docker --version
kind --version
kubectl version --client
helm version
jq --version
```

## Quick Start

### 1. Check Prerequisites

```bash
cd kubernetes
./check-prerequisites.sh
```

### 2. Start the Complete Stack

```bash
./start-kafka-stack.sh
```

This command will:
- Create a Kind cluster named `kafka-mcp-cluster`
- Add required Helm repositories (Strimzi, AKHQ, Bitnami, Kafka MCP)
- Install Strimzi Kafka operator via Helm
- Deploy a single-node Kafka cluster using Strimzi
- Deploy Schema Registry using Bitnami Helm chart
- Deploy AKHQ using official AKHQ Helm chart
- Build and deploy your MCP server using a custom Helm chart

The deployment takes approximately 5-10 minutes depending on your internet connection and system resources.

### 3. Access the Services

Once deployment is complete, you can access the services at:

- **Kafka Bootstrap Server**: `localhost:39092`
- **Schema Registry**: http://localhost:38081
- **AKHQ (Kafka UI)**: http://localhost:38080
- **MCP Server**: http://localhost:38000

### 4. Test the Deployment

```bash
# Test Schema Registry
curl http://localhost:38081/subjects

# Test MCP Server (if it has a health endpoint)
curl http://localhost:38000/health

# Check all pods are running
kubectl get pods --all-namespaces

# Check Helm releases
helm list --all-namespaces
```

## Script Commands

The `start-kafka-stack.sh` script supports several commands:

### Start the Stack
```bash
./start-kafka-stack.sh start
# or simply
./start-kafka-stack.sh
```

### Stop the Stack
```bash
./start-kafka-stack.sh stop
```

### Check Status
```bash
./start-kafka-stack.sh status
```

### View Logs
```bash
# MCP Server logs
./start-kafka-stack.sh logs mcp-server

# Kafka logs
./start-kafka-stack.sh logs kafka

# Schema Registry logs
./start-kafka-stack.sh logs schema-registry

# AKHQ logs
./start-kafka-stack.sh logs akhq
```

### Restart Services
```bash
# Restart MCP server
./start-kafka-stack.sh restart mcp-server

# Restart Kafka cluster
./start-kafka-stack.sh restart kafka

# Restart Schema Registry
./start-kafka-stack.sh restart schema-registry

# Restart AKHQ
./start-kafka-stack.sh restart akhq
```

### Upgrade Services
```bash
# Upgrade MCP server (rebuilds image)
./start-kafka-stack.sh upgrade mcp-server

# Upgrade Kafka cluster
./start-kafka-stack.sh upgrade kafka

# Upgrade Schema Registry
./start-kafka-stack.sh upgrade schema-registry

# Upgrade AKHQ
./start-kafka-stack.sh upgrade akhq

# Upgrade all services
./start-kafka-stack.sh upgrade all
```

### Check Helm Status
```bash
./start-kafka-stack.sh helm-status
```

### Help
```bash
./start-kafka-stack.sh help
```

## Helm Charts Used

### External Charts

1. **Strimzi Kafka Operator**
   - Repository: https://strimzi.io/charts/
   - Chart: `strimzi/strimzi-kafka-operator`
   - Values: `charts/strimzi-values.yaml`

2. **AKHQ**
   - Repository: https://akhq.io/
   - Chart: `akhq/akhq`
   - Values: `charts/akhq-values.yaml`

3. **Bitnami Schema Registry**
   - Repository: https://charts.bitnami.com/bitnami
   - Chart: `bitnami/schema-registry`
   - Values: `charts/schema-registry-values.yaml`

4. **MCP Server**
   - Repository: https://aywengo.github.io/kafka-schema-reg-mcp
   - Chart: `kafka-mcp/kafka-schema-registry-mcp`
   - Values: `charts/mcp-server-values.yaml`

### Local Charts

5. **Kafka Cluster**
   - Location: `charts/kafka-cluster/`
   - Custom Helm chart for Strimzi Kafka cluster

## Architecture

### Cluster Layout

```
Kind Cluster: kafka-mcp-cluster
├── Namespace: kafka-system
│   ├── Strimzi Operator (Helm: strimzi-kafka-operator)
│   ├── Kafka Cluster (Helm: kafka-cluster)
│   ├── Schema Registry (Helm: schema-registry)
│   └── AKHQ UI (Helm: akhq)
└── Namespace: mcp-system
    └── MCP Server (Helm: kafka-mcp/kafka-schema-registry-mcp)
```

### Port Mappings

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| Kafka | 9092 | 39092 | Kafka Bootstrap Server |
| Schema Registry | 8081 | 38081 | Schema Registry API |
| AKHQ | 8080 | 38080 | Kafka Web UI |
| MCP Server | 8000 | 38000 | MCP Server API |

### Networking

- Services within the cluster communicate using Kubernetes DNS names
- External access is provided through NodePort services
- Kind cluster exposes services on localhost ports

## Configuration

### Customizing Helm Values

You can customize the deployment by editing the values files in the `charts/` directory:

- `charts/strimzi-values.yaml` - Strimzi operator configuration
- `charts/kafka-cluster/values.yaml` - Kafka cluster configuration
- `charts/akhq-values.yaml` - AKHQ web UI configuration
- `charts/schema-registry-values.yaml` - Bitnami Schema Registry configuration
- `charts/mcp-server-values.yaml` - Published MCP server configuration

### Environment Variables

The MCP Server is configured with these environment variables in `charts/mcp-server-values.yaml`:

```yaml
env:
- name: SCHEMA_REGISTRY_URL
  value: "http://schema-registry.kafka-system.svc.cluster.local:8081"
- name: SCHEMA_REGISTRY_USER
  value: ""
- name: SCHEMA_REGISTRY_PASSWORD
  value: ""
```

### Kafka Configuration

The Kafka cluster configuration is in `charts/kafka-cluster.yaml`:
- Single replica for all topics (development setup)
- Auto-topic creation enabled
- Minimal resource requirements
- No TLS/authentication
- Metrics enabled for monitoring

### Storage

- Kafka uses 10Gi persistent volumes
- ZooKeeper uses 5Gi persistent volumes
- Volumes are retained when pods restart but deleted when cluster is destroyed

## Troubleshooting

### Common Issues

1. **Kind cluster creation fails**
   ```bash
   # Check Docker is running
   docker ps
   
   # Check if cluster name conflicts
   kind get clusters
   
   # Delete existing cluster
   kind delete cluster --name kafka-mcp-cluster
   ```

2. **Helm repository issues**
   ```bash
   # Update repositories
   helm repo update
   
   # List repositories
   helm repo list
   
   # Add missing repository
   helm repo add bitnami https://charts.bitnami.com/bitnami
   ```

3. **Pods stuck in Pending state**
   ```bash
   # Check node resources
   kubectl top nodes
   
   # Check pod events
   kubectl describe pod <pod-name> -n <namespace>
   
   # Check Helm release status
   helm status <release-name> -n <namespace>
   ```

4. **Schema Registry connection issues**
   ```bash
   # Check Kafka is ready first
   kubectl get kafka kafka-mcp -n kafka-system
   
   # Check Schema Registry logs
   kubectl logs deployment/schema-registry -n kafka-system
   
   # Check Helm release
   helm status schema-registry -n kafka-system
   ```

5. **MCP Server build fails**
   ```bash
   # Check Docker daemon is running
   docker info
   
   # Try building manually
   cd ..
   docker build -t kafka-schema-reg-mcp:local .
   
   # Load into Kind
   kind load docker-image kafka-schema-reg-mcp:local --name kafka-mcp-cluster
   ```

### Useful Debugging Commands

```bash
# Get all resources in all namespaces
kubectl get all --all-namespaces

# Check Helm releases
helm list --all-namespaces

# Get Helm release details
helm status <release-name> -n <namespace>

# Check Helm release history
helm history <release-name> -n <namespace>

# Describe a specific pod
kubectl describe pod <pod-name> -n <namespace>

# Get events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'

# Check node status
kubectl get nodes -o wide

# Check persistent volumes
kubectl get pv

# Check service endpoints
kubectl get endpoints --all-namespaces
```

### Resource Requirements

Minimum system requirements:
- 4GB RAM
- 2 CPU cores
- 10GB available disk space
- Docker with at least 4GB memory limit

## Customization

### Modifying Kafka Configuration

To change Kafka settings, edit the values file in `charts/kafka-cluster/values.yaml`:

```yaml
kafka:
  config:
    # Add your custom Kafka configurations here
    log.retention.hours: 168
    num.partitions: 3
```

### Adding Additional Services

To add more services to the stack:

1. Add the Helm repository in the `add_helm_repositories()` function
2. Create a values file in the `charts/` directory
3. Add a deployment function similar to the existing ones
4. Call the function in the `main()` deployment sequence
5. Add appropriate cleanup in `uninstall_helm_releases()`

### Changing Resource Limits

To modify resource requests/limits, edit the values files in the `charts/` directory:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

### Using Different Chart Versions

You can pin specific chart versions by modifying the Helm install commands:

```bash
helm upgrade --install schema-registry bitnami/schema-registry \
    --version 7.5.0 \
    --namespace $NAMESPACE \
    --values "${CHARTS_DIR}/schema-registry-values.yaml"
```

## Production Considerations

This setup is designed for **development and testing only**. For production use, consider:

### Security
- Enable TLS/SSL for all communications
- Configure authentication and authorization
- Use Kubernetes secrets for sensitive configuration
- Enable network policies
- Use Pod Security Standards

### High Availability
- Use multiple Kafka brokers
- Deploy across multiple nodes/zones
- Configure proper replication factors
- Use external storage for persistence
- Implement backup strategies

### Monitoring
- Enable Prometheus metrics collection
- Deploy Grafana for visualization
- Configure proper logging aggregation
- Set up alerting rules
- Monitor resource usage

### Scaling
- Use Horizontal Pod Autoscaler
- Configure resource requests/limits properly
- Use dedicated node pools
- Consider using managed Kubernetes services
- Implement load balancing

### Helm Best Practices
- Use Helm values files for environment-specific configuration
- Implement proper release management
- Use Helm hooks for complex deployment scenarios
- Implement rollback strategies
- Use Helm secrets for sensitive data

## Development Workflow

### Making Changes to MCP Server

1. Make your changes to the MCP server code
2. Upgrade the deployment:
   ```bash
   ./start-kafka-stack.sh upgrade mcp-server
   ```

### Updating Helm Charts

1. Modify the values files in `charts/`
2. Upgrade specific services:
   ```bash
   ./start-kafka-stack.sh upgrade schema-registry
   ./start-kafka-stack.sh upgrade akhq
   ```

### Testing Schema Registry Changes

1. Use AKHQ web interface at http://localhost:38080
2. Or use curl commands:
   ```bash
   # List subjects
   curl http://localhost:38081/subjects
   
   # Register a schema
   curl -X POST http://localhost:38081/subjects/test-subject/versions \
     -H "Content-Type: application/vnd.schemaregistry.v1+json" \
     -d '{"schema": "{\"type\":\"string\"}"}'
   ```

### Cleaning Up

```bash
# Stop and delete the entire cluster
./start-kafka-stack.sh stop

# Or manually
kind delete cluster --name kafka-mcp-cluster
```

## Directory Structure

```
kubernetes/
├── charts/
│   ├── strimzi-values.yaml          # Strimzi operator configuration
│   ├── kafka-cluster/               # Custom Kafka cluster Helm chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── kafka.yaml
│   │       ├── configmap.yaml
│   │       └── _helpers.tpl
│   ├── akhq-values.yaml             # AKHQ configuration
│   ├── schema-registry-values.yaml  # Schema Registry configuration
│   └── mcp-server-values.yaml       # Published MCP server configuration
├── start-kafka-stack.sh            # Main deployment script
├── check-prerequisites.sh          # Prerequisites checker
└── README.md                       # This file
```

## Contributing

When making changes to the Kubernetes deployment:

1. Test changes on a clean cluster
2. Update this README if adding new features
3. Ensure backwards compatibility
4. Add appropriate error handling
5. Follow Helm best practices
6. Update values files with proper documentation

## Support

For issues with:
- **Kind/Kubernetes**: Check [Kind documentation](https://kind.sigs.k8s.io/)
- **Strimzi/Kafka**: Check [Strimzi documentation](https://strimzi.io/)
- **Helm**: Check [Helm documentation](https://helm.sh/docs/)
- **AKHQ**: Check [AKHQ documentation](https://akhq.io/)
- **Bitnami Charts**: Check [Bitnami documentation](https://github.com/bitnami/charts)
- **MCP Server**: Check the main project README and issues

## License

This deployment configuration follows the same license as the main project. 