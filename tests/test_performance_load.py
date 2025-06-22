#!/usr/bin/env python3
"""
Performance and Load Testing for unified server in multi-registry mode

Tests system performance under various loads:
- Concurrent operations across registries
- Large-scale schema registration
- Bulk migration operations
- Registry comparison with many schemas
- Memory and resource usage patterns
- Response time measurements
- Throughput testing
"""

import asyncio
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client


# Performance test schemas
def generate_test_schema(name: str, field_count: int = 10) -> Dict[str, Any]:
    """Generate a test schema with specified number of fields."""
    return {
        "type": "record",
        "name": name,
        "fields": [
            {
                "name": f"field_{i}",
                "type": "string",
                "doc": f"Test field {i} for performance testing",
            }
            for i in range(field_count)
        ],
    }


def generate_complex_schema(name: str) -> Dict[str, Any]:
    """Generate a complex schema with nested structures."""
    return {
        "type": "record",
        "name": name,
        "fields": [
            {"name": "id", "type": "long"},
            {
                "name": "metadata",
                "type": {
                    "type": "record",
                    "name": "Metadata",
                    "fields": [
                        {"name": "created_at", "type": "long"},
                        {"name": "updated_at", "type": "long"},
                        {"name": "version", "type": "string"},
                    ],
                },
            },
            {"name": "tags", "type": {"type": "array", "items": "string"}},
            {"name": "properties", "type": {"type": "map", "values": "string"}},
            {
                "name": "optional_data",
                "type": [
                    "null",
                    {
                        "type": "record",
                        "name": "OptionalData",
                        "fields": [{"name": "extra_field", "type": "string"}],
                    },
                ],
                "default": None,
            },
        ],
    }


