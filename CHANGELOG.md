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

### Added
- Interactive single schema migration with elicitation support
- Smart pre-migration analysis with schema existence detection
- Automatic backup operations before schema replacement
- Post-migration verification with comprehensive schema validation
- Migration elicitation infrastructure with dynamic field generation

### Fixed
- Security Issue #26: Credential exposure vulnerability in logging and object representations
- Security Issue #24: SSL/TLS configuration with explicit certificate verification
- Secure header management with dynamic authentication flow
- Enhanced SSL/TLS security with TLS 1.2+ enforcement and custom CA bundle support

### Security
- Implemented `SecureHeaderDict` for fresh credential headers
- Added `SensitiveDataFilter` for automatic credential masking in logs
- Enhanced SSL/TLS configuration with strict hostname verification
- Custom CA bundle support for enterprise environments

## [2.0.1] - 2025-06-27

### Added
- Local JSON Schema handling for draft-07 meta-schemas
- Enhanced elicitation tools with structured output decorators
- Migration confirmation system with ID preservation handling
- Custom requests adapter for local schema resolution

### Changed
- Major code refactoring across 74 files for improved readability and performance
- Streamlined error handling and consolidated list comprehensions
- Enhanced logging statements and improved resource management

### Removed
- 2,442 lines of redundant code while maintaining full functionality

## [2.0.0] - 2025-06-26

### Added
- FastMCP 2.8.0+ framework integration with MCP 2025-06-18 specification compliance
- Native OAuth provider integration (Azure AD, Google, Keycloak, Okta, GitHub)
- Enhanced client API with modern FastMCP.Client interface
- Comprehensive migration guide and compliance status tools
- SSL/TLS security enhancement with explicit certificate verification

### Changed
- Complete migration from legacy `mcp[cli]==1.9.4` to FastMCP 2.8.0+
- Updated client interface using FastMCP's dependency injection system
- Enhanced authentication with native FastMCP BearerAuth provider

### Removed
- JSON-RPC batching support (breaking change per MCP 2025-06-18 specification)

### Security
- Explicit SSL/TLS certificate verification for all HTTP requests
- TLS 1.2+ enforcement with strong cipher suites
- Custom CA bundle support for enterprise environments

## [1.8.3] - 2025-06-07

### Changed
- `migrate_context` now generates Docker commands instead of configuration files
- Simplified workflow using [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator)
- Better error handling and recovery capabilities for migrations

## [1.8.2] - 2025-06-06

### Changed
- Enforced tool-level OAuth scope requirements with explicit `@require_scopes` decorators
- Updated README with tool-to-scope mapping matching code implementation
- Internal consistency improvements for OAuth scope protection

## [1.8.1] - 2025-06-06

### Added
- Modular architecture: Split monolithic file into 8 specialized modules
- Task management, migration tools, comparison tools, export tools modules
- Batch operations, statistics tools, core registry tools modules
- Enhanced development workflow with focused module responsibilities

### Changed
- Architecture from single 3917-line file to 8 focused modules
- Improved maintainability and parallel development capabilities

## [1.7.2] - 2025-06-01

### Changed
- `migrate_context` generates Docker configuration files for external migration tool
- Enhanced migration workflow with `.env`, `docker-compose.yml`, and shell scripts

## [1.7.0] - 2025-05-31

### Added
- Async task queue system with ThreadPoolExecutor backend
- Enhanced progress tracking with detailed stages for all operations
- Task management tools for monitoring long-running operations
- Comprehensive async operation testing framework

### Fixed
- Event loop issues during shutdown and task cleanup race conditions
- Batch cleanup test failures with async task patterns

## [1.6.0] - 2024-12-XX

### Added
- Batch cleanup tools for efficient context cleanup
- `clear_context_batch()` and `clear_multiple_contexts_batch()` operations
- Enhanced migration with better error handling and parallel deletion support

## [1.5.0] - 2024-12-XX

### Added
- Multi-registry mode supporting up to 8 Schema Registry instances
- Numbered environment configuration pattern
- Per-registry READONLY control and cross-registry operations

## [1.4.0] - 2024-12-XX

### Added
- Async task management system with real-time progress tracking
- Task lifecycle management and operation classification
- Progress monitoring tools for migrations, cleanup, and comparisons
- Enhanced async operations with immediate task ID returns

## [1.3.0] - 2024-11-XX

### Added
- True MCP Server implementation with Message Control Protocol
- Claude Desktop integration with 48 MCP tools
- Context support for environment isolation
- Schema export in JSON and Avro IDL formats
- READONLY mode and Docker support with multi-platform images

### Changed
- Architecture from REST API to MCP protocol
- Configuration to environment variables
