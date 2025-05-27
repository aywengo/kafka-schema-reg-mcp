#!/usr/bin/env python3
"""
Test for Zero Migration Bug Fix

This test specifically validates that the migrate_context function
actually migrates schemas and doesn't just return metadata with 
"0 subjects migrated" as it did before the fix.
"""

import os
import sys
import json
import uuid
import requests
from unittest.mock import Mock, patch

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

def test_migrate_context_bug_fix():
    """
    Test that migrate_context actually performs migrations
    and doesn't return 0 subjects migrated when there are subjects to migrate.
    """
    print("🧪 Testing migrate_context bug fix (0 subjects migrated)")
    
    # Test context
    test_context = f"test-{uuid.uuid4().hex[:8]}"
    
    # Mock registry clients
    source_client = Mock()
    target_client = Mock()
    
    # Mock source client to return test subjects
    test_subjects = ["user-events", "order-events", "product-events"]
    source_client.get_subjects.return_value = test_subjects
    source_client.config.name = "dev"
    source_client.auth = None
    source_client.headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    
    # Mock target client
    target_client.config.name = "prod"
    target_client.auth = None
    target_client.headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    
    # Mock build_context_url method
    def mock_build_context_url(path, context=None):
        if context:
            return f"http://mock-registry/contexts/{context}{path}"
        return f"http://mock-registry{path}"
    
    source_client.build_context_url = mock_build_context_url
    target_client.build_context_url = mock_build_context_url
    
    # Mock successful schema retrieval and registration
    mock_schema_data = {
        "schema": json.dumps({
            "type": "record",
            "name": "TestEvent",
            "fields": [{"name": "id", "type": "string"}]
        }),
        "schemaType": "AVRO",
        "id": 123,
        "version": 1
    }
    
    # Mock requests for successful migrations
    def mock_requests_get(url, **kwargs):
        response = Mock()
        if "versions/latest" in url:
            response.status_code = 200
            response.json.return_value = mock_schema_data
        else:
            response.status_code = 404  # Not found in target
        return response
    
    def mock_requests_post(url, **kwargs):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"id": 456}
        response.raise_for_status = Mock()
        return response
    
    # Patch registry manager and requests
    with patch.object(mcp_server.registry_manager, 'get_registry') as mock_get_registry, \
         patch('kafka_schema_registry_multi_mcp.requests.get', side_effect=mock_requests_get), \
         patch('kafka_schema_registry_multi_mcp.requests.post', side_effect=mock_requests_post):
        
        def mock_registry_lookup(name):
            if name == "dev":
                return source_client
            elif name == "prod":
                return target_client
            return None
        
        mock_get_registry.side_effect = mock_registry_lookup
        
        # Call migrate_context (the fixed version)
        result = mcp_server.migrate_context(
            context=test_context,
            source_registry="dev",
            target_registry="prod",
            dry_run=False
        )
        
        # Validate the fix worked
        print(f"📋 Migration result: {json.dumps(result, indent=2)}")
        
        # Critical assertions to validate the bug is fixed
        assert "error" not in result, f"Migration failed with error: {result.get('error')}"
        
        # The key fix: successful_migrations should NOT be 0
        successful_migrations = result.get('successful_migrations', 0)
        assert successful_migrations > 0, f"BUG STILL EXISTS: {successful_migrations} subjects migrated (should be > 0)"
        
        # Should match the number of test subjects
        assert successful_migrations == len(test_subjects), f"Expected {len(test_subjects)} migrations, got {successful_migrations}"
        
        # Should have proper migration results structure
        assert 'results' in result, "Missing detailed migration results"
        assert 'successful_subjects' in result['results'], "Missing successful_subjects in results"
        
        successful_subjects = result['results']['successful_subjects']
        assert len(successful_subjects) == len(test_subjects), f"Results mismatch: {len(successful_subjects)} vs {len(test_subjects)}"
        
        # Validate migration tracking
        assert 'migration_id' in result, "Missing migration_id"
        assert result.get('status') == 'completed', f"Expected status 'completed', got {result.get('status')}"
        
        print("✅ migrate_context bug fix validated:")
        print(f"   • Successfully migrated: {successful_migrations} subjects")
        print(f"   • Total subjects: {result.get('total_subjects', 0)}")
        print(f"   • Success rate: {result.get('success_rate', '0%')}")
        print(f"   • Migration ID: {result.get('migration_id', 'None')}")
        
        return True

def test_dry_run_vs_actual_migration():
    """
    Test that dry run and actual migration produce different results
    """
    print("\n🧪 Testing dry run vs actual migration behavior")
    
    # Mock setup (simplified)
    with patch.object(mcp_server.registry_manager, 'get_registry') as mock_get_registry:
        source_client = Mock()
        source_client.get_subjects.return_value = ["test-subject"]
        source_client.config.name = "dev"
        
        target_client = Mock()
        target_client.config.name = "prod"
        
        def mock_registry_lookup(name):
            return source_client if name == "dev" else target_client
        
        mock_get_registry.side_effect = mock_registry_lookup
        
        # Test dry run
        dry_run_result = mcp_server.migrate_context(
            context="test-context",
            source_registry="dev",
            target_registry="prod",
            dry_run=True
        )
        
        # Dry run should show preview, not completed migration
        assert dry_run_result.get('dry_run') == True, "Dry run not marked correctly"
        assert dry_run_result.get('status') == 'preview', f"Expected preview status, got {dry_run_result.get('status')}"
        assert 'successful_migrations' not in dry_run_result, "Dry run should not have successful_migrations"
        assert 'subject_count' in dry_run_result, "Dry run should show subject_count"
        
        print("✅ Dry run behavior validated")
        return True

def test_empty_context_handling():
    """
    Test that empty contexts are handled correctly
    """
    print("\n🧪 Testing empty context handling")
    
    with patch.object(mcp_server.registry_manager, 'get_registry') as mock_get_registry:
        source_client = Mock()
        source_client.get_subjects.return_value = []  # Empty context
        source_client.config.name = "dev"
        
        target_client = Mock()
        target_client.config.name = "prod"
        
        def mock_registry_lookup(name):
            return source_client if name == "dev" else target_client
        
        mock_get_registry.side_effect = mock_registry_lookup
        
        # Test empty context migration
        result = mcp_server.migrate_context(
            context="empty-context",
            source_registry="dev", 
            target_registry="prod",
            dry_run=False
        )
        
        # Should handle empty context gracefully
        if 'error' in result:
            assert "No subjects found" in result['error'], f"Unexpected error message: {result['error']}"
        else:
            assert result.get('subjects_found', -1) == 0, "Should report 0 subjects found"
        
        print("✅ Empty context handling validated")
        return True

def main():
    """Run all bug fix validation tests"""
    print("🚀 Testing Migration Bug Fixes")
    print("=" * 40)
    
    tests = [
        ("Zero Migration Bug Fix", test_migrate_context_bug_fix),
        ("Dry Run vs Actual", test_dry_run_vs_actual_migration), 
        ("Empty Context Handling", test_empty_context_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL BUG FIX TESTS PASSED!")
        print("✅ The '0 subjects migrated' bug has been fixed")
        print("✅ migrate_context now actually performs migrations")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 