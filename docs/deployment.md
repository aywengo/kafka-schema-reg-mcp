# Deployment Guide

This guide covers various deployment scenarios for the Kafka Schema Registry MCP Server v1.7.0, from local development to production environments, including async task management, multi-registry support, and backup strategies.

## 🐳 Docker Deployment

### Quick Start with Pre-built Images (Recommended)

The fastest way to get started is using our pre-built DockerHub images:

```bash
# Option 1: Using Docker Compose with override (easiest)
git clone <repository-url>
cd kafka-schema-reg-mcp
docker-compose up -d

# Option 2: Direct Docker run
docker run -p 38000:8000 aywengo/kafka-schema-reg-mcp:1.7.0

# Option 3: With external Schema Registry
docker run -p 38000:8000 \
  -e SCHEMA_REGISTRY_URL=http://your-schema-registry:8081 \
  aywengo/kafka-schema-reg-mcp:1.7.0

# Option 4: Multi-Registry Configuration
docker run -p 38000:8000 \
  -e REGISTRIES_CONFIG='{"production":{"url":"http://prod-registry:8081"},"staging":{"url":"http://stage-registry:8081"}}' \
  aywengo/kafka-schema-reg-mcp:1.7.0
```

**Available DockerHub Tags:**
- `aywengo/kafka-schema-reg-mcp:latest` - Latest build
- `aywengo/kafka-schema-reg-mcp:stable` - Stable release pointer
- `aywengo/kafka-schema-reg-mcp:1.7.0` - Async operations & progress tracking
- `aywengo/kafka-schema-reg-mcp:1.6.0` - Batch cleanup & migrations
- `aywengo/kafka-schema-reg-mcp:1.5.0` - Multi-registry support
- **Multi-Platform Support**: Automatically detects `linux/amd64` or `linux/arm64`

### Docker Compose Override

The repository includes a `docker-compose.override.yml` file that automatically uses the DockerHub image:

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  mcp-server:
    image: aywengo/kafka-schema-reg-mcp:1.7.0
    # Override: use DockerHub image instead of building locally
```

**Switching between modes:**
```bash
# Use pre-built image (default)
docker-compose up -d

# Build from source (remove override)
mv docker-compose.override.yml docker-compose.override.yml.bak
docker-compose up -d --build

# Restore pre-built mode
mv docker-compose.override.yml.bak docker-compose.override.yml
```

### Local Development

For development or custom builds:

```bash
# Clone the repository
git clone <repository-url>
cd kafka-schema-reg-mcp

# Remove override to build locally
mv docker-compose.override.yml docker-compose.override.yml.bak

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

For production deployments, create a production-specific Docker Compose configuration with v1.7.0 features:

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
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: false
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_SEGMENT_BYTES: 1073741824
      KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS: 300000
    volumes:
      - kafka_data:/var/lib/kafka/data
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  schema-registry:
    image: confluentinc/cp-schema-registry:latest
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
      SCHEMA_REGISTRY_SCHEMA_REGISTRY_GROUP_ID: schema-registry
      SCHEMA_REGISTRY_MASTER_ELIGIBILITY: true
      SCHEMA_REGISTRY_HEAP_OPTS: "-Xms512m -Xmx1024m"
      SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR: 3
      SCHEMA_REGISTRY_MODE_MUTABILITY: true
      SCHEMA_REGISTRY_COMPATIBILITY_LEVEL: BACKWARD
    depends_on:
      - kafka
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  mcp-server:
    image: aywengo/kafka-schema-reg-mcp:1.7.0
    environment:
      # Single Registry Configuration
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
      SCHEMA_REGISTRY_USER: ${SCHEMA_REGISTRY_USER:-}
      SCHEMA_REGISTRY_PASSWORD: ${SCHEMA_REGISTRY_PASSWORD:-}
      # Multi-Registry Configuration (v1.5.0+)
      REGISTRIES_CONFIG: |
        {
          "production": {
            "url": "http://schema-registry:8081",
            "user": "${PROD_REGISTRY_USER}",
            "password": "${PROD_REGISTRY_PASSWORD}",
            "description": "Production Schema Registry"
          },
          "staging": {
            "url": "http://staging-registry:8081",
            "user": "${STAGE_REGISTRY_USER}",
            "password": "${STAGE_REGISTRY_PASSWORD}",
            "description": "Staging Schema Registry"
          }
        }
      # Async Task Configuration (v1.7.0+)
      TASK_POOL_SIZE: 10
      TASK_QUEUE_SIZE: 100
      PYTHONUNBUFFERED: 1
    ports:
      - "38000:8000"
    depends_on:
      - schema-registry
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G  # Increased for async operations
          cpus: '1.0' # Increased for parallel tasks
        reservations:
          memory: 512M
          cpus: '0.5'
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

