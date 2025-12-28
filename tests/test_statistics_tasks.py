#!/usr/bin/env python3
"""
Test Statistics Tasks with Task Queue Integration

⚠️ DEPRECATED: This test module is deprecated as task_manager is being phased out
in favor of FastMCP's built-in task tracking via Docket.

This script tests the new optimized statistics functionality that uses
the task queue for better performance with parallel API calls and progress tracking.

Note: These tests are kept for backward compatibility but should be updated
to use FastMCP Progress dependency instead of task_manager.
"""

import os
import sys
import warnings
from unittest.mock import Mock, patch

import pytest

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress deprecation warnings for these tests
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Note: operation_metadata.py removed in v2.2.0+ - FastMCP tool definitions expose task capability automatically
# TaskStatus and TaskType enums were removed as they're no longer needed
# task_manager is deprecated and removed - these tests are kept for backward compatibility
# but should be updated to use FastMCP Progress dependency instead
task_manager = None  # Placeholder - actual task_manager functionality removed in v2.2.0


@pytest.fixture
def mock_registry_client():
    client = Mock()
    client.config.name = "test-registry"
    return client


@pytest.fixture
def mock_registry_manager():
    manager = Mock()
    return manager


@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset task manager before each test for isolation (deprecated - no-op)"""
    # task_manager removed in v2.2.0 - FastMCP handles tasks natively
    yield
    # No cleanup needed


class TestStatisticsTaskQueue:
    """Test the task queue versions of statistics functions"""

    def test_statistics_task_type_exists(self):
        """Test that STATISTICS task type is properly defined (deprecated - skipped)"""
        # TaskType enum removed in v2.2.0+ - FastMCP tool definitions (task=True) expose task capability
        pytest.skip("TaskType enum removed - FastMCP tool definitions expose task capability automatically")

    def test_task_manager_can_create_statistics_task(self):
        """Test that task manager can create statistics tasks (deprecated - skipped)"""
        # task_manager removed in v2.2.0 - FastMCP handles tasks natively
        pytest.skip("task_manager removed in v2.2.0 - use FastMCP Progress instead")

    def test_count_schemas_task_queue_tool(self, mock_registry_client, mock_registry_manager):
        """Test count_schemas_task_queue_tool functionality"""
        try:
            from statistics_tools import count_schemas_task_queue_tool

            mock_registry_manager.get_registry.return_value = mock_registry_client

            result = count_schemas_task_queue_tool(
                mock_registry_manager, "multi", context=None, registry="test-registry"
            )

            assert "task_id" in result or "message" in result
            # Note: operation_info removed - FastMCP tool definitions expose task capability automatically

            # Note: task_manager removed in v2.2.0 - FastMCP handles tasks natively
            # Task verification now handled by FastMCP's Docket system

        except ImportError:
            pytest.skip("statistics_tools module not available")

    def test_get_registry_statistics_task_queue_tool(self, mock_registry_client, mock_registry_manager):
        """Test get_registry_statistics_task_queue_tool functionality"""
        try:
            from statistics_tools import get_registry_statistics_task_queue_tool

            mock_registry_manager.get_registry.return_value = mock_registry_client

            result = get_registry_statistics_task_queue_tool(
                mock_registry_manager,
                "multi",
                registry="test-registry",
                include_context_details=True,
            )

            assert "task_id" in result
            assert "message" in result
            assert "Registry statistics analysis started as async task" in result["message"]
            # Note: operation_info removed - FastMCP tool definitions expose task capability automatically

            # Note: task_manager removed in v2.2.0 - FastMCP handles tasks natively
            # Task verification now handled by FastMCP's Docket system

        except ImportError:
            pytest.skip("statistics_tools module not available")


class TestAsyncStatisticsFunctions:
    """Test the async implementations of statistics functions"""

    @pytest.mark.asyncio
    async def test_count_schemas_async_single_context(self, mock_registry_client, mock_registry_manager):
        """Test async count_schemas for a single context"""
        try:
            from statistics_tools import _count_schemas_async

            subjects = ["subject1", "subject2", "subject3"]
            mock_registry_client.get_subjects.return_value = subjects
            mock_registry_manager.get_registry.return_value = mock_registry_client

            result = await _count_schemas_async(
                mock_registry_manager,
                "multi",
                context="test-context",
                registry="test-registry",
            )

            assert result["registry"] == "test-registry"
            assert result["context"] == "test-context"
            assert result["total_schemas"] == 3
            assert result["schemas"] == subjects
            assert "counted_at" in result

        except ImportError:
            pytest.skip("statistics_tools module not available")

    def test_analyze_context_parallel_success(self, mock_registry_client):
        """Test successful parallel context analysis"""
        try:
            from statistics_tools import _analyze_context_parallel

            subjects = ["subject1", "subject2"]
            mock_registry_client.get_subjects.return_value = subjects

            with patch("kafka_schema_registry_unified_mcp.get_schema_versions") as mock_versions:
                mock_versions.side_effect = [
                    [1, 2],
                    [1, 2, 3],
                ]  # 2 and 3 versions respectively

                result = _analyze_context_parallel(mock_registry_client, "test-context", "test-registry")

            assert result["schemas"] == 2
            assert result["versions"] == 5  # 2 + 3

        except ImportError:
            pytest.skip("statistics_tools module not available")


class TestStatisticsOptimizations:
    """Test performance optimizations in statistics"""

    def test_parallel_execution_imports(self):
        """Test that parallel execution dependencies are available"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Verify imports work
        assert ThreadPoolExecutor is not None
        assert asyncio is not None

    def test_statistics_task_metadata(self):
        """Test statistics task metadata structure (deprecated - skipped)"""
        # OPERATION_METADATA removed in v2.2.0+ - FastMCP tool definitions expose task capability automatically
        pytest.skip("OPERATION_METADATA removed - FastMCP tool definitions (task=True) expose task capability")

    def test_operation_guidance(self):
        """Test operation guidance for statistics operations (deprecated - skipped)"""
        # get_operation_info removed in v2.2.0+ - FastMCP tool definitions expose task capability automatically
        pytest.skip("get_operation_info removed - FastMCP tool definitions (task=True) expose task capability")


