# Deployment Guide

This guide covers various deployment scenarios for the Kafka Schema Registry MCP Server v2.0.2 with **FastMCP 2.8.0+ framework**, **MCP 2025-06-18 specification compliance**, **Interactive Schema Migration**, and **Enhanced Security Features**, from local development to production environments.

## 🐳 Docker Deployment

### Quick Start with Pre-built Images (Recommended)

The fastest way to get started is using our pre-built DockerHub images:

```bash
# Option 1: Using Docker Compose (easiest)
git clone <repository-url>
cd kafka-schema-reg-mcp
docker-compose up -d

# Option 2: Direct Docker run with stable tag
docker run -p 38000:8000 aywengo/kafka-schema-reg-mcp:stable

# Option 3: With external Schema Registry
docker run -p 38000:8000 \
  -e SCHEMA_REGISTRY_URL=http://your-schema-registry:8081 \
  aywengo/kafka-schema-reg-mcp:stable

# Option 4: Multi-Registry Configuration
docker run -p 38000:8000 \
  -e SCHEMA_REGISTRY_NAME_1=production \
  -e SCHEMA_REGISTRY_URL_1=http://prod-registry:8081 \
  -e SCHEMA_REGISTRY_NAME_2=staging \
  -e SCHEMA_REGISTRY_URL_2=http://stage-registry:8081 \
  aywengo/kafka-schema-reg-mcp:stable
```

**Available DockerHub Tags:**
- `aywengo/kafka-schema-reg-mcp:stable` - **Current stable release (v2.0.2) - Recommended**
- `aywengo/kafka-schema-reg-mcp:latest` - Latest build (may be pre-release)
- `aywengo/kafka-schema-reg-mcp:2.0.2` - Specific stable version
- `aywengo/kafka-schema-reg-mcp:2.0.1` - Previous stable version
- `aywengo/kafka-schema-reg-mcp:2.0.0` - FastMCP 2.8.0+ initial release
- **Multi-Platform Support**: Automatically detects `linux/amd64` or `linux/arm64`

> **💡 Recommendation**: Use `:stable` tag for production deployments to automatically receive stable updates.

### Local Development

For development or custom builds:

```bash
# Clone the repository
git clone <repository-url>
cd kafka-schema-reg-mcp

# Build and start all services
docker-compose up -d --build

# Verify deployment
curl http://localhost:38000/
```

**Services included:**
- **Kafka** (KRaft mode): `localhost:39092`
- **Schema Registry**: `localhost:38081`
- **MCP Server**: `localhost:38000`
- **AKHQ UI**: `localhost:38080`

### Production Docker Deployment

For production deployments, create a production-specific Docker Compose configuration:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: false
    volumes:
      - kafka_data:/var/lib/kafka/data
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  schema-registry:
    image: confluentinc/cp-schema-registry:latest
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
      SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR: 3
    depends_on:
      - kafka
    deploy:
      replicas: 2

  mcp-server:
    image: aywengo/kafka-schema-reg-mcp:stable
    environment:
      # Single Registry Configuration
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
      SCHEMA_REGISTRY_USER: ${SCHEMA_REGISTRY_USER:-}
      SCHEMA_REGISTRY_PASSWORD: ${SCHEMA_REGISTRY_PASSWORD:-}
      
      # Multi-Registry Configuration (v1.5.0+)
      SCHEMA_REGISTRY_NAME_1: "production"
      SCHEMA_REGISTRY_URL_1: "http://schema-registry:8081"
      SCHEMA_REGISTRY_USER_1: "${PROD_REGISTRY_USER}"
      SCHEMA_REGISTRY_PASSWORD_1: "${PROD_REGISTRY_PASSWORD}"
      READONLY_1: "false"
      
      SCHEMA_REGISTRY_NAME_2: "backup"
      SCHEMA_REGISTRY_URL_2: "http://backup-registry:8081"
      SCHEMA_REGISTRY_USER_2: "${BACKUP_REGISTRY_USER}"
      SCHEMA_REGISTRY_PASSWORD_2: "${BACKUP_REGISTRY_PASSWORD}"
      READONLY_2: "true"
      
      # Security Configuration (v2.0.x)
      ENABLE_AUTH: "${ENABLE_AUTH:-false}"
      AUTH_ISSUER_URL: "${AUTH_ISSUER_URL:-}"
      AUTH_AUDIENCE: "${AUTH_AUDIENCE:-}"
      
      # SSL/TLS Security Configuration (v2.0.0+)
      ENFORCE_SSL_TLS_VERIFICATION: "${ENFORCE_SSL_TLS_VERIFICATION:-true}"
      CUSTOM_CA_BUNDLE_PATH: "${CUSTOM_CA_BUNDLE_PATH:-}"
      
      PYTHONUNBUFFERED: 1
    ports:
      - "38000:8000"
    depends_on:
      - schema-registry
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]

