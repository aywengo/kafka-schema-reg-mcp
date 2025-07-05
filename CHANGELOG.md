# Changelog

All notable changes to the Kafka Schema Registry MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.3] - 2025-07-01

### Added
- MCP ping/pong protocol support for health checks and proxy compatibility
- Comprehensive `SECURITY.md` with vulnerability reporting process and security practices
- Automatic GitHub issue creation for critical vulnerabilities in security scan workflow
- Enhanced `.trivyignore` documentation with detailed CVE analysis and security rationale

### Fixed
- Docker build failures due to incorrect dependency versions (avro-python3)
- Security vulnerabilities: 22 CVEs addressed through package removal and documentation

### Security
- Enhanced Dockerfile with security hardening (removed perl, ncurses packages)
- Updated all Python dependencies to latest secure versions with conservative build compatibility
- Added file permissions (750 for directories, 550 for Python files) and restrictive umask
- Documented security exceptions for 22 CVEs with detailed non-exploitability rationale
- Enhanced security scanning workflow with multi-scan dashboard and automated monitoring

## [2.0.2] - 2025-06-30

### Fixed
- **🔒 Security Issue #26**: Resolved credential exposure vulnerability in logging and object representations
  - **Secure Header Management**: Implemented `SecureHeaderDict` to generate fresh headers with credentials on each access instead of storing them persistently
  - **Logging Security Filter**: Added `SensitiveDataFilter` to automatically mask authorization headers and sensitive data in all log messages
  - **Safe Object Representations**: Updated `RegistryClient` and `RegistryConfig` `__repr__` and `__str__` methods to mask credentials
  - **Library Security Configuration**: Enhanced secure logging for requests/urllib3 libraries to prevent credential leakage
  - **Dynamic Authentication**: Modified authentication flow to create headers dynamically without storing credentials as instance variables
- **🔒 Security Issue #24**: Resolved credential exposure vulnerability in SSL/TLS configuration
  - **Explicit SSL/TLS Certificate Verification**: All HTTP requests now use explicit SSL certificate verification
  - **Secure Sessions**: All Schema Registry and OAuth provider communications use secure `requests.Session` with `verify=True`
  - **SecureHTTPAdapter**: Custom HTTP adapter with enhanced SSL/TLS security configuration
  - **TLS 1.2+ Enforcement**: Minimum TLS version 1.2 with strong cipher suites only
  - **Hostname Verification**: Strict hostname verification enabled for all connections
  - **Custom CA Bundle Support**: Enterprise environment compatibility with custom Certificate Authority bundles

### Added

#### Interactive Single Schema Migration with Elicitation Support
- **🤖 Smart Schema Migration**: Interactive `migrate_schema_interactive()` function with intelligent user preference elicitation
  - **Schema Existence Detection**: Automatically detects if target schema exists using HTTP requests to target registry
  - **Conditional Elicitation**: Dynamic elicitation fields based on schema existence status
  - **User Preference Collection**: Interactive collection of migration preferences including:
    - `replace_existing`: Whether to replace existing schemas in target registry
    - `backup_before_replace`: Whether to create backup before replacement
    - `preserve_ids`: Whether to preserve schema IDs during migration
    - `compare_after_migration`: Whether to verify schemas match after migration
    - `migrate_all_versions`: Whether to migrate all versions or just latest
    - `dry_run`: Whether to perform a test run without actual changes

- **🔍 Pre-Migration Intelligence**: Smart pre-migration analysis and user guidance
  - **Target Registry Scanning**: Uses HTTP requests to check schema existence in target registry
  - **Version Detection**: Identifies existing versions in target registry for informed decisions
  - **Conflict Resolution**: Blocks migration gracefully when user declines replacement of existing schemas
  - **Safety Checks**: Prevents accidental overwrites through explicit user confirmation

- **💾 Automatic Backup Operations**: Integrated backup creation before schema replacement
  - **Conditional Backup**: Creates backups only when schema exists and user requests it
  - **Export Integration**: Uses existing `export_schema_tool` for reliable backup creation
  - **Backup Metadata**: Includes backup results in migration response for audit trails
  - **Error Handling**: Graceful backup failure handling with warning messages

- **✅ Post-Migration Verification**: Comprehensive schema verification after successful migration
  - **Multi-Level Checks**: Validates schema existence, content match, type match, and ID preservation
  - **Detailed Reporting**: Provides specific check results with pass/fail status
  - **Schema Comparison**: Compares source and target schemas for content accuracy
  - **ID Preservation Validation**: Verifies schema IDs match when preservation is requested
  - **Overall Success Indicator**: Clear success/failure status with detailed check breakdown

- **📊 Comprehensive Result Metadata**: Enhanced migration results with complete operation context
  - **Elicitation Status**: Records whether elicitation was used and what preferences were collected
  - **Schema Existence**: Documents whether schema existed in target before migration
  - **User Preferences**: Captures all elicited user preferences for audit and debugging
  - **Backup Results**: Includes backup operation results when performed
  - **Verification Results**: Complete post-migration verification details with individual check results

- **🛡️ Robust Error Handling**: Comprehensive error management for all migration scenarios
  - **Elicitation Failures**: Graceful handling when user input cannot be collected
  - **Replacement Declined**: Clear error messages when user declines schema replacement
  - **Backup Failures**: Warning handling for backup operations with migration continuation
  - **Verification Failures**: Detailed reporting of post-migration verification issues
  - **Network Errors**: Resilient handling of registry connectivity issues during existence checks