class PerformanceMetrics:
    """Track performance metrics during tests."""

    def __init__(self):
        self.operation_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self.concurrent_operations = 0
        self.max_concurrent = 0

    def record_operation(self, operation: str, duration: float, success: bool):
        """Record an operation's performance."""
        if operation not in self.operation_times:
            self.operation_times[operation] = []
            self.error_counts[operation] = 0
            self.success_counts[operation] = 0

        self.operation_times[operation].append(duration)

        if success:
            self.success_counts[operation] += 1
        else:
            self.error_counts[operation] += 1

    def start_concurrent_operation(self):
        """Track start of concurrent operation."""
        self.concurrent_operations += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent_operations)

    def end_concurrent_operation(self):
        """Track end of concurrent operation."""
        self.concurrent_operations -= 1

    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation."""
        if operation not in self.operation_times:
            return {"error": "No data for operation"}

        times = self.operation_times[operation]
        return {
            "count": len(times),
            "success_rate": self.success_counts[operation] / len(times) if times else 0,
            "avg_time_ms": statistics.mean(times) * 1000,
            "min_time_ms": min(times) * 1000,
            "max_time_ms": max(times) * 1000,
            "median_time_ms": statistics.median(times) * 1000,
            "p95_time_ms": (
                statistics.quantiles(times, n=20)[18] * 1000
                if len(times) > 5
                else max(times) * 1000
            ),
            "total_errors": self.error_counts[operation],
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        all_operations = list(self.operation_times.keys())
        return {
            "operations_tested": len(all_operations),
            "max_concurrent_operations": self.max_concurrent,
            "operation_stats": {op: self.get_stats(op) for op in all_operations},
        }


# Global metrics instance
metrics = PerformanceMetrics()


async def timed_operation(
    client: Client, operation: str, tool_name: str, params: Dict[str, Any]
) -> bool:
    """Execute an operation and record its performance."""
    metrics.start_concurrent_operation()
    start_time = time.time()
    success = True

    try:
        result = await client.call_tool(tool_name, params)
        response_text = result[0].text if result else "{}"
        response = json.loads(response_text)
        if response.get("error"):
            success = False
    except Exception:
        success = False
    finally:
        duration = time.time() - start_time
        metrics.record_operation(operation, duration, success)
        metrics.end_concurrent_operation()

    return success


async def test_schema_registration_performance():
    """Test performance of schema registration operations."""
    print("\n📊 Testing Schema Registration Performance")
    print("-" * 50)

    # Set up environment
    env = {
        "SCHEMA_REGISTRY_NAME_1": "perf_test",
        "SCHEMA_REGISTRY_URL_1": "http://localhost:38081",
        "READONLY_1": "false",
    }

    for key, value in env.items():
        os.environ[key] = value

    server_script = "kafka_schema_registry_unified_mcp.py"

    try:
        client = Client(server_script)

        async with client:
            # Test 1: Sequential schema registration
            print("Test 1: Sequential schema registration (50 schemas)")
            for i in range(50):
                schema = generate_test_schema(f"PerfTest{i}", field_count=5)
                await timed_operation(
                    client,
                    "sequential_registration",
                    "register_schema",
                    {
                        "subject": f"perf-test-sequential-{i}",
                        "schema_definition": schema,
                        "registry": "perf_test",
                    },
                )

            # Test 2: Concurrent schema registration
            print("Test 2: Concurrent schema registration (20 schemas)")
            tasks = []
            for i in range(20):
                schema = generate_test_schema(f"ConcurrentTest{i}", field_count=3)
                task = timed_operation(
                    client,
                    "concurrent_registration",
                    "register_schema",
                    {
                        "subject": f"perf-test-concurrent-{i}",
                        "schema_definition": schema,
                        "registry": "perf_test",
                    },
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Test 3: Complex schema registration
            print("Test 3: Complex schema registration")
            for i in range(10):
                complex_schema = generate_complex_schema(f"Complex{i}")
                await timed_operation(
                    client,
                    "complex_registration",
                    "register_schema",
                    {
                        "subject": f"perf-test-complex-{i}",
                        "schema_definition": complex_schema,
                        "registry": "perf_test",
                    },
                )

            print("✅ Schema registration performance tests completed")

    except Exception as e:
        print(f"❌ Schema registration performance test failed: {e}")


async def test_concurrent_operations():
    """Test concurrent operations across different tools."""
    print("\n🔄 Testing Concurrent Operations")
    print("-" * 50)

    # Set up environment
    env = {"SCHEMA_REGISTRY_URL": "http://localhost:38081"}

    for key, value in env.items():
        os.environ[key] = value

    server_script = "kafka_schema_registry_unified_mcp.py"

    try:
        client = Client(server_script)

        async with client:

            async def register_concurrent_schema(index: int):
                """Register a schema concurrently."""
                schema = generate_test_schema(f"Concurrent{index}")
                return await timed_operation(
                    client,
                    "concurrent_mixed",
                    "register_schema",
                    {
                        "subject": f"concurrent-test-{index}",
                        "schema_definition": schema,
                    },
                )

            async def mixed_operation(index: int):
                """Perform mixed operations concurrently."""
                operations = [
                    ("list_subjects", {}),
                    ("get_global_config", {}),
                    ("list_contexts", {}),
                ]

                op_name, params = operations[index % len(operations)]
                return await timed_operation(
                    client, f"concurrent_{op_name}", op_name, params
                )

            # Run concurrent operations
            tasks = []

            # Add schema registration tasks
            for i in range(5):
                tasks.append(register_concurrent_schema(i))

            # Add mixed operation tasks
            for i in range(10):
                tasks.append(mixed_operation(i))

            await asyncio.gather(*tasks, return_exceptions=True)

            print("✅ Concurrent operations test completed")

    except Exception as e:
        print(f"❌ Concurrent operations test failed: {e}")


async def main():
    """Run all performance tests."""
    print("🚀 Starting Performance and Load Testing")
    print("=" * 60)

    try:
        await test_schema_registration_performance()
        await test_concurrent_operations()

        # Print final metrics
        print("\n📊 Performance Test Summary")
        print("=" * 60)
        summary = metrics.get_summary()
        print(f"Operations tested: {summary['operations_tested']}")
        print(f"Max concurrent operations: {summary['max_concurrent_operations']}")

        for operation, stats in summary["operation_stats"].items():
            if stats.get("count", 0) > 0:
                print(f"\n{operation}:")
                print(f"  Count: {stats['count']}")
                print(f"  Success rate: {stats.get('success_rate', 0)*100:.1f}%")
                print(f"  Avg time: {stats.get('avg_time_ms', 0):.1f}ms")
                print(f"  Min time: {stats.get('min_time_ms', 0):.1f}ms")
                print(f"  Max time: {stats.get('max_time_ms', 0):.1f}ms")
                print(f"  P95 time: {stats.get('p95_time_ms', 0):.1f}ms")
                if stats.get("total_errors", 0) > 0:
                    print(f"  Errors: {stats['total_errors']}")

        print("\n✅ All performance tests completed!")

    except Exception as e:
        print(f"❌ Performance testing failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
