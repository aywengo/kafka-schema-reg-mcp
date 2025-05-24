import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from mcp_server import app

# Test schemas
AVRO_SCHEMA_V1 = {
    "type": "record",
    "name": "User",
    "fields": [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "string"}
    ]
}

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Kafka Schema Registry MCP Server"

@patch('mcp_server.requests.post')
def test_register_schema_success(mock_post, client):
    """Test successful schema registration."""
    # Mock the Schema Registry response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    response = client.post(
        "/schemas",
        json={
            "subject": "test-subject",
            "schema": json.dumps(AVRO_SCHEMA_V1),
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch('mcp_server.requests.get')
def test_get_schema_success(mock_get, client):
    """Test successful schema retrieval."""
    # Mock the Schema Registry response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "subject": "test-subject",
        "version": 1,
        "id": 1,
        "schema": json.dumps(AVRO_SCHEMA_V1)
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    response = client.get("/schemas/test-subject")
    
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "test-subject"
    assert data["version"] == 1

@patch('mcp_server.requests.get')
def test_get_schema_not_found(mock_get, client):
    """Test schema not found scenario."""
    # Mock the Schema Registry 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")
    mock_get.return_value = mock_response
    
    response = client.get("/schemas/non-existent-subject")
    
    assert response.status_code == 404

@patch('mcp_server.requests.get')
def test_get_schema_versions_success(mock_get, client):
    """Test successful schema versions retrieval."""
    # Mock the Schema Registry response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [1, 2, 3]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    response = client.get("/schemas/test-subject/versions")
    
    assert response.status_code == 200
    versions = response.json()
    assert versions == [1, 2, 3]

@patch('mcp_server.requests.post')
def test_check_compatibility_success(mock_post, client):
    """Test successful compatibility check."""
    # Mock the Schema Registry response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"is_compatible": True}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    response = client.post(
        "/compatibility",
        json={
            "subject": "test-subject",
            "schema": json.dumps(AVRO_SCHEMA_V1),
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_compatible"] is True

def test_invalid_request_body(client):
    """Test invalid request body handling."""
    response = client.post(
        "/schemas",
        json={"invalid": "data"}
    )
    
    assert response.status_code == 422  # Validation error 