#### Migration Elicitation Infrastructure
- **📝 Schema Migration Elicitation**: New `create_migrate_schema_elicitation()` function
  - **Dynamic Field Generation**: Context-aware elicitation fields based on migration scenario
  - **Conditional Logic**: Different fields shown based on whether schema exists in target
  - **Form Validation**: Structured form elicitation with validation and sensible defaults
  - **User-Friendly Interface**: Clear descriptions and help text for migration decisions

#### Testing & Quality Assurance
- **🧪 Comprehensive Test Coverage**: Extensive testing suite ensuring reliability
  - **9 New Test Functions**: Complete coverage of interactive migration functionality
  - **Edge Case Testing**: Tests for declined replacements, elicitation failures, and error scenarios
  - **Integration Testing**: End-to-end workflow testing with mocked registry clients and HTTP requests
  - **Verification Testing**: Tests for all post-migration verification scenarios
  - **Single Registry Support**: Tests ensuring compatibility with single registry mode

### Usage Example

```python
# Interactive schema migration with elicitation
from interactive_tools import migrate_schema_interactive

result = await migrate_schema_interactive(
    subject="user-events",
    source_registry="development", 
    target_registry="staging",
    source_context="events",
    target_context="events",
    # No migration preferences specified - will trigger elicitation
    migrate_schema_tool=migrate_schema_tool,
    export_schema_tool=export_schema_tool,
    registry_manager=registry_manager,
    registry_mode="multi"
)

# Result includes elicitation metadata, backup results, and verification
print(f"Elicitation used: {result['elicitation_used']}")
print(f"Schema existed in target: {result['schema_existed_in_target']}")
print(f"Backup created: {result.get('backup_result', {}).get('success', False)}")
print(f"Verification passed: {result.get('verification_result', {}).get('overall_success', False)}")
```

## [2.0.1] - 2025-06-27

### 📈 **Performance & Code Quality Improvements**
- **🔧 Major Code Refactoring**: Streamlined codebase across 74 files with improved readability and performance
- **📊 Reduced Code Complexity**: Simplified error handling, consolidated list comprehensions, and enhanced function definitions
- **🧹 Clean Architecture**: Removed 2,442 lines of redundant code while maintaining full functionality
- **⚡ Memory Optimization**: Enhanced logging statements and improved resource management

### 🛡️ **Enhanced Schema Validation & Local Processing**
- **🏠 Local JSON Schema Handling**: Implemented custom handler for draft-07 JSON Schema meta-schemas
- **🚀 Zero Network Dependencies**: Local schema resolution prevents external network requests during validation
- **📦 Custom Requests Adapter**: Enhanced requests library integration with mock responses for draft-07 schemas
- **⚡ Improved Performance**: Faster validation and testing with consistent local behavior

### 🎭 **Advanced Elicitation Management**
- **✨ Enhanced Elicitation Tools**: Added structured output decorators for `cancel_elicitation_request` and `get_elicitation_status`
- **📋 New Schema Definitions**: Introduced comprehensive schemas for elicitation requests and status management
- **🔄 Improved Response Structure**: Better error handling and compliance with expected response formats
- **🎯 Reliable Validation**: Local draft-07 schema resolver for consistent elicitation workflows

### 🔄 **Robust Migration Confirmation System**
- **⚠️ New Exception Handling**: `IDPreservationError` and `MigrationConfirmationRequired` for better migration control
- **✅ User Confirmation Flow**: Enhanced `migrate_schema_tool` with ID preservation failure handling
- **🛠️ New Confirmation Tool**: `confirm_migration_without_ids_tool` for proceeding without ID preservation
- **📊 Detailed Migration Metadata**: Comprehensive structured output for migration results
- **🧪 Comprehensive Testing**: 233 new test cases for migration confirmation scenarios
            

## [2.0.0] - 2025-06-26

### 🚀 MAJOR RELEASE: FastMCP 2.8.0+ Upgrade & MCP 2025-06-18 Specification Compliance

This **major version release** represents the complete migration to **FastMCP 2.8.0+** framework and full compliance with the **MCP 2025-06-18 specification**. This upgrade ensures compatibility with the latest Message Control Protocol ecosystem and provides a foundation for modern AI agent integration.

**🔥 BREAKING CHANGES & FRAMEWORK MIGRATION:**
- **FastMCP 2.8.0+ Framework**: Complete migration from legacy `mcp[cli]==1.9.4` to modern FastMCP architecture
- **MCP 2025-06-18 Compliance**: Full support for the latest MCP specification
- **JSON-RPC Batching Removal**: JSON-RPC batching explicitly disabled per MCP 2025-06-18 specification
- **Enhanced Authentication**: Native FastMCP BearerAuth provider with OAuth 2.0 integration
- **Modernized Client API**: Updated client interface using FastMCP's dependency injection system

#### 🎯 Why v2.0.0? - Major Version Justification

This release qualifies as a **major version bump** because it introduces:

