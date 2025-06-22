# MCP 2025-06-18 Protocol Version Header Validation

This document describes the implementation of MCP-Protocol-Version header validation in the Kafka Schema Registry MCP Server, ensuring compliance with the MCP 2025-06-18 specification.

## Overview

The MCP 2025-06-18 specification requires all HTTP requests after initialization to include the `MCP-Protocol-Version` header. This server implements comprehensive header validation middleware to ensure compliance.

## Implementation Details

### Header Validation Middleware

The server implements FastAPI middleware that validates the `MCP-Protocol-Version` header on all incoming requests:

```python
async def validate_mcp_protocol_version_middleware(request: Request, call_next):
    """
    Middleware to validate MCP-Protocol-Version header on all requests.
    
    Per MCP 2025-06-18 specification, all HTTP requests after initialization
    must include the MCP-Protocol-Version header.
    """
```

### Supported Protocol Version

- **Current Version**: `2025-06-18`
- **Supported Versions**: `["2025-06-18"]`

### Exempt Paths

The following paths are exempt from header validation (as required by the specification):

- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics endpoint  
- `/ready` - Kubernetes readiness check
- `/.well-known/*` - OAuth discovery and other well-known endpoints

### Response Behavior

#### Valid Requests
Requests with the correct `MCP-Protocol-Version: 2025-06-18` header:
- ✅ Pass validation
- ✅ Processed normally
- ✅ Response includes `MCP-Protocol-Version: 2025-06-18` header

#### Missing Header
Requests without the `MCP-Protocol-Version` header:
- ❌ Return `400 Bad Request`
- ❌ Include detailed error message
- ✅ Response includes `MCP-Protocol-Version: 2025-06-18` header

```json
{
  "error": "Missing MCP-Protocol-Version header",
  "details": "The MCP-Protocol-Version header is required for all MCP requests per MCP 2025-06-18 specification",
  "supported_versions": ["2025-06-18"],
  "example": "MCP-Protocol-Version: 2025-06-18"
}
```

#### Invalid Header
Requests with an unsupported protocol version:
- ❌ Return `400 Bad Request`
- ❌ Include version-specific error message
- ✅ Response includes `MCP-Protocol-Version: 2025-06-18` header

```json
{
  "error": "Unsupported MCP-Protocol-Version",
  "details": "Received version 'invalid-version' is not supported",
  "supported_versions": ["2025-06-18"],
  "received_version": "invalid-version"
}
```

#### Exempt Endpoints
Requests to exempt paths:
- ✅ No header validation required
- ✅ Processed normally
- ✅ Response includes `MCP-Protocol-Version: 2025-06-18` header

## Client Integration Guide

### Required Changes

All MCP clients must be updated to include the `MCP-Protocol-Version` header in every request:

```javascript
// Example: JavaScript/Node.js client
const response = await fetch('https://your-mcp-server.com/mcp', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'MCP-Protocol-Version': '2025-06-18'
  },
  body: JSON.stringify(mcpRequest)
});
```

```python
# Example: Python client
import requests

response = requests.post(
    'https://your-mcp-server.com/mcp',
    headers={
        'Content-Type': 'application/json',
        'MCP-Protocol-Version': '2025-06-18'
    },
    json=mcp_request
)
```

```bash
# Example: curl
curl -X POST https://your-mcp-server.com/mcp \
  -H "Content-Type: application/json" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Testing Client Compliance

Use the provided test endpoints to verify your client implementation:

```bash
# Test MCP endpoint (requires header)
curl -X POST http://localhost:8000/mcp \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test without header (should return 400)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test exempt endpoint (works without header)
curl http://localhost:8000/health
```

## Migration Strategy

### Phase 1: Preparation (Before Deployment)
1. **Update all MCP clients** to include the `MCP-Protocol-Version` header
2. **Test clients** against the new server implementation
3. **Verify monitoring tools** can still access health/metrics endpoints

### Phase 2: Deployment
1. **Deploy the updated server** with header validation enabled
2. **Monitor error logs** for clients missing the header
3. **Update any remaining clients** that generate 400 errors

### Phase 3: Verification
1. **Confirm all requests** include the proper header
2. **Validate monitoring** and health checks continue working
3. **Review compliance status** using the built-in tools

## Monitoring and Observability

### Prometheus Metrics

The server exposes metrics for header validation:

```
# MCP Protocol Version header validation attempts
mcp_protocol_header_validations_total

# MCP Protocol Version header validation failures  
mcp_protocol_header_validation_failures_total

# MCP Protocol Version header validation successes
mcp_protocol_header_validation_successes_total

# MCP Protocol Version information
mcp_protocol_version_info{version="2025-06-18"} 1
```

### Health Check Information

The health endpoint includes compliance information:

```json
{
  "status": "healthy",
  "mcp_protocol_version": "2025-06-18",
  "mcp_compliance": {
    "header_validation_enabled": true,
    "jsonrpc_batching_disabled": true,
    "specification": "MCP 2025-06-18"
  }
}
```

### Compliance Status Tool

Use the built-in compliance status tool to verify implementation:

```bash
# Check compliance status
curl -X POST http://localhost:8000/mcp \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_mcp_compliance_status"
    },
    "id": 1
  }'
