# Deployment Guide

This guide covers various deployment scenarios for the Kafka Schema Registry MCP Server, from local development to production environments.

## 🐳 Docker Deployment

### Local Development

The easiest way to get started is using Docker Compose for local development:

```bash
# Clone the repository
git clone <repository-url>
cd kafka-schema-reg-mcp

# Start all services
docker-compose up -d

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
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
      SCHEMA_REGISTRY_USER: ${SCHEMA_REGISTRY_USER:-}
      SCHEMA_REGISTRY_PASSWORD: ${SCHEMA_REGISTRY_PASSWORD:-}
      PYTHONUNBUFFERED: 1
    ports:
      - "38000:8000"
    depends_on:
      - schema-registry
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

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

### MCP Server Deployment

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
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/kafka-schema-mcp:latest
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
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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

## ☁️ Cloud Platform Deployments

### AWS EKS with Helm

Create a Helm chart for easy deployment:

```yaml
# helm/kafka-schema-mcp/values.yaml
global:
  imageRegistry: ""
  imagePullSecrets: []

kafka:
  enabled: true
  replicaCount: 3
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1000m
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3

schemaRegistry:
  enabled: true
  replicaCount: 2
  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 1Gi
      cpu: 500m

mcpServer:
  image:
    repository: your-account.dkr.ecr.region.amazonaws.com/kafka-schema-mcp
    tag: latest
    pullPolicy: Always
  replicaCount: 3
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
    limits:
      memory: 512Mi
      cpu: 500m
  
  service:
    type: LoadBalancer
    port: 80
    targetPort: 8000
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: nlb
      service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

  ingress:
    enabled: true
    className: alb
    annotations:
      kubernetes.io/ingress.class: alb
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/cert-id
    hosts:
    - host: schema-mcp.your-domain.com
      paths:
      - path: /
        pathType: Prefix

  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    path: /metrics

auth:
  enabled: false
  existingSecret: ""
  username: ""
  password: ""
```

Deploy with Helm:
```bash
# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install
helm install kafka-schema-mcp ./helm/kafka-schema-mcp \
  --namespace kafka-schema-registry \
  --create-namespace \
  --values values-production.yaml
```

### Google Cloud Run

For serverless deployment on Google Cloud:

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: 
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/kafka-schema-mcp:$COMMIT_SHA'
      - '.'
    
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push' 
      - 'gcr.io/$PROJECT_ID/kafka-schema-mcp:$COMMIT_SHA'

  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'kafka-schema-mcp'
      - '--image=gcr.io/$PROJECT_ID/kafka-schema-mcp:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=512Mi'
      - '--cpu=1'
      - '--concurrency=80'
      - '--max-instances=10'
      - '--set-env-vars=SCHEMA_REGISTRY_URL=https://your-schema-registry.com'

images:
  - 'gcr.io/$PROJECT_ID/kafka-schema-mcp:$COMMIT_SHA'
```

Deploy:
```bash
gcloud builds submit --config cloudbuild.yaml
```

### Azure Container Instances

```yaml
# azure-container-instance.yaml
apiVersion: 2019-12-01
location: eastus
name: kafka-schema-mcp
properties:
  containers:
  - name: mcp-server
    properties:
      image: your-registry.azurecr.io/kafka-schema-mcp:latest
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 1.0
      ports:
      - port: 8000
        protocol: TCP
      environmentVariables:
      - name: SCHEMA_REGISTRY_URL
        value: https://your-schema-registry.com
      - name: SCHEMA_REGISTRY_USER
        secureValue: your-username
      - name: SCHEMA_REGISTRY_PASSWORD
        secureValue: your-password
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 80
    - protocol: TCP  
      port: 8000
    dnsNameLabel: kafka-schema-mcp
type: Microsoft.ContainerInstance/containerGroups
```

Deploy:
```bash
az container create --resource-group myResourceGroup --file azure-container-instance.yaml
```

---

## 🔐 Security Considerations

### Authentication and Authorization

#### Schema Registry Authentication

```bash
# Set authentication environment variables
export SCHEMA_REGISTRY_USER="schema-admin"
export SCHEMA_REGISTRY_PASSWORD="secure-password"

# For Kubernetes, create secret
kubectl create secret generic schema-registry-auth \
  --from-literal=username=schema-admin \
  --from-literal=password=secure-password \
  --namespace kafka-schema-registry
```

#### Network Security

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-network-policy
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
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

#### TLS/SSL Configuration

```yaml
# k8s/tls-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-server-tls
  namespace: kafka-schema-registry
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi... # base64 encoded certificate
  tls.key: LS0tLS1CRUdJTi... # base64 encoded private key
```

---

## 📊 Monitoring and Observability

### Prometheus Metrics

Add metrics endpoint to the MCP server:

```python
# Add to mcp_server.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# Metrics
REQUEST_COUNT = Counter('mcp_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('mcp_request_duration_seconds', 'Request duration', ['method', 'endpoint'])

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method, 
        endpoint=request.url.path, 
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### ServiceMonitor for Prometheus

```yaml
# k8s/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-server-metrics
  namespace: kafka-schema-registry
spec:
  selector:
    matchLabels:
      app: mcp-server
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Kafka Schema Registry MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Request Duration",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(mcp_requests_total{status=~\"4..|5..\"}[5m]) / rate(mcp_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

---

## 🚀 Performance Optimization

### Production Configuration

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# Install production dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py .

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp
USER mcp

# Production server with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "mcp_server:app"]
```

### Resource Limits and Requests

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
  namespace: kafka-schema-registry
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Schema Registry Connection Issues

```bash
# Check connectivity
kubectl exec -it deployment/mcp-server -n kafka-schema-registry -- \
  curl -I http://schema-registry-service:8081/

# Check DNS resolution
kubectl exec -it deployment/mcp-server -n kafka-schema-registry -- \
  nslookup schema-registry-service
```

#### 2. Memory Issues

```bash
# Monitor memory usage
kubectl top pods -n kafka-schema-registry

# Check memory limits
kubectl describe pod <pod-name> -n kafka-schema-registry
```

#### 3. Network Policies

```bash
# Test network connectivity
kubectl exec -it deployment/mcp-server -n kafka-schema-registry -- \
  nc -zv schema-registry-service 8081
```

### Health Checks

```bash
# Application health
curl http://mcp-server-service:8000/

# Detailed health check script
#!/bin/bash
echo "=== MCP Server Health Check ==="

# Check if service is responding
if curl -f -s http://mcp-server-service:8000/ > /dev/null; then
    echo "✅ MCP Server is responding"
else
    echo "❌ MCP Server is not responding"
    exit 1
fi

# Check Schema Registry connectivity
if curl -f -s http://schema-registry-service:8081/ > /dev/null; then
    echo "✅ Schema Registry is accessible"
else
    echo "❌ Schema Registry is not accessible"
    exit 1
fi

# Check contexts endpoint
if curl -f -s http://mcp-server-service:8000/contexts | jq . > /dev/null; then
    echo "✅ Context endpoint is working"
else
    echo "❌ Context endpoint has issues"
    exit 1
fi

echo "✅ All health checks passed"
```

---

This deployment guide provides comprehensive instructions for deploying the Kafka Schema Registry MCP Server across various environments, from local development to production-ready cloud deployments with proper security, monitoring, and scaling configurations. 