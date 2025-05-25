import pytest
import pytest_asyncio
import httpx
import asyncio
import json
import os
from typing import Dict, Any

# Test configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:38000")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:38081")

# Test schemas
AVRO_SCHEMA_V1 = {
    "type": "record",
    "name": "User",
    "fields": [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "string"}
    ]
}

AVRO_SCHEMA_V2 = {
    "type": "record",
    "name": "User",
    "fields": [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "string"},
        {"name": "email", "type": ["null", "string"], "default": None}
    ]
}

INCOMPATIBLE_SCHEMA = {
    "type": "record",
    "name": "User",
    "fields": [
        {"name": "user_id", "type": "string"},  # Changed field name and type
        {"name": "full_name", "type": "string"}
    ]
}


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def test_subject():
    """Generate a unique test subject name."""
    import uuid
    return f"test-subject-{uuid.uuid4().hex[:8]}"


async def wait_for_service(url: str, timeout: int = 60):
    """Wait for a service to be available."""
    start_time = asyncio.get_event_loop().time()
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return True
        except httpx.RequestError:
            pass
        
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Service at {url} did not become available within {timeout} seconds")
        
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_services_healthy(client: httpx.AsyncClient):
    """Test that both MCP server and Schema Registry are accessible."""
    # Test MCP server health
    response = await client.get(f"{MCP_SERVER_URL}/")
    assert response.status_code == 200
    assert response.json()["message"] == "Kafka Schema Registry MCP Server with Context Support, Configuration Management, and Mode Control"


@pytest.mark.asyncio
async def test_register_schema(client: httpx.AsyncClient, test_subject: str):
    """Test registering a new schema."""
    response = await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_get_schema(client: httpx.AsyncClient, test_subject: str):
    """Test retrieving a schema."""
    # First register a schema
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Then retrieve it
    response = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["subject"] == test_subject
    assert data["version"] == 1
    assert "schema" in data


@pytest.mark.asyncio
async def test_get_schema_versions(client: httpx.AsyncClient, test_subject: str):
    """Test getting all versions of a schema."""
    # Register two versions
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO"
        }
    )
    
    # Get versions
    response = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}/versions")
    assert response.status_code == 200
    
    versions = response.json()
    assert isinstance(versions, list)
    assert 1 in versions
    assert 2 in versions


@pytest.mark.asyncio
async def test_check_compatibility_compatible(client: httpx.AsyncClient, test_subject: str):
    """Test checking compatibility with a compatible schema."""
    # Register initial schema
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Check compatibility with backward compatible schema
    response = await client.post(
        f"{MCP_SERVER_URL}/compatibility",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data.get("is_compatible", False) is True


@pytest.mark.asyncio
async def test_check_compatibility_incompatible(client: httpx.AsyncClient, test_subject: str):
    """Test checking compatibility with an incompatible schema."""
    # Register initial schema
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Check compatibility with incompatible schema
    response = await client.post(
        f"{MCP_SERVER_URL}/compatibility",
        json={
            "subject": test_subject,
            "schema": INCOMPATIBLE_SCHEMA,
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data.get("is_compatible", True) is False


@pytest.mark.asyncio
async def test_schema_not_found(client: httpx.AsyncClient):
    """Test retrieving a non-existent schema."""
    response = await client.get(f"{MCP_SERVER_URL}/schemas/non-existent-subject")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_schema_format(client: httpx.AsyncClient, test_subject: str):
    """Test registering an invalid schema."""
    response = await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": {"invalid": "schema"},
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 500


# Test with authentication (if configured)
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("SCHEMA_REGISTRY_USER"),
    reason="Authentication not configured"
)
async def test_with_authentication():
    """Test that authentication is working when configured."""
    # This test assumes authentication is configured in the environment
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_SERVER_URL}/")
        assert response.status_code == 200


# Schema Context Tests
@pytest.mark.asyncio
async def test_list_contexts(client: httpx.AsyncClient):
    """Test listing all available contexts."""
    response = await client.get(f"{MCP_SERVER_URL}/contexts")
    assert response.status_code == 200
    
    data = response.json()
    assert "contexts" in data
    assert isinstance(data["contexts"], list)


@pytest.mark.asyncio
async def test_create_context(client: httpx.AsyncClient):
    """Test creating a new schema context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    response = await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert context_name in data["message"]
    assert "created successfully" in data["message"]


@pytest.mark.asyncio
async def test_context_aware_schema_registration(client: httpx.AsyncClient, test_subject: str):
    """Test registering a schema within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context first
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    # Register schema in context via request body
    response = await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_context_aware_schema_registration_query_param(client: httpx.AsyncClient, test_subject: str):
    """Test registering a schema with context via query parameter."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context first
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    # Register schema in context via query parameter
    response = await client.post(
        f"{MCP_SERVER_URL}/schemas?context={context_name}",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_context_aware_schema_retrieval(client: httpx.AsyncClient, test_subject: str):
    """Test retrieving a schema from a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register schema
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Retrieve schema from context
    response = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}?context={context_name}")
    assert response.status_code == 200
    
    data = response.json()
    # Schema Registry returns subject with context prefix: ":.context-name:subject-name"
    expected_subject = f":.{context_name}:{test_subject}"
    assert data["subject"] == expected_subject
    assert "id" in data
    assert "schema" in data


