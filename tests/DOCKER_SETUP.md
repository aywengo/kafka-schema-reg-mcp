# Unified Docker Test Environment

This directory contains a **unified Docker setup** that supports both single-registry and multi-registry testing scenarios using a single `docker-compose.yml` file.

## Overview

The unified setup provides:
- **Development Environment**: Kafka + Schema Registry on standard ports (9092, 38081)
- **Production Environment**: Kafka + Schema Registry on alternate ports (39093, 38082)
- **AKHQ UI**: Web interface for monitoring both environments (38080)
- **Flexible Deployment**: Can run just DEV, or full multi-registry setup

## Quick Start

### Start Full Environment (Recommended)
```bash
# Start all services (DEV + PROD + UI)
./start_test_environment.sh

# Or explicitly
./start_test_environment.sh multi
```

### Start Development Only
```bash
# Start only DEV registry for single-registry tests
./start_test_environment.sh dev
```

### Stop Environment
```bash
# Normal stop
./stop_test_environment.sh

# Clean stop (removes volumes)
./stop_test_environment.sh clean
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Kafka DEV | `localhost:9092` | Primary Kafka for single-registry tests |
| Schema Registry DEV | `localhost:38081` | Primary registry (backward compatibility) |
| Kafka PROD | `localhost:39093` | Secondary Kafka for multi-registry tests |
| Schema Registry PROD | `localhost:38082` | Secondary registry (forward compatibility) |
| AKHQ UI | `http://localhost:38080` | Web UI for monitoring |

## Environment Configurations

### Single-Registry Tests
For existing tests that expect single registry:
- **Kafka**: `localhost:9092`
- **Schema Registry**: `localhost:38081`
- **Environment Variables**:
  ```bash
  SCHEMA_REGISTRY_URL=http://localhost:38081
  ```

### Multi-Registry Tests
For tests requiring multiple registries:
- **DEV Registry**: `localhost:38081`
- **PROD Registry**: `localhost:38082`
- **Environment Variables**:
  ```bash
  SCHEMA_REGISTRY_NAME_1=dev
  SCHEMA_REGISTRY_URL_1=http://localhost:38081
  SCHEMA_REGISTRY_NAME_2=prod
  SCHEMA_REGISTRY_URL_2=http://localhost:38082
  ```

## Test Compatibility

### ✅ Fully Compatible
All existing tests work without modification:
- Single-registry tests use DEV registry (port 38081)
- Multi-registry tests use both DEV and PROD registries
- MCP client tests work with both modes

### 🔄 Migration Benefits
1. **Unified Setup**: One docker-compose.yml for all scenarios
2. **Port Compatibility**: DEV registry uses standard port 38081
3. **Backward Compatibility**: All existing test configurations work
4. **Enhanced Flexibility**: Can start partial or full environments

## Container Details

### Kafka Clusters
```yaml
# Development Kafka
kafka-dev:
  ports: ["9092:9092", "9094:9094", "39092:39092"]
  cluster_id: "dev-cluster-kafka-mcp"

# Production Kafka  
kafka-prod:
  ports: ["39093:9093", "39095:9095"]
  cluster_id: "prod-cluster-kafka-mcp"
```

### Schema Registries
```yaml
# Development Schema Registry
schema-registry-dev:
  port: "38081:8081"
  compatibility: "backward"
  kafka: kafka-dev:9092

# Production Schema Registry
schema-registry-prod:
  port: "38082:8082" 
  compatibility: "forward"
  kafka: kafka-prod:9093
```

### AKHQ UI
```yaml
akhq:
  port: "38080:8080"
  connections:
    - development: kafka-dev + schema-registry-dev
    - production: kafka-prod + schema-registry-prod
```

## Advanced Usage

### Environment-Specific Operations

#### Check Service Health
```bash
# Check all services
docker-compose ps

# Check specific service
docker logs schema-registry-dev
docker logs schema-registry-prod
```

#### Scale Services
```bash
# Start only required services
docker-compose up -d kafka-dev schema-registry-dev

# Add PROD services later
docker-compose up -d kafka-prod schema-registry-prod
```

#### Restart Specific Service
```bash
# Restart DEV registry
docker-compose restart schema-registry-dev

# Restart PROD registry  
docker-compose restart schema-registry-prod
```

### Development Workflow

1. **Start Environment**:
   ```bash
   ./start_test_environment.sh
   ```

2. **Run Tests**:
   ```bash
   # Single-registry tests
   python test_basic_operations.py
   
   # Multi-registry tests
   python test_multi_registry_sync.py
   ```

3. **Monitor in UI**:
   - Open http://localhost:38080
   - Switch between DEV and PROD connections

4. **Clean Up**:
   ```bash
   ./stop_test_environment.sh clean
   ```

## Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :38081
lsof -i :38082

# Kill conflicting processes
./stop_test_environment.sh clean
```

### Service Startup Issues
```bash
# Check logs
docker logs kafka-dev
docker logs schema-registry-dev

# Restart specific service
docker-compose restart schema-registry-dev
```

### Network Issues
```bash
# Recreate network
docker network rm kafka-test-network
./start_test_environment.sh
```

### Reset Everything
```bash
# Complete cleanup and restart
./stop_test_environment.sh clean
./start_test_environment.sh multi
```

## Migration from Old Setup

### Removed Files
- ❌ `docker-compose.test.yml` (single-registry)
- ❌ `docker-compose.multi-test.yml` (multi-registry)
- ❌ `start_multi_registry_environment.sh`
- ❌ `stop_multi_registry_environment.sh`

### New Files
- ✅ `docker-compose.yml` (unified setup)
- ✅ Enhanced `start_test_environment.sh` (supports modes)
- ✅ Enhanced `stop_test_environment.sh` (supports cleanup levels)

### Update Your Scripts
Replace old references:
```bash
# Old
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.multi-test.yml up -d

# New
docker-compose up -d
```

## Performance Notes

### Resource Usage
- **DEV Only**: ~1.5GB RAM, 2 containers
- **Full Setup**: ~3GB RAM, 5 containers
- **Startup Time**: 
  - DEV only: ~45 seconds
  - Full setup: ~90 seconds

### Recommended Settings
```bash
# Docker Desktop settings
Memory: 4GB minimum, 6GB recommended
CPU: 2+ cores
Disk: 20GB available
```

## Support

For issues with the unified setup:
1. Check logs: `docker-compose logs -f`
2. Verify connectivity: `curl http://localhost:38081/subjects`
3. Clean restart: `./stop_test_environment.sh clean && ./start_test_environment.sh`
4. Check this documentation for troubleshooting steps 