1. **📡 MCP Framework Migration**: Complete architectural shift from legacy MCP SDK to FastMCP 2.8.0+
2. **🚫 JSON-RPC Batching Removal**: Breaking change removing JSON-RPC batching support (MCP 2025-06-18 requirement)
3. **🔄 Client API Changes**: New FastMCP client interface replacing legacy `mcp.ClientSession`
4. **🔐 Authentication Architecture**: Migration to FastMCP's native BearerAuth system
5. **📚 Import Structure Changes**: Updated import paths from `mcp.server.fastmcp` to `fastmcp`
6. **🔧 Dependency System**: New FastMCP dependency injection for access tokens and authentication
7. **🏗️ Test Framework Updates**: Complete test suite migration to new FastMCP client API
8. **📖 API Surface Evolution**: Enhanced OAuth discovery endpoints and MCP compliance features

**Migration Impact**: While basic functionality remains the same, the underlying MCP framework has been completely modernized. Custom clients and tests will need updates to use the new FastMCP API, and any clients using JSON-RPC batching must migrate to individual requests.

#### Added

##### MCP 2025-06-18 Specification Compliance
- **🚫 JSON-RPC Batching Disabled**: Explicitly disabled JSON-RPC batching per MCP 2025-06-18 specification
  - FastMCP configuration: `allow_batch_requests: False`, `batch_support: False`
  - Protocol version enforcement: `protocol_version: "2025-06-18"`
  - Clear separation between JSON-RPC batching (disabled) and application-level batching (enabled)
- **📊 Compliance Status Tool**: New `get_mcp_compliance_status()` tool for verification
  - Real-time compliance status checking
  - Configuration validation and verification
  - Migration guidance and performance notes
  - Detailed batching configuration status
- **📋 Application-Level Batching Enhanced**: Clear distinction and enhanced functionality
  - `clear_context_batch()`: Uses individual requests internally with parallel processing
  - `clear_multiple_contexts_batch()`: Enhanced with compliance metadata
  - Performance maintained through ThreadPoolExecutor and async coordination
- **📚 Comprehensive Migration Guide**: `MCP-2025-06-18-MIGRATION-GUIDE.md`
  - Step-by-step migration from JSON-RPC batching to individual requests
  - Performance optimization strategies using parallel processing
  - Code examples for client-side migration patterns
  - Troubleshooting guide and rollout timeline

##### FastMCP 2.8.0+ Framework Integration
- **Modern MCP Architecture**: Complete migration from legacy `mcp[cli]==1.9.4` to FastMCP 2.8.0+
- **Native BearerAuth Provider**: FastMCP's built-in authentication system with OAuth 2.0 support
- **Dependency Injection System**: Modern access token management using FastMCP's `get_access_token()`
- **Enhanced Transport Support**: Native stdio, SSE, and Streamable HTTP transport capabilities

##### OAuth Provider Integration (FastMCP Compatible)
- **Multi-Provider OAuth Support**: Native integration with 5 major identity platforms
  - **Azure AD / Entra ID**: Enterprise identity with Microsoft Graph API scopes
  - **Google OAuth 2.0**: Google Workspace and Cloud integration
  - **Keycloak**: Self-hosted open-source identity management
  - **Okta**: Enterprise SaaS identity platform
  - **GitHub OAuth**: GitHub and GitHub Apps authentication
- **FastMCP BearerAuthProvider**: Native FastMCP authentication provider with scope-based authorization
- **Scope-Based Permissions**: Fine-grained `read`, `write`, `admin` permissions mapped to MCP tools
- **Development Token Support**: Safe testing tokens (`dev-token-read`, `dev-token-write`, etc.)

##### SSL/TLS Security Enhancement (Issue #24)
- **🔒 Explicit SSL/TLS Certificate Verification**: All HTTP requests now use explicit SSL certificate verification
  - **Secure Sessions**: All Schema Registry and OAuth provider communications use secure `requests.Session` with `verify=True`
  - **SecureHTTPAdapter**: Custom HTTP adapter with enhanced SSL/TLS security configuration
  - **TLS 1.2+ Enforcement**: Minimum TLS version 1.2 with strong cipher suites only
  - **Hostname Verification**: Strict hostname verification enabled for all connections
- **🏢 Custom CA Bundle Support**: Enterprise environment compatibility with custom Certificate Authority bundles
  - **Environment Variable**: `CUSTOM_CA_BUNDLE_PATH` for custom CA certificate files
  - **Automatic Fallback**: Falls back to system CA bundle if custom bundle is missing or invalid
  - **Corporate Networks**: Support for internal/corporate certificate authorities
- **📊 Security Logging & Monitoring**: Comprehensive SSL/TLS status tracking and logging
  - **SSL Configuration Logging**: Startup logging of SSL/TLS verification status and CA bundle configuration
  - **Session Creation Logging**: Secure session creation logged for each registry client
  - **Registry Info Integration**: SSL verification status included in registry information and connection tests
  - **Sensitive Data Protection**: Enhanced logging filters to prevent credential exposure
- **⚠️ SSL Error Handling**: Robust error handling for SSL/TLS connection failures
  - **SSLError Detection**: Specific handling and reporting of SSL certificate verification failures
  - **Clear Error Messages**: Detailed error messages for SSL-related connection issues
  - **Status Reporting**: SSL error flags in connection test results for debugging
- **🧪 Comprehensive Testing**: Dedicated SSL/TLS integration test suite with 11 test cases
  - **Test Coverage**: SSL verification, custom CA bundles, secure sessions, error handling
  - **Integration Testing**: Included in both essential and full test suite categories
  - **Environment Testing**: SSL environment variable control and configuration testing

