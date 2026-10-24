# Deployment Guide

This guide covers deployment scenarios for the Kafka Schema Registry MCP Server **3.0.0** with **FastMCP 4.1+**, **MCP 2026-07-28**, the three runtime editions, MRTR workflows and the 3.0 security model, from local development to production environments.

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
- `aywengo/kafka-schema-reg-mcp:stable` - Current stable release, `viewer` edition
- `aywengo/kafka-schema-reg-mcp:stable-editor` - Stable `editor` edition
- `aywengo/kafka-schema-reg-mcp:stable-admin` - Stable `admin` edition
- `aywengo/kafka-schema-reg-mcp:3.0.0` - Pinned 3.0.0 `viewer` image
- `aywengo/kafka-schema-reg-mcp:3.0.0-viewer` - Explicit 3.0.0 `viewer` image
- `aywengo/kafka-schema-reg-mcp:3.0.0-editor` - Pinned 3.0.0 `editor` image
- `aywengo/kafka-schema-reg-mcp:3.0.0-admin` - Pinned 3.0.0 `admin` image
- `aywengo/kafka-schema-reg-mcp:latest` - Latest release, `viewer` edition
- **Multi-Platform Support**: `linux/amd64` and `linux/arm64`

> **💡 Recommendation**: Use `:stable-admin`, `:stable-editor` or `:stable` deliberately. Plain tags are `viewer`; writes and administrative tools require an `editor` or `admin` image or `MCP_EDITION`.

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
      VIEWONLY_1: "false"

      SCHEMA_REGISTRY_NAME_2: "backup"
      SCHEMA_REGISTRY_URL_2: "http://backup-registry:8081"
      SCHEMA_REGISTRY_USER_2: "${BACKUP_REGISTRY_USER}"
      SCHEMA_REGISTRY_PASSWORD_2: "${BACKUP_REGISTRY_PASSWORD}"
      VIEWONLY_2: "true"

      # Security Configuration
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
  VIEWONLY_1: "false"

  SCHEMA_REGISTRY_NAME_2: "backup"
  SCHEMA_REGISTRY_URL_2: "http://backup-registry-service:8081"
  VIEWONLY_2: "true"

  # SSL/TLS Security Configuration (v2.0.0+)
  ENFORCE_SSL_TLS_VERIFICATION: "true"
  CUSTOM_CA_BUNDLE_PATH: ""
```

### MCP Server Deployment

```yaml
# k8s/mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: kafka-schema-registry
  labels:
    app: mcp-server
    version: "3.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
        version: "3.0.0"
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

        # MCP Server Authentication
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

### Environment Variables

#### Core Configuration
| Variable | Description | Default | Since |
|----------|-------------|---------|-------|
| `SCHEMA_REGISTRY_URL` | Primary Schema Registry URL | `http://localhost:8081` | v1.0.0 |
| `SCHEMA_REGISTRY_USER` | Username for backend Schema Registry | *(empty)* | v1.0.0 |
| `SCHEMA_REGISTRY_PASSWORD` | Password for backend Schema Registry | *(empty)* | v1.0.0 |
| `VIEWONLY` | Enable view-only mode | `false` | v1.3.0 |
| `MCP_EDITION` | `viewer`, `editor` or `admin` tool surface | `viewer` | v3.0.0 |
| `MCP_EDITION_DEFAULT` | Image-level fallback when `MCP_EDITION` is unset | `viewer` | v3.0.0 |
| `REQUEST_STATE_KEY` | Signing key for resumable MRTR state (32+ bytes) | *(generated by Helm)* | v3.0.0 |
| `TASKS_BACKEND` | `memory` or `redis` for long-running tasks | `memory` | v3.0.0 |
| `TASKS_BACKEND_URL` | Redis/Valkey URL when `TASKS_BACKEND=redis` | *(empty)* | v3.0.0 |

#### Multi-Registry Configuration (v1.5.0+)
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCHEMA_REGISTRY_NAME_X` | Registry alias (X=1-8) | *(required)* | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint (X=1-8) | *(required)* | `http://prod-registry:8081` |
| `SCHEMA_REGISTRY_USER_X` | Username (X=1-8) | *(empty)* | `prod-user` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password (X=1-8) | *(empty)* | `prod-password` |
| `VIEWONLY_X` | Per-registry viewonly (X=1-8) | `false` | `true` |

#### Request-state key rotation (v3.0.0+)

MRTR suspensions are signed with `REQUEST_STATE_KEY`. Helm generates a
32-byte Secret on first install and reuses it on upgrade through `lookup`.
Rotate it deliberately:

1. Generate a new value: `openssl rand -base64 48`.
2. Update the Secret or `requestStateKey.value` and run `helm upgrade`.
3. In-flight suspensions created with the old key fail once; restart them from
   the client. Completed workflows are unaffected.
4. Keep the old key available for one deployment cycle if you must drain
   long-running suspensions.

GitOps renderers such as Argo CD and `helm template` cannot read a live Secret
with Helm `lookup`. Set `requestStateKey.value` from an external secret, or set
`requestStateKey.existingSecret` to a pre-created Secret, and set
`requestStateKey.disallowGenerated=true` so a render fails instead of rotating
the key.