Deploy with:
```bash
docker-compose -f docker-compose.prod.yml up -d
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
  # Async Task Configuration
  TASK_POOL_SIZE: "10"
  TASK_QUEUE_SIZE: "100"
  # Multi-Registry Configuration
  REGISTRIES_CONFIG: |
    {
      "default": {
        "url": "http://schema-registry-service:8081",
        "description": "Default cluster registry"
      },
      "backup": {
        "url": "http://backup-registry-service:8081",
        "description": "Backup registry for DR"
      }
    }
```

### Kafka Deployment

```yaml
# k8s/kafka-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
  namespace: kafka-schema-registry
spec:
  serviceName: kafka-service
  replicas: 3
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
      - name: kafka
        image: confluentinc/cp-kafka:latest
        ports:
        - containerPort: 9092
        - containerPort: 29093
        env:
        - name: KAFKA_NODE_ID
          value: "1"
        - name: KAFKA_PROCESS_ROLES
          value: "broker,controller"
        - name: KAFKA_CONTROLLER_QUORUM_VOTERS
          value: "1@kafka-0.kafka-service:29093,2@kafka-1.kafka-service:29093,3@kafka-2.kafka-service:29093"
        - name: KAFKA_LISTENERS
          value: "PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093"
        - name: KAFKA_ADVERTISED_LISTENERS
          value: "PLAINTEXT://kafka-service:9092"
        - name: KAFKA_CONTROLLER_LISTENER_NAMES
          value: "CONTROLLER"
        - name: KAFKA_INTER_BROKER_LISTENER_NAME
          value: "PLAINTEXT"
        - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
          value: "3"
        - name: KAFKA_AUTO_CREATE_TOPICS_ENABLE
          value: "false"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: kafka-storage
          mountPath: /var/lib/kafka/data
  volumeClaimTemplates:
  - metadata:
      name: kafka-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi

---
apiVersion: v1
kind: Service
metadata:
  name: kafka-service
  namespace: kafka-schema-registry
spec:
  clusterIP: None
  selector:
    app: kafka
  ports:
  - name: kafka
    port: 9092
    targetPort: 9092
```

### Schema Registry Deployment

```yaml
# k8s/schema-registry-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: schema-registry
  namespace: kafka-schema-registry
spec:
  replicas: 2
  selector:
    matchLabels:
      app: schema-registry
  template:
    metadata:
      labels:
        app: schema-registry
    spec:
      containers:
      - name: schema-registry
        image: confluentinc/cp-schema-registry:latest
        ports:
        - containerPort: 8081
        env:
        - name: SCHEMA_REGISTRY_HOST_NAME
          value: "schema-registry"
        - name: SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS
          value: "kafka-service:9092"
        - name: SCHEMA_REGISTRY_LISTENERS
          value: "http://0.0.0.0:8081"
        - name: SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR
          value: "3"
        - name: SCHEMA_REGISTRY_HEAP_OPTS
          value: "-Xms512m -Xmx1024m"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8081
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: schema-registry-service
  namespace: kafka-schema-registry
spec:
  selector:
    app: schema-registry
  ports:
  - name: http
    port: 8081
    targetPort: 8081
  type: ClusterIP
```

### MCP Server Deployment (Updated for v1.7.0)

```yaml
# k8s/mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: kafka-schema-registry
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
      version: "1.7.0"
  template:
    metadata:
      labels:
        app: mcp-server
        version: "1.7.0"
    spec:
      containers:
      - name: mcp-server
        image: aywengo/kafka-schema-reg-mcp:1.7.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: mcp-server-config
        env:
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
        resources:
          requests:
            memory: "512Mi"  # Increased for async operations
            cpu: "250m"      # Increased for parallel tasks
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
        # Volume for task persistence (optional)
        volumeMounts:
        - name: task-cache
          mountPath: /app/task-cache
      volumes:
      - name: task-cache
        emptyDir:
          sizeLimit: 1Gi

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

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/kafka-deployment.yaml
kubectl apply -f k8s/schema-registry-deployment.yaml
kubectl apply -f k8s/mcp-server-deployment.yaml

# Verify deployment
kubectl get pods -n kafka-schema-registry
kubectl get services -n kafka-schema-registry

# Check logs
kubectl logs -f deployment/mcp-server -n kafka-schema-registry
```

