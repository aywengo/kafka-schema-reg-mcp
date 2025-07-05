# Kafka Schema Registry MCP Server Helm Chart

A Helm chart for deploying the Kafka Schema Registry MCP Server v1.8.0 with OAuth2 authentication support.

## Features

- ✅ **OAuth2 Authentication**: Secure deployment with Google OAuth2 or custom providers
- ✅ **Multi-Registry Support**: Connect to multiple Schema Registry instances
- ✅ **Existing Secret Support**: Use external secret management systems
- ✅ **High Availability**: Auto-scaling, pod disruption budgets, and anti-affinity
- ✅ **Security**: Network policies, security contexts, and RBAC
- ✅ **Monitoring**: Prometheus metrics and health checks
- ✅ **Ingress & TLS**: HTTPS termination with automatic certificates

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- cert-manager (for automatic TLS certificates)
- NGINX Ingress Controller (recommended)

## Installation

### Quick Start

```bash
# Add the chart repository (when published)
helm repo add kafka-mcp https://charts.example.com/kafka-mcp
helm repo update

# Install with default values
helm install my-mcp-server kafka-mcp/kafka-schema-registry-mcp
```

### From Source

```bash
# Clone the repository
git clone https://github.com/aywengo/kafka-schema-reg-mcp.git
cd kafka-schema-reg-mcp/helm

# Install with default values
helm install my-mcp-server . -n kafka-mcp --create-namespace

# Install with custom values
helm install my-mcp-server . -n kafka-mcp --create-namespace -f examples/values-production.yaml
```

## Configuration

### Basic Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `aywengo/kafka-schema-reg-mcp` |
| `image.tag` | Image tag | `1.8.0` |
| `image.pullPolicy` | Image pull policy | `Always` |

### OAuth2 Authentication

| Parameter | Description | Default |
|-----------|-------------|---------|
| `auth.enabled` | Enable OAuth2 authentication | `true` |
| `auth.oauth2.issuerUrl` | OAuth2 issuer URL | `https://accounts.google.com` |
| `auth.oauth2.validScopes` | Valid OAuth2 scopes | `openid,email,profile,https://www.googleapis.com/auth/userinfo.email` |
| `auth.oauth2.requiredScopes` | Required OAuth2 scopes | `openid,email` |

#### Using Existing Secrets for OAuth2

**Recommended for production:**

```yaml
auth:
  enabled: true
  existingSecret:
    enabled: true
    name: "google-oauth2-credentials"
    clientIdKey: "client-id"
    clientSecretKey: "client-secret"
  createSecret:
    enabled: false
```

Create the secret manually:

```bash
kubectl create secret generic google-oauth2-credentials \
  --from-literal=client-id="your-google-client-id.apps.googleusercontent.com" \
  --from-literal=client-secret="your-google-client-secret" \
  -n kafka-mcp
```

#### Creating Secrets from Values

**Not recommended for production:**

```yaml
auth:
  enabled: true
  createSecret:
    enabled: true
    clientId: "your-google-client-id.apps.googleusercontent.com"
    clientSecret: "your-google-client-secret"
  existingSecret:
    enabled: false
```

### Schema Registry Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `schemaRegistry.url` | Primary Schema Registry URL | `http://schema-registry:8081` |
| `schemaRegistry.user` | Schema Registry username | `""` |
| `schemaRegistry.password` | Schema Registry password | `""` |

#### Using Existing Secrets for Schema Registry

```yaml
schemaRegistry:
  url: "http://schema-registry:8081"
  existingSecret:
    enabled: true
    name: "schema-registry-credentials"
    userKey: "username"
    passwordKey: "password"
```

Create the secret:

```bash
kubectl create secret generic schema-registry-credentials \
  --from-literal=username="schema-user" \
  --from-literal=password="schema-password" \
  -n kafka-mcp
```

#### Multi-Registry Configuration

```yaml
schemaRegistry:
  multiRegistry:
    enabled: true
    registries:
      - name: "production"
        url: "http://prod-schema-registry:8081"
        viewonly: false
        user: "prod-user"
        password: "prod-pass"
      - name: "staging"
        url: "http://staging-schema-registry:8081"
        viewonly: true
        user: "staging-user"
        password: "staging-pass"
```

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname for ingress | `mcp-server.example.com` |
| `ingress.tls` | TLS configuration | See values.yaml |

Example ingress configuration:

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: mcp-schema-registry.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: mcp-schema-registry-tls
      hosts:
        - mcp-schema-registry.yourdomain.com
```

### Resource Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.requests.cpu` | CPU requests | `100m` |
| `resources.requests.memory` | Memory requests | `256Mi` |
| `resources.limits.cpu` | CPU limits | `500m` |
| `resources.limits.memory` | Memory limits | `512Mi` |