volumes:
  kafka_data:
    driver: local
```

---

## ☸️ Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kafka-schema-registry
  labels:
    name: kafka-schema-registry

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-server-config
  namespace: kafka-schema-registry
data:
  SCHEMA_REGISTRY_URL: "http://schema-registry-service:8081"
  PYTHONUNBUFFERED: "1"
  
  # Multi-Registry Configuration (v1.5.0+)
  SCHEMA_REGISTRY_NAME_1: "default"
  SCHEMA_REGISTRY_URL_1: "http://schema-registry-service:8081"
  READONLY_1: "false"
  
  SCHEMA_REGISTRY_NAME_2: "backup"
  SCHEMA_REGISTRY_URL_2: "http://backup-registry-service:8081"
  READONLY_2: "true"
  
  # SSL/TLS Security Configuration (v2.0.0+)
  ENFORCE_SSL_TLS_VERIFICATION: "true"
  CUSTOM_CA_BUNDLE_PATH: ""
```

### MCP Server Deployment (v2.0.2)

```yaml
# k8s/mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: kafka-schema-registry
  labels:
    app: mcp-server
    version: "2.0.2"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
        version: "2.0.2"
    spec:
      containers:
      - name: mcp-server
        image: aywengo/kafka-schema-reg-mcp:stable
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: mcp-server-config
        env:
        # Backend Schema Registry Authentication
        - name: SCHEMA_REGISTRY_USER
          valueFrom:
            secretKeyRef:
              name: schema-registry-auth
              key: username
              optional: true
        - name: SCHEMA_REGISTRY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: schema-registry-auth
              key: password
              optional: true
        
        # MCP Server Authentication (v2.0.x)
        - name: ENABLE_AUTH
          valueFrom:
            configMapRef:
              name: mcp-server-config
              key: ENABLE_AUTH
              optional: true
        - name: AUTH_ISSUER_URL
          valueFrom:
            secretKeyRef:
              name: oauth-config
              key: issuer-url
              optional: true
        - name: AUTH_AUDIENCE
          valueFrom:
            secretKeyRef:
              name: oauth-config
              key: audience
              optional: true
        
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
  namespace: kafka-schema-registry
spec:
  selector:
    app: mcp-server
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-server-ingress
  namespace: kafka-schema-registry
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - schema-mcp.your-domain.com
    secretName: mcp-server-tls
  rules:
  - host: schema-mcp.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server-service
            port:
              number: 8000
```

---

## 🔧 Configuration Options

### Environment Variables (v2.0.2)

#### Core Configuration
| Variable | Description | Default | Since |
|----------|-------------|---------|-------|
| `SCHEMA_REGISTRY_URL` | Primary Schema Registry URL | `http://localhost:8081` | v1.0.0 |
| `SCHEMA_REGISTRY_USER` | Username for backend Schema Registry | *(empty)* | v1.0.0 |
| `SCHEMA_REGISTRY_PASSWORD` | Password for backend Schema Registry | *(empty)* | v1.0.0 |
| `READONLY` | Enable read-only mode | `false` | v1.3.0 |

#### Multi-Registry Configuration (v1.5.0+)
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCHEMA_REGISTRY_NAME_X` | Registry alias (X=1-8) | *(required)* | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint (X=1-8) | *(required)* | `http://prod-registry:8081` |
| `SCHEMA_REGISTRY_USER_X` | Username (X=1-8) | *(empty)* | `prod-user` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password (X=1-8) | *(empty)* | `prod-password` |
| `READONLY_X` | Per-registry readonly (X=1-8) | `false` | `true` |

