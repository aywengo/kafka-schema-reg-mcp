#!/usr/bin/env python3
"""
Test script for Schema Registry metadata endpoints.

This script demonstrates how to use the new metadata endpoints to gather
information about schema registries including version, commit ID, and
cluster information.

Usage:
    python test-registry-metadata.py
"""

import json
import requests
from typing import Dict, Any

# Configuration
SCHEMA_REGISTRY_URL = "http://localhost:8081"
MCP_SERVER_URL = "http://localhost:38000"


def test_direct_metadata_endpoints():
    """Test the metadata endpoints directly against the Schema Registry."""
    print("🔍 Testing direct Schema Registry metadata endpoints...")
    
    # Test /v1/metadata/id endpoint
    print("\n📋 Testing /v1/metadata/id endpoint:")
    try:
        response = requests.get(f"{SCHEMA_REGISTRY_URL}/v1/metadata/id", timeout=10)
        if response.status_code == 200:
            metadata_id = response.json()
            print(f"   ✅ Metadata ID: {json.dumps(metadata_id, indent=2)}")
            
            # Extract cluster information
            scope = metadata_id.get("scope", {})
            clusters = scope.get("clusters", {})
            kafka_cluster = clusters.get("kafka-cluster")
            schema_registry_cluster = clusters.get("schema-registry-cluster")
            
            print(f"   📊 Kafka Cluster ID: {kafka_cluster}")
            print(f"   📊 Schema Registry Cluster ID: {schema_registry_cluster}")
        else:
            print(f"   ❌ Failed to get metadata ID: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting metadata ID: {e}")
    
    # Test /v1/metadata/version endpoint
    print("\n📋 Testing /v1/metadata/version endpoint:")
    try:
        response = requests.get(f"{SCHEMA_REGISTRY_URL}/v1/metadata/version", timeout=10)
        if response.status_code == 200:
            metadata_version = response.json()
            print(f"   ✅ Metadata Version: {json.dumps(metadata_version, indent=2)}")
            
            # Extract version information
            version = metadata_version.get("version")
            commit_id = metadata_version.get("commitId")
            
            print(f"   📊 Schema Registry Version: {version}")
            print(f"   📊 Commit ID: {commit_id}")
        else:
            print(f"   ❌ Failed to get metadata version: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting metadata version: {e}")


def test_mcp_metadata_tools():
    """Test the enhanced MCP tools that now include metadata."""
    print("\n🔧 Testing enhanced MCP tools with metadata...")
    
    # Test enhanced connection test tool
    print("\n📋 Testing test_registry_connection tool (now enhanced with metadata):")
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/tools/test_registry_connection",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            connection_info = response.json()
            print(f"   ✅ Enhanced connection test: {json.dumps(connection_info, indent=2)}")
        else:
            print(f"   ❌ Failed to get enhanced connection test: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting enhanced connection test: {e}")
    
    # Test enhanced statistics tools
    print("\n📋 Testing count_schemas tool (now enhanced with metadata):")
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/tools/count_schemas",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            stats_info = response.json()
            print(f"   ✅ Enhanced schema count: {json.dumps(stats_info, indent=2)}")
        else:
            print(f"   ❌ Failed to get enhanced schema count: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting enhanced schema count: {e}")


def test_enhanced_registry_info():
    """Test the enhanced get_registry_info tool."""
    print("\n🔧 Testing enhanced get_registry_info tool...")
    
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/tools/get_registry_info",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            registry_info = response.json()
            print(f"   ✅ Enhanced registry info: {json.dumps(registry_info, indent=2)}")
            
            # Highlight the new metadata fields
            if "version" in registry_info:
                print(f"   📊 Registry Version: {registry_info['version']}")
            if "commit_id" in registry_info:
                print(f"   📊 Commit ID: {registry_info['commit_id']}")
            if "kafka_cluster_id" in registry_info:
                print(f"   📊 Kafka Cluster ID: {registry_info['kafka_cluster_id']}")
            if "schema_registry_cluster_id" in registry_info:
                print(f"   📊 Schema Registry Cluster ID: {registry_info['schema_registry_cluster_id']}")
        else:
            print(f"   ❌ Failed to get enhanced registry info: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting enhanced registry info: {e}")


def test_enhanced_statistics():
    """Test the enhanced statistics tools that now include metadata."""
    print("\n🔧 Testing enhanced statistics tools...")
    
    # Test enhanced registry statistics
    print("\n📋 Testing get_registry_statistics tool (now enhanced with metadata):")
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/tools/get_registry_statistics",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            stats_info = response.json()
            print(f"   ✅ Enhanced registry statistics: {json.dumps(stats_info, indent=2)}")
            
            # Highlight the new metadata fields
            if "version" in stats_info:
                print(f"   📊 Registry Version: {stats_info['version']}")
            if "commit_id" in stats_info:
                print(f"   📊 Commit ID: {stats_info['commit_id']}")
        else:
            print(f"   ❌ Failed to get enhanced registry statistics: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting enhanced registry statistics: {e}")
    
    # Test enhanced contexts count
    print("\n📋 Testing count_contexts tool (now enhanced with metadata):")
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/tools/count_contexts",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            contexts_info = response.json()
            print(f"   ✅ Enhanced contexts count: {json.dumps(contexts_info, indent=2)}")
        else:
            print(f"   ❌ Failed to get enhanced contexts count: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting enhanced contexts count: {e}")


def main():
    """Run all metadata tests."""
    print("🚀 Schema Registry Metadata Testing")
    print("=" * 50)
    
    # Test direct endpoints
    test_direct_metadata_endpoints()
    
    # Test enhanced MCP tools
    test_mcp_metadata_tools()
    
    # Test enhanced registry info
    test_enhanced_registry_info()
    
    # Test enhanced statistics
    test_enhanced_statistics()
    
    print("\n✅ Metadata testing completed!")
    print("\n💡 Usage Examples:")
    print("   - Use get_registry_info() for comprehensive registry information with metadata")
    print("   - Use test_registry_connection() for connection testing with metadata")
    print("   - Use count_schemas(), count_contexts(), etc. for statistics with metadata")
    print("   - Use get_registry_statistics() for comprehensive stats with metadata")


if __name__ == "__main__":
    main() 