##### Enhanced Client API
- **FastMCP Client**: Modern client interface replacing legacy `mcp.ClientSession`
- **Simplified Connection**: Direct `Client()` instantiation with automatic protocol handling
- **Async/Await Support**: Native async operations with better error handling
- **Improved Testing**: Streamlined test framework with easier mocking and setup

##### Updated Test Framework
- **FastMCP Client Migration**: All tests updated to use new `fastmcp.Client` interface
- **Simplified Test Setup**: Removed complex server parameter configuration
- **Better Error Handling**: Enhanced error messages and debugging capabilities
- **OAuth Discovery Testing**: Comprehensive testing of MCP 2025-06-18 OAuth endpoints

##### Documentation & Examples
- **FastMCP Usage Examples**: Updated code examples for new client API
- **OAuth Discovery Endpoints**: MCP-compliant OAuth metadata endpoints
- **Migration Guide**: Comprehensive guide for upgrading from legacy MCP SDK
- **Enhanced Error Messages**: Better debugging information for authentication issues

#### Changed

##### JSON-RPC Batching Removal (Breaking Change)
- **⚠️ Breaking Change**: JSON-RPC batching support completely removed
  - **Reason**: MCP 2025-06-18 specification explicitly removes JSON-RPC batching
  - **Impact**: Clients using batch requests must migrate to individual requests
  - **Migration Required**: See `MCP-2025-06-18-MIGRATION-GUIDE.md` for detailed migration steps
- **Application-Level Batching**: Enhanced to use individual requests internally
  - `clear_context_batch()`: Now uses parallel individual requests for performance
  - `clear_multiple_contexts_batch()`: Enhanced with individual request coordination
  - Maintains performance through ThreadPoolExecutor and async processing
- **Performance Strategy**: Client-side request queuing replaces JSON-RPC batching
  - Parallel processing with `asyncio.gather()` for multiple operations
  - Request throttling and connection pooling for efficiency
  - Enhanced error handling with individual request isolation

##### Server Configuration Changes
- **FastMCP Configuration**: Updated for MCP 2025-06-18 compliance
  ```python
  config = {
      "name": server_name,
      "allow_batch_requests": False,      # Explicitly disabled
      "batch_support": False,             # No batch support
      "protocol_version": "2025-06-18",   # Compliance version
      "jsonrpc_batching_disabled": True,  # Clear flag,
  }
  ```
- **Enhanced Logging**: Clear startup messages about batching status
- **Resource Updates**: All MCP resources now include compliance status

#### Improved

##### Framework Architecture
- **Performance**: FastMCP 2.8.0+ provides better performance and reliability than legacy MCP SDK
- **Error Handling**: Enhanced error messages and recovery mechanisms with FastMCP's improved architecture
- **Memory Usage**: More efficient memory management with modern FastMCP framework
- **Protocol Compliance**: Full compliance with MCP 2025-06-18 specification requirements

##### Authentication System
- **Simplified Configuration**: Streamlined OAuth setup with FastMCP's native BearerAuth
- **Better Token Management**: FastMCP's dependency injection system for access tokens
- **Enhanced Security**: Improved JWT validation with FastMCP's built-in cryptographic verification
- **Scope Validation**: More robust scope checking with FastMCP's permission system

##### Client Experience
- **Modern API**: Clean, async-first client interface with FastMCP.Client
- **Simplified Connection**: Direct client instantiation without complex server parameters
- **Better Debugging**: Enhanced error messages and stack traces with FastMCP
- **Test Simplicity**: Streamlined test setup and mocking capabilities

##### Developer Experience
- **Migration Support**: Comprehensive migration guide from legacy MCP SDK
- **Code Examples**: Updated examples using modern FastMCP patterns
- **Documentation**: Clear documentation of FastMCP-specific features and capabilities
- **Troubleshooting**: Better diagnostic tools for FastMCP authentication issues

#### Technical Details

##### MCP 2025-06-18 Compliance Summary
| Feature | Status | Implementation |
|---------|---------|----------------|
| **JSON-RPC Batching** | ❌ **DISABLED** | FastMCP config: `allow_batch_requests: False` |
| **Individual Requests** | ✅ **REQUIRED** | All operations use individual JSON-RPC requests |
| **Application Batching** | ✅ **ENHANCED** | Uses individual requests internally with parallel processing |
| **Protocol Version** | ✅ **2025-06-18** | Explicit protocol version enforcement |
| **Compliance Tools** | ✅ **ADDED** | `get_mcp_compliance_status()` for verification |

##### FastMCP 2.8.0+ Framework Migration
| Component | Legacy (v1.x) | FastMCP 2.8.0+ (v2.0.0) |
|-----------|---------------|--------------------------| 
| **Framework** | `mcp[cli]==1.9.4` | `fastmcp>=2.8.0` |
| **Server Import** | `from mcp.server.fastmcp import FastMCP` | `from fastmcp import FastMCP` |
| **Client Import** | `from mcp import ClientSession, StdioServerParameters` | `from fastmcp import Client` |
| **JSON-RPC Batching** | Supported (legacy) | **DISABLED** (MCP 2025-06-18) |
| **Authentication** | Custom OAuth implementation | Native FastMCP BearerAuthProvider |
| **Token Access** | Manual token parsing | FastMCP dependency injection (`get_access_token()`) |
| **Transport** | stdio via complex setup | Native stdio, SSE, HTTP support |