#### Authentication & Authorization (v2.0.x)
| Variable | Description | Default | Applies To |
|----------|-------------|---------|------------|
| `ENABLE_AUTH` | Enable OAuth 2.1 authentication | `false` | MCP Server (frontend) |
| `AUTH_ISSUER_URL` | OAuth 2.1 issuer URL (automatic discovery) | *(empty)* | MCP Server (frontend) |
| `AUTH_AUDIENCE` | OAuth client ID or API identifier | *(empty)* | MCP Server (frontend) |
| `AUTH_VALID_SCOPES` | Comma-separated list of valid scopes | `read,write,admin` | MCP Server (frontend) |
| `AUTH_DEFAULT_SCOPES` | Comma-separated list of default scopes | `read` | MCP Server (frontend) |
| `AUTH_REQUIRED_SCOPES` | Comma-separated list of required scopes | `read` | MCP Server (frontend) |

### OAuth 2.1 Configuration Examples

#### Universal Provider Setup (v2.0.x)
```bash
# Enable OAuth 2.1 authentication
export ENABLE_AUTH=true

# Works with ANY OAuth 2.1 compliant provider
export AUTH_ISSUER_URL="https://your-oauth-provider.com"
export AUTH_AUDIENCE="your-client-id-or-api-identifier"
```

#### Provider-Specific Examples

**Azure AD:**
```bash
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0"
export AUTH_AUDIENCE="your-azure-client-id"
```

**Google OAuth 2.0:**
```bash
export AUTH_ISSUER_URL="https://accounts.google.com"
export AUTH_AUDIENCE="your-client-id.apps.googleusercontent.com"
```

**Keycloak:**
```bash
export AUTH_ISSUER_URL="https://your-keycloak-server.com/realms/your-realm"
export AUTH_AUDIENCE="your-keycloak-client-id"
```

### Multi-Registry Configuration Example

```bash
# Development Registry
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-registry:8081"
export SCHEMA_REGISTRY_USER_1="dev-user"
export SCHEMA_REGISTRY_PASSWORD_1="dev-pass"
export READONLY_1="false"

# Production Registry (with safety)
export SCHEMA_REGISTRY_NAME_2="production"
export SCHEMA_REGISTRY_URL_2="https://prod-registry:8081"
export SCHEMA_REGISTRY_USER_2="prod-user"
export SCHEMA_REGISTRY_PASSWORD_2="prod-pass"
export READONLY_2="true"  # Production safety

# Staging Registry
export SCHEMA_REGISTRY_NAME_3="staging"
export SCHEMA_REGISTRY_URL_3="https://staging-registry:8081"
export READONLY_3="false"
```

---

## 📊 Resource Requirements

### Recommended Resources (v2.0.2)

| Component | CPU | Memory | Storage | Use Case |
|-----------|-----|--------|---------|----------|
| **MCP Server (Small)** | 0.5 | 512MB | - | <100 schemas, light usage |
| **MCP Server (Medium)** | 1.0 | 1GB | - | 100-1000 schemas, moderate operations |
| **MCP Server (Large)** | 2.0 | 2GB | 10GB | >1000 schemas, heavy migrations |
| **Schema Registry** | 0.5 | 1GB | 20GB | Per instance |
| **Kafka Broker** | 1.0 | 2GB | 100GB | Per broker, 3 minimum |

### Performance Considerations (v2.0.2)

The v2.0.2 release includes significant performance improvements:
- **Code Optimization**: 2,442 lines of redundant code removed
- **Memory Efficiency**: Enhanced resource management
- **Local Schema Validation**: Zero network dependencies for validation
- **Secure Logging**: No performance impact from credential masking

---

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Enable authentication on Schema Registry (backend)
- [ ] Enable MCP Server authentication with `ENABLE_AUTH=true` (frontend)
- [ ] Use HTTPS/TLS for all connections
- [ ] Set `READONLY=true` for production MCP instances
- [ ] Implement network policies in Kubernetes
- [ ] Use secrets management for credentials
- [ ] Enable audit logging
- [ ] Regular security scanning of images
- [ ] Implement rate limiting on ingress

### 🔑 Authentication Layers (v2.0.x)

**Two distinct authentication layers:**

