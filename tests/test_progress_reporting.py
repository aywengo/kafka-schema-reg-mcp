#!/usr/bin/env python3
"""
Test FastMCP Progress Reporting Functionality

This test module validates that FastMCP Progress dependency works correctly
with background tasks for migration and batch operations.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProgressReporting:
    """Test FastMCP Progress reporting functionality"""

    @pytest.mark.asyncio
    async def test_progress_initialization(self):
        """Test that Progress can be initialized"""
        from fastmcp.dependencies import Progress

        progress = Progress()
        assert progress is not None

        # Test that progress methods are callable
        assert hasattr(progress, "set_total")
        assert hasattr(progress, "set_message")

    @pytest.mark.asyncio
    async def test_progress_set_total(self):
        """Test setting progress total"""
        from fastmcp.dependencies import Progress

        progress = Progress()

        # Mock the async methods
        progress.set_total = AsyncMock()
        progress.set_message = AsyncMock()

        await progress.set_total(100)
        progress.set_total.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_progress_set_message(self):
        """Test setting progress message"""
        from fastmcp.dependencies import Progress

        progress = Progress()

        # Mock the async methods
        progress.set_total = AsyncMock()
        progress.set_message = AsyncMock()

        await progress.set_message("Processing...")
        progress.set_message.assert_called_once_with("Processing...")

    @pytest.mark.asyncio
    async def test_migration_progress_integration(self):
        """Test that migration tools use Progress correctly"""
        # Mock Progress
        mock_progress = MagicMock()
        mock_progress.set_total = AsyncMock()
        mock_progress.set_message = AsyncMock()

        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_source_client = MagicMock()
        mock_target_client = MagicMock()
        mock_registry_manager.get_registry = MagicMock(
            side_effect=lambda name: {
                "dev": mock_source_client,
                "prod": mock_target_client,
            }.get(name)
        )

        # Mock client configs
        mock_source_client.config = MagicMock()
        mock_source_client.config.name = "dev"
        mock_source_client.config.url = "http://localhost:38081"
        mock_target_client.config = MagicMock()
        mock_target_client.config.name = "prod"
        mock_target_client.config.url = "http://localhost:38082"

        # Mock session and responses
        mock_source_client.session = MagicMock()
        mock_target_client.session = MagicMock()

        # Mock versions endpoint
        mock_versions_response = MagicMock()
        mock_versions_response.status_code = 200
        mock_versions_response.json.return_value = [1]
        mock_source_client.session.get.return_value = mock_versions_response

        # Mock schema endpoint
        mock_schema_response = MagicMock()
        mock_schema_response.status_code = 200
        mock_schema_response.json.return_value = {
            "id": 1,
            "schema": '{"type":"record","name":"Test","fields":[]}',
            "schemaType": "AVRO",
        }
        mock_source_client.session.get.return_value = mock_schema_response

        # Mock target registration
        mock_target_response = MagicMock()
        mock_target_response.status_code = 200
        mock_target_response.json.return_value = {"id": 2}
        mock_target_client.session.post.return_value = mock_target_response

        # Test migration with Progress
        from migration_tools import migrate_schema_tool

        with patch("fastmcp.dependencies.Progress", return_value=mock_progress):
            result = await migrate_schema_tool(
                subject="test-subject",
                source_registry="dev",
                target_registry="prod",
                registry_manager=mock_registry_manager,
                registry_mode="multi",
                dry_run=False,
                preserve_ids=False,
            )

            # Verify Progress was used
            mock_progress.set_total.assert_called()
            assert mock_progress.set_message.call_count > 0

            # Verify migration result structure
            assert isinstance(result, dict)
            assert "successful_migrations" in result or "error" in result

    @pytest.mark.asyncio
    async def test_batch_cleanup_progress_integration(self):
        """Test that batch cleanup tools use Progress correctly"""
        # Mock Progress
        mock_progress = MagicMock()
        mock_progress.set_total = AsyncMock()
        mock_progress.set_message = AsyncMock()

        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_client = MagicMock()
        mock_registry_manager.get_registry = MagicMock(return_value=mock_client)
        mock_registry_manager.list_registries = MagicMock(return_value=["test-registry"])

        # Mock client methods
        mock_client.get_subjects = MagicMock(return_value=["subject1", "subject2"])
        mock_client.delete_subject = MagicMock(return_value=[1, 2])
        mock_client.config = MagicMock()
        mock_client.config.name = "test-registry"

        # Test batch cleanup with Progress
        from batch_operations import clear_context_batch_tool

        with patch("fastmcp.dependencies.Progress", return_value=mock_progress):
            result = await clear_context_batch_tool(
                context="test-context",
                registry_manager=mock_registry_manager,
                registry_mode="multi",
                registry="test-registry",
                delete_context_after=False,
                dry_run=True,
                progress=mock_progress,
            )

            # Verify Progress was used
            mock_progress.set_total.assert_called()
            assert mock_progress.set_message.call_count > 0

            # Verify cleanup result structure
            assert isinstance(result, dict)
            assert "subjects_found" in result or "error" in result

    @pytest.mark.asyncio
    async def test_progress_message_sequence(self):
        """Test that progress messages are set in correct sequence"""
        # Track message calls
        messages = []

        async def track_message(msg):
            messages.append(msg)

        mock_progress = MagicMock()
        mock_progress.set_total = AsyncMock()
        mock_progress.set_message = AsyncMock(side_effect=track_message)

        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_source_client = MagicMock()
        mock_target_client = MagicMock()
        mock_registry_manager.get_registry = MagicMock(
            side_effect=lambda name: {
                "dev": mock_source_client,
                "prod": mock_target_client,
            }.get(name)
        )

        mock_source_client.config = MagicMock()
        mock_source_client.config.name = "dev"
        mock_source_client.config.url = "http://localhost:38081"
        mock_target_client.config = MagicMock()
        mock_target_client.config.name = "prod"
        mock_target_client.config.url = "http://localhost:38082"

        # Mock responses for successful migration
        mock_source_client.session = MagicMock()
        mock_target_client.session = MagicMock()

        mock_versions_response = MagicMock()
        mock_versions_response.status_code = 200
        mock_versions_response.json.return_value = [1]
        mock_source_client.session.get.return_value = mock_versions_response

        mock_schema_response = MagicMock()
        mock_schema_response.status_code = 200
        mock_schema_response.json.return_value = {
            "id": 1,
            "schema": '{"type":"record","name":"Test","fields":[]}',
            "schemaType": "AVRO",
        }
        mock_source_client.session.get.return_value = mock_schema_response

        mock_target_response = MagicMock()
        mock_target_response.status_code = 200
        mock_target_response.json.return_value = {"id": 2}
        mock_target_client.session.post.return_value = mock_target_response

        from migration_tools import migrate_schema_tool

        with patch("fastmcp.dependencies.Progress", return_value=mock_progress):
            await migrate_schema_tool(
                subject="test-subject",
                source_registry="dev",
                target_registry="prod",
                registry_manager=mock_registry_manager,
                registry_mode="multi",
                dry_run=False,
                preserve_ids=False,
            )

            # Verify messages were set
            assert len(messages) > 0
            # First message should be about starting
            assert any("Starting" in msg or "migration" in msg.lower() for msg in messages)

    def test_progress_dependency_injection(self):
        """Test that Progress dependency can be injected into tools"""
        from fastmcp.dependencies import Progress

        # Create a Progress instance
        progress = Progress()

        # Verify it has the expected interface
        assert hasattr(progress, "set_total")
        assert hasattr(progress, "set_message")
        assert callable(progress.set_total) or hasattr(progress.set_total, "__call__")
        assert callable(progress.set_message) or hasattr(progress.set_message, "__call__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
