# Remote MCP Server Metrics & Monitoring

This document describes the comprehensive monitoring and metrics capabilities available when running the Kafka Schema Registry MCP Server in **remote mode**.

## 📊 **Monitoring Endpoints**

### **Health Check Endpoint**
```
GET /health
```

**Purpose**: Kubernetes health checks and monitoring  
**Response Format**: JSON  
**Response Codes**: 
- `200`: All systems healthy
- `503`: Service unavailable or degraded

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-08T10:30:00.000Z",
  "uptime_seconds": 3600,
  "registry_mode": "multi",
  "oauth_enabled": true,
  "transport": "streamable-http",
  "registries": {
    "production": {
      "status": "connected",
      "url": "https://prod-registry.company.com",
      "response_time_ms": 45
    },
    "staging": {
      "status": "connected", 
      "url": "https://staging-registry.company.com",
      "response_time_ms": 38
    }
  },
  "response_time_ms": 127
}
```

### **Prometheus Metrics Endpoint**
```
GET /metrics
```

**Purpose**: Prometheus monitoring and alerting  
**Response Format**: Prometheus text format  
**Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

### **Readiness Check Endpoint**
```
GET /ready
```

**Purpose**: Kubernetes readiness probes (simpler than health check)  
**Response Format**: JSON  
**Response Codes**:
- `200`: Server ready to accept requests
- `503`: Server not ready

## 📈 **Prometheus Metrics**

### **Server Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_server_uptime_seconds` | Counter | Time since server started |
| `mcp_registry_mode_info{mode="single\|multi"}` | Gauge | Registry mode information |

### **Request Metrics**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcp_requests_total` | Counter | `method` | Total MCP requests by method |
| `mcp_request_errors_total` | Counter | `method` | Total MCP request errors by method |
| `mcp_request_duration_seconds_avg` | Gauge | `method` | Average request duration |
| `mcp_request_duration_seconds_max` | Gauge | `method` | Maximum request duration |
| `mcp_request_duration_seconds_min` | Gauge | `method` | Minimum request duration |

**Common Method Labels**:
- `tools/list` - List available tools
- `tools/call` - Execute MCP tools
- `resources/list` - List resources
- `resources/read` - Read resource content
- `health` - Health check requests
- `metrics` - Metrics requests

### **Authentication Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_oauth_validations_total` | Counter | Total OAuth token validations |
| `mcp_oauth_validation_errors_total` | Counter | Failed OAuth validations |

### **Registry Health Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_registry_health_checks_total` | Counter | Registry health checks performed |

### **Schema Registry Specific Metrics**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcp_schema_registry_operations_total` | Counter | `operation` | Operations by type (register_schema, check_compatibility, etc.) |
| `mcp_schema_registry_operations_by_registry_total` | Counter | `registry` | Total operations per registry |
| `mcp_schema_registry_errors_total` | Counter | `registry` | Failed operations per registry |
| `mcp_schema_registry_response_time_seconds_avg` | Gauge | `registry` | Average response time per registry |
| `mcp_schema_registry_response_time_seconds_max` | Gauge | `registry` | Maximum response time per registry |
| `mcp_schema_registry_response_time_seconds_min` | Gauge | `registry` | Minimum response time per registry |
| `mcp_schema_registry_registrations_total` | Counter | `registry` | Schema registrations per registry |
| `mcp_schema_registry_compatibility_checks_total` | Counter | `registry` | Compatibility checks per registry |
| `mcp_schema_registry_exports_total` | Counter | `registry` | Schema exports per registry |
| `mcp_schema_registry_subjects` | Gauge | `registry` | Current number of subjects |
| `mcp_schema_registry_schemas` | Gauge | `registry` | Current number of schemas |
| `mcp_schema_registry_contexts` | Gauge | `registry` | Current number of contexts |
| `mcp_schema_registry_status` | Gauge | `registry` | Registry health (1=healthy, 0=unhealthy) |
| `mcp_schema_registry_context_operations_total` | Counter | `registry`, `context` | Operations per context |

## 🔍 **Example Prometheus Metrics Output**

