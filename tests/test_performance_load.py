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
import os
import sys
import json
import time
import statistics
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import threading

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
                "doc": f"Test field {i} for performance testing"
            }
            for i in range(field_count)
        ]
    }

def generate_complex_schema(name: str) -> Dict[str, Any]:
    """Generate a complex schema with nested structures."""
    return {
        "type": "record",
        "name": name,
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "metadata", "type": {
                "type": "record",
                "name": "Metadata",
                "fields": [
                    {"name": "created_at", "type": "long"},
                    {"name": "updated_at", "type": "long"},
                    {"name": "version", "type": "string"}
                ]
            }},
            {"name": "tags", "type": {"type": "array", "items": "string"}},
            {"name": "properties", "type": {"type": "map", "values": "string"}},
            {"name": "optional_data", "type": ["null", {
                "type": "record",
                "name": "OptionalData",
                "fields": [
                    {"name": "extra_field", "type": "string"}
                ]
            }], "default": None}
        ]
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
            "p95_time_ms": statistics.quantiles(times, n=20)[18] * 1000 if len(times) > 5 else max(times) * 1000,
            "total_errors": self.error_counts[operation]
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        all_operations = list(self.operation_times.keys())
        return {
            "operations_tested": len(all_operations),
            "max_concurrent_operations": self.max_concurrent,
            "operation_stats": {op: self.get_stats(op) for op in all_operations}
        }

# Global metrics instance
metrics = PerformanceMetrics()

async def timed_operation(session: ClientSession, operation: str, tool_name: str, params: Dict[str, Any]) -> bool:
    """Execute an operation and record its performance."""
    metrics.start_concurrent_operation()
    start_time = time.time()
    success = True
    
    try:
        result = await session.call_tool(tool_name, params)
        response = json.loads(result.content[0].text) if result.content else {}
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
    
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    env["SCHEMA_REGISTRY_NAME_1"] = "perf_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_unified_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Sequential schema registration
                print("Test 1: Sequential schema registration (50 schemas)")
                for i in range(50):
                    schema = generate_test_schema(f"PerfTest{i}", field_count=5)
                    await timed_operation(session, "register_schema_seq", "register_schema", {
                        "subject": f"perf-test-{i}",
                        "schema_definition": schema,
                        "registry": "perf_test"
                    })
                
                seq_stats = metrics.get_stats("register_schema_seq")
                print(f"  ✅ Sequential registration: {seq_stats['avg_time_ms']:.2f}ms avg, {seq_stats['success_rate']:.2%} success")
                
                # Test 2: List subjects performance
                print("\nTest 2: List subjects with many schemas")
                for i in range(10):
                    await timed_operation(session, "list_subjects_perf", "list_subjects", {
                        "registry": "perf_test"
                    })
                
                list_stats = metrics.get_stats("list_subjects_perf")
                print(f"  ✅ List subjects: {list_stats['avg_time_ms']:.2f}ms avg, {list_stats['success_rate']:.2%} success")
                
                # Test 3: Schema retrieval performance
                print("\nTest 3: Schema retrieval performance")
                for i in range(20):
                    await timed_operation(session, "get_schema_perf", "get_schema", {
                        "subject": f"perf-test-{i % 10}",  # Cycle through first 10 schemas
                        "registry": "perf_test"
                    })
                
                get_stats = metrics.get_stats("get_schema_perf")
                print(f"  ✅ Get schema: {get_stats['avg_time_ms']:.2f}ms avg, {get_stats['success_rate']:.2%} success")
                
                print("\n🎉 Schema Registration Performance Tests Complete!")
                
    except Exception as e:
        print(f"❌ Schema registration performance test failed: {e}")