---

## 🔧 Configuration Options

### Environment Variables (v1.7.0)

| Variable | Description | Default | Since |
|----------|-------------|---------|-------|
| `SCHEMA_REGISTRY_URL` | Primary Schema Registry URL | `http://localhost:8081` | v1.0.0 |
| `SCHEMA_REGISTRY_USER` | Basic auth username | - | v1.0.0 |
| `SCHEMA_REGISTRY_PASSWORD` | Basic auth password | - | v1.0.0 |
| `READONLY` | Enable read-only mode | `false` | v1.3.0 |
| `REGISTRIES_CONFIG` | JSON config for multiple registries | - | v1.5.0 |
| `TASK_POOL_SIZE` | ThreadPoolExecutor size | `10` | v1.7.0 |
| `TASK_QUEUE_SIZE` | Max queued tasks | `100` | v1.7.0 |
| `TASK_TIMEOUT` | Default task timeout (seconds) | `3600` | v1.7.0 |

### Multi-Registry Configuration Example

```bash
export REGISTRIES_CONFIG='{
  "production": {
    "url": "https://prod.schema-registry.com:8081",
    "user": "prod-user",
    "password": "prod-pass",
    "description": "Production Schema Registry"
  },
  "staging": {
    "url": "https://stage.schema-registry.com:8081",
    "user": "stage-user", 
    "password": "stage-pass",
    "description": "Staging Schema Registry"
  },
  "development": {
    "url": "http://localhost:8081",
    "description": "Local Development"
  }
}'
```

---

## 📊 Resource Requirements

### Recommended Resources (v1.7.0)

Based on the async task management capabilities:

| Component | CPU | Memory | Storage | Notes |
|-----------|-----|--------|---------|-------|
| MCP Server (Small) | 0.5 | 512MB | - | <100 schemas, light usage |
| MCP Server (Medium) | 1.0 | 1GB | - | 100-1000 schemas, moderate async tasks |
| MCP Server (Large) | 2.0 | 2GB | 10GB | >1000 schemas, heavy migrations |
| Schema Registry | 0.5 | 1GB | 20GB | Per instance |
| Kafka Broker | 1.0 | 2GB | 100GB | Per broker, 3 minimum |

### Performance Tuning

For high-volume async operations:

```yaml
# High-performance configuration
environment:
  TASK_POOL_SIZE: "20"        # More parallel workers
  TASK_QUEUE_SIZE: "500"      # Larger task queue
  TASK_TIMEOUT: "7200"        # 2-hour timeout for large migrations
  # Python optimizations
  PYTHONUNBUFFERED: "1"
  PYTHONDONTWRITEBYTECODE: "1"
```

---

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Enable authentication on Schema Registry
- [ ] Use HTTPS/TLS for all connections
- [ ] Set `READONLY=true` for production MCP instances
- [ ] Implement network policies in Kubernetes
- [ ] Use secrets management for credentials
- [ ] Enable audit logging
- [ ] Regular security scanning of images
- [ ] Implement rate limiting on ingress

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

The MCP server provides health endpoints:

```bash
# Basic health check
curl http://localhost:38000/

# Async task queue status (v1.7.0+)
curl http://localhost:38000/tasks/status
```

### Prometheus Metrics (Coming in v1.8.0)

Future versions will expose metrics:
- Task queue depth
- Task completion rate
- Migration success/failure rate
- Registry connection health
- Operation latency histograms

---

## 🔄 Upgrade Guide

### Upgrading to v1.7.0

1. **Review Breaking Changes**: None in v1.7.0
2. **Update Image Tags**: Change to `aywengo/kafka-schema-reg-mcp:1.7.0`
3. **Adjust Resources**: Increase CPU/memory for async operations
4. **Test Async Features**: Verify task management works correctly