### Autoscaling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU % | `70` |
| `autoscaling.targetMemoryUtilizationPercentage` | Target Memory % | `80` |

## Example Deployments

### Production Deployment with Google OAuth2

```bash
# Create OAuth2 secret
kubectl create secret generic google-oauth2-credentials \
  --from-literal=client-id="123456789.apps.googleusercontent.com" \
  --from-literal=client-secret="your-secret" \
  -n kafka-mcp

# Create Schema Registry secret
kubectl create secret generic schema-registry-credentials \
  --from-literal=username="sr-user" \
  --from-literal=password="sr-password" \
  -n kafka-mcp

# Deploy with production values
helm install mcp-prod . -n kafka-mcp --create-namespace \
  -f examples/values-production.yaml \
  --set ingress.hosts[0].host=mcp.yourdomain.com \
  --set ingress.tls[0].hosts[0]=mcp.yourdomain.com
```

### Development Deployment

```bash
# Simple development deployment
helm install mcp-dev . -n kafka-mcp-dev --create-namespace \
  -f examples/values-development.yaml \
  --set schemaRegistry.url=http://localhost:8081
```

### Multi-Registry Production Deployment

```bash
helm install mcp-multi . -n kafka-mcp --create-namespace \
  --set auth.enabled=true \
  --set auth.existingSecret.enabled=true \
  --set auth.existingSecret.name=google-oauth2-credentials \
  --set schemaRegistry.multiRegistry.enabled=true \
  --set-json 'schemaRegistry.multiRegistry.registries=[
    {"name":"prod","url":"http://prod-sr:8081","viewonly":false},
    {"name":"dr","url":"http://dr-sr:8081","viewonly":true}
  ]'
```

## Web-Claude Integration

After deployment, configure Web-Claude to use your secured MCP server:

```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "mcp-client",
      "args": ["https://mcp-schema-registry.yourdomain.com"],
      "auth": {
        "type": "oauth2",
        "provider": "google",
        "client_id": "your-google-client-id.apps.googleusercontent.com",
        "scopes": ["openid", "email"]
      }
    }
  }
}
```

## Monitoring

The chart includes Prometheus monitoring support:

```yaml
monitoring:
  enabled: true
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
```

Monitor your deployment:

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=kafka-schema-registry-mcp -n kafka-mcp

# View logs
kubectl logs -l app.kubernetes.io/name=kafka-schema-registry-mcp -n kafka-mcp

# Check HPA status
kubectl get hpa -n kafka-mcp
```

## Security

### Network Policies

Network policies are enabled by default for production security:

```yaml
networkPolicy:
  enabled: true
  ingress:
    enabled: true
    from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
  egress:
    enabled: true
```

### Security Contexts

Secure defaults are applied:

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: false
  runAsNonRoot: true
  runAsUser: 1000
```

## Troubleshooting

### Common Issues

1. **OAuth2 Authentication Failing**
   ```bash
   # Check OAuth2 secret
   kubectl get secret google-oauth2-credentials -n kafka-mcp -o yaml
   
   # Check pod logs for auth errors
   kubectl logs -l app.kubernetes.io/name=kafka-schema-registry-mcp -n kafka-mcp | grep -i auth
   ```

2. **Schema Registry Connection Issues**
   ```bash
   # Test Schema Registry connectivity
   kubectl exec -it deploy/my-mcp-server -n kafka-mcp -- curl http://schema-registry:8081/subjects
   
   # Check network policies
   kubectl get networkpolicy -n kafka-mcp
   ```

3. **Certificate Issues**
   ```bash
   # Check cert-manager certificates
   kubectl get certificates -n kafka-mcp
   kubectl describe certificate mcp-schema-registry-tls -n kafka-mcp
   ```

## Upgrading

```bash
# Upgrade to new version
helm repo update
helm upgrade my-mcp-server kafka-mcp/kafka-schema-registry-mcp -n kafka-mcp

# Upgrade with new values
helm upgrade my-mcp-server . -n kafka-mcp -f values-new.yaml
```

## Uninstalling

```bash
# Remove the release
helm uninstall my-mcp-server -n kafka-mcp

# Remove the namespace (optional)
kubectl delete namespace kafka-mcp
```

## Support

- GitHub Issues: https://github.com/aywengo/kafka-schema-reg-mcp/issues
- Documentation: https://github.com/aywengo/kafka-schema-reg-mcp/docs
- MCP Tools Reference: https://github.com/aywengo/kafka-schema-reg-mcp/docs/mcp-tools-reference.md 