##### Migration from JSON-RPC Batching
| Aspect | Before (JSON-RPC Batching) | After (Individual Requests) |
|--------|---------------------------|----------------------------|
| **Request Format** | Array of JSON-RPC requests | Individual JSON-RPC requests |
| **Network Overhead** | 1 HTTP request for N operations | N HTTP requests |
| **Performance Strategy** | Single batch request | Parallel individual requests |
| **Error Handling** | Batch-level error management | Individual request error isolation |
| **Implementation** | Client sends request array | Client uses `asyncio.gather()` for parallelization |

##### OAuth Provider Support (FastMCP Compatible)
| Provider | Authentication Method | Scope Mapping | Environment Variables |
|----------|----------------------|---------------|----------------------|
| **Azure AD** | FastMCP BearerAuth + JWT | Azure scopes → MCP permissions | AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID |
| **Google** | FastMCP BearerAuth + JWT | Google scopes → MCP permissions | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET |
| **Keycloak** | FastMCP BearerAuth + JWT | OIDC scopes → MCP permissions | KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_SERVER_URL |
| **Okta** | FastMCP BearerAuth + JWT | Okta scopes → MCP permissions | OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_DOMAIN |
| **GitHub** | FastMCP BearerAuth + API | GitHub scopes → MCP permissions | GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_ORG |

##### Backward Compatibility
- **✅ 100% Tool Compatibility**: All 48 MCP tools work identically with new framework
- **✅ Configuration Preserved**: All environment variables and settings remain the same
- **✅ Optional Authentication**: OAuth can be enabled/disabled without affecting core functionality
- **⚠️ JSON-RPC Batching**: Breaking change - clients must migrate to individual requests
- **✅ Application Batching**: Enhanced application-level operations remain functional

#### Usage Examples

##### Migration from JSON-RPC Batching

**❌ Before (JSON-RPC Batching - No Longer Supported):**
```python
# This will now fail with MCP 2025-06-18 compliance
batch_request = [
    {"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 1},
    {"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 2},
    {"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 3},
]
response = await client.send_batch(batch_request)  # ❌ NOT SUPPORTED
```

**✅ After (Individual Requests with Parallelization):**
```python
# New compliant approach using individual requests
import asyncio
from fastmcp import Client

async def main():
    client = Client("kafka_schema_registry_unified_mcp.py")
    
    async with client:
        # Method 1: Sequential individual requests
        result1 = await client.call_tool("list_subjects", {"context": "users"})
        result2 = await client.call_tool("get_schema", {"subject": "user-events"})
        result3 = await client.call_tool("register_schema", {...})
        
        # Method 2: Parallel individual requests (recommended for performance)
        tasks = [
            client.call_tool("list_subjects", {"context": "users"}),
            client.call_tool("get_schema", {"subject": "user-events"}),
            client.call_tool("register_schema", {...})
        ]
        results = await asyncio.gather(*tasks)
        
        # Method 3: Use application-level batching where available
        batch_result = await client.call_tool("clear_context_batch", {
            "context": "test-context",
            "dry_run": False
        })
        # Monitor task progress
        task_id = batch_result["task_id"]
        status = await client.call_tool("get_task_status", {"task_id": task_id})

if __name__ == "__main__":
    asyncio.run(main())
```

##### Check MCP 2025-06-18 Compliance
```python
from fastmcp import Client

async def check_compliance():
    client = Client("kafka_schema_registry_unified_mcp.py")
    
    async with client:
        # Verify server compliance
        compliance = await client.call_tool("get_mcp_compliance_status")
        
        print(f"Compliance Status: {compliance['compliance_status']}")
        print(f"Protocol Version: {compliance['protocol_version']}")
        print(f"JSON-RPC Batching: {compliance['batching_configuration']['jsonrpc_batching']}")
        print(f"Application Batching: {compliance['batching_configuration']['application_level_batching']}")
        
        # Check if migration is needed
        if compliance['compliance_status'] == 'COMPLIANT':
            print("✅ Server is MCP 2025-06-18 compliant")
        else:
            print("⚠️  Server requires updates for compliance")
```

##### FastMCP Client (New in v2.0.0)
```python
from fastmcp import Client
import asyncio

async def main():
    # Modern FastMCP client usage
    client = Client("kafka_schema_registry_unified_mcp.py")
    
    async with client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {len(tools)}")
        
        # Call a tool with authentication
        result = await client.call_tool("register_schema", {
            "subject": "user-events",
            "schema_definition": {"type": "record", "name": "User", "fields": [
                {"name": "id", "type": "long"},
                {"name": "name", "type": "string"}
            ]},
            "schema_type": "AVRO"
        })

if __name__ == "__main__":
    asyncio.run(main())
```

##### OAuth Authentication Setup
```bash
# Enable FastMCP OAuth authentication
export ENABLE_AUTH=true
export AUTH_PROVIDER=azure  # or google, keycloak, okta, github
export AUTH_ISSUER_URL=https://login.microsoftonline.com/your-tenant/v2.0
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret

# Run with FastMCP 2.8.0+ and MCP 2025-06-18 compliance
python kafka_schema_registry_unified_mcp.py
```