```

Response includes detailed compliance information:

```json
{
  "protocol_version": "2025-06-18",
  "supported_versions": ["2025-06-18"],
  "header_validation_enabled": true,
  "compliance_status": "COMPLIANT",
  "header_validation": {
    "required_header": "MCP-Protocol-Version",
    "exempt_paths": ["/health", "/metrics", "/ready", "/.well-known"],
    "validation_active": true,
    "error_response_code": 400
  }
}
```

## Testing

### Automated Test Suite

Run the comprehensive test suite:

```bash
# Run all tests
python test_mcp_header_validation.py

# Run with demonstration mode
python test_mcp_header_validation.py --demo

# Run with pytest for detailed output
python -m pytest test_mcp_header_validation.py -v

# Test against live server
TEST_SERVER_URL=http://localhost:8000 python test_mcp_header_validation.py
```

### Manual Testing

Use the OAuth discovery endpoint testing tool:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "test_oauth_discovery_endpoints",
      "arguments": {"server_url": "http://localhost:8000"}
    },
    "id": 1
  }'
```

## Breaking Changes

### What Changed
- **Header Requirement**: All MCP requests now require `MCP-Protocol-Version` header
- **Error Responses**: Missing/invalid headers return 400 Bad Request
- **Response Headers**: All responses include the protocol version header

### What Stayed the Same
- **Exempt Endpoints**: Health, metrics, and well-known endpoints work without headers
- **JSON-RPC Protocol**: Core MCP functionality unchanged
- **Authentication**: OAuth and other auth mechanisms unaffected
- **Tool Functionality**: All 48 schema registry tools work identically

### Backward Compatibility
- ❌ **MCP Endpoints**: Require header update (breaking change)
- ✅ **Monitoring Endpoints**: Unchanged (health, metrics, ready)
- ✅ **OAuth Discovery**: Unchanged (well-known endpoints)
- ✅ **Tool Responses**: Same format and functionality

## Troubleshooting

### Common Issues

#### 400 Bad Request Errors
**Symptom**: All MCP requests return 400 with "Missing MCP-Protocol-Version header"

**Solution**: Add the required header to all client requests:
```
MCP-Protocol-Version: 2025-06-18
```

#### Monitoring Tools Broken
**Symptom**: Health check or metrics endpoints return errors

**Solution**: These endpoints should be exempt. Check:
1. Request path is exactly `/health`, `/metrics`, or `/ready`
2. No middleware conflicts in deployment
3. Server logs for specific errors

#### OAuth Discovery Issues
**Symptom**: OAuth endpoints return unexpected errors

**Solution**: Well-known endpoints are exempt. Verify:
1. Path starts with `/.well-known/`
2. OAuth is properly configured if expecting 200 responses
3. Check server logs for authentication issues

#### Version Mismatch
**Symptom**: "Unsupported MCP-Protocol-Version" errors

**Solution**: Ensure client sends exactly `2025-06-18`:
```bash
# Correct
curl -H "MCP-Protocol-Version: 2025-06-18" ...

# Incorrect
curl -H "MCP-Protocol-Version: 2025-06-18-draft" ...
curl -H "MCP-Protocol-Version: 2.0" ...
```

### Debug Commands

```bash
# Check server compliance status
curl http://localhost:8000/health | jq .mcp_compliance

# Test header validation
curl -I -X POST http://localhost:8000/mcp

# Check Prometheus metrics for validation stats
curl http://localhost:8000/metrics | grep mcp_protocol_header

# Verify all responses include the header
curl -I http://localhost:8000/health
curl -I http://localhost:8000/metrics  
curl -I http://localhost:8000/.well-known/oauth-authorization-server-custom
```

## Specification Compliance

This implementation ensures full compliance with MCP 2025-06-18:

- ✅ **Header Validation**: All MCP requests require `MCP-Protocol-Version` header
- ✅ **Error Responses**: 400 Bad Request for missing/invalid headers
- ✅ **Version Negotiation**: Server declares supported versions in error responses
- ✅ **Response Headers**: All responses include protocol version header
- ✅ **Exempt Endpoints**: Health, metrics, and well-known paths excluded
- ✅ **JSON-RPC Batching**: Disabled per specification
- ✅ **Backward Compatibility**: Monitoring endpoints unaffected

## Support

For issues related to MCP-Protocol-Version header validation:

1. **Check compliance status** using the built-in tool
2. **Review client implementation** against this guide
3. **Run the test suite** to verify server functionality
4. **Examine server logs** for specific error details
5. **Use debug commands** to troubleshoot specific issues

The implementation follows the MCP 2025-06-18 specification exactly and provides comprehensive tooling for migration and troubleshooting.
