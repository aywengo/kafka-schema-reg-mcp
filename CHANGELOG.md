# Changelog

All notable changes to the Kafka Schema Registry MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.2] - Unreleased

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

## [1.8.2] - 2025-06-07

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
- **Per-Registry READONLY**: Independent `READONLY_X` control for each registry
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
- **READONLY Mode**: Production safety features
- **Docker Support**: Multi-platform images (AMD64/ARM64)

### Changed
- Architecture from REST API to MCP protocol
- Configuration to environment variables
- Documentation for MCP usage

### Compatibility
- Backward compatible with v1.3.x
- All existing tools continue to work
- New async pattern opt-in for long operations

### Docker
```bash
docker pull aywengo/kafka-schema-reg-mcp:1.7.0
docker pull aywengo/kafka-schema-reg-mcp:stable  # Latest stable
``` 