```bash
# Rolling update in Kubernetes
kubectl set image deployment/mcp-server mcp-server=aywengo/kafka-schema-reg-mcp:1.7.0 -n kafka-schema-registry

# Monitor rollout
kubectl rollout status deployment/mcp-server -n kafka-schema-registry
```

---

## 🚀 CI/CD & Automated Publishing

### GitHub Actions Workflows

The project includes production-ready GitHub Actions workflows for automated building, testing, and publishing:

#### **Build Workflow** (`.github/workflows/build.yml`)
Triggered on pushes to main and pull requests:
- ✅ **Multi-platform builds** (AMD64 + ARM64)
- ✅ **Security scanning** with Trivy vulnerability scanner
- ✅ **Docker image testing** to verify startup
- ✅ **GitHub Actions caching** for faster builds
- ✅ **SARIF upload** to GitHub Security tab

#### **Publish Workflow** (`.github/workflows/publish.yml`)
Triggered on version tags (e.g., `v1.3.0`):
- ✅ **Automated DockerHub publishing** with multiple tags
- ✅ **Multi-platform images** (AMD64 + ARM64)
- ✅ **Security vulnerability scanning** 
- ✅ **Automatic DockerHub description updates**
- ✅ **GitHub release creation** with Docker pull commands
- ✅ **Semantic versioning** support (major.minor.patch)

### Setting Up CI/CD

1. **Configure DockerHub Secrets** in your GitHub repository:
   ```bash
   # Repository Settings → Secrets and variables → Actions
   DOCKERHUB_USERNAME=your-username
   DOCKERHUB_TOKEN=your-access-token
   ```

2. **Create and Push a Version Tag**:
   ```bash
   git tag v1.3.0
   git push origin v1.3.0
   ```

3. **Automated Publishing Process**:
   - GitHub Actions builds multi-platform images
   - Runs security scans with Trivy
   - Pushes to DockerHub with semantic versioning tags
   - Updates DockerHub repository description
   - Creates GitHub release with pull instructions

### Image Metadata & Labels

All published images include comprehensive OCI metadata:

```dockerfile
LABEL org.opencontainers.image.title="Kafka Schema Registry MCP Server"
LABEL org.opencontainers.image.description="Message Control Protocol server with Context Support and Export"
LABEL org.opencontainers.image.version="v1.3.0"
LABEL org.opencontainers.image.vendor="aywengo"
LABEL org.opencontainers.image.source="https://github.com/aywengo/kafka-schema-reg-mcp"
```

### Multi-Platform Support

Images are built for multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit (standard servers, x86 Macs)
- **linux/arm64** - ARM 64-bit (Apple Silicon, ARM servers, Raspberry Pi)

Docker automatically selects the correct architecture:
```bash
# Works on both Intel and ARM systems
docker run aywengo/kafka-schema-reg-mcp:stable
```

### Security & Vulnerability Scanning

Every build and publish includes:
- **Trivy security scanning** for known vulnerabilities
- **SARIF reports** uploaded to GitHub Security tab
- **Automated dependency updates** recommendations
- **Base image security** with Python 3.11-slim

---

## 📦 Export Infrastructure & Backup Strategies

### Export Storage Configuration

For production deployments, configure dedicated storage for schema exports and backups:

```yaml
# k8s/export-storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: schema-export-storage
  namespace: kafka-schema-registry
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd

---
# Mount export storage in MCP server deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        volumeMounts:
        - name: export-storage
          mountPath: /exports
        env:
        - name: EXPORT_STORAGE_PATH
          value: "/exports"
      volumes:
      - name: export-storage
        persistentVolumeClaim:
          claimName: schema-export-storage
```

### Automated Backup CronJob

```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: schema-registry-backup
  namespace: kafka-schema-registry
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              echo "Starting backup at $DATE"
              
              # Global backup
              curl -X POST http://mcp-server-service:8000/export/global \
                -H "Content-Type: application/json" \
                -d '{
                  "format": "bundle",
                  "include_metadata": true,
                  "include_config": true,
                  "include_versions": "all"
                }' --output /backups/global_backup_$DATE.zip
              
              # Production context backup
              curl -X POST http://mcp-server-service:8000/export/contexts/production \
                -H "Content-Type: application/json" \
                -d '{
                  "format": "json",
                  "include_metadata": true,
                  "include_config": true,
                  "include_versions": "all"
                }' --output /backups/production_backup_$DATE.json
              
              echo "Backup completed: $DATE"
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: schema-export-storage
          restartPolicy: OnFailure
```