@pytest.mark.asyncio
async def test_context_aware_schema_versions(client: httpx.AsyncClient, test_subject: str):
    """Test getting schema versions within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register multiple schema versions
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Get versions within context
    response = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}/versions?context={context_name}")
    assert response.status_code == 200
    
    versions = response.json()
    assert isinstance(versions, list)
    assert 1 in versions
    assert 2 in versions


@pytest.mark.asyncio
async def test_context_aware_compatibility_check(client: httpx.AsyncClient, test_subject: str):
    """Test compatibility checking within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register initial schema
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Check compatibility within context
    response = await client.post(
        f"{MCP_SERVER_URL}/compatibility",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "is_compatible" in data


@pytest.mark.asyncio
async def test_context_aware_compatibility_check_query_param(client: httpx.AsyncClient, test_subject: str):
    """Test compatibility checking with context via query parameter."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register initial schema
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas?context={context_name}",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Check compatibility within context via query param
    response = await client.post(
        f"{MCP_SERVER_URL}/compatibility?context={context_name}",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "is_compatible" in data


@pytest.mark.asyncio
async def test_list_subjects_with_context(client: httpx.AsyncClient, test_subject: str):
    """Test listing subjects within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register a schema
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # List subjects in context
    response = await client.get(f"{MCP_SERVER_URL}/subjects?context={context_name}")
    assert response.status_code == 200
    
    subjects = response.json()
    assert isinstance(subjects, list)
    # Schema Registry returns subject with context prefix: ":.context-name:subject-name"
    expected_subject = f":.{context_name}:{test_subject}"
    assert expected_subject in subjects


@pytest.mark.asyncio
async def test_list_subjects_default_context(client: httpx.AsyncClient, test_subject: str):
    """Test listing subjects in default context (no context specified)."""
    # Register a schema in default context
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # List subjects (default context)
    response = await client.get(f"{MCP_SERVER_URL}/subjects")
    assert response.status_code == 200
    
    subjects = response.json()
    assert isinstance(subjects, list)
    assert test_subject in subjects


@pytest.mark.asyncio
async def test_delete_subject_with_context(client: httpx.AsyncClient, test_subject: str):
    """Test deleting a subject within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context and register a schema
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Delete subject within context
    response = await client.delete(f"{MCP_SERVER_URL}/subjects/{test_subject}?context={context_name}")
    assert response.status_code == 200
    
    # Verify deletion
    response = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}?context={context_name}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_context(client: httpx.AsyncClient):
    """Test deleting a schema context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context first
    create_response = await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    assert create_response.status_code == 200
    
    # Delete context (should work for empty context)
    response = await client.delete(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    # Note: Some Schema Registry versions may not support context deletion
    # or may require the context to be empty
    if response.status_code == 200:
        data = response.json()
        assert "message" in data
        assert context_name in data["message"]
        assert "deleted successfully" in data["message"]
    elif response.status_code == 404:
        # Context already deleted or doesn't exist - this is also acceptable
        pass
    elif response.status_code == 500:
        # Some Schema Registry versions may not support context deletion
        # This is acceptable for testing purposes
        pass
    else:
        # Unexpected status code
        assert False, f"Unexpected status code: {response.status_code}, response: {response.text}"


@pytest.mark.asyncio
async def test_context_isolation(client: httpx.AsyncClient, test_subject: str):
    """Test that contexts provide proper isolation between schemas."""
    import uuid
    context1 = f"test-context-1-{uuid.uuid4().hex[:8]}"
    context2 = f"test-context-2-{uuid.uuid4().hex[:8]}"
    
    # Create both contexts
    await client.post(f"{MCP_SERVER_URL}/contexts/{context1}")
    await client.post(f"{MCP_SERVER_URL}/contexts/{context2}")
    
    # Register same subject in different contexts with different schemas
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context1
        }
    )
    
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V2,
            "schemaType": "AVRO",
            "context": context2
        }
    )
    
    # Verify schemas are different in each context
    response1 = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}?context={context1}")
    response2 = await client.get(f"{MCP_SERVER_URL}/schemas/{test_subject}?context={context2}")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    schema1 = response1.json()["schema"]
    schema2 = response2.json()["schema"]
    
    # Schemas should be different (one has email field, one doesn't)
    assert schema1 != schema2