async def test_concurrent_operations():
    """Test performance under concurrent load."""
    print("\n⚡ Testing Concurrent Operations Performance")
    print("-" * 50)
    
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    env["SCHEMA_REGISTRY_NAME_1"] = "concurrent_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_unified_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Concurrent schema registration
                print("Test 1: Concurrent schema registration (20 concurrent)")
                
                async def register_concurrent_schema(index: int):
                    schema = generate_test_schema(f"ConcurrentTest{index}", field_count=3)
                    return await timed_operation(session, "register_concurrent", "register_schema", {
                        "subject": f"concurrent-test-{index}",
                        "schema_definition": schema,
                        "registry": "concurrent_test"
                    })
                
                # Run 20 concurrent registrations
                tasks = [register_concurrent_schema(i) for i in range(20)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if r is True)
                concurrent_stats = metrics.get_stats("register_concurrent")
                print(f"  ✅ Concurrent registration: {success_count}/20 successful")
                print(f"     Average time: {concurrent_stats['avg_time_ms']:.2f}ms")
                print(f"     Max concurrent: {metrics.max_concurrent}")
                
                # Test 2: Mixed concurrent operations
                print("\nTest 2: Mixed concurrent operations (read/write)")
                
                async def mixed_operation(index: int):
                    if index % 3 == 0:
                        return await timed_operation(session, "mixed_list", "list_subjects", {
                            "registry": "concurrent_test"
                        })
                    elif index % 3 == 1:
                        return await timed_operation(session, "mixed_get", "get_schema", {
                            "subject": f"concurrent-test-{index % 10}",
                            "registry": "concurrent_test"
                        })
                    else:
                        schema = generate_test_schema(f"MixedTest{index}")
                        return await timed_operation(session, "mixed_register", "register_schema", {
                            "subject": f"mixed-test-{index}",
                            "schema_definition": schema,
                            "registry": "concurrent_test"
                        })
                
                # Run 30 mixed concurrent operations
                mixed_tasks = [mixed_operation(i) for i in range(30)]
                mixed_results = await asyncio.gather(*mixed_tasks, return_exceptions=True)
                
                mixed_success = sum(1 for r in mixed_results if r is True)
                print(f"  ✅ Mixed operations: {mixed_success}/30 successful")
                
                for op_type in ["mixed_list", "mixed_get", "mixed_register"]:
                    if op_type in metrics.operation_times:
                        stats = metrics.get_stats(op_type)
                        print(f"     {op_type}: {stats['avg_time_ms']:.2f}ms avg")
                
                print("\n🎉 Concurrent Operations Performance Tests Complete!")
                
    except Exception as e:
        print(f"❌ Concurrent operations performance test failed: {e}")