### Export Performance Optimization

For high-volume registries, configure export performance:

```yaml
# Production MCP server with export optimization
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"      # Increased for large exports
            cpu: "1000m"
        env:
        - name: EXPORT_CHUNK_SIZE
          value: "1000"        # Process exports in chunks
        - name: EXPORT_TIMEOUT
          value: "600"         # 10 minute timeout for large exports
        - name: EXPORT_COMPRESSION_LEVEL
          value: "6"           # Balance between speed and compression
```

### Cloud Storage Integration

#### AWS S3 Integration

```yaml
# Export with S3 storage
apiVersion: batch/v1
kind: CronJob
metadata:
  name: schema-backup-s3
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: s3-backup-service-account
          containers:
          - name: s3-backup
            image: amazon/aws-cli:latest
            command:
            - /bin/bash
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              
              # Export to local file
              curl -X POST http://mcp-server-service:8000/export/global \
                -H "Content-Type: application/json" \
                -d '{"format": "bundle", "include_metadata": true, "include_config": true, "include_versions": "all"}' \
                --output /tmp/backup_$DATE.zip
              
              # Upload to S3
              aws s3 cp /tmp/backup_$DATE.zip s3://schema-registry-backups/daily/
              
              # Cleanup old backups (keep 30 days)
              aws s3 ls s3://schema-registry-backups/daily/ | \
                awk '$1 < "'$(date -d '30 days ago' '+%Y-%m-%d')'" {print $4}' | \
                xargs -I {} aws s3 rm s3://schema-registry-backups/daily/{}
```

#### Azure Blob Storage

```yaml
# Export with Azure Blob storage
apiVersion: batch/v1
kind: CronJob
metadata:
  name: schema-backup-azure
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: azure-backup
            image: mcr.microsoft.com/azure-cli:latest
            env:
            - name: AZURE_STORAGE_ACCOUNT
              valueFrom:
                secretKeyRef:
                  name: azure-storage-secret
                  key: account
            - name: AZURE_STORAGE_KEY
              valueFrom:
                secretKeyRef:
                  name: azure-storage-secret
                  key: key
            command:
            - /bin/bash
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              
              # Export schemas
              curl -X POST http://mcp-server-service:8000/export/global \
                -H "Content-Type: application/json" \
                -d '{"format": "bundle", "include_metadata": true, "include_config": true, "include_versions": "all"}' \
                --output /tmp/backup_$DATE.zip
              
              # Upload to Azure Blob
              az storage blob upload \
                --container-name schema-backups \
                --file /tmp/backup_$DATE.zip \
                --name daily/backup_$DATE.zip
```

### Export Monitoring & Alerting

```yaml
# ServiceMonitor for export metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-export-metrics
spec:
  selector:
    matchLabels:
      app: mcp-server
  endpoints:
  - port: http
    path: /metrics
    interval: 30s

---
# PrometheusRule for export alerting
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: schema-export-alerts
spec:
  groups:
  - name: schema.export
    rules:
    - alert: ExportJobFailed
      expr: increase(mcp_export_failures_total[1h]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Schema export job failed"
        description: "Export job has failed {{ $value }} times in the last hour"
    
    - alert: ExportDurationHigh
      expr: histogram_quantile(0.95, rate(mcp_export_duration_seconds_bucket[5m])) > 300
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Schema export taking too long"
        description: "95th percentile export duration is {{ $value }} seconds"
    
    - alert: BackupJobMissing
      expr: time() - schema_registry_last_backup_timestamp > 86400
      for: 1h
      labels:
        severity: critical
      annotations:
        summary: "Schema registry backup is overdue"
        description: "Last backup was {{ $value }} seconds ago (>24h)"
```

---

## 🤖 Claude Desktop Integration

### MCP Server Configuration

Once your Kafka Schema Registry MCP Server is deployed, configure Claude Desktop for seamless integration.

#### Docker-based Integration (Recommended)

For deployments using Docker, use this Claude Desktop configuration pattern:

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

#### Configuration for Different Environments