### Maintained
- **All 48 MCP Tools**: Complete backward compatibility (except JSON-RPC batching removal)
- **Multi-Registry Support**: Existing functionality enhanced with OAuth
- **Docker Images**: Same deployment patterns with OAuth support
- **Configuration**: All existing environment variables supported
- **Application-Level Batching**: Enhanced and maintained with individual request implementation

### Removed (Breaking Changes)
- **JSON-RPC Batching Support**: Removed per MCP 2025-06-18 specification requirement
  - Clients using batch requests must migrate to individual requests
  - See `MCP-2025-06-18-MIGRATION-GUIDE.md` for detailed migration guidance
  - Performance maintained through parallel individual requests and application-level batching

### Migration Guide

#### For Existing Users (v1.x → v2.0.0)
1. **Basic Usage**: No changes required for standard MCP tool usage
2. **JSON-RPC Batching**: Migrate to individual requests with parallel processing
3. **Authentication**: OAuth is optional and can be enabled incrementally
4. **Testing**: Update test framework if using custom FastMCP clients

#### For JSON-RPC Batching Users
1. **Immediate Action**: Review client code for JSON-RPC batch usage
2. **Migration Path**: Implement parallel individual requests using `asyncio.gather()`
3. **Performance**: Use application-level batch operations where available
4. **Testing**: Validate performance with new individual request patterns

See `MCP-2025-06-18-MIGRATION-GUIDE.md` for comprehensive migration instructions.

## [1.8.3] - 2025-06-07

### 🚀 Simplified Context Migration with External Tool Integration

#### Changed
- **`migrate_context` Simplified**: Now generates ready-to-run Docker commands instead of configuration files
  - Returns single Docker command with all necessary environment variables
  - Simplified workflow: copy command → run → monitor output
  - Leverages [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator) for robust context migrations
  - Automatic registry credential mapping and context handling
  - Clear separation: MCP handles single schema operations, external tool handles context migrations
  - Updated tests to match new simplified behavior

#### Improved
- **Migration Architecture**: Clear separation of concerns between MCP and external migration tool
- **User Experience**: Streamlined from multi-file configuration to single command execution
- **Documentation**: Updated all references to reflect new migrate_context behavior
- **Test Coverage**: Comprehensive testing of Docker command generation and validation

## [1.8.2] - 2025-06-06

### 🔒 Security, OAuth, and Documentation Consistency Release

#### Changed
- **Enforced tool-level OAuth scope requirements**: All MCP tools now have explicit `@require_scopes` decorators (`read`, `write`, or `admin`) matching their intended permissions.
- **README updated**: Tool-to-scope mapping in the documentation now matches the code exactly. Security and OAuth documentation clarified.
- **Internal consistency**: All `@mcp.tool()` functions are now consistently protected by the correct scope decorators.
- **No breaking changes**: All tool signatures and APIs remain backward compatible.
- **Minor documentation improvements**: Clarified how to audit tool permissions using `get_oauth_scopes_info`.
- **No configuration or deployment changes**: All environment variables and Docker usage remain the same.

## [1.8.1] - 2025-06-06

### 🏗️ Modular Architecture Refactoring

This release introduces a comprehensive modular architecture that transforms the monolithic codebase into 8 specialized modules, significantly improving maintainability, development efficiency, and code organization.

### Added
- **Modular Architecture**: Split 3917-line monolithic file into 8 focused modules
  - `task_management.py` (280 lines): Async task queue operations for long-running processes
  - `migration_tools.py` (400+ lines): Schema and context migration between registries
  - `comparison_tools.py` (160 lines): Registry and context comparison operations
  - `export_tools.py` (200 lines): Schema export in multiple formats (JSON, Avro IDL)
  - `batch_operations.py` (350+ lines): Batch cleanup operations with progress tracking
  - `statistics_tools.py` (150 lines): Counting and statistics operations
  - `core_registry_tools.py` (600+ lines): Basic CRUD operations for schemas, subjects, configs
  - `kafka_schema_registry_unified_modular.py` (500 lines): Main orchestration server file

### Improved

#### Development & Maintainability
- **Focused Responsibility**: Each module handles a specific area of functionality
- **Parallel Development**: Multiple developers can work on different modules simultaneously
- **Code Navigation**: Smaller, focused files are significantly easier to understand and navigate
- **Isolated Testing**: Modules can be tested independently for better test coverage
- **Easier Debugging**: Clear module boundaries help isolate and fix issues faster

#### Architecture Benefits
- **Single Responsibility Principle**: Each module has one clear purpose
- **Reduced Merge Conflicts**: Developers working on different features rarely conflict
- **Plugin-Ready Structure**: Foundation for future plugin architecture
- **Selective Loading**: Potential for loading only needed modules
- **Better Documentation**: Each module is self-documenting with focused docstrings

#### Performance & Scalability
- **Memory Efficiency**: Only required modules are fully loaded
- **Faster Startup**: Reduced initial loading time
- **Better Resource Management**: Cleaner separation of concerns
- **Future Optimizations**: Module-specific performance improvements possible

### Maintained
- **100% Backward Compatibility**: Original monolithic file still available and functional
- **All 48 MCP Tools**: Every existing tool continues to work exactly as before
- **API Compatibility**: No breaking changes to any tool signatures or responses
- **Configuration Support**: All environment variables and settings remain the same
- **Docker Images**: Same container behavior and deployment process

