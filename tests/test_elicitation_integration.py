#!/usr/bin/env python3
"""
Integration tests for the elicitation system with MCP
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from elicitation import (
    ElicitationField,
    ElicitationType,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationManager,
)
from interactive_tools import (
    check_compatibility_interactive,
    create_context_interactive,
    export_global_interactive,
    migrate_context_interactive,
    migrate_schema_interactive,
    register_schema_interactive,
)

logger = logging.getLogger(__name__)


class TestElicitationIntegration:
    """Test elicitation integration with the full system."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Create a fresh elicitation manager for each test
        self.manager = ElicitationManager()

        # Mock MCP instance
        self.mock_mcp = MagicMock()
        self.mock_mcp.send_elicitation_request = AsyncMock()
        self.mock_mcp.send_notification = AsyncMock()
        self.mock_mcp.call_method = AsyncMock()
        self.mock_mcp.create_resource = AsyncMock()

        # Mock registry components
        self.mock_registry_manager = MagicMock()
        self.mock_auth = MagicMock()
        self.mock_headers = {"Content-Type": "application/json"}
        self.registry_mode = "multi"
        self.schema_registry_url = "http://test-registry:8081"

    @pytest.mark.asyncio
    async def test_end_to_end_schema_registration_workflow(self):
        """Test complete interactive schema registration workflow."""
        # Test scenario: User wants to register a schema but provides incomplete information

        # Step 1: Call interactive schema registration with minimal info
        subject = "test-user-events"
        incomplete_schema = {
            "type": "record",
            "name": "UserEvent",
            "fields": [],  # No fields defined - should trigger elicitation
        }

        # Mock the underlying schema registration tool
        mock_register_tool = MagicMock(return_value={"success": True, "id": 123, "subject": subject, "version": 1})

        # Mock elicitation response simulating user input
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = ElicitationResponse(
                request_id="test-request-123",
                values={
                    "field_name": "user_id",
                    "field_type": "string",
                    "nullable": "false",
                    "default_value": "",
                    "documentation": "Unique identifier for the user",
                },
                complete=True,
                metadata={"source": "user_input"},
            )
            mock_elicit.return_value = mock_response

            # Execute the interactive registration
            result = await register_schema_interactive(
                subject=subject,
                schema_definition=incomplete_schema,
                schema_type="AVRO",
                context="user-events",
                registry="test-registry",
                register_schema_tool=mock_register_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Verify elicitation was triggered
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Define Schema Field"

        # Verify result indicates elicitation was used
        assert result["success"] is True
        assert result["elicitation_used"] is True
        assert "user_id" in result["elicited_fields"]

        # Verify the underlying tool was called with enhanced schema
        mock_register_tool.assert_called_once()
        call_args = mock_register_tool.call_args
        enhanced_schema = call_args[1]  # Second positional argument is schema_definition

        # The schema should now have the user-defined field
        assert len(enhanced_schema["fields"]) == 1
        assert enhanced_schema["fields"][0]["name"] == "user_id"
        assert enhanced_schema["fields"][0]["type"] == "string"

    @pytest.mark.asyncio
    async def test_migration_preferences_elicitation_workflow(self):
        """Test interactive migration with preference elicitation."""
        # Test scenario: User wants to migrate context but doesn't specify preferences

        source_registry = "prod-registry"
        target_registry = "dev-registry"
        context = "user-schemas"

        # Mock the underlying migration tool
        mock_migrate_tool = AsyncMock(
            return_value={
                "success": True,
                "migrated_schemas": 5,
                "dry_run": True,
                "preserved_ids": True,
            }
        )

        # Mock elicitation response with user preferences
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = ElicitationResponse(
                request_id="migration-request-456",
                values={
                    "preserve_ids": "true",
                    "dry_run": "false",
                    "migrate_all_versions": "true",
                    "conflict_resolution": "overwrite",
                    "batch_size": "25",
                },
                complete=True,
                metadata={"source": "user_preferences"},
            )
            mock_elicit.return_value = mock_response

            # Execute interactive migration with missing preferences
            result = await migrate_context_interactive(
                source_registry=source_registry,
                target_registry=target_registry,
                context=context,
                preserve_ids=None,  # Not specified - should trigger elicitation
                dry_run=None,  # Not specified
                migrate_all_versions=None,  # Not specified
                migrate_context_tool=mock_migrate_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
            )

        # Verify elicitation was triggered for migration preferences
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Migration Preferences"
        assert source_registry in elicitation_request.description
        assert target_registry in elicitation_request.description

        # Verify the migration tool was called with elicited preferences
        mock_migrate_tool.assert_called_once()
        call_kwargs = mock_migrate_tool.call_args.kwargs
        assert call_kwargs["preserve_ids"] is True
        assert call_kwargs["dry_run"] is False
        assert call_kwargs["migrate_all_versions"] is True

        # Verify result indicates elicitation was used
        assert result["success"] is True
        assert result["elicitation_used"] is True
        assert result["elicited_preferences"]["preserve_ids"] is True

    @pytest.mark.asyncio
    async def test_compatibility_resolution_guidance(self):
        """Test interactive compatibility checking with resolution guidance."""
        # Test scenario: Schema has compatibility issues, system guides user to resolution

        subject = "payment-events"
        incompatible_schema = {
            "type": "record",
            "name": "PaymentEvent",
            "fields": [
                {"name": "payment_id", "type": "string"},
                # This field removal would cause compatibility issues
                # {"name": "amount", "type": "double"},  # Missing field
            ],
        }

        # Mock compatibility check that finds issues
        mock_compatibility_tool = MagicMock(
            return_value={
                "compatible": False,
                "messages": [
                    "Field 'amount' was removed, violating BACKWARD compatibility",
                    "Schema evolution requires all existing fields to be preserved",
                ],
            }
        )

        # Mock elicitation response with resolution strategy
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = ElicitationResponse(
                request_id="compatibility-request-789",
                values={
                    "resolution_strategy": "add_default_values",
                    "compatibility_level": "FORWARD",
                    "notes": "Add default values to maintain backward compatibility",
                },
                complete=True,
                metadata={"source": "resolution_guidance"},
            )
            mock_elicit.return_value = mock_response

            # Execute interactive compatibility check
            result = await check_compatibility_interactive(
                subject=subject,
                schema_definition=incompatible_schema,
                schema_type="AVRO",
                context="payments",
                registry="prod-registry",
                check_compatibility_tool=mock_compatibility_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Verify compatibility check was performed
        mock_compatibility_tool.assert_called_once()

        # Verify elicitation was triggered for resolution
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Resolve Compatibility Issues"
        assert subject in elicitation_request.description

        # Verify result contains resolution guidance
        assert result["compatible"] is False
        assert result["resolution_guidance"]["strategy"] == "add_default_values"
        assert result["resolution_guidance"]["compatibility_level"] == "FORWARD"
        assert result["resolution_guidance"]["elicitation_used"] is True

    @pytest.mark.asyncio
    async def test_context_metadata_collection(self):
        """Test interactive context creation with metadata collection."""
        # Test scenario: Creating a new context with guided metadata collection

        context_name = "analytics-events"

        # Mock context creation tool
        mock_create_tool = MagicMock(return_value={"success": True, "context": context_name, "created": True})

        # Mock elicitation response with metadata
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = ElicitationResponse(
                request_id="context-metadata-101",
                values={
                    "description": "Analytics and behavioral event schemas for data pipeline",
                    "owner": "data-platform-team",
                    "environment": "production",
                    "tags": "analytics,events,pipeline,gdpr-compliant",
                },
                complete=True,
                metadata={"source": "context_setup"},
            )
            mock_elicit.return_value = mock_response

            # Execute interactive context creation
            result = await create_context_interactive(
                context=context_name,
                registry="analytics-registry",
                # All metadata parameters are None - should trigger elicitation
                description=None,
                owner=None,
                environment=None,
                tags=None,
                create_context_tool=mock_create_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Verify elicitation was triggered for metadata
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Context Metadata"
        assert context_name in elicitation_request.description

        # Verify context creation tool was called
        mock_create_tool.assert_called_once()

        # Verify result contains collected metadata
        assert result["success"] is True
        assert result["elicitation_used"] is True
        assert result["metadata"]["description"] == "Analytics and behavioral event schemas for data pipeline"
        assert result["metadata"]["owner"] == "data-platform-team"
        assert result["metadata"]["environment"] == "production"
        assert result["metadata"]["tags"] == [
            "analytics",
            "events",
            "pipeline",
            "gdpr-compliant",
        ]

    @pytest.mark.asyncio
    async def test_export_preferences_workflow(self):
        """Test interactive export with format preferences."""
        # Test scenario: User wants to export all schemas but needs guidance on format options

        registry = "compliance-registry"

        # Mock export tool
        mock_export_tool = MagicMock(
            return_value={
                "success": True,
                "exported_schemas": 25,
                "export_format": "json",
                "file_size": "2.4MB",
            }
        )

        # Mock elicitation response with export preferences
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_response = ElicitationResponse(
                request_id="export-prefs-202",
                values={
                    "format": "yaml",
                    "include_metadata": "true",
                    "include_versions": "latest",
                    "compression": "gzip",
                },
                complete=True,
                metadata={"source": "export_configuration"},
            )
            mock_elicit.return_value = mock_response

            # Execute interactive export with missing preferences
            result = await export_global_interactive(
                registry=registry,
                # All preferences are None - should trigger elicitation
                include_metadata=None,
                include_config=None,
                include_versions=None,
                format=None,
                compression=None,
                export_global_tool=mock_export_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
            )

        # Verify elicitation was triggered for export preferences
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Export Preferences"
        assert "global_export" in elicitation_request.description

        # Verify export tool was called
        mock_export_tool.assert_called_once()

        # Verify result contains export preferences
        assert result["success"] is True
        assert result["elicitation_used"] is True
        assert result["export_preferences"]["format"] == "yaml"
        assert result["export_preferences"]["compression"] == "gzip"

    @pytest.mark.asyncio
    async def test_migrate_schema_interactive_workflow(self):
        """Test complete interactive schema migration workflow."""
        # Test scenario: User wants to migrate a schema that already exists in target registry

        subject = "user-profile-events"
        source_registry = "development"
        target_registry = "staging"

        # Mock the underlying migration tool
        mock_migrate_tool = MagicMock(
            return_value={
                "success": True,
                "total_versions": 3,
                "successful_migrations": 3,
                "failed_migrations": 0,
                "migration_details": [
                    {"version": 1, "status": "migrated", "source_id": 101, "target_id": 201},
                    {"version": 2, "status": "migrated", "source_id": 102, "target_id": 202},
                    {"version": 3, "status": "migrated", "source_id": 103, "target_id": 203},
                ],
            }
        )

        # Mock export tool for backup
        mock_export_tool = MagicMock(
            return_value={
                "success": True,
                "subject": subject,
                "backup_location": "/backups/user-profile-events.json",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        )

        # Mock registry clients
        mock_source_client = MagicMock()
        mock_target_client = MagicMock()
        mock_target_client.config.url = "http://staging-registry:8081"
        mock_target_client.auth = self.mock_auth
        mock_target_client.headers = self.mock_headers

        # Mock schema verification responses
        mock_source_client.get_schema.return_value = {
            "schema": {
                "type": "record",
                "name": "UserProfileEvent",
                "fields": [
                    {"name": "user_id", "type": "string"},
                    {"name": "profile_data", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                ],
            },
            "schemaType": "AVRO",
            "id": 103,
            "version": 3,
        }

        mock_target_client.get_schema.return_value = {
            "schema": {
                "type": "record",
                "name": "UserProfileEvent",
                "fields": [
                    {"name": "user_id", "type": "string"},
                    {"name": "profile_data", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                ],
            },
            "schemaType": "AVRO",
            "id": 203,  # Different ID (not preserved)
            "version": 3,
        }

        def get_registry_side_effect(name):
            if name == source_registry:
                return mock_source_client
            elif name == target_registry:
                return mock_target_client
            return None

        self.mock_registry_manager.get_registry.side_effect = get_registry_side_effect

        # Mock requests to simulate schema existence check
        with patch("interactive_tools.requests.get") as mock_get:
            # First call: check if schema exists in target (returns 200 with versions)
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [1, 2, 3]

            # Mock elicitation response with complete user preferences
            with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
                mock_response = ElicitationResponse(
                    request_id="migrate-schema-integration-test",
                    values={
                        "replace_existing": "true",  # User agrees to replace
                        "backup_before_replace": "true",  # User wants backup
                        "preserve_ids": "false",  # Don't preserve IDs
                        "compare_after_migration": "true",  # Verify after migration
                        "migrate_all_versions": "true",  # Migrate all versions
                        "dry_run": "false",  # Perform actual migration
                    },
                    complete=True,
                    metadata={"source": "integration_test_user"},
                )
                mock_elicit.return_value = mock_response

                # Execute the interactive migration
                result = await migrate_schema_interactive(
                    subject=subject,
                    source_registry=source_registry,
                    target_registry=target_registry,
                    source_context="user-events",
                    target_context="user-events",
                    migrate_schema_tool=mock_migrate_tool,
                    export_schema_tool=mock_export_tool,
                    registry_manager=self.mock_registry_manager,
                    registry_mode=self.registry_mode,
                )

        # Verify elicitation was triggered with correct request
        mock_elicit.assert_called_once()
        elicitation_request = mock_elicit.call_args[0][0]
        assert elicitation_request.type == ElicitationType.FORM
        assert elicitation_request.title == "Schema Migration Preferences"
        assert subject in elicitation_request.description
        assert "already exists" in elicitation_request.description

        # Verify schema existence was properly detected
        assert elicitation_request.context["schema_exists_in_target"] is True
        assert elicitation_request.context["existing_versions"] == [1, 2, 3]

        # Verify backup was performed
        mock_export_tool.assert_called_once()
        export_call_kwargs = mock_export_tool.call_args.kwargs
        assert export_call_kwargs["subject"] == subject
        assert export_call_kwargs["registry"] == target_registry
        assert export_call_kwargs["include_metadata"] is True

        # Verify migration was executed with correct preferences
        mock_migrate_tool.assert_called_once()
        migrate_call_kwargs = mock_migrate_tool.call_args.kwargs
        assert migrate_call_kwargs["subject"] == subject
        assert migrate_call_kwargs["source_registry"] == source_registry
        assert migrate_call_kwargs["target_registry"] == target_registry
        assert migrate_call_kwargs["preserve_ids"] is False
        assert migrate_call_kwargs["dry_run"] is False
        assert migrate_call_kwargs["migrate_all_versions"] is True

        # Verify result structure
        assert result["success"] is True
        assert result["elicitation_used"] is True
        assert result["schema_existed_in_target"] is True

        # Verify elicited preferences are recorded
        elicited_prefs = result["elicited_preferences"]
        assert elicited_prefs["replace_existing"] is True
        assert elicited_prefs["backup_before_replace"] is True
        assert elicited_prefs["preserve_ids"] is False
        assert elicited_prefs["compare_after_migration"] is True

        # Verify backup result is included
        assert result["backup_result"]["success"] is True
        assert result["backup_result"]["subject"] == subject

        # Verify post-migration verification was performed
        verification_result = result["verification_result"]
        assert verification_result["verification_type"] == "basic"
        assert verification_result["overall_success"] is True

        # Check that verification included expected checks
        checks = verification_result["checks"]
        check_names = [check["check"] for check in checks]
        assert "schema_exists_in_target" in check_names
        assert "schema_content_match" in check_names
        assert "schema_type_match" in check_names
        # ID preservation check should NOT be present since preserve_ids=false
        assert "id_preservation" not in check_names

        # Verify specific check results
        schema_exists_check = next(c for c in checks if c["check"] == "schema_exists_in_target")
        assert schema_exists_check["passed"] is True

        content_match_check = next(c for c in checks if c["check"] == "schema_content_match")
        assert content_match_check["passed"] is True

        type_match_check = next(c for c in checks if c["check"] == "schema_type_match")
        assert type_match_check["passed"] is True

        logger.info("✅ Complete interactive schema migration workflow test passed")

    @pytest.mark.asyncio
    async def test_elicitation_timeout_handling(self):
        """Test elicitation timeout and cleanup behavior."""
        # Test scenario: Elicitation request times out and is properly cleaned up

        manager = ElicitationManager()

        # Create request with very short timeout
        request = ElicitationRequest(
            title="Timeout Test",
            fields=[ElicitationField("test_field", "text", required=True)],
            timeout_seconds=0.1,  # 100ms timeout
        )

        # Create and track the request
        request_id = await manager.create_request(request)
        assert request_id in manager.pending_requests

        # Wait for timeout to occur
        await asyncio.sleep(0.2)

        # Request should be automatically cleaned up
        assert request_id not in manager.pending_requests

        # Verify we can't submit a response to expired request
        response = ElicitationResponse(request_id=request_id, values={"test_field": "too_late"})

        success = await manager.submit_response(response)
        assert success is False

    @pytest.mark.asyncio
    async def test_multi_round_elicitation_workflow(self):
        """Test complex workflow requiring multiple elicitation rounds."""
        # Test scenario: Schema registration that requires multiple rounds of user input

        subject = "complex-user-profile"

        # Mock registration tool
        mock_register_tool = MagicMock(return_value={"success": True, "id": 456, "subject": subject, "version": 1})

        # First round: Basic field definition
        first_response = ElicitationResponse(
            request_id="round-1",
            values={
                "field_name": "user_id",
                "field_type": "string",
                "nullable": "false",
                "documentation": "Primary user identifier",
            },
            complete=True,
        )

        # Simulate multiple elicitation rounds
        elicitation_call_count = 0

        async def mock_elicit_multiple_rounds(request):
            nonlocal elicitation_call_count
            elicitation_call_count += 1

            if elicitation_call_count == 1:
                # First round: Add user_id field
                return first_response
            elif elicitation_call_count == 2:
                # Second round: Add email field
                return ElicitationResponse(
                    request_id="round-2",
                    values={
                        "field_name": "email",
                        "field_type": "string",
                        "nullable": "true",
                        "documentation": "User email address",
                    },
                    complete=True,
                )
            else:
                # No more fields needed
                return None

        with patch(
            "interactive_tools.elicit_with_fallback",
            side_effect=mock_elicit_multiple_rounds,
        ):
            result = await register_schema_interactive(
                subject=subject,
                schema_definition={
                    "type": "record",
                    "name": "UserProfile",
                    "fields": [],
                },
                register_schema_tool=mock_register_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Verify multiple elicitation rounds occurred
        assert elicitation_call_count >= 1
        assert result["success"] is True
        assert result["elicitation_used"] is True

    @pytest.mark.asyncio
    async def test_fallback_when_elicitation_fails(self):
        """Test graceful fallback when elicitation fails or times out."""
        # Test scenario: Elicitation system fails, but operation should continue with defaults

        subject = "fallback-test-schema"
        incomplete_schema = {"type": "record", "name": "FallbackTest", "fields": []}

        # Mock registration tool to expect a call even with fallback
        mock_register_tool = MagicMock(
            return_value={
                "error": "Schema validation failed",
                "details": "No fields defined in schema",
            }
        )

        # Mock elicitation to fail/timeout
        with patch("interactive_tools.elicit_with_fallback", return_value=None):
            result = await register_schema_interactive(
                subject=subject,
                schema_definition=incomplete_schema,
                register_schema_tool=mock_register_tool,
                registry_manager=self.mock_registry_manager,
                registry_mode=self.registry_mode,
                auth=self.mock_auth,
                headers=self.mock_headers,
                schema_registry_url=self.schema_registry_url,
            )

        # Should return error indicating elicitation failed
        assert "error" in result
        assert "INCOMPLETE_SCHEMA_DEFINITION" in result.get("error_code", "")
        assert "elicitation_status" in result.get("details", {})

    @pytest.mark.asyncio
    async def test_real_mcp_elicitation_integration(self):
        """Test real MCP protocol elicitation integration."""
        # Test scenario: Verify MCP protocol integration works correctly

        from elicitation_mcp_integration import real_mcp_elicit, set_mcp_instance

        # Set up mock MCP instance
        set_mcp_instance(self.mock_mcp)

        # Configure mock MCP to return successful elicitation response
        self.mock_mcp.send_elicitation_request.return_value = {
            "values": {"test_field": "mcp_response"},
            "complete": True,
            "metadata": {"source": "mcp_client"},
        }

        # Create test elicitation request
        request = ElicitationRequest(
            title="MCP Protocol Test",
            fields=[ElicitationField("test_field", "text", required=True)],
        )

        # Execute real MCP elicitation
        response = await real_mcp_elicit(request)

        # Verify MCP method was called
        self.mock_mcp.send_elicitation_request.assert_called_once()

        # Verify response was processed correctly
        assert response is not None
        assert response.values["test_field"] == "mcp_response"
        assert response.complete is True

    @pytest.mark.asyncio
    async def test_elicitation_response_submission(self):
        """Test client response submission through MCP protocol."""
        # Test scenario: Client submits elicitation response via MCP tool

        manager = ElicitationManager()

        # Create pending request
        request = ElicitationRequest(
            title="Response Submission Test",
            fields=[ElicitationField("user_input", "text", required=True)],
        )

        request_id = await manager.create_request(request)

        # Simulate client response submission
        response_data = {
            "values": {"user_input": "client_provided_value"},
            "complete": True,
            "metadata": {"source": "mcp_client_submission"},
        }

        # Test the response handling
        success = await handle_elicitation_response(request_id, response_data)

        # Verify response was processed
        assert success is True

        # Verify response is stored and request is cleaned up
        stored_response = manager.get_response(request_id)
        assert stored_response is not None
        assert stored_response.values["user_input"] == "client_provided_value"
        assert request_id not in manager.pending_requests

    def test_elicitation_manager_concurrent_requests(self):
        """Test elicitation manager handles concurrent requests correctly."""
        # Test scenario: Multiple concurrent elicitation requests

        async def test_concurrent():
            manager = ElicitationManager()

            # Create multiple requests concurrently
            request1 = ElicitationRequest(title="Concurrent Test 1")
            request2 = ElicitationRequest(title="Concurrent Test 2")
            request3 = ElicitationRequest(title="Concurrent Test 3")

            # Submit all requests
            ids = await asyncio.gather(
                manager.create_request(request1),
                manager.create_request(request2),
                manager.create_request(request3),
            )

            # Verify all requests are tracked
            assert len(manager.pending_requests) == 3
            assert all(req_id in manager.pending_requests for req_id in ids)

            # Submit responses concurrently
            responses = [ElicitationResponse(req_id, {"test": f"value_{i}"}) for i, req_id in enumerate(ids)]

            results = await asyncio.gather(*[manager.submit_response(resp) for resp in responses])

            # Verify all responses were processed
            assert all(results)
            assert len(manager.pending_requests) == 0

            # Verify responses are stored
            for req_id in ids:
                stored = manager.get_response(req_id)
                assert stored is not None

        # Run the concurrent test
        asyncio.run(test_concurrent())

    @pytest.mark.asyncio
    async def test_enhanced_elicitation_with_fallback_chain(self):
        """Test the enhanced elicitation function's fallback chain."""
        # Test scenario: Verify fallback chain from real MCP to mock works correctly

        from elicitation_mcp_integration import (
            enhanced_elicit_with_fallback,
            set_mcp_instance,
        )

        # Test 1: Real MCP elicitation succeeds
        mock_mcp = MagicMock()
        mock_mcp.send_elicitation_request = AsyncMock(
            return_value={"values": {"field": "real_mcp_value"}, "complete": True}
        )
        set_mcp_instance(mock_mcp)

        request = ElicitationRequest(
            title="Fallback Chain Test",
            fields=[ElicitationField("field", "text", default="fallback_value")],
        )

        response = await enhanced_elicit_with_fallback(request)
        assert response.values["field"] == "real_mcp_value"

        # Test 2: Real MCP fails, fallback to mock
        mock_mcp.send_elicitation_request.side_effect = Exception("MCP failed")

        response = await enhanced_elicit_with_fallback(request)
        assert response.values["field"] == "fallback_value"  # From mock fallback
        assert response.metadata["source"] == "mock_fallback"


class TestElicitationPerformance:
    """Test elicitation system performance and resource usage."""

    @pytest.mark.asyncio
    async def test_large_scale_elicitation_handling(self):
        """Test system behavior with many concurrent elicitation requests."""
        manager = ElicitationManager()

        # Create many requests quickly
        num_requests = 100
        requests = [
            ElicitationRequest(
                title=f"Performance Test {i}",
                fields=[ElicitationField(f"field_{i}", "text")],
            )
            for i in range(num_requests)
        ]

        start_time = datetime.utcnow()

        # Submit all requests
        request_ids = await asyncio.gather(*[manager.create_request(req) for req in requests])

        submission_time = datetime.utcnow() - start_time

        # Verify all requests were created quickly (< 1 second)
        assert submission_time.total_seconds() < 1.0
        assert len(manager.pending_requests) == num_requests

        # Submit responses
        responses = [ElicitationResponse(req_id, {f"field_{i}": f"value_{i}"}) for i, req_id in enumerate(request_ids)]

        start_time = datetime.utcnow()
        results = await asyncio.gather(*[manager.submit_response(resp) for resp in responses])
        processing_time = datetime.utcnow() - start_time

        # Verify all responses processed quickly
        assert processing_time.total_seconds() < 2.0
        assert all(results)
        assert len(manager.pending_requests) == 0

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_completion(self):
        """Test that completed elicitation requests are properly cleaned up."""
        manager = ElicitationManager()

        # Create and complete several requests
        for i in range(10):
            request = ElicitationRequest(title=f"Cleanup Test {i}")
            request_id = await manager.create_request(request)

            response = ElicitationResponse(request_id, {"test": f"value_{i}"})
            await manager.submit_response(response)

        # Verify all requests are cleaned up from pending
        assert len(manager.pending_requests) == 0

        # Verify responses are still accessible (for audit/debugging)
        assert len(manager.responses) == 10


# Mock functions for testing
async def handle_elicitation_response(request_id: str, response_data: dict) -> bool:
    """Mock elicitation response handler for testing."""
    manager = ElicitationManager()
    response = ElicitationResponse(
        request_id=request_id,
        values=response_data.get("values", {}),
        complete=response_data.get("complete", True),
        metadata=response_data.get("metadata", {}),
    )
    return await manager.submit_response(response)


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