**Local Development:**
```json
{
  "env": {
    "SCHEMA_REGISTRY_URL": "http://localhost:8081",
    "SCHEMA_REGISTRY_USER": "",
    "SCHEMA_REGISTRY_PASSWORD": ""
  }
}
```

**Remote Deployment:**
```json
{
  "env": {
    "SCHEMA_REGISTRY_URL": "https://schema-registry.your-domain.com",
    "SCHEMA_REGISTRY_USER": "your-username",
    "SCHEMA_REGISTRY_PASSWORD": "your-password"
  }
}
```

**Production with Authentication:**
```json
{
  "env": {
    "SCHEMA_REGISTRY_URL": "https://prod-schema-registry.company.com:8081",
    "SCHEMA_REGISTRY_USER": "${SCHEMA_REGISTRY_PROD_USER}",
    "SCHEMA_REGISTRY_PASSWORD": "${SCHEMA_REGISTRY_PROD_PASSWORD}"
  }
}
```

### Configuration Best Practices

#### 1. Environment Variable Pattern
Always use the `-e VARIABLE_NAME` pattern (without values) in args combined with the `env` section:

**✅ Recommended:**
```json
{
  "args": ["-e", "SCHEMA_REGISTRY_URL"],
  "env": {"SCHEMA_REGISTRY_URL": "http://localhost:8081"}
}
```

**❌ Not Recommended:**
```json
{
  "args": ["-e", "SCHEMA_REGISTRY_URL=http://localhost:8081"]
}
```

**Benefits:**
- ✅ **Maintainable**: Configuration values separated from Docker arguments
- ✅ **Secure**: Environment variables not exposed in process lists
- ✅ **Flexible**: Easy to change values without modifying args array
- ✅ **Standard**: Follows Docker and MCP best practices

#### 2. Network Configuration

**Local Development (host network):**
```json
{"args": ["--network", "host"]}
```

**Production (bridge network):**
```json
{
  "args": ["--network", "kafka-network"],
  "env": {"SCHEMA_REGISTRY_URL": "http://schema-registry:8081"}
}
```

#### 3. Security Considerations

**Environment Variables:**
- Store sensitive credentials in environment variables
- Use tools like `direnv` for local development
- Configure proper secret management for production

**Network Isolation:**
- Use Docker networks for service isolation
- Consider VPN or SSH tunneling for remote access
- Implement proper firewall rules

### Claude Desktop Integration Testing

Verify your configuration with these commands:

1. **Test Connection:**
   ```
   "Check the status of the Schema Registry connection"
   ```

2. **List Resources:**
   ```
   "List all available schema contexts"
   ```

3. **Test Schema Operations:**
   ```
   "Show me all subjects in the production context"
   ```

4. **Test Export Functionality:**
   ```
   "Export all schemas from the development context in JSON format"
   ```

### Troubleshooting Claude Desktop Integration

#### Common Issues

1. **Connection Refused:**
   - Check SCHEMA_REGISTRY_URL is correct
   - Verify network connectivity with `--network host`
   - Ensure Schema Registry is running and accessible

2. **Environment Variables Not Working:**
   - Use `-e VARIABLE_NAME` pattern in args
   - Define values in `env` section
   - Restart Claude Desktop after configuration changes

3. **Docker Network Issues:**
   - For local development, use `--network host`
   - For containerized Schema Registry, use custom Docker network
   - Check Docker network connectivity with `docker exec`

4. **Authentication Failures:**
   - Verify username/password in environment variables
   - Test credentials directly with curl
   - Check Schema Registry authentication configuration

#### Debug Commands

```bash
# Test Docker configuration manually
docker run --rm -i --network host \
  -e SCHEMA_REGISTRY_URL=http://localhost:8081 \
  aywengo/kafka-schema-reg-mcp:stable \
  python -c "import os; print(f'URL: {os.getenv(\"SCHEMA_REGISTRY_URL\")}')"

# Test Schema Registry connectivity
curl -I http://localhost:8081/subjects

# Test MCP server Docker container
docker run --rm --network host \
  -e SCHEMA_REGISTRY_URL=http://localhost:8081 \
  aywengo/kafka-schema-reg-mcp:stable \
  python -c "import requests; print(requests.get('http://localhost:8081/subjects').json())"
```

---

This deployment guide provides comprehensive instructions for deploying the Kafka Schema Registry MCP Server v1.7.0 with its new async task management features and multi-registry support across various environments. 