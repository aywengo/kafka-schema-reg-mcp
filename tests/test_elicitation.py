#!/usr/bin/env python3
"""
Tests for the elicitation system functionality
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path to import modules from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import elicitation modules
from elicitation import (
    ElicitationField,
    ElicitationManager,
    ElicitationPriority,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationType,
    create_compatibility_resolution_elicitation,
    create_context_metadata_elicitation,
    create_export_preferences_elicitation,
    create_migrate_schema_elicitation,
    create_migration_preferences_elicitation,
    create_schema_field_elicitation,
    elicit_with_fallback,
    is_elicitation_supported,
    mock_elicit,
)
from interactive_tools import (
    check_compatibility_interactive,
    create_context_interactive,
    export_global_interactive,
    migrate_context_interactive,
    migrate_schema_interactive,
    register_schema_interactive,
)


class TestElicitationCore:
    """Test core elicitation functionality."""

    def test_elicitation_field_creation(self):
        """Test creating elicitation fields with various configurations."""
        # Basic field
        field = ElicitationField(name="test_field", type="text", required=True)
        assert field.name == "test_field"
        assert field.type == "text"
        assert field.required is True
        assert field.label is None
        assert field.default is None

        # Complex field with all options
        field = ElicitationField(
            name="complex_field",
            type="choice",
            label="Complex Field",
            description="A complex field for testing",
            required=False,
            default="option1",
            options=["option1", "option2", "option3"],
            validation={"min_length": 3},
            placeholder="Select an option",
        )
        assert field.name == "complex_field"
        assert field.type == "choice"
        assert field.label == "Complex Field"
        assert field.description == "A complex field for testing"
        assert field.required is False
        assert field.default == "option1"
        assert field.options == ["option1", "option2", "option3"]
        assert field.validation == {"min_length": 3}
        assert field.placeholder == "Select an option"

    def test_elicitation_request_creation(self):
        """Test creating elicitation requests."""
        fields = [
            ElicitationField("field1", "text", required=True),
            ElicitationField("field2", "choice", options=["a", "b", "c"]),
        ]

        request = ElicitationRequest(
            type=ElicitationType.FORM,
            title="Test Request",
            description="A test elicitation request",
            fields=fields,
            priority=ElicitationPriority.HIGH,
            timeout_seconds=300,
        )

        assert request.type == ElicitationType.FORM
        assert request.title == "Test Request"
        assert request.description == "A test elicitation request"
        assert len(request.fields) == 2
        assert request.priority == ElicitationPriority.HIGH
        assert request.timeout_seconds == 300
        assert request.expires_at is not None
        assert not request.is_expired()

    def test_elicitation_request_expiration(self):
        """Test elicitation request expiration logic."""
        # Create request that expires in 1 second
        request = ElicitationRequest(title="Expiring Request", timeout_seconds=1)

        # Should not be expired immediately
        assert not request.is_expired()

        # Manually set expiration to past
        request.expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert request.is_expired()

    def test_elicitation_request_to_dict(self):
        """Test serialization of elicitation requests."""
        fields = [
            ElicitationField(
                name="test_field",
                type="text",
                label="Test Field",
                required=True,
                default="default_value",
            )
        ]

        request = ElicitationRequest(
            type=ElicitationType.TEXT,
            title="Test Request",
            fields=fields,
            context={"test": "context"},
        )

        data = request.to_dict()

        assert data["type"] == "text"
        assert data["title"] == "Test Request"
        assert len(data["fields"]) == 1
        assert data["fields"][0]["name"] == "test_field"
        assert data["fields"][0]["type"] == "text"
        assert data["fields"][0]["label"] == "Test Field"
        assert data["fields"][0]["required"] is True
        assert data["fields"][0]["default"] == "default_value"
        assert data["context"] == {"test": "context"}

    def test_elicitation_response_creation(self):
        """Test creating elicitation responses."""
        response = ElicitationResponse(
            request_id="test-request-123",
            values={"field1": "value1", "field2": "value2"},
            complete=True,
            metadata={"source": "user"},
        )

        assert response.request_id == "test-request-123"
        assert response.values == {"field1": "value1", "field2": "value2"}
        assert response.complete is True
        assert response.metadata == {"source": "user"}
        assert response.timestamp is not None

    def test_elicitation_response_to_dict(self):
        """Test serialization of elicitation responses."""
        response = ElicitationResponse(
            request_id="test-request-123",
            values={"test": "value"},
            metadata={"source": "test"},
        )

        data = response.to_dict()

        assert data["request_id"] == "test-request-123"
        assert data["values"] == {"test": "value"}
        assert data["complete"] is True
        assert data["metadata"] == {"source": "test"}
        assert "timestamp" in data


class TestElicitationManager:
    """Test elicitation manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a fresh elicitation manager for each test."""
        return ElicitationManager()

    @pytest.mark.asyncio
    async def test_create_request(self, manager):
        """Test creating and storing elicitation requests."""
        request = ElicitationRequest(title="Test Request", timeout_seconds=300)

        request_id = await manager.create_request(request)

        assert request_id == request.id
        assert request_id in manager.pending_requests
        assert manager.get_request(request_id) == request

    @pytest.mark.asyncio
    async def test_submit_response(self, manager):
        """Test submitting responses to elicitation requests."""
        request = ElicitationRequest(
            title="Test Request",
            fields=[ElicitationField("test", "text", required=True)],
        )

        await manager.create_request(request)

        response = ElicitationResponse(request_id=request.id, values={"test": "value"})

        success = await manager.submit_response(response)

        assert success is True
        assert manager.get_response(request.id) == response
        assert request.id not in manager.pending_requests

    @pytest.mark.asyncio
    async def test_submit_invalid_response(self, manager):
        """Test submitting invalid responses."""
        request = ElicitationRequest(
            title="Test Request",
            fields=[ElicitationField("required_field", "text", required=True)],
        )

        await manager.create_request(request)

        # Response missing required field
        response = ElicitationResponse(request_id=request.id, values={"wrong_field": "value"})

        success = await manager.submit_response(response)

        assert success is False
        assert manager.get_response(request.id) is None
        assert request.id in manager.pending_requests

    @pytest.mark.asyncio
    async def test_wait_for_response(self, manager):
        """Test waiting for responses with timeout."""
        request = ElicitationRequest(title="Test Request", timeout_seconds=1)  # Short timeout for testing

        await manager.create_request(request)

        # Test timeout
        response = await manager.wait_for_response(request.id, timeout=0.5)
        assert response is None

        # Test successful response
        test_response = ElicitationResponse(request_id=request.id, values={"test": "value"})

        # Submit response in background
        async def submit_response():
            await asyncio.sleep(0.1)
            await manager.submit_response(test_response)

        # Start both tasks
        response_task = manager.wait_for_response(request.id, timeout=1.0)
        submit_task = submit_response()

        response, _ = await asyncio.gather(response_task, submit_task)

        assert response == test_response

    def test_list_pending_requests(self, manager):
        """Test listing pending requests."""
        request1 = ElicitationRequest(title="Request 1")
        request2 = ElicitationRequest(title="Request 2")

        asyncio.run(manager.create_request(request1))
        asyncio.run(manager.create_request(request2))

        pending = manager.list_pending_requests()

        assert len(pending) == 2
        assert request1 in pending
        assert request2 in pending

    def test_cancel_request(self, manager):
        """Test cancelling requests."""
        request = ElicitationRequest(title="Test Request")

        asyncio.run(manager.create_request(request))

        assert request.id in manager.pending_requests

        cancelled = manager.cancel_request(request.id)

        assert cancelled is True
        assert request.id not in manager.pending_requests

    @pytest.mark.asyncio
    async def test_timeout_handling(self, manager):
        """Test automatic timeout handling."""
        request = ElicitationRequest(title="Timeout Test", timeout_seconds=0.1)  # Very short timeout

        await manager.create_request(request)

        # Wait for timeout to trigger
        await asyncio.sleep(0.2)

        # Request should be automatically cleaned up
        assert request.id not in manager.pending_requests


class TestElicitationHelpers:
    """Test elicitation helper functions."""

    def test_create_schema_field_elicitation(self):
        """Test creating schema field elicitation requests."""
        request = create_schema_field_elicitation(
            context="test-context",
            existing_fields=["existing_field1", "existing_field2"],
        )

        assert request.type == ElicitationType.FORM
        assert request.title == "Define Schema Field"
        assert request.allow_multiple is True
        assert request.timeout_seconds == 600
        assert request.context["existing_fields"] == [
            "existing_field1",
            "existing_field2",
        ]
        assert request.context["schema_context"] == "test-context"

        # Check required fields
        field_names = [f.name for f in request.fields]
        assert "field_name" in field_names
        assert "field_type" in field_names
        assert "nullable" in field_names

    def test_create_migration_preferences_elicitation(self):
        """Test creating migration preferences elicitation requests."""
        request = create_migration_preferences_elicitation(
            source_registry="source", target_registry="target", context="test-context"
        )

        assert request.type == ElicitationType.FORM
        assert request.title == "Migration Preferences"
        assert "from source to target" in request.description
        assert request.context["source_registry"] == "source"
        assert request.context["target_registry"] == "target"
        assert request.context["context"] == "test-context"

        # Check required fields
        field_names = [f.name for f in request.fields]
        assert "preserve_ids" in field_names
        assert "migrate_all_versions" in field_names
        assert "conflict_resolution" in field_names
        assert "dry_run" in field_names

    def test_create_compatibility_resolution_elicitation(self):
        """Test creating compatibility resolution elicitation requests."""
        errors = ["Error 1", "Error 2"]
        request = create_compatibility_resolution_elicitation(subject="test-subject", compatibility_errors=errors)

        assert request.type == ElicitationType.FORM
        assert request.title == "Resolve Compatibility Issues"
        assert "test-subject" in request.description
        assert request.context["subject"] == "test-subject"
        assert request.context["compatibility_errors"] == errors

        # Check required fields
        field_names = [f.name for f in request.fields]
        assert "resolution_strategy" in field_names
        assert "compatibility_level" in field_names

    def test_create_context_metadata_elicitation(self):
        """Test creating context metadata elicitation requests."""
        request = create_context_metadata_elicitation("test-context")

        assert request.type == ElicitationType.FORM
        assert request.title == "Context Metadata"
        assert "test-context" in request.description
        assert request.context["context_name"] == "test-context"

        # Check fields
        field_names = [f.name for f in request.fields]
        assert "description" in field_names
        assert "owner" in field_names
        assert "environment" in field_names
        assert "tags" in field_names

    def test_create_export_preferences_elicitation(self):
        """Test creating export preferences elicitation requests."""
        request = create_export_preferences_elicitation("global_export")

        assert request.type == ElicitationType.FORM
        assert request.title == "Export Preferences"
        assert "global_export" in request.description
        assert request.context["operation"] == "global_export"

        # Check fields
        field_names = [f.name for f in request.fields]
        assert "format" in field_names
        assert "include_metadata" in field_names
        assert "include_versions" in field_names
        assert "compression" in field_names

    def test_create_migrate_schema_elicitation_new_schema(self):
        """Test creating migrate schema elicitation for new schema (doesn't exist in target)."""
        request = create_migrate_schema_elicitation(
            subject="test-subject",
            source_registry="source-reg",
            target_registry="target-reg",
            schema_exists_in_target=False,
            context="test-context",
        )

        assert request.type == ElicitationType.FORM
        assert request.title == "Schema Migration Preferences"
        assert "test-subject" in request.description
        assert "source-reg" in request.description
        assert "target-reg" in request.description
        assert request.context["subject"] == "test-subject"
        assert request.context["source_registry"] == "source-reg"
        assert request.context["target_registry"] == "target-reg"
        assert request.context["schema_exists_in_target"] is False

        # Check fields - should NOT include replacement fields
        field_names = [f.name for f in request.fields]
        assert "replace_existing" not in field_names
        assert "backup_before_replace" not in field_names
        assert "preserve_ids" in field_names
        assert "compare_after_migration" in field_names
        assert "migrate_all_versions" in field_names
        assert "dry_run" in field_names

    def test_create_migrate_schema_elicitation_existing_schema(self):
        """Test creating migrate schema elicitation for existing schema in target."""
        existing_versions = [1, 2, 3]
        request = create_migrate_schema_elicitation(
            subject="existing-subject",
            source_registry="source-reg",
            target_registry="target-reg",
            schema_exists_in_target=True,
            existing_versions=existing_versions,
            context="test-context",
        )

        assert request.type == ElicitationType.FORM
        assert request.title == "Schema Migration Preferences"
        assert "already exists" in request.description
        assert str(existing_versions) in request.description
        assert request.context["schema_exists_in_target"] is True
        assert request.context["existing_versions"] == existing_versions

        # Check fields - should include replacement fields
        field_names = [f.name for f in request.fields]
        assert "replace_existing" in field_names
        assert "backup_before_replace" in field_names
        assert "preserve_ids" in field_names
        assert "compare_after_migration" in field_names
        assert "migrate_all_versions" in field_names
        assert "dry_run" in field_names

        # Check replace_existing field details
        replace_field = next(f for f in request.fields if f.name == "replace_existing")
        assert replace_field.required is True
        assert replace_field.default == "false"
        assert "already exists" in replace_field.description

        # Check backup field
        backup_field = next(f for f in request.fields if f.name == "backup_before_replace")
        assert backup_field.required is False
        assert backup_field.default == "true"

    @pytest.mark.asyncio
    async def test_mock_elicit(self):
        """Test mock elicitation function."""
        request = ElicitationRequest(
            title="Test Mock",
            fields=[
                ElicitationField("text_field", "text", placeholder="test placeholder"),
                ElicitationField("choice_field", "choice", options=["a", "b", "c"]),
                ElicitationField("default_field", "text", default="default_value"),
            ],
        )

        response = await mock_elicit(request)

        assert response is not None
        assert response.request_id == request.id
        assert response.complete is True
        assert response.metadata["source"] == "mock_fallback"
        assert response.metadata["auto_generated"] is True

        # Check that defaults are applied
        assert response.values["choice_field"] == "a"  # First option
        assert response.values["default_field"] == "default_value"
        assert response.values["text_field"] == "test placeholder"

    @pytest.mark.asyncio
    async def test_elicit_with_fallback(self):
        """Test elicitation with fallback mechanism."""
        request = ElicitationRequest(
            title="Fallback Test",
            fields=[ElicitationField("test", "text", default="fallback_value")],
        )

        # Should use fallback (mock) implementation
        response = await elicit_with_fallback(request)

        assert response is not None
        assert response.values["test"] == "fallback_value"
        assert response.metadata["source"] == "mock_fallback"

    def test_is_elicitation_supported(self):
        """Test elicitation support detection."""
        # Currently always returns True in our implementation
        assert is_elicitation_supported() is True


class TestInteractiveTools:
    """Test interactive tool implementations."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Mock registry components
        self.mock_registry_manager = Mock()
        self.mock_auth = Mock()
        self.mock_headers = {"Content-Type": "application/json"}
        self.registry_mode = "multi"
        self.schema_registry_url = "http://test-registry:8081"

    @pytest.mark.asyncio
    async def test_register_schema_interactive_complete_schema(self):
        """Test interactive schema registration with complete schema."""
        # Mock the core register_schema_tool
        mock_register_tool = Mock(return_value={"success": True, "id": 123})

        complete_schema = {
            "type": "record",
            "name": "TestSchema",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }

        result = await register_schema_interactive(
            subject="test-subject",
            schema_definition=complete_schema,
            register_schema_tool=mock_register_tool,
            registry_manager=self.mock_registry_manager,
            registry_mode=self.registry_mode,
            auth=self.mock_auth,
            headers=self.mock_headers,
            schema_registry_url=self.schema_registry_url,
        )

        # Should call the original tool directly without elicitation
        mock_register_tool.assert_called_once()
        assert result["success"] is True
        assert result["elicitation_used"] is False

    @pytest.mark.asyncio
    async def test_register_schema_interactive_incomplete_schema(self):
        """Test interactive schema registration with incomplete schema."""
        # Mock the core register_schema_tool
        mock_register_tool = Mock(return_value={"success": True, "id": 123})

        # Schema with no fields
        incomplete_schema = {"type": "record", "name": "TestSchema", "fields": []}

        # Mock elicitation to return field definition
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = Mock()
            mock_response.complete = True
            mock_response.values = {
                "field_name": "test_field",
                "field_type": "string",
                "nullable": "false",
                "documentation": "Test field",
            }
            mock_elicit.return_value = mock_response

            result = await register_schema_interactive(
                subject="test-subject",
                schema_definition=incomplete_schema,
                register_schema_tool=mock_register_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Should have used elicitation
        assert result["elicitation_used"] is True
        assert "test_field" in result["elicited_fields"]
        mock_register_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_context_interactive_with_preferences(self):
        """Test interactive context migration with all preferences provided."""
        # Mock the core migrate_context_tool
        mock_migrate_tool = Mock(return_value={"success": True, "migrated": 5})

        result = await migrate_context_interactive(
            source_registry="source",
            target_registry="target",
            preserve_ids=True,
            dry_run=False,
            migrate_all_versions=True,
            migrate_context_tool=mock_migrate_tool,
            registry_manager=self.mock_registry_manager,
            registry_mode=self.registry_mode,
        )

        # Should call the original tool directly without elicitation
        mock_migrate_tool.assert_called_once()
        assert result["success"] is True
        assert result["elicitation_used"] is False

    @pytest.mark.asyncio
    async def test_migrate_context_interactive_missing_preferences(self):
        """Test interactive context migration with missing preferences."""
        # Mock the core migrate_context_tool
        mock_migrate_tool = Mock(return_value={"success": True, "migrated": 5})

        # Mock elicitation to return preferences
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = Mock()
            mock_response.complete = True
            mock_response.values = {
                "preserve_ids": "true",
                "dry_run": "false",
                "migrate_all_versions": "true",
            }
            mock_elicit.return_value = mock_response

            result = await migrate_context_interactive(
                source_registry="source",
                target_registry="target",
                preserve_ids=None,  # Missing
                dry_run=None,  # Missing
                migrate_all_versions=None,  # Missing
                migrate_context_tool=mock_migrate_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
            )

        # Should have used elicitation
        assert result["elicitation_used"] is True
        assert result["elicited_preferences"]["preserve_ids"] is True
        assert result["elicited_preferences"]["dry_run"] is False
        assert result["elicited_preferences"]["migrate_all_versions"] is True
        mock_migrate_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_compatibility_interactive_compatible(self):
        """Test interactive compatibility check with compatible schema."""
        # Mock compatibility tool to return compatible result
        mock_compatibility_tool = Mock(return_value={"compatible": True, "messages": []})

        result = await check_compatibility_interactive(
            subject="test-subject",
            schema_definition={"type": "string"},
            check_compatibility_tool=mock_compatibility_tool,
            registry_manager=self.mock_registry_manager,
            registry_mode=self.registry_mode,
            auth=self.mock_auth,
            headers=self.mock_headers,
            schema_registry_url=self.schema_registry_url,
        )

        # Should not use elicitation for compatible schemas
        assert result["compatible"] is True
        assert result["resolution_guidance"]["strategy"] == "none_needed"
        assert result["resolution_guidance"]["elicitation_used"] is False

    @pytest.mark.asyncio
    async def test_check_compatibility_interactive_incompatible(self):
        """Test interactive compatibility check with incompatible schema."""
        # Mock compatibility tool to return incompatible result
        mock_compatibility_tool = Mock(
            return_value={
                "compatible": False,
                "messages": ["Field removed", "Type changed"],
            }
        )

        # Mock elicitation to return resolution strategy
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = Mock()
            mock_response.complete = True
            mock_response.values = {
                "resolution_strategy": "modify_schema",
                "compatibility_level": "FORWARD",
                "notes": "Make fields optional",
            }
            mock_elicit.return_value = mock_response

            result = await check_compatibility_interactive(
                subject="test-subject",
                schema_definition={"type": "string"},
                check_compatibility_tool=mock_compatibility_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Should have used elicitation for resolution guidance
        assert result["compatible"] is False
        assert result["resolution_guidance"]["strategy"] == "modify_schema"
        assert result["resolution_guidance"]["compatibility_level"] == "FORWARD"
        assert result["resolution_guidance"]["notes"] == "Make fields optional"
        assert result["resolution_guidance"]["elicitation_used"] is True

    @pytest.mark.asyncio
    async def test_create_context_interactive_with_metadata(self):
        """Test interactive context creation with metadata elicitation."""
        # Mock the core create_context_tool
        mock_create_tool = Mock(return_value={"success": True, "context": "test-context"})

        # Mock elicitation to return metadata
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = Mock()
            mock_response.complete = True
            mock_response.values = {
                "description": "Test context for unit tests",
                "owner": "test-team",
                "environment": "testing",
                "tags": "unit-test,schema",
            }
            mock_elicit.return_value = mock_response

            result = await create_context_interactive(
                context="test-context",
                create_context_tool=mock_create_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Should have used elicitation for metadata
        assert result["elicitation_used"] is True
        assert result["metadata"]["description"] == "Test context for unit tests"
        assert result["metadata"]["owner"] == "test-team"
        assert result["metadata"]["environment"] == "testing"
        assert result["metadata"]["tags"] == ["unit-test", "schema"]
        mock_create_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_global_interactive_with_preferences(self):
        """Test interactive global export with preference elicitation."""
        # Mock the core export_global_tool
        mock_export_tool = Mock(return_value={"success": True, "exported": 10})

        # Mock elicitation to return export preferences
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = Mock()
            mock_response.complete = True
            mock_response.values = {
                "format": "yaml",
                "include_metadata": "true",
                "include_versions": "latest",
                "compression": "gzip",
            }
            mock_elicit.return_value = mock_response

            result = await export_global_interactive(
                registry="test-registry",
                export_global_tool=mock_export_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
            )

        # Should have used elicitation for preferences
        assert result["elicitation_used"] is True
        assert result["export_preferences"]["format"] == "yaml"
        assert result["export_preferences"]["compression"] == "gzip"
        assert result["export_preferences"]["include_metadata"] is True
        assert result["export_preferences"]["include_versions"] == "latest"
        mock_export_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_no_elicitation_needed(self):
        """Test interactive schema migration when all preferences are provided."""
        # Mock the core migrate_schema_tool
        mock_migrate_tool = Mock(return_value={"success": True, "migrated_versions": [1, 2]})

        # Mock registry client for checking schema existence
        mock_target_client = Mock()
        mock_target_client.config.url = "http://target-registry:8081"
        mock_target_client.auth = self.mock_auth
        mock_target_client.headers = self.mock_headers

        self.mock_registry_manager.get_registry.return_value = mock_target_client

        # Mock requests.get to simulate schema doesn't exist (404)
        with patch("interactive_tools.requests.get") as mock_get:
            mock_get.return_value.status_code = 404

            result = await migrate_schema_interactive(
                subject="test-subject",
                source_registry="source",
                target_registry="target",
                preserve_ids=True,
                dry_run=False,
                migrate_all_versions=True,
                migrate_schema_tool=mock_migrate_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
            )

        # Should call the original tool directly without elicitation
        mock_migrate_tool.assert_called_once()
        assert result["success"] is True
        assert result["elicitation_used"] is False
        assert result["schema_existed_in_target"] is False

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_schema_exists_allow_replace(self):
        """Test interactive schema migration when schema exists and user allows replacement."""
        # Mock the core migrate_schema_tool
        mock_migrate_tool = Mock(return_value={"success": True, "migrated_versions": [1, 2]})
        mock_export_tool = Mock(return_value={"success": True, "backup_created": True})

        # Mock registry client for checking schema existence
        mock_target_client = Mock()
        mock_target_client.config.url = "http://target-registry:8081"
        mock_target_client.auth = self.mock_auth
        mock_target_client.headers = self.mock_headers

        self.mock_registry_manager.get_registry.return_value = mock_target_client

        # Mock requests.get to simulate schema exists
        with patch("interactive_tools.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [1, 2, 3]

            # Mock elicitation to return user preferences
            with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
                mock_response = Mock()
                mock_response.complete = True
                mock_response.values = {
                    "replace_existing": "true",
                    "backup_before_replace": "true",
                    "preserve_ids": "false",
                    "compare_after_migration": "false",
                    "migrate_all_versions": "true",
                    "dry_run": "false",
                }
                mock_elicit.return_value = mock_response

                result = await migrate_schema_interactive(
                    subject="existing-subject",
                    source_registry="source",
                    target_registry="target",
                    migrate_schema_tool=mock_migrate_tool,
                    export_schema_tool=mock_export_tool,
                    registry_manager=self.mock_registry_manager,
                    registry_mode=self.registry_mode,
                )

        # Should have used elicitation and allowed replacement
        assert result["elicitation_used"] is True
        assert result["schema_existed_in_target"] is True
        assert result["elicited_preferences"]["replace_existing"] is True
        assert result["elicited_preferences"]["backup_before_replace"] is True
        assert result["backup_result"]["success"] is True
        mock_migrate_tool.assert_called_once()
        mock_export_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_schema_exists_decline_replace(self):
        """Test interactive schema migration when schema exists and user declines replacement."""
        # Mock registry client for checking schema existence
        mock_target_client = Mock()
        mock_target_client.config.url = "http://target-registry:8081"
        mock_target_client.auth = self.mock_auth
        mock_target_client.headers = self.mock_headers

        self.mock_registry_manager.get_registry.return_value = mock_target_client

        # Mock requests.get to simulate schema exists
        with patch("interactive_tools.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [1, 2]

            # Mock elicitation to return user declining replacement
            with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
                mock_response = Mock()
                mock_response.complete = True
                mock_response.values = {
                    "replace_existing": "false",  # User declines
                    "backup_before_replace": "true",
                    "preserve_ids": "true",
                    "compare_after_migration": "true",
                    "migrate_all_versions": "false",
                    "dry_run": "true",
                }
                mock_elicit.return_value = mock_response

                result = await migrate_schema_interactive(
                    subject="existing-subject",
                    source_registry="source",
                    target_registry="target",
                    migrate_schema_tool=Mock(),  # Should not be called
                    registry_manager=self.mock_registry_manager,
                    registry_mode=self.registry_mode,
                )

        # Should return error indicating replacement was declined
        assert "error" in result
        assert "MIGRATION_DECLINED_EXISTING_SCHEMA" in result["error_code"]
        assert "existing_versions" in result["details"]

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_with_verification(self):
        """Test interactive schema migration with post-migration verification."""
        # Mock the core migrate_schema_tool
        mock_migrate_tool = Mock(return_value={"success": True, "migrated_versions": [1]})

        # Mock registry clients for verification
        mock_source_client = Mock()
        mock_target_client = Mock()
        mock_source_client.get_schema.return_value = {
            "schema": {"type": "record", "name": "Test"},
            "schemaType": "AVRO",
            "id": 123,
        }
        mock_target_client.get_schema.return_value = {
            "schema": {"type": "record", "name": "Test"},
            "schemaType": "AVRO",
            "id": 123,
        }

        def get_registry_side_effect(name):
            if name == "source":
                return mock_source_client
            elif name == "target":
                return mock_target_client
            return None

        self.mock_registry_manager.get_registry.side_effect = get_registry_side_effect

        # Mock requests.get to simulate schema doesn't exist initially
        with patch("interactive_tools.requests.get") as mock_get:
            mock_get.return_value.status_code = 404

            # Mock elicitation to request verification
            with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
                mock_response = Mock()
                mock_response.complete = True
                mock_response.values = {
                    "preserve_ids": "true",
                    "compare_after_migration": "true",
                    "migrate_all_versions": "false",
                    "dry_run": "false",
                }
                mock_elicit.return_value = mock_response

                result = await migrate_schema_interactive(
                    subject="verify-subject",
                    source_registry="source",
                    target_registry="target",
                    migrate_schema_tool=mock_migrate_tool,
                    registry_manager=self.mock_registry_manager,
                    registry_mode=self.registry_mode,
                )

        # Should have performed verification
        assert result["elicitation_used"] is True
        assert result["elicited_preferences"]["compare_after_migration"] is True
        assert "verification_result" in result
        assert result["verification_result"]["verification_type"] == "basic"
        assert result["verification_result"]["overall_success"] is True

        # Check verification details
        checks = result["verification_result"]["checks"]
        check_names = [check["check"] for check in checks]
        assert "schema_exists_in_target" in check_names
        assert "schema_content_match" in check_names
        assert "schema_type_match" in check_names
        assert "id_preservation" in check_names

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_elicitation_fails(self):
        """Test graceful fallback when elicitation fails."""
        # Mock registry client
        mock_target_client = Mock()
        mock_target_client.config.url = "http://target-registry:8081"
        mock_target_client.auth = self.mock_auth
        mock_target_client.headers = self.mock_headers

        self.mock_registry_manager.get_registry.return_value = mock_target_client

        # Mock requests.get to simulate schema exists (trigger elicitation)
        with patch("interactive_tools.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [1]

            # Mock elicitation to fail
            with patch("interactive_tools.elicit_with_fallback", return_value=None):
                result = await migrate_schema_interactive(
                    subject="fail-subject",
                    source_registry="source",
                    target_registry="target",
                    migrate_schema_tool=Mock(),  # Should not be called
                    registry_manager=self.mock_registry_manager,
                    registry_mode=self.registry_mode,
                )

        # Should return error indicating elicitation failed
        assert "error" in result
        assert "INCOMPLETE_MIGRATION_PREFERENCES" in result["error_code"]
        assert "elicitation_status" in result["details"]

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_single_registry_mode(self):
        """Test that interactive migration works in single registry mode."""
        result = await migrate_schema_interactive(
            subject="test-subject",
            source_registry="source",
            target_registry="target",
            migrate_schema_tool=Mock(),
            registry_manager=self.mock_registry_manager,
            registry_mode="single",  # Single registry mode
        )

        # Should work but without existence checking (no elicitation triggered)
        # The actual behavior depends on the migrate_schema_tool implementation
        # In this test we're just ensuring no errors occur in single mode
        assert result is not None  # Ensure the function completes without error


class TestElicitationIntegration:
    """Test elicitation integration with MCP server."""

    def test_elicitation_management_tools_structure(self):
        """Test that elicitation management tools are properly structured."""
        # This would test the actual MCP tool implementations
        # For now, we'll test the function signatures and basic structure

        from kafka_schema_registry_unified_mcp import (
            cancel_elicitation_request,
            get_elicitation_request,
            get_elicitation_status,
            list_elicitation_requests,
        )

        # Test that functions exist and are callable
        assert callable(list_elicitation_requests)
        assert callable(get_elicitation_request)
        assert callable(cancel_elicitation_request)
        assert callable(get_elicitation_status)

    @pytest.mark.asyncio
    async def test_elicitation_timeout_cleanup(self):
        """Test that expired elicitation requests are properly cleaned up."""
        manager = ElicitationManager()

        # Create request with very short timeout
        request = ElicitationRequest(title="Cleanup Test", timeout_seconds=0.1)

        await manager.create_request(request)
        assert request.id in manager.pending_requests

        # Wait for cleanup
        await asyncio.sleep(0.2)

        # Request should be cleaned up
        assert request.id not in manager.pending_requests

    def test_elicitation_field_validation(self):
        """Test field validation in elicitation responses."""
        manager = ElicitationManager()

        # Create request with validation rules
        fields = [
            ElicitationField("email", "email", required=True),
            ElicitationField("choice", "choice", options=["a", "b", "c"], required=True),
        ]

        request = ElicitationRequest(title="Validation Test", fields=fields)

        # Test invalid email
        response = ElicitationResponse(request_id=request.id, values={"email": "invalid-email", "choice": "a"})

        assert not manager._validate_response(request, response)

        # Test invalid choice
        response = ElicitationResponse(
            request_id=request.id,
            values={"email": "test@example.com", "choice": "invalid"},
        )

        assert not manager._validate_response(request, response)

        # Test valid response
        response = ElicitationResponse(request_id=request.id, values={"email": "test@example.com", "choice": "a"})

        assert manager._validate_response(request, response)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