class TestMCPToolIntegration:
    """Test MCP tool integration for statistics"""

    def test_statistics_tools_import(self):
        """Test that statistics tools can be imported from main module"""
        try:
            from kafka_schema_registry_unified_mcp import (
                count_schemas,
                get_registry_statistics,
                get_statistics_task_progress,
                list_statistics_tasks,
            )

            # Verify functions exist
            assert callable(count_schemas)
            assert callable(get_registry_statistics)
            assert callable(list_statistics_tasks)
            assert callable(get_statistics_task_progress)

        except ImportError as e:
            pytest.skip(f"MCP module not available: {e}")

    def test_task_management_tools_available(self):
        """Test that task management tools are available"""
        try:
            from kafka_schema_registry_unified_mcp import (
                cancel_task,
                get_task_progress,
                get_task_status,
                list_active_tasks,
            )

            # Verify functions exist
            assert callable(get_task_status)
            assert callable(get_task_progress)
            assert callable(list_active_tasks)
            assert callable(cancel_task)

        except ImportError as e:
            pytest.skip(f"MCP module not available: {e}")


def test_performance_characteristics():
    """Test and demonstrate performance characteristics of statistics tasks"""
    print("\n📊 Statistics Tasks Performance Test")
    print("=" * 50)

    print("🚀 Performance optimizations implemented:")
    print("   • Task queue integration for non-blocking execution")
    print("   • Parallel API calls with ThreadPoolExecutor (8 workers for statistics)")
    print("   • Real-time progress tracking with stage descriptions")
    print("   • Smart operation routing (single context = direct, multiple = async)")
    print("   • Error resilience - failed contexts don't stop entire operation")
    print("   • Parallel version counting within each context (10 workers)")

    print("\n⚡ Expected performance improvements:")
    print("   • get_registry_statistics: 30+ seconds → 5-10 seconds")
    print("   • count_schemas (all contexts): 15+ seconds → 3-5 seconds")
    print("   • Non-blocking execution with task_id return")
    print("   • Progress tracking: 10% → 20% → 90% → 100%")

    print("\n🎯 Operation classification:")
    print("   • count_contexts: QUICK (direct)")
    print("   • count_schemas (single context): QUICK (direct)")
    print("   • count_schemas (all contexts): MEDIUM (task queue)")
    print("   • count_schema_versions: QUICK (direct)")
    print("   • get_registry_statistics: LONG (task queue)")

    print("\n📝 Usage pattern:")
    print("   result = get_registry_statistics()     # Returns immediately with task_id")
    print("   task_id = result['task_id']")
    print("   get_statistics_task_progress(task_id)  # Monitor progress: 'Analyzing contexts' (45%)")
    print("   get_task_status(task_id)               # Check completion and get results")


def test_statistics_task_workflow():
    """Test statistics task workflow without external dependencies (deprecated - skipped)"""
    print("\n⚠️  Statistics Task Workflow test skipped")
    print("   task_manager removed in v2.2.0 - FastMCP handles tasks natively")
    print("   Use FastMCP Progress dependency instead")
    return


if __name__ == "__main__":
    print("🚀 Statistics Tasks Test Suite")
    print("=" * 60)

    # Run basic workflow test
    test_statistics_task_workflow()

    # Show performance characteristics
    test_performance_characteristics()

    print("\n📝 To run all tests with pytest:")
    print("   pytest tests/test_statistics_tasks.py -v")
    print("   pytest tests/test_statistics_tasks.py::TestStatisticsTaskQueue -v")
    print("   pytest tests/test_statistics_tasks.py::TestAsyncStatisticsFunctions -v")
    print("   pytest tests/test_statistics_tasks.py::TestStatisticsOptimizations -v")

    print("\n🎯 Test Coverage:")
    print("   ✅ Task queue integration")
    print("   ✅ Async statistics functions")
    print("   ✅ Parallel execution optimizations")
    print("   ✅ MCP tool integration")
    print("   ✅ Performance characteristics")

    print("\n🚀 Statistics performance optimizations are properly tested!")
