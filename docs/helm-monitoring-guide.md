# Helm Monitoring Guide - PodMonitor & Grafana Dashboard

This guide explains how to set up comprehensive monitoring for the Kafka Schema Registry MCP Server using the Helm chart's PodMonitor and Grafana dashboard.

## Table of Contents

1. [PodMonitor Configuration](#podmonitor-configuration)
2. [Grafana Dashboard Setup](#grafana-dashboard-setup)
3. [Instance Identification](#instance-identification)
4. [Prometheus Configuration](#prometheus-configuration)
5. [Troubleshooting](#troubleshooting)

## PodMonitor Configuration

### Overview

The Helm chart includes a PodMonitor resource that enables Prometheus to scrape metrics directly from your MCP server pods. PodMonitor is preferred over ServiceMonitor for direct pod monitoring and provides better labeling capabilities.

### Enabling PodMonitor

```yaml
# values.yaml
monitoring:
  enabled: true
  
  podMonitor:
    enabled: true
    interval: 30s
    path: /metrics
    scrapeTimeout: 10s
    
    # Labels for PodMonitor resource
    labels:
      release: prometheus
      component: mcp-server
    
    # Labels to copy from pods to metrics
    podTargetLabels:
      - instanceId
      - deployment
      - environment
      - app.kubernetes.io/version
```

### Instance Identification

The PodMonitor automatically adds several labels for instance identification:

- **`instanceId`**: The Helm release name (e.g., `mcp-prod`, `mcp-staging`)
- **`deployment`**: Full deployment name including namespace
- **`environment`**: Environment label (production, staging, development)
- **`cluster`**: Kubernetes cluster identifier
- **`service`**: Service name (`kafka-schema-registry-mcp`)

### Relabeling Rules

The PodMonitor includes intelligent relabeling to enhance metrics with context:

```yaml
relabelings:
  # Add cluster label
  - sourceLabels: []
    targetLabel: cluster
    replacement: "{{ .Values.global.cluster | default \"default\" }}"
  
  # Add service label  
  - sourceLabels: []
    targetLabel: service
    replacement: "kafka-schema-registry-mcp"
    
  # Preserve instance label as instanceId
  - sourceLabels: [__meta_kubernetes_pod_label_instanceId]
    targetLabel: instanceId
```

## Grafana Dashboard Setup

### Importing the Dashboard

1. **Copy the Dashboard JSON**:
   ```bash
   cp helm/examples/grafana-dashboard-mcp-metrics.json /tmp/
   ```

2. **Import in Grafana**:
   - Go to Grafana → Dashboard → Import
   - Upload `grafana-dashboard-mcp-metrics.json`
   - Configure data source (typically named `prometheus`)

3. **Configure Variables**:
   - The dashboard includes two template variables:
     - `$instance`: Filter by instanceId (Helm release name)
     - `$registry`: Filter by schema registry name

### Dashboard Panels

The dashboard includes the following visualization panels:

#### Core MCP Metrics
- **MCP Request Rate by Method**: Rate of MCP requests per method
- **MCP Request Error Rate**: Error rate percentage for MCP requests
- **Server Uptime**: Server uptime in seconds

#### Schema Registry Metrics
- **Schema Registry Health Status**: Number of healthy registries
- **Schema Registry Operation Rate**: Rate of operations by type
- **Schema Registry Response Times**: Average and maximum response times
- **Schema Registry Operations by Registry**: Operations broken down by registry

#### Schema Statistics
- **Total Schema Subjects**: Current count of schema subjects
- **Total Schema Versions**: Current count of schema versions
- **Schema Subjects Distribution**: Pie chart showing distribution across registries

### Dashboard Variables

The dashboard supports dynamic filtering through variables:

```json
"templating": {
  "list": [
    {
      "name": "instance",
      "query": "label_values(mcp_server_uptime_seconds, instanceId)",
      "multi": true,
      "includeAll": true
    },
    {
      "name": "registry", 
      "query": "label_values(mcp_schema_registry_subjects, registry)",
      "multi": true,
      "includeAll": true
    }
  ]
}
```

## Prometheus Configuration

### ServiceMonitor vs PodMonitor

While both are supported, **PodMonitor is recommended** for the following reasons:

| Feature | ServiceMonitor | PodMonitor |
|---------|----------------|------------|
| **Target Discovery** | Via Service | Direct Pods |
| **Label Preservation** | Limited | Full Pod Labels |
| **Instance Identification** | Service-based | Pod-based |
| **Scaling Visibility** | Aggregated | Per-instance |

### Prometheus Operator Configuration

Ensure your Prometheus Operator can discover PodMonitors:

```yaml
# prometheus.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  podMonitorSelector:
    matchLabels:
      release: prometheus
  podMonitorNamespaceSelector: {}
```

### Manual Prometheus Configuration

If using manual Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-server-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
        action: keep
        regex: kafka-schema-registry-mcp
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

## Instance Identification

### Deployment Labels

The deployment template adds instance identification labels to pods:

```yaml
labels:
  instanceId: {{ .Release.Name }}
  deployment: {{ include "kafka-schema-registry-mcp.fullname" . }}
  environment: {{ .Values.global.environment | default .Release.Namespace }}
```

### Metrics Labels

All metrics include instance identification:

```bash
# Example metric with labels
mcp_requests_total{
  instanceId="mcp-prod",
  deployment="mcp-prod-kafka-schema-registry-mcp", 
  environment="production",
  method="list_subjects"
} 42
```

### Multi-Instance Monitoring

When running multiple instances, you can:

1. **Filter by Instance**: Use the `$instance` variable in Grafana
2. **Compare Instances**: Select multiple instances in the variable
3. **Environment-based Filtering**: Filter by environment label

## Troubleshooting

### PodMonitor Not Discovered

**Problem**: Prometheus not discovering PodMonitor

**Solutions**:
1. Check PodMonitor labels match Prometheus selector:
   ```bash
   kubectl get podmonitor -o yaml
   ```

2. Verify Prometheus configuration:
   ```bash
   kubectl get prometheus -o yaml
   ```

3. Check Prometheus logs:
   ```bash
   kubectl logs -f prometheus-prometheus-0
   ```

### Missing Metrics

**Problem**: Metrics not appearing in Prometheus

**Solutions**:
1. Verify `/metrics` endpoint is accessible:
   ```bash
   kubectl port-forward pod/mcp-server-xyz 8000:8000
   curl http://localhost:8000/metrics
   ```

2. Check pod labels:
   ```bash
   kubectl get pods --show-labels
   ```

3. Verify PodMonitor targets in Prometheus UI:
   - Go to Prometheus → Status → Targets
   - Look for `podMonitor/namespace/mcp-server/0`

### Grafana Dashboard Issues

**Problem**: Dashboard showing no data

**Solutions**:
1. Verify data source configuration
2. Check metric names in Prometheus:
   ```promql
   {__name__=~"mcp_.*"}
   ```

3. Validate template variables:
   ```promql
   label_values(mcp_server_uptime_seconds, instanceId)
   ```

### Common PromQL Queries

For debugging, try these queries in Prometheus:

```promql
# Check if metrics are being scraped
up{job=~".*mcp.*"}

# List all MCP metrics
{__name__=~"mcp_.*"}

# Check instance labels
mcp_server_uptime_seconds

# Schema registry health
mcp_schema_registry_status
```

## Best Practices

### Resource Limits

Configure appropriate limits for the PodMonitor:

```yaml
podMonitor:
  sampleLimit: 10000      # Limit samples per scrape
  targetLimit: 100        # Limit targets
  scrapeTimeout: 10s      # Reasonable timeout
```

### Label Management

Keep labels consistent across deployments:

```yaml
global:
  cluster: "production-us-west-2"
  environment: "production"
  
commonLabels:
  team: "platform"
  component: "mcp-server"
```

### Alerting

Create alerts based on the metrics:

```yaml
# PrometheusRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mcp-server-alerts
spec:
  groups:
    - name: mcp-server
      rules:
        - alert: MCPServerDown
          expr: up{job=~".*mcp.*"} == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "MCP Server is down"
            
        - alert: SchemaRegistryUnhealthy
          expr: mcp_schema_registry_status == 0
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "Schema Registry is unhealthy"
```

## Integration Examples

### Kubernetes Deployment

```bash
# Deploy with monitoring enabled
helm install mcp-prod ./helm \
  --set monitoring.enabled=true \
  --set monitoring.podMonitor.enabled=true \
  --set global.environment=production \
  --set global.cluster=prod-us-west-2
```

### Prometheus Stack Integration

```yaml
# kube-prometheus-stack values
prometheus:
  prometheusSpec:
    podMonitorSelector:
      matchLabels:
        release: prometheus

grafana:
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
        - name: 'mcp-dashboards'
          type: file
          folder: 'MCP'
          options:
            path: /var/lib/grafana/dashboards/mcp
```

This comprehensive monitoring setup provides complete observability for your Kafka Schema Registry MCP Server deployment with proper instance identification and rich visualizations. 