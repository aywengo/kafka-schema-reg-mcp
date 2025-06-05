import sys
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Add the parent directory to sys.path so we can import oauth_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_schema_registry_multi_mcp import (
    count_contexts,
    count_schemas,
    count_schema_versions,
    get_registry_statistics
)

@pytest.fixture
def mock_registry_client():
    client = Mock()
    client.config.name = "test-registry"
    return client

@pytest.fixture
def mock_registry_manager():
    manager = Mock()
    return manager

def test_count_contexts_success(mock_registry_client, mock_registry_manager):
    # Setup
    contexts = ["context1", "context2", "context3"]
    mock_registry_client.get_contexts.return_value = contexts
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager):
        result = count_contexts("test-registry")
        
        assert result["registry"] == "test-registry"
        assert result["total_contexts"] == 3
        assert result["contexts"] == contexts
        assert "counted_at" in result

def test_count_contexts_registry_not_found(mock_registry_manager):
    mock_registry_manager.get_registry.return_value = None
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager):
        result = count_contexts("non-existent")
        
        assert "error" in result
        assert "not found" in result["error"]

def test_count_schemas_success(mock_registry_client, mock_registry_manager):
    # Setup
    subjects = ["subject1", "subject2"]
    mock_registry_client.get_subjects.return_value = subjects
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager):
        result = count_schemas(context="test-context", registry="test-registry")
        
        assert result["registry"] == "test-registry"
        assert result["context"] == "test-context"
        assert result["total_schemas"] == 2
        assert result["schemas"] == subjects
        assert "counted_at" in result

def test_count_schema_versions_success(mock_registry_client, mock_registry_manager):
    # Setup
    versions = [1, 2, 3]
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager), \
         patch('kafka_schema_registry_multi_mcp.get_schema_versions', return_value=versions):
        result = count_schema_versions(
            subject="test-subject",
            context="test-context",
            registry="test-registry"
        )
        
        assert result["registry"] == "test-registry"
        assert result["context"] == "test-context"
        assert result["subject"] == "test-subject"
        assert result["total_versions"] == 3
        assert result["versions"] == versions
        assert "counted_at" in result

def test_get_registry_statistics_success(mock_registry_client, mock_registry_manager):
    # Setup
    contexts = ["context1", "context2"]
    subjects_context1 = ["subject1", "subject2"]
    subjects_context2 = ["subject3"]
    versions_subject1 = [1, 2]
    versions_subject2 = [1]
    versions_subject3 = [1, 2, 3]
    
    mock_registry_client.get_contexts.return_value = contexts
    mock_registry_client.get_subjects.side_effect = [
        subjects_context1,  # for context1
        subjects_context2,  # for context2
        []  # for default context
    ]
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager), \
         patch('kafka_schema_registry_multi_mcp.get_schema_versions', side_effect=[
             versions_subject1,  # for subject1
             versions_subject2,  # for subject2
             versions_subject3   # for subject3
         ]):
        result = get_registry_statistics(registry="test-registry")
        
        assert result["registry"] == "test-registry"
        assert result["total_contexts"] == 2
        assert result["total_schemas"] == 3
        assert result["total_versions"] == 6
        assert result["average_versions_per_schema"] == 2.0
        assert len(result["contexts"]) == 3  # 2 named contexts + 1 default context
        assert "counted_at" in result

def test_get_registry_statistics_without_details(mock_registry_client, mock_registry_manager):
    # Setup
    contexts = ["context1", "context2"]
    subjects_context1 = ["subject1"]
    subjects_context2 = ["subject2"]
    
    mock_registry_client.get_contexts.return_value = contexts
    mock_registry_client.get_subjects.side_effect = [
        subjects_context1,  # for context1
        subjects_context2,  # for context2
        []  # for default context
    ]
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager), \
         patch('kafka_schema_registry_multi_mcp.get_schema_versions', return_value=[1]):
        result = get_registry_statistics(
            registry="test-registry",
            include_context_details=False
        )
        
        assert result["registry"] == "test-registry"
        assert result["total_contexts"] == 2
        assert result["total_schemas"] == 2
        assert result["total_versions"] == 2
        assert result["contexts"] is None
        assert "counted_at" in result

def test_error_handling(mock_registry_client, mock_registry_manager):
    # Setup
    mock_registry_client.get_contexts.side_effect = Exception("Test error")
    mock_registry_manager.get_registry.return_value = mock_registry_client
    
    with patch('kafka_schema_registry_multi_mcp.registry_manager', mock_registry_manager):
        result = count_contexts("test-registry")
        
        assert "error" in result
        assert "Test error" in result["error"] 