```prometheus
# HELP mcp_server_uptime_seconds Time since server started
# TYPE mcp_server_uptime_seconds counter
mcp_server_uptime_seconds 3600.123456

# HELP mcp_requests_total Total number of MCP requests
# TYPE mcp_requests_total counter
mcp_requests_total{method="tools/list"} 45
mcp_requests_total{method="tools/call"} 123
mcp_requests_total{method="health"} 72

# HELP mcp_request_errors_total Total number of MCP request errors
# TYPE mcp_request_errors_total counter
mcp_request_errors_total{method="tools/call"} 3

# HELP mcp_request_duration_seconds Request duration in seconds
# TYPE mcp_request_duration_seconds histogram
mcp_request_duration_seconds_avg{method="tools/list"} 0.045000
mcp_request_duration_seconds_max{method="tools/list"} 0.120000
mcp_request_duration_seconds_min{method="tools/list"} 0.015000

# HELP mcp_oauth_validations_total Total OAuth token validations
# TYPE mcp_oauth_validations_total counter
mcp_oauth_validations_total 89

# HELP mcp_oauth_validation_errors_total OAuth validation errors
# TYPE mcp_oauth_validation_errors_total counter
mcp_oauth_validation_errors_total 2

# HELP mcp_registry_health_checks_total Registry health checks performed
# TYPE mcp_registry_health_checks_total counter
mcp_registry_health_checks_total 72

# HELP mcp_registry_mode_info Registry mode information
# TYPE mcp_registry_mode_info gauge
mcp_registry_mode_info{mode="multi"} 1

# HELP mcp_schema_registry_operations_total Total schema registry operations by type
# TYPE mcp_schema_registry_operations_total counter
mcp_schema_registry_operations_total{operation="register_schema"} 25
mcp_schema_registry_operations_total{operation="get_schema"} 156
mcp_schema_registry_operations_total{operation="check_compatibility"} 42
mcp_schema_registry_operations_total{operation="list_subjects"} 89

# HELP mcp_schema_registry_operations_by_registry_total Operations by registry
# TYPE mcp_schema_registry_operations_by_registry_total counter
mcp_schema_registry_operations_by_registry_total{registry="production"} 198
mcp_schema_registry_operations_by_registry_total{registry="staging"} 114

# HELP mcp_schema_registry_subjects Current number of subjects per registry
# TYPE mcp_schema_registry_subjects gauge
mcp_schema_registry_subjects{registry="production"} 45
mcp_schema_registry_subjects{registry="staging"} 23

# HELP mcp_schema_registry_schemas Current number of schemas per registry
# TYPE mcp_schema_registry_schemas gauge
mcp_schema_registry_schemas{registry="production"} 127
mcp_schema_registry_schemas{registry="staging"} 67

# HELP mcp_schema_registry_status Registry health status (1=healthy, 0=unhealthy)
# TYPE mcp_schema_registry_status gauge
mcp_schema_registry_status{registry="production"} 1
mcp_schema_registry_status{registry="staging"} 1

# HELP mcp_schema_registry_response_time_seconds Registry response times
# TYPE mcp_schema_registry_response_time_seconds histogram
mcp_schema_registry_response_time_seconds_avg{registry="production"} 0.089000
mcp_schema_registry_response_time_seconds_max{registry="production"} 0.450000
mcp_schema_registry_response_time_seconds_min{registry="production"} 0.023000
```

## 🏗️ **Kubernetes Integration**

### **Helm Configuration**

The metrics are automatically configured in the Helm chart:

```yaml
# Health checks
deployment:
  healthCheck:
    enabled: true
    httpGet:
      path: "/health"
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3

# Prometheus monitoring
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    path: /metrics
```

### **Prometheus ServiceMonitor**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kafka-schema-registry-mcp
spec:
  selector:
    matchLabels:
      app: kafka-schema-registry-remote-mcp
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

## 📊 **Grafana Dashboard**

### **Key Metrics to Monitor**

1. **Server Health**:
   - Uptime
   - Request rate and errors
   - Response times

2. **Authentication**:
   - OAuth validation success rate
   - Failed authentication attempts

3. **Registry Connectivity**:
   - Registry health status
   - Connection response times

4. **Performance**:
   - Request duration percentiles
   - Error rates by operation

### **Recommended Alerts**

```yaml
# High error rate
- alert: MCPHighErrorRate
  expr: rate(mcp_request_errors_total[5m]) / rate(mcp_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High error rate on MCP server"

# OAuth validation failures
- alert: MCPOAuthFailures
  expr: rate(mcp_oauth_validation_errors_total[5m]) > 1
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "OAuth validation failures detected"

# Server down
- alert: MCPServerDown
  expr: up{job="kafka-schema-registry-mcp"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "MCP server is down"
```

## 🔧 **Custom Metrics Collection**

### **Adding Application-Specific Metrics**

You can extend the metrics collection by modifying the `RemoteMCPMetrics` class:

```python
# In remote-mcp-server.py
class RemoteMCPMetrics:
    def __init__(self):
        # ... existing metrics ...
        self.schema_operations = defaultdict(int)
        self.registry_errors = defaultdict(int)
    
    def record_schema_operation(self, operation: str, registry: str):
        """Record schema registry operations."""
        self.schema_operations[f"{registry}_{operation}"] += 1
    
    def record_registry_error(self, registry: str, error_type: str):
        """Record registry-specific errors."""
        self.registry_errors[f"{registry}_{error_type}"] += 1
```

## 🚀 **Testing Metrics**

### **Local Testing**

```bash
# Start remote server
python remote-mcp-server.py

# Test health endpoint
curl http://localhost:8000/health

# Test metrics endpoint
curl http://localhost:8000/metrics

# Test readiness
curl http://localhost:8000/ready
```

### **Production Testing**

```bash
# Health check
curl https://mcp-schema-registry.your-domain.com/health

# Metrics (may require authentication)
curl -H "Authorization: Bearer $TOKEN" \
  https://mcp-schema-registry.your-domain.com/metrics
```

## 📚 **Monitoring Best Practices**

1. **Set up alerting** for critical metrics (server down, high error rates)
2. **Monitor OAuth failures** to detect authentication issues
3. **Track registry health** to identify connectivity problems
4. **Use request duration metrics** to detect performance degradation
5. **Set up dashboards** for operational visibility
6. **Regular health check monitoring** for proactive issue detection

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Metrics endpoint not accessible**:
   - Check if server is running with correct transport
   - Verify port and path configuration
   - Ensure ingress/service configuration

2. **Health check failures**:
   - Check registry connectivity
   - Verify OAuth configuration
   - Review server logs

3. **Missing metrics in Prometheus**:
   - Verify ServiceMonitor configuration
   - Check Prometheus targets
   - Ensure correct metrics path and port

---

## Summary

The remote MCP server provides comprehensive monitoring capabilities with:

- ✅ **Health checks**: Deep registry connectivity testing
- ✅ **Prometheus metrics**: Performance, errors, and OAuth monitoring  
- ✅ **Kubernetes integration**: Helm charts with monitoring configuration
- ✅ **Production-ready**: Alerting and dashboard support
- ✅ **Extensible**: Custom metrics collection framework

This monitoring stack enables production-grade observability for remote MCP deployments! 📊 