The bundled Valkey task store uses a PersistentVolumeClaim by default
(`tasks.redis.persistence.enabled=true`). Set it to `false` only for disposable
development clusters; queued tasks are lost when the pod is replaced.

#### Authentication & Authorization
| Variable | Description | Default | Applies To |
|----------|-------------|---------|------------|
| `ENABLE_AUTH` | Enable OAuth 2.1 authentication | `false` | MCP Server (frontend) |
| `AUTH_ISSUER_URL` | OAuth 2.1 issuer URL (automatic discovery) | *(empty)* | MCP Server (frontend) |
| `AUTH_AUDIENCE` | OAuth client ID or API identifier | *(empty)* | MCP Server (frontend) |
| `AUTH_VALID_SCOPES` | Comma-separated list of valid scopes | `read,write,admin` | MCP Server (frontend) |
| `AUTH_DEFAULT_SCOPES` | Comma-separated list of default scopes | `read` | MCP Server (frontend) |
| `AUTH_REQUIRED_SCOPES` | Comma-separated list of required scopes | `read` | MCP Server (frontend) |

### OAuth 2.1 Configuration Examples

#### Universal Provider Setup
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
export VIEWONLY_1="false"

# Production Registry (with safety)
export SCHEMA_REGISTRY_NAME_2="production"
export SCHEMA_REGISTRY_URL_2="https://prod-registry:8081"
export SCHEMA_REGISTRY_USER_2="prod-user"
export SCHEMA_REGISTRY_PASSWORD_2="prod-pass"
export VIEWONLY_2="true"  # Production safety

# Staging Registry
export SCHEMA_REGISTRY_NAME_3="staging"
export SCHEMA_REGISTRY_URL_3="https://staging-registry:8081"
export VIEWONLY_3="false"
```

---

## 📊 Resource Requirements

### Recommended Resources

| Component | CPU | Memory | Storage | Use Case |
|-----------|-----|--------|---------|----------|
| **MCP Server (Small)** | 0.5 | 512MB | - | <100 schemas, light usage |
| **MCP Server (Medium)** | 1.0 | 1GB | - | 100-1000 schemas, moderate operations |
| **MCP Server (Large)** | 2.0 | 2GB | 10GB | >1000 schemas, heavy migrations |
| **Schema Registry** | 0.5 | 1GB | 20GB | Per instance |
| **Kafka Broker** | 1.0 | 2GB | 100GB | Per broker, 3 minimum |

### Performance Considerations

The 3.0 architecture keeps the read path lightweight:
- **Edition registration**: out-of-edition tools are never registered, reducing client context
- **Catalog-driven annotations**: scope and safety metadata come from one table
- **Background tasks**: long operations run through the `fastmcp-tasks` extension
- **Shared resources**: reads remain available in every edition

---

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Enable authentication on Schema Registry (backend)
- [ ] Enable MCP Server authentication with `ENABLE_AUTH=true` (frontend)
- [ ] Use HTTPS/TLS for all connections
- [ ] Set `VIEWONLY=true` for production MCP instances
- [ ] Implement network policies in Kubernetes
- [ ] Use secrets management for credentials
- [ ] Enable audit logging
- [ ] Regular security scanning of images
- [ ] Implement rate limiting on ingress

### 🔑 Authentication Layers

**Two distinct authentication layers:**

1. **Schema Registry Authentication (Backend)**
   - Controls how the MCP server connects to Kafka Schema Registry instances
   - Set via `SCHEMA_REGISTRY_USER`, `SCHEMA_REGISTRY_PASSWORD`
   - These credentials are NOT used to authenticate users of the MCP server

2. **MCP Server Authentication (Frontend)**
   - Controls who can access the MCP server and its tools
   - Enable with `ENABLE_AUTH=true` and configure OAuth 2.1 settings
   - Optional - defaults to open access if not configured

### Security Features

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

# OAuth discovery endpoints
curl http://localhost:38000/.well-known/oauth-authorization-server
curl http://localhost:38000/.well-known/oauth-protected-resource

# Test MCP compliance
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

### Upgrading to 3.0.0

1. **Review breaking changes**: See the [v3.0 migration guide](v3-migration-guide.md).
2. **Choose an edition**: plain tags are `viewer`; set `MCP_EDITION=editor|admin` or use a suffixed image.
3. **Replace `READONLY*`**: use `VIEWONLY` / `VIEWONLY_<n>` and the edition model.
4. **Update Helm values**: set `edition` instead of `SLIM_MODE`; see the chart README.
5. **Verify workflows**: interactive tools now use MRTR on modern clients and `elicitation/create` on legacy clients.

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
   git tag v3.0.0
   git push origin v3.0.0
   ```

3. **Automated Process**: GitHub Actions handles building, testing, and publishing

---

This deployment guide provides instructions for deploying Kafka Schema Registry MCP Server 3.0.0 with FastMCP 4.1+, the three editions, MRTR workflows and the 3.0 security model across production environments.