### Technical Details

#### Module Dependencies
```
kafka_schema_registry_unified_modular.py (main server)
├── task_management.py (task queue & progress tracking)
├── migration_tools.py ────┐
├── comparison_tools.py    │── All import task_management
├── export_tools.py        │   for async operations
├── batch_operations.py ───┘
├── statistics_tools.py
├── core_registry_tools.py (foundation CRUD operations)
├── schema_registry_common.py (shared utilities)
└── oauth_provider.py (authentication)
```

#### Migration Path
- **Gradual Migration**: Users can switch to modular version when ready
- **Development Choice**: New features developed in modular structure
- **Zero Downtime**: Switch between versions without service interruption
- **Rollback Support**: Can revert to monolithic version if needed

### Developer Experience

#### Before (Monolithic)
- Single 3917-line file
- Difficult to navigate and find specific functionality
- Merge conflicts common with multiple developers
- Hard to test individual features in isolation
- Debugging required searching through large file

#### After (Modular)
- 8 focused modules with clear responsibilities
- Easy to locate and modify specific functionality
- Parallel development without conflicts
- Independent module testing
- Clear boundaries for issue isolation

### Future Enhancements Enabled
- **Plugin Architecture**: Third-party modules can be added
- **Independent Versioning**: Modules can be versioned separately
- **Selective Deployment**: Deploy only needed functionality
- **Better Testing**: Comprehensive per-module test suites
- **Community Contributions**: Easier for external contributors

### Usage
Both versions are available and fully compatible:

```bash
# New modular version (recommended for development)
python kafka_schema_registry_unified_modular.py

# Original monolithic version (still supported)  
python kafka_schema_registry_unified_mcp.py
```

### Docker Support
The Docker image includes both versions with the modular version as default:

```bash
# Uses modular version by default
docker run aywengo/kafka-schema-reg-mcp:1.8.1

# Explicitly use original version
docker run aywengo/kafka-schema-reg-mcp:1.8.1 python kafka_schema_registry_unified_mcp.py
```

### Documentation
- Added `MODULAR_ARCHITECTURE.md` with comprehensive architecture guide
- Module responsibility documentation
- Development guidelines for modular structure
- Migration path documentation

## [1.7.2] - 2025-06-01

### Changed
- **`migrate_context` Enhancement**: Now generates Docker configuration files for [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator) instead of performing direct migration
  - Generates `.env` file with registry credentials
  - Creates `docker-compose.yml` for easy execution
  - Provides `migrate-context.sh` shell script
  - Better error handling and recovery capabilities
  - Scalable bulk migrations with progress logging
  - Users can review configuration before execution

### Documentation
- Updated all references to `migrate_context` in documentation
- Added migration guide showing Docker-based workflow
- Updated test README with new migration flow

## [1.7.0] - 2025-05-31

### 🚀 Enhanced Async Operations & Task Management

This release completes the async transformation with comprehensive task queue implementation, progress tracking enhancements, and improved testing framework for all long-running operations.

### Added
- **Async Task Queue System**: Full implementation with ThreadPoolExecutor backend
- **Enhanced Progress Tracking**: Detailed progress stages for all operations
- **Comparison Progress Tools**: New monitoring for context comparison operations
- **Migration Progress Tools**: Enhanced tracking for schema migration tasks
- **Cleanup Progress Tools**: Detailed monitoring for batch cleanup operations
- **Task Management Tools**: `list_all_active_tasks()`, operation-specific task listings

### Improved
- **MCP Client Guidance**: Enhanced operation metadata and async pattern documentation
- **Event Loop Handling**: Automatic fallback to threading when no event loop available
- **Task Shutdown**: Graceful cleanup with proper cancellation handling
- **Progress Descriptions**: Human-readable stage descriptions for all operations
- **Test Framework**: Comprehensive async operation testing

### Fixed
- Fixed batch cleanup test failures with async task patterns
- Resolved event loop issues during shutdown
- Fixed task cleanup race conditions
- Corrected progress tracking for concurrent operations

### Dependencies
- Added `aiohttp` for improved async HTTP operations

## [1.6.0] - 2024-12-XX

### 🔧 Batch Cleanup Tools & Migration Enhancements

### Added
- **Batch Cleanup Tools**: Efficient context cleanup for single and multi-registry modes
  - `clear_context_batch()`: Remove all subjects from a context with parallel execution
  - `clear_multiple_contexts_batch()`: Clean multiple contexts in one operation
  - Default `dry_run=True` for safety
- **Migration Enhancements**: Improved schema migration with better error handling
- **Test Suites**: Comprehensive migration and cleanup testing

### Improved
- Enhanced default context handling in migrations
- Better error messages for migration failures
- Parallel deletion support (up to 10 concurrent operations)
- Performance metrics reporting

## [1.5.0] - 2024-12-XX

### 🌐 Multi-Registry Support & Configuration

### Added
- **Multi-Registry Mode**: Support for up to 8 Schema Registry instances
- **Numbered Environment Config**: Clean `SCHEMA_REGISTRY_NAME_X`, `SCHEMA_REGISTRY_URL_X` pattern
- **Per-Registry VIEWONLY**: Independent `VIEWONLY_X` control for each registry
- **Registry Management Tools**: List, test, and manage multiple registries
- **Cross-Registry Operations**: Compare and migrate between registries