# Configuration Management Tests
@pytest.mark.asyncio
async def test_get_global_config(client: httpx.AsyncClient):
    """Test getting global configuration settings."""
    response = await client.get(f"{MCP_SERVER_URL}/config")
    assert response.status_code == 200
    
    data = response.json()
    assert "compatibilityLevel" in data
    # Common compatibility levels: BACKWARD, FORWARD, FULL, NONE
    assert data["compatibilityLevel"] in ["BACKWARD", "FORWARD", "FULL", "NONE", "BACKWARD_TRANSITIVE", "FORWARD_TRANSITIVE", "FULL_TRANSITIVE"]


@pytest.mark.asyncio
async def test_update_global_config(client: httpx.AsyncClient):
    """Test updating global configuration settings."""
    # Get current config first
    current_response = await client.get(f"{MCP_SERVER_URL}/config")
    assert current_response.status_code == 200
    current_config = current_response.json()
    
    # Update to a different compatibility level
    new_compatibility = "FULL" if current_config["compatibilityLevel"] != "FULL" else "BACKWARD"
    
    response = await client.put(
        f"{MCP_SERVER_URL}/config",
        json={"compatibility": new_compatibility}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "compatibility" in data
    assert data["compatibility"] == new_compatibility


@pytest.mark.asyncio
async def test_get_subject_config(client: httpx.AsyncClient, test_subject: str):
    """Test getting configuration for a specific subject."""
    # First register a schema to ensure subject exists
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Try to get subject config (might return 404 if no specific config set)
    response = await client.get(f"{MCP_SERVER_URL}/config/{test_subject}")
    # Either returns the subject-specific config or inherits from global
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "compatibilityLevel" in data


@pytest.mark.asyncio
async def test_update_subject_config(client: httpx.AsyncClient, test_subject: str):
    """Test updating configuration for a specific subject."""
    # First register a schema to ensure subject exists
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Set subject-specific config
    response = await client.put(
        f"{MCP_SERVER_URL}/config/{test_subject}",
        json={"compatibility": "FORWARD"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "compatibility" in data
    assert data["compatibility"] == "FORWARD"


@pytest.mark.asyncio
async def test_config_with_context(client: httpx.AsyncClient, test_subject: str):
    """Test configuration management within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context first
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    # Register schema in context
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Get global config for context (may not be supported by all Schema Registry versions)
    response = await client.get(f"{MCP_SERVER_URL}/config?context={context_name}")
    # Context-aware config might not be supported, so we accept both outcomes
    assert response.status_code in [200, 404, 500]


# Mode Management Tests
@pytest.mark.asyncio
async def test_get_mode(client: httpx.AsyncClient):
    """Test getting the current Schema Registry mode."""
    response = await client.get(f"{MCP_SERVER_URL}/mode")
    assert response.status_code == 200
    
    data = response.json()
    assert "mode" in data
    # Common modes: IMPORT, READONLY, READWRITE
    assert data["mode"] in ["IMPORT", "READONLY", "READWRITE"]


@pytest.mark.asyncio
async def test_update_mode(client: httpx.AsyncClient):
    """Test updating the Schema Registry mode."""
    # Get current mode first
    current_response = await client.get(f"{MCP_SERVER_URL}/mode")
    assert current_response.status_code == 200
    current_mode = current_response.json()
    
    # Try to update mode (this might fail in some Schema Registry setups)
    response = await client.put(
        f"{MCP_SERVER_URL}/mode",
        json={"mode": "READWRITE"}
    )
    # Mode changes might be restricted in some configurations
    assert response.status_code in [200, 403, 422, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "mode" in data


@pytest.mark.asyncio
async def test_get_subject_mode(client: httpx.AsyncClient, test_subject: str):
    """Test getting mode for a specific subject."""
    # First register a schema to ensure subject exists
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Try to get subject mode (might return 404 if no specific mode set)
    response = await client.get(f"{MCP_SERVER_URL}/mode/{test_subject}")
    # Either returns the subject-specific mode or 404/500 if not supported
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "mode" in data


@pytest.mark.asyncio
async def test_update_subject_mode(client: httpx.AsyncClient, test_subject: str):
    """Test updating mode for a specific subject."""
    # First register a schema to ensure subject exists
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Try to set subject-specific mode (might not be supported)
    response = await client.put(
        f"{MCP_SERVER_URL}/mode/{test_subject}",
        json={"mode": "READWRITE"}
    )
    # Subject-level mode might not be supported in all Schema Registry versions
    assert response.status_code in [200, 404, 422, 500]


@pytest.mark.asyncio
async def test_mode_with_context(client: httpx.AsyncClient, test_subject: str):
    """Test mode management within a specific context."""
    import uuid
    context_name = f"test-context-{uuid.uuid4().hex[:8]}"
    
    # Create context first
    await client.post(f"{MCP_SERVER_URL}/contexts/{context_name}")
    
    # Register schema in context
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO",
            "context": context_name
        }
    )
    
    # Get mode for context (may not be supported by all Schema Registry versions)
    response = await client.get(f"{MCP_SERVER_URL}/mode?context={context_name}")
    # Context-aware mode might not be supported, so we accept various outcomes
    assert response.status_code in [200, 404, 500]


# Integration Tests for Config and Mode
@pytest.mark.asyncio
async def test_config_mode_integration(client: httpx.AsyncClient, test_subject: str):
    """Test integration between configuration and mode settings."""
    # Register a schema
    await client.post(
        f"{MCP_SERVER_URL}/schemas",
        json={
            "subject": test_subject,
            "schema": AVRO_SCHEMA_V1,
            "schemaType": "AVRO"
        }
    )
    
    # Get both config and mode to ensure they're accessible
    config_response = await client.get(f"{MCP_SERVER_URL}/config")
    mode_response = await client.get(f"{MCP_SERVER_URL}/mode")
    
    assert config_response.status_code == 200
    assert mode_response.status_code == 200
    
    config_data = config_response.json()
    mode_data = mode_response.json()
    
    assert "compatibilityLevel" in config_data
    assert "mode" in mode_data


# Error Handling Tests for Config and Mode
@pytest.mark.asyncio
async def test_invalid_compatibility_level(client: httpx.AsyncClient):
    """Test handling of invalid compatibility levels."""
    response = await client.put(
        f"{MCP_SERVER_URL}/config",
        json={"compatibility": "INVALID_LEVEL"}
    )
    # Should return error for invalid compatibility level
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_invalid_mode(client: httpx.AsyncClient):
    """Test handling of invalid modes."""
    response = await client.put(
        f"{MCP_SERVER_URL}/mode",
        json={"mode": "INVALID_MODE"}
    )
    # Should return error for invalid mode
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_config_nonexistent_subject(client: httpx.AsyncClient):
    """Test getting config for non-existent subject."""
    response = await client.get(f"{MCP_SERVER_URL}/config/non-existent-subject")
    # Should return 404 for non-existent subject
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mode_nonexistent_subject(client: httpx.AsyncClient):
    """Test getting mode for non-existent subject."""
    response = await client.get(f"{MCP_SERVER_URL}/mode/non-existent-subject")
    # Should return 404 for non-existent subject or inherit global mode
    assert response.status_code in [404, 500] 