async def test_multi_registry_performance():
    """Test performance with multiple registries."""
    print("\n🏢 Testing Multi-Registry Performance")
    print("-" * 50)
    
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    # Setup 4 registries for performance testing
    for i in range(1, 5):
        env[f"SCHEMA_REGISTRY_NAME_{i}"] = f"registry_{i}"
        env[f"SCHEMA_REGISTRY_URL_{i}"] = "http://localhost:38081"
        env[f"READONLY_{i}"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_unified_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Registry listing performance
                print("Test 1: Registry operations performance")
                for i in range(10):
                    await timed_operation(session, "list_registries_perf", "list_registries", {})
                
                # Test 2: Cross-registry connection testing
                print("\nTest 2: Cross-registry connection testing")
                for i in range(5):
                    await timed_operation(session, "test_all_registries_perf", "test_all_registries", {})
                
                # Test 3: Schema registration across registries
                print("\nTest 3: Schema registration across multiple registries")
                registries = ["registry_1", "registry_2", "registry_3", "registry_4"]
                
                for i, registry in enumerate(registries):
                    for j in range(5):  # 5 schemas per registry
                        schema = generate_test_schema(f"MultiReg{i}_{j}")
                        await timed_operation(session, f"register_multi_{registry}", "register_schema", {
                            "subject": f"multi-reg-{i}-{j}",
                            "schema_definition": schema,
                            "registry": registry
                        })
                
                # Test 4: Cross-registry comparison performance
                print("\nTest 4: Cross-registry comparison performance")
                for i in range(3):
                    await timed_operation(session, "compare_registries_perf", "compare_registries", {
                        "source_registry": "registry_1",
                        "target_registry": "registry_2"
                    })
                
                # Test 5: Registry info retrieval
                print("\nTest 5: Registry info retrieval performance")
                for registry in registries:
                    for i in range(3):
                        await timed_operation(session, "get_registry_info_perf", "get_registry_info", {
                            "registry_name": registry
                        })
                
                # Report multi-registry stats
                list_reg_stats = metrics.get_stats("list_registries_perf")
                test_all_stats = metrics.get_stats("test_all_registries_perf") 
                compare_stats = metrics.get_stats("compare_registries_perf")
                info_stats = metrics.get_stats("get_registry_info_perf")
                
                print(f"\n  ✅ Performance Results:")
                print(f"     List registries: {list_reg_stats['avg_time_ms']:.2f}ms")
                print(f"     Test all registries: {test_all_stats['avg_time_ms']:.2f}ms")
                print(f"     Compare registries: {compare_stats['avg_time_ms']:.2f}ms")
                print(f"     Registry info: {info_stats['avg_time_ms']:.2f}ms")
                
                print("\n🎉 Multi-Registry Performance Tests Complete!")
                
    except Exception as e:
        print(f"❌ Multi-registry performance test failed: {e}")

async def test_large_schema_performance():
    """Test performance with large and complex schemas."""
    print("\n📈 Testing Large Schema Performance")
    print("-" * 50)
    
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    env["SCHEMA_REGISTRY_NAME_1"] = "large_schema_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_unified_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Large schemas (many fields)
                print("Test 1: Large schemas with many fields")
                field_counts = [50, 100, 200]
                
                for field_count in field_counts:
                    large_schema = generate_test_schema(f"LargeSchema{field_count}Fields", field_count)
                    await timed_operation(session, f"register_large_{field_count}", "register_schema", {
                        "subject": f"large-schema-{field_count}-fields",
                        "schema_definition": large_schema,
                        "registry": "large_schema_test"
                    })
                    
                    stats = metrics.get_stats(f"register_large_{field_count}")
                    print(f"  ✅ {field_count} fields: {stats['avg_time_ms']:.2f}ms")
                
                # Test 2: Complex nested schemas
                print("\nTest 2: Complex nested schemas")
                for i in range(10):
                    complex_schema = generate_complex_schema(f"ComplexSchema{i}")
                    await timed_operation(session, "register_complex", "register_schema", {
                        "subject": f"complex-schema-{i}",
                        "schema_definition": complex_schema,
                        "registry": "large_schema_test"
                    })
                
                complex_stats = metrics.get_stats("register_complex")
                print(f"  ✅ Complex schemas: {complex_stats['avg_time_ms']:.2f}ms avg")
                
                # Test 3: Retrieve large schemas
                print("\nTest 3: Retrieve large schemas performance")
                for field_count in field_counts:
                    await timed_operation(session, f"get_large_{field_count}", "get_schema", {
                        "subject": f"large-schema-{field_count}-fields",
                        "registry": "large_schema_test"
                    })
                    
                    stats = metrics.get_stats(f"get_large_{field_count}")
                    print(f"  ✅ Get {field_count} fields: {stats['avg_time_ms']:.2f}ms")
                
                # Test 4: Compatibility checking with large schemas
                print("\nTest 4: Compatibility checking performance")
                modified_schema = generate_test_schema("LargeSchema50Fields", 51)  # Add one field
                await timed_operation(session, "check_compatibility_large", "check_compatibility", {
                    "subject": "large-schema-50-fields",
                    "schema_definition": modified_schema,
                    "registry": "large_schema_test"
                })
                
                compat_stats = metrics.get_stats("check_compatibility_large")
                print(f"  ✅ Compatibility check: {compat_stats['avg_time_ms']:.2f}ms")
                
                print("\n🎉 Large Schema Performance Tests Complete!")
                
    except Exception as e:
        print(f"❌ Large schema performance test failed: {e}")

async def test_memory_and_resource_usage():
    """Test memory usage and resource consumption patterns."""
    print("\n💾 Testing Memory and Resource Usage")
    print("-" * 50)
    
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    env["SCHEMA_REGISTRY_NAME_1"] = "resource_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_unified_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Sustained load test
                print("Test 1: Sustained load test (100 operations)")
                for i in range(100):
                    if i % 4 == 0:
                        await timed_operation(session, "sustained_register", "register_schema", {
                            "subject": f"sustained-test-{i}",
                            "schema_definition": generate_test_schema(f"SustainedTest{i}"),
                            "registry": "resource_test"
                        })
                    elif i % 4 == 1:
                        await timed_operation(session, "sustained_list", "list_subjects", {
                            "registry": "resource_test"
                        })
                    elif i % 4 == 2:
                        await timed_operation(session, "sustained_get", "get_schema", {
                            "subject": f"sustained-test-{i // 4 * 4}",
                            "registry": "resource_test"
                        })
                    else:
                        await timed_operation(session, "sustained_config", "get_global_config", {
                            "registry": "resource_test"
                        })
                    
                    # Brief pause to simulate realistic usage
                    await asyncio.sleep(0.01)
                
                print("  ✅ Sustained load test completed")
                
                for op_type in ["sustained_register", "sustained_list", "sustained_get", "sustained_config"]:
                    if op_type in metrics.operation_times:
                        stats = metrics.get_stats(op_type)
                        print(f"     {op_type}: {stats['avg_time_ms']:.2f}ms avg, {stats['success_rate']:.2%} success")
                
                # Test 2: Memory stress test with many schemas
                print("\nTest 2: Memory stress test (creating many schemas)")
                batch_size = 50
                for batch in range(3):  # 3 batches of 50
                    print(f"  Processing batch {batch + 1}/3...")
                    batch_tasks = []
                    for i in range(batch_size):
                        schema_index = batch * batch_size + i
                        schema = generate_test_schema(f"MemoryStress{schema_index}", field_count=20)
                        task = timed_operation(session, "memory_stress", "register_schema", {
                            "subject": f"memory-stress-{schema_index}",
                            "schema_definition": schema,
                            "registry": "resource_test"
                        })
                        batch_tasks.append(task)
                    
                    await asyncio.gather(*batch_tasks)
                
                memory_stats = metrics.get_stats("memory_stress")
                print(f"  ✅ Memory stress test: {memory_stats['avg_time_ms']:.2f}ms avg, {memory_stats['success_rate']:.2%} success")
                
                print("\n🎉 Memory and Resource Usage Tests Complete!")
                
    except Exception as e:
        print(f"❌ Memory and resource usage test failed: {e}")

async def main():
    """Run all performance and load tests."""
    print("🧪 Starting Performance and Load Testing")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        await test_schema_registration_performance()
        await test_concurrent_operations()
        await test_multi_registry_performance()
        await test_large_schema_performance()
        await test_memory_and_resource_usage()
        
        total_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("🎉 All Performance and Load Tests Complete!")
        print(f"\n📊 **Overall Performance Summary:**")
        print(f"• Total test time: {total_time:.2f}s")
        
        summary = metrics.get_summary()
        print(f"• Operations tested: {summary['operations_tested']}")
        print(f"• Max concurrent operations: {summary['max_concurrent_operations']}")
        
        print(f"\n🏆 **Top Performance Results:**")
        # Find fastest and slowest operations
        op_stats = summary['operation_stats']
        if op_stats:
            fastest = min(op_stats.items(), key=lambda x: x[1].get('avg_time_ms', float('inf')))
            slowest = max(op_stats.items(), key=lambda x: x[1].get('avg_time_ms', 0))
            
            print(f"• Fastest operation: {fastest[0]} ({fastest[1]['avg_time_ms']:.2f}ms avg)")
            print(f"• Slowest operation: {slowest[0]} ({slowest[1]['avg_time_ms']:.2f}ms avg)")
            
            # Calculate overall success rate
            total_success = sum(stats['count'] * stats['success_rate'] for stats in op_stats.values())
            total_operations = sum(stats['count'] for stats in op_stats.values())
            overall_success_rate = total_success / total_operations if total_operations > 0 else 0
            
            print(f"• Overall success rate: {overall_success_rate:.2%}")
            print(f"• Total operations executed: {total_operations}")
        
        print(f"\n✅ **Performance Test Categories:**")
        print("• Schema Registration Performance")
        print("• Concurrent Operations")
        print("• Multi-Registry Operations")
        print("• Large Schema Handling")
        print("• Memory and Resource Usage")
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Performance and load tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 