1. **Schema Registry Authentication (Backend)**
   - Controls how the MCP server connects to Kafka Schema Registry instances
   - Set via `SCHEMA_REGISTRY_USER`, `SCHEMA_REGISTRY_PASSWORD`
   - These credentials are NOT used to authenticate users of the MCP server

2. **MCP Server Authentication (Frontend)**
   - Controls who can access the MCP server and its tools
   - Enable with `ENABLE_AUTH=true` and configure OAuth 2.1 settings
   - Optional - defaults to open access if not configured

### Security Features (v2.0.2)

- **🔒 Credential Protection**: Secure header management prevents credential exposure
- **📝 Secure Logging**: Automatic masking of authorization headers and sensitive data
- **🛡️ Safe Object Representations**: Credentials masked in `__repr__` and `__str__` methods
- **🔐 Dynamic Authentication**: Headers generated fresh on each access

### Example Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-netpol
  namespace: kafka-schema-registry
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: allowed-namespace
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: schema-registry
    ports:
    - protocol: TCP
      port: 8081
```

---

## 📈 Monitoring & Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:38000/

# OAuth discovery endpoints (v2.0.x)
curl http://localhost:38000/.well-known/oauth-authorization-server
curl http://localhost:38000/.well-known/oauth-protected-resource

# Test MCP compliance (v2.0.x)
curl http://localhost:38000/mcp/compliance-status
```

### Docker Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

## 🔄 Upgrade Guide

### Upgrading to v2.0.2

1. **Review Breaking Changes**: None between v2.0.1 and v2.0.2
2. **Update Image Tags**: Change to `aywengo/kafka-schema-reg-mcp:stable`
3. **Test New Features**: Interactive migration and enhanced security
4. **Verify Performance**: Check for improvements from code optimization

```bash
# Rolling update in Kubernetes
kubectl set image deployment/mcp-server \
  mcp-server=aywengo/kafka-schema-reg-mcp:stable \
  -n kafka-schema-registry

# Monitor rollout
kubectl rollout status deployment/mcp-server -n kafka-schema-registry
```

### Upgrading from v1.x to v2.x

See the comprehensive [v2.x Migration Guide](v2-migration-guide.md) for detailed instructions.

---

## 🤖 Claude Desktop Integration

### Docker-based Claude Desktop Configuration

```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_URL",
        "-e", "SCHEMA_REGISTRY_USER",
        "-e", "SCHEMA_REGISTRY_PASSWORD",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://localhost:8081",
        "SCHEMA_REGISTRY_USER": "",
        "SCHEMA_REGISTRY_PASSWORD": ""
      }
    }
  }
}
```

### Multi-Registry Claude Desktop Configuration

```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_NAME_1",
        "-e", "SCHEMA_REGISTRY_URL_1",
        "-e", "SCHEMA_REGISTRY_NAME_2", 
        "-e", "SCHEMA_REGISTRY_URL_2",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://localhost:8081",
        "SCHEMA_REGISTRY_NAME_2": "production",
        "SCHEMA_REGISTRY_URL_2": "https://prod-registry.company.com:8081"
      }
    }
  }
}
```

### Testing Claude Desktop Integration

```bash
# Test Claude Desktop integration
"Test the connection to all Schema Registry instances"
"Show me the interactive migration features"
"List all available OAuth scopes and permissions"
```

---

## 🚀 CI/CD & Automated Publishing

### GitHub Actions Workflows

The project includes production-ready workflows:

- **Build Workflow**: Multi-platform builds with security scanning
- **Publish Workflow**: Automated DockerHub publishing on version tags
- **Multi-Platform Support**: AMD64 + ARM64 architectures
- **Security Scanning**: Trivy vulnerability analysis

### Setting Up CI/CD

1. **Configure DockerHub Secrets**:
   ```bash
   DOCKERHUB_USERNAME=your-username
   DOCKERHUB_TOKEN=your-access-token
   ```

2. **Create Version Tag**:
   ```bash
   git tag v2.0.3
   git push origin v2.0.3
   ```

3. **Automated Process**: GitHub Actions handles building, testing, and publishing

---

This deployment guide provides comprehensive instructions for deploying the Kafka Schema Registry MCP Server v2.0.2 with FastMCP 2.8.0+ framework, enhanced security features, and interactive migration capabilities across various production environments.