### Improved
- Configuration validation and error handling
- Registry connection testing
- Documentation for multi-mode setup

### Removed
- Deprecated configuration files
- Legacy test result files

## [1.4.0] - 2024-12-XX

### 🚀 Major Features: Async Operations & Progress Tracking

This release introduces a comprehensive async task management system with real-time progress tracking for long-running operations, making the MCP server more responsive and providing better visibility into operation status.

### Added

#### Async Task Management System
- **Task Queue Architecture**: Background execution for long-running operations (migration, cleanup, comparison)
- **Real-time Progress Tracking**: Monitor operation progress with percentage completion and status updates
- **Task Lifecycle Management**: Create, execute, monitor, and cancel tasks
- **Operation Classification**: Operations categorized as QUICK (<5s), MEDIUM (5-30s), or LONG (>30s)
- **Graceful Shutdown**: Proper cleanup of running tasks on exit

#### New Progress Monitoring Tools
- `get_task_progress(task_id)`: Get detailed progress for any task
- `get_migration_progress(task_id)`: Migration-specific progress monitoring
- `get_cleanup_progress(task_id)`: Cleanup operation progress
- `get_comparison_progress(task_id)`: Comparison operation progress
- `list_all_active_tasks()`: View all running/pending tasks
- `list_migration_tasks()`: List migration-specific tasks
- `list_cleanup_tasks()`: List cleanup-specific tasks
- `list_comparison_tasks()`: List comparison tasks
- `watch_comparison_progress()`: Guidance for real-time monitoring

#### Enhanced Async Operations
- **Migration Operations**: `migrate_schema`, `migrate_context` now return task IDs immediately
- **Cleanup Operations**: `clear_context_batch`, `clear_multiple_contexts_batch` use task queue
- **Comparison Operations**: `compare_contexts_across_registries`, `compare_different_contexts` run async
- **Progress Stages**: Human-readable progress descriptions for each operation phase

### Improved

#### Error Handling
- Better handling of missing event loops (fallback to threading)
- Graceful task cancellation during shutdown
- Comprehensive error reporting in task results

#### Performance
- Non-blocking execution for long operations
- Parallel task execution with ThreadPoolExecutor
- Progress-based time estimation for running tasks

#### MCP Client Experience
- Operations return immediately with task IDs
- Clients can poll for progress without timeout issues
- Clear operation metadata (duration, pattern) via `get_operation_info_tool()`

### Fixed
- Event loop closed errors during shutdown
- Task cleanup issues with interrupted operations
- Async operation handling without active event loops
- Test failures related to async task patterns

### Technical Details

#### Task States
- **PENDING**: Task created but not started
- **RUNNING**: Task actively executing
- **COMPLETED**: Task finished successfully
- **FAILED**: Task encountered an error
- **CANCELLED**: Task was cancelled

#### Progress Tracking
- 0-100% completion tracking
- Operation-specific progress stages
- Duration tracking and time estimation
- Detailed result storage

### Migration Guide

For MCP clients using long-running operations:

**Before (v1.3.x):**
```python
# Operation blocks until complete
result = migrate_context(source="dev", target="prod", context="production")
# Client might timeout on long operations
```

**After (v1.4.0):**
```python
# Operation returns immediately with task info
task_info = migrate_context(source="dev", target="prod", context="production")
task_id = task_info["task_id"]

# Poll for progress
while True:
    progress = get_task_progress(task_id)
    print(f"Status: {progress['status']}, Progress: {progress['progress_percent']}%")
    if progress['status'] in ['completed', 'failed', 'cancelled']:
        break
    time.sleep(2)
```

## [1.3.0] - 2024-11-XX

### 🎯 Initial MCP Implementation

### Added
- **True MCP Server**: Transformed from REST API to Message Control Protocol server
- **Claude Desktop Integration**: Direct compatibility with Claude Desktop app
- **48 MCP Tools**: Comprehensive schema registry operations
- **Context Support**: Production/staging environment isolation
- **Schema Export**: JSON and Avro IDL export formats
- **VIEWONLY Mode**: Production safety features
- **Docker Support**: Multi-platform images (AMD64/ARM64)

### Changed
- Architecture from REST API to MCP protocol
- Configuration to environment variables
- Documentation for MCP usage

### Compatibility & Migration (v1.x → v2.0.0)
- **100% Backward Compatible**: All existing local deployments continue to work unchanged
- **All 48 Tools Preserved**: Every existing MCP tool maintains the same API and functionality
- **Configuration Migration**: Existing environment variables and Docker usage remain the same
- **Optional Features**: OAuth and remote deployment are opt-in features
- **⚠️ JSON-RPC Batching**: Breaking change - removed per MCP 2025-06-18 specification
- **Zero Downtime Upgrades**: Can upgrade from v1.x to v2.0.0 without service interruption (except batching)

### Docker v2.0.3
```bash
# v2.0.3 Release (Security & Ping/Pong)
docker pull aywengo/kafka-schema-reg-mcp:2.0.3
docker pull aywengo/kafka-schema-reg-mcp:stable  # Latest stable

# Previous stable
docker pull aywengo/kafka-schema-reg-mcp:2.0.2
``` 
