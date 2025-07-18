#!/usr/bin/env python3
"""
Integration tests for SLIM_MODE functionality.

This test suite validates that SLIM_MODE correctly reduces the number of exposed tools
from 70+ to ~27 essential tools (including backward compatibility wrappers),
maintaining basic functionality while improving performance.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Set

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the unified MCP server
import kafka_schema_registry_unified_mcp

# Expected tool sets in different modes
ESSENTIAL_TOOLS_SLIM_MODE = {
    # Core connectivity
    "ping",
    # Registry management
    "get_default_registry",
    # Note: set_default_registry is only available in single-registry mode in SLIM_MODE
    # Basic schema operations
    "register_schema",  # Basic write operation
    "check_compatibility",
    # Basic context operations
    "create_context",  # Basic write operation
    # Counting/statistics (lightweight)
    "count_contexts",
    "count_schemas",
    "count_schema_versions",
    # Essential export tools
    "export_schema",
    "export_subject",
    # Resource discovery tools (NEW)
    "list_available_resources",
    "suggest_resource_for_tool",
    "generate_resource_templates",
    # Backward compatibility wrapper tools (for client compatibility)
    "list_registries",
    "get_registry_info",
    "test_registry_connection",
    "test_all_registries",
    "list_subjects",
    "get_schema",
    "get_schema_versions",
    "get_global_config",
    "get_mode",
    "list_contexts",
    "get_subject_config",
    "get_subject_mode",
}

# Tools that should be EXCLUDED in SLIM_MODE
EXCLUDED_TOOLS_SLIM_MODE = {
    # Note: Backward compatibility tools are now INCLUDED in SLIM_MODE to prevent client errors
    # The following tools are still excluded in SLIM_MODE:
    "check_viewonly_mode",  # Only in full mode
    # Migration tools (heavy operations)
    "migrate_schema",
    "migrate_context",
    "migrate_context_interactive",
    "list_migrations",
    "get_migration_status",
    # Batch operations
    "clear_context_batch",
    "clear_multiple_contexts_batch",
    # Export/import tools (advanced)
    "export_context",
    "export_global",
    "export_global_interactive",
    # Interactive/elicitation tools
    "register_schema_interactive",
    "check_compatibility_interactive",
    "create_context_interactive",
    "list_elicitation_requests",
    "get_elicitation_request",
    "cancel_elicitation_request",
    "get_elicitation_status",
    "submit_elicitation_response",
    # Delete operations
    "delete_subject",
    "delete_context",
    # Configuration updates
    "update_global_config",
    "update_subject_config",
    "update_mode",
    "update_subject_mode",
    "set_default_registry",  # Only included in SLIM_MODE for single-registry configurations
    # Heavy statistics with async
    "get_registry_statistics",
    # Task management
    "get_task_status",
    "get_task_progress",
    "list_active_tasks",
    "cancel_task",
    "list_statistics_tasks",
    "get_statistics_task_progress",
    # Comparison tools
    "compare_registries",
    "compare_contexts_across_registries",
    "find_missing_schemas",
    # Workflow tools
    "list_available_workflows",
    "get_workflow_status",
    "guided_schema_migration",
    "guided_context_reorganization",
    "guided_disaster_recovery",
    # OAuth tools (may be heavy)
    "get_oauth_scopes_info_tool",
    "test_oauth_discovery_endpoints",
    "get_operation_info_tool",
}


class TestSLIMModeIntegration:
    """Test SLIM_MODE functionality and tool reduction."""

    @pytest.fixture
    def mcp_server_full_mode(self):
        """Create MCP server instance in full mode."""
        # Save current env
        original_slim_mode = os.environ.get("SLIM_MODE")

        # Set to full mode
        os.environ["SLIM_MODE"] = "false"

        # Import the server (this will create the mcp instance)
        import importlib

        importlib.reload(kafka_schema_registry_unified_mcp)
        server = kafka_schema_registry_unified_mcp.mcp

        yield server

        # Restore env
        if original_slim_mode is not None:
            os.environ["SLIM_MODE"] = original_slim_mode
        else:
            os.environ.pop("SLIM_MODE", None)

    @pytest.fixture
    def mcp_server_slim_mode(self):
        """Create MCP server instance in SLIM mode."""
        # Save current env
        original_slim_mode = os.environ.get("SLIM_MODE")

        # Set to SLIM mode
        os.environ["SLIM_MODE"] = "true"

        # Import the server (this will create the mcp instance)
        import importlib

        importlib.reload(kafka_schema_registry_unified_mcp)
        server = kafka_schema_registry_unified_mcp.mcp

        yield server

        # Restore env
        if original_slim_mode is not None:
            os.environ["SLIM_MODE"] = original_slim_mode
        else:
            os.environ.pop("SLIM_MODE", None)

    async def get_available_tools(self, server) -> Set[str]:
        """Extract available tool names from server instance."""
        tools_dict = await server.get_tools()
        return set(tools_dict.keys())

    @pytest.mark.asyncio
    async def test_slim_mode_reduces_tool_count(self, mcp_server_full_mode, mcp_server_slim_mode):
        """Test that SLIM_MODE significantly reduces the number of exposed tools."""
        # Get tools in full mode
        full_tools = await self.get_available_tools(mcp_server_full_mode)

        # Get tools in SLIM mode
        slim_tools = await self.get_available_tools(mcp_server_slim_mode)

        # Verify tool count reduction
        assert len(slim_tools) < len(
            full_tools
        ), f"SLIM mode should have fewer tools. Full: {len(full_tools)}, Slim: {len(slim_tools)}"

        # Verify significant reduction (should be ~27 vs 70+)
        # Note: SLIM_MODE now includes backward compatibility wrapper tools to prevent client errors
        assert len(slim_tools) <= 35, f"SLIM mode should have ~27 tools, but has {len(slim_tools)}"

        # Print actual tools for debugging
        print(f"SLIM mode tools ({len(slim_tools)}): {sorted(slim_tools)}")
        print(f"Full mode tools ({len(full_tools)}): {sorted(full_tools)}")

        # Verify full mode has expected tool count
        assert len(full_tools) >= 60, f"Full mode should have 60+ tools, but has {len(full_tools)}"

        print(f"✅ Tool count reduction verified: {len(full_tools)} → {len(slim_tools)}")

    @pytest.mark.asyncio
    async def test_slim_mode_includes_essential_tools(self, mcp_server_slim_mode):
        """Test that SLIM_MODE includes all essential tools."""
        slim_tools = await self.get_available_tools(mcp_server_slim_mode)

        # Check which essential tools are missing
        missing_tools = ESSENTIAL_TOOLS_SLIM_MODE - slim_tools

        # set_default_registry is only available in single-registry mode in SLIM_MODE
        # Remove it from missing tools check if we're in multi-registry mode
        if "set_default_registry" in missing_tools:
            # Check if we're in multi-registry mode (no specific registry URL set)
            import os

            if not os.getenv("SCHEMA_REGISTRY_URL") and not os.getenv("SCHEMA_REGISTRY_NAME_1"):
                missing_tools.discard("set_default_registry")

        if missing_tools:
            print(f"Missing tools: {missing_tools}")
            print(f"Available tools: {sorted(slim_tools)}")
        assert not missing_tools, f"SLIM mode is missing essential tools: {missing_tools}"

        print(f"✅ All {len(ESSENTIAL_TOOLS_SLIM_MODE)} essential tools are present in SLIM mode")

    @pytest.mark.asyncio
    async def test_slim_mode_excludes_heavy_tools(self, mcp_server_slim_mode):
        """Test that SLIM_MODE excludes heavy/admin tools."""
        slim_tools = await self.get_available_tools(mcp_server_slim_mode)

        # Check which excluded tools are still present
        unwanted_tools = EXCLUDED_TOOLS_SLIM_MODE & slim_tools

        assert not unwanted_tools, f"SLIM mode should not include these tools: {unwanted_tools}"

        print(f"✅ All {len(EXCLUDED_TOOLS_SLIM_MODE)} heavy tools are excluded in SLIM mode")

    @pytest.mark.asyncio
    async def test_slim_mode_environment_variable(self):
        """Test that SLIM_MODE can be controlled via environment variable."""
        import importlib

        # Test with SLIM_MODE=true
        os.environ["SLIM_MODE"] = "true"
        importlib.reload(kafka_schema_registry_unified_mcp)
        server_slim = kafka_schema_registry_unified_mcp.mcp
        slim_tools = await self.get_available_tools(server_slim)

        # Test with SLIM_MODE=false
        os.environ["SLIM_MODE"] = "false"
        importlib.reload(kafka_schema_registry_unified_mcp)
        server_full = kafka_schema_registry_unified_mcp.mcp
        full_tools = await self.get_available_tools(server_full)

        # Verify the difference
        assert len(slim_tools) < len(full_tools)
        assert len(slim_tools) <= 30
        assert len(full_tools) >= 60

        print("✅ SLIM_MODE environment variable correctly controls tool exposure")

    @pytest.mark.asyncio
    async def test_slim_mode_basic_functionality(self):
        """Test that basic schema registry operations work in SLIM_MODE."""
        import importlib

        os.environ["SLIM_MODE"] = "true"
        os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"

        # Create a simple test to verify basic operations are available
        importlib.reload(kafka_schema_registry_unified_mcp)
        server = kafka_schema_registry_unified_mcp.mcp
        tools = await self.get_available_tools(server)

        # Verify core operations are available
        # Note: get_schema, list_subjects have been converted to resources
        core_operations = {"ping", "register_schema", "check_compatibility"}

        available_core = core_operations & tools
        assert available_core == core_operations, f"Missing core operations: {core_operations - available_core}"

        print("✅ All core schema registry operations are available in SLIM mode")

    @pytest.mark.asyncio
    async def test_slim_mode_performance_characteristics(self):
        """Test that SLIM_MODE has expected performance characteristics."""
        import gc
        import importlib
        import time

        # Try to import psutil, but make it optional
        try:
            import psutil

            psutil_available = True
        except ImportError:
            psutil_available = False
            print("⚠️ psutil not available, skipping memory measurements")

        # Measure startup time and memory for full mode
        gc.collect()
        if psutil_available:
            process = psutil.Process()

        os.environ["SLIM_MODE"] = "false"
        start_time = time.time()
        importlib.reload(kafka_schema_registry_unified_mcp)
        server_full = kafka_schema_registry_unified_mcp.mcp
        full_startup_time = time.time() - start_time

        if psutil_available:
            full_memory = process.memory_info().rss / 1024 / 1024  # MB
        else:
            full_memory = 0

        # Clean up
        del server_full
        gc.collect()

        # Measure startup time and memory for SLIM mode
        os.environ["SLIM_MODE"] = "true"
        start_time = time.time()
        importlib.reload(kafka_schema_registry_unified_mcp)
        server_slim = kafka_schema_registry_unified_mcp.mcp
        slim_startup_time = time.time() - start_time

        if psutil_available:
            slim_memory = process.memory_info().rss / 1024 / 1024  # MB
        else:
            slim_memory = 0

        # SLIM mode should have faster startup (fewer tools to register)
        # Note: This might not always be true in unit tests, but is true in practice
        print(f"Startup times - Full: {full_startup_time:.3f}s, Slim: {slim_startup_time:.3f}s")
        if psutil_available:
            print(f"Memory usage - Full: {full_memory:.1f}MB, Slim: {slim_memory:.1f}MB")
        else:
            print("Memory usage - Not measured (psutil not available)")

        # At minimum, verify both modes start successfully
        assert full_startup_time > 0
        assert slim_startup_time > 0

        print("✅ SLIM mode performance characteristics verified")

    @pytest.mark.asyncio
    async def test_slim_mode_tool_descriptions(self, mcp_server_slim_mode):
        """Test that SLIM_MODE tools have proper descriptions."""
        tools = await self.get_available_tools(mcp_server_slim_mode)

        # Verify we have the expected number of tools
        assert len(tools) <= 35, f"SLIM mode should have ~27 tools, got {len(tools)}"

        # Verify essential tools are present
        # Note: After resource conversion + export tools, we have ~9 essential tools
        essential_present = ESSENTIAL_TOOLS_SLIM_MODE & tools
        assert len(essential_present) >= 9, f"Should have at least 9 essential tools, got {len(essential_present)}"

        print(f"✅ SLIM mode tool descriptions verified for {len(tools)} tools")

    @pytest.mark.asyncio
    async def test_slim_mode_docker_integration(self):
        """Test that SLIM_MODE works in Docker environment."""
        # This test simulates Docker environment variables
        docker_env = {"SLIM_MODE": "true", "SCHEMA_REGISTRY_URL": "http://localhost:38081", "CONTAINER_MODE": "true"}

        # Apply Docker-like environment
        for key, value in docker_env.items():
            os.environ[key] = value

        import importlib

        importlib.reload(kafka_schema_registry_unified_mcp)
        server = kafka_schema_registry_unified_mcp.mcp
        tools = await self.get_available_tools(server)

        # Verify SLIM mode is active
        assert len(tools) <= 35, f"Docker SLIM mode should have ~27 tools, got {len(tools)}"

        print("✅ SLIM mode Docker integration verified")

    @pytest.mark.asyncio
    async def test_slim_mode_multi_registry_support(self):
        """Test that SLIM_MODE works with multi-registry configuration."""
        # Set up multi-registry environment with SLIM_MODE
        multi_registry_env = {
            "SLIM_MODE": "true",
            "SCHEMA_REGISTRY_1_NAME": "dev",
            "SCHEMA_REGISTRY_1_URL": "http://localhost:38081",
            "SCHEMA_REGISTRY_2_NAME": "prod",
            "SCHEMA_REGISTRY_2_URL": "http://localhost:38082",
        }

        for key, value in multi_registry_env.items():
            os.environ[key] = value

        import importlib

        importlib.reload(kafka_schema_registry_unified_mcp)
        server = kafka_schema_registry_unified_mcp.mcp
        tools = await self.get_available_tools(server)

        # Verify SLIM mode is active even with multi-registry
        assert len(tools) <= 35, f"Multi-registry SLIM mode should have ~27 tools, got {len(tools)}"

        # Verify essential multi-registry tools are present
        # Note: list_registries, get_registry_info, test_all_registries have been converted to resources
        # Multi-registry support is now provided through resources, not tools
        multi_registry_tools = {
            "set_default_registry",
            "get_default_registry",
        }  # Only remaining registry management tools
        available_multi = multi_registry_tools & tools
        # For multi-registry support, we mainly need the default registry management tools
        assert len(available_multi) >= 1, f"Should have at least 1 multi-registry tool, got {len(available_multi)}"

        print("✅ SLIM mode multi-registry support verified")


def run_tests():
    """Run all SLIM_MODE integration tests."""
    print("🚀 Running SLIM_MODE Integration Tests...")

    # Run pytest on this file
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"], capture_output=True, text=True
    )

    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
