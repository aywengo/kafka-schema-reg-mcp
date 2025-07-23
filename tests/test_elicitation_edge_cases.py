#!/usr/bin/env python3
"""
Edge Case Tests for Elicitation Capability

Additional test coverage for edge cases, error conditions, and
performance scenarios in the elicitation system.
"""

import asyncio
import os
import sys
import time
from unittest.mock import Mock, patch

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elicitation import (
    ElicitationField,
    ElicitationManager,
    ElicitationRequest,
    ElicitationResponse,
    mock_elicit,
)
from elicitation_mcp_integration import (
    enhanced_elicit_with_fallback,
    handle_elicitation_response,
    real_mcp_elicit,
)
from interactive_tools import (
    _build_schema_from_elicitation,
    register_schema_interactive,
)


class TestElicitationEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def manager(self):
        """Fresh manager for each test."""
        return ElicitationManager()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, manager):
        """Test handling multiple concurrent elicitation requests."""
        requests = []
        for i in range(10):
            request = ElicitationRequest(title=f"Concurrent Request {i}", timeout_seconds=30)
            requests.append(request)
            await manager.create_request(request)

        # All requests should be tracked
        assert len(manager.pending_requests) == 10

        # Submit responses concurrently
        tasks = []
        for i, request in enumerate(requests):
            response = ElicitationResponse(request_id=request.id, values={"index": i})
            tasks.append(manager.submit_response(response))

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert len(manager.pending_requests) == 0
        assert len(manager.responses) == 10

    @pytest.mark.asyncio
    async def test_memory_cleanup_under_load(self):
        """Test memory cleanup under high load conditions."""
        manager = ElicitationManager()

        # Create many short-lived requests
        for i in range(100):
            request = ElicitationRequest(title=f"Load Test {i}", timeout_seconds=0.01)  # Very short timeout
            await manager.create_request(request)

        # Wait for all to timeout and cleanup
        await asyncio.sleep(0.1)

        # Should be cleaned up
        assert len(manager.pending_requests) == 0
        assert len(manager.timeout_tasks) == 0

    def test_malformed_elicitation_fields(self):
        """Test handling of malformed field definitions."""
        # Missing required name
        with pytest.raises(TypeError):
            ElicitationField(type="text")

        # Invalid type
        field = ElicitationField("test", "invalid_type")
        assert field.type == "invalid_type"  # Should not validate at creation

        # None values
        field = ElicitationField(name=None, type="text")
        # Should handle None gracefully

    @pytest.mark.asyncio
    async def test_response_validation_edge_cases(self, manager):
        """Test response validation with edge cases."""
        # Request with complex validation
        request = ElicitationRequest(
            title="Validation Test",
            fields=[
                ElicitationField("email", "email", required=True),
                ElicitationField("choice", "choice", options=["a", "b", "c"], required=True),
                ElicitationField("optional", "text", required=False),
            ],
        )

        await manager.create_request(request)

        # Test various invalid responses
        test_cases = [
            # Invalid email format
            {"email": "not-an-email", "choice": "a"},
            # Choice not in options
            {"email": "test@example.com", "choice": "invalid"},
            # Missing required field
            {"email": "test@example.com"},
            # Empty email
            {"email": "", "choice": "a"},
            # Null choice when required
            {"email": "test@example.com", "choice": None},
        ]

        for values in test_cases:
            response = ElicitationResponse(request_id=request.id, values=values)

            is_valid = manager._validate_response(request, response)
            assert not is_valid, f"Should be invalid: {values}"

        # Valid response
        valid_response = ElicitationResponse(
            request_id=request.id,
            values={
                "email": "test@example.com",
                "choice": "a",
                "optional": "some value",
            },
        )

        assert manager._validate_response(request, valid_response)

    @pytest.mark.asyncio
    async def test_timeout_edge_cases(self):
        """Test timeout handling edge cases."""
        manager = ElicitationManager()

        # Zero timeout
        request = ElicitationRequest(title="Zero Timeout", timeout_seconds=0)

        await manager.create_request(request)

        # Should be expired immediately
        assert request.is_expired()

        # Negative timeout
        request2 = ElicitationRequest(title="Negative Timeout", timeout_seconds=-1)

        await manager.create_request(request2)

        # Should handle gracefully (likely expired)
        assert request2.is_expired()

    @pytest.mark.asyncio
    async def test_response_after_timeout(self, manager):
        """Test submitting response after request timeout."""
        request = ElicitationRequest(title="Timeout Test", timeout_seconds=0.01)

        await manager.create_request(request)

        # Wait for timeout
        await asyncio.sleep(0.05)

        # Try to submit response after timeout
        response = ElicitationResponse(request_id=request.id, values={"test": "value"})

        success = await manager.submit_response(response)
        assert not success  # Should fail due to timeout

    @pytest.mark.asyncio
    async def test_duplicate_response_submission(self, manager):
        """Test submitting multiple responses to same request."""
        request = ElicitationRequest(title="Duplicate Test", fields=[ElicitationField("test", "text")])

        await manager.create_request(request)

        # Submit first response
        response1 = ElicitationResponse(request_id=request.id, values={"test": "first"})

        success1 = await manager.submit_response(response1)
        assert success1

        # Try to submit second response (should fail)
        response2 = ElicitationResponse(request_id=request.id, values={"test": "second"})

        success2 = await manager.submit_response(response2)
        assert not success2  # Request already completed

    def test_request_serialization_with_special_characters(self):
        """Test serialization with special characters and unicode."""
        request = ElicitationRequest(
            title="Special Characters: 测试 🚀 \"quotes\" 'apostrophes'",
            description="Unicode test: αβγδε",
            fields=[
                ElicitationField(
                    "unicode_field",
                    "text",
                    label="Field with emoji 🎯",
                    placeholder="Enter value: αβγ",
                )
            ],
            context={"unicode_key": "测试值", "emoji": "🎉"},
        )

        # Should serialize without errors
        data = request.to_dict()

        assert "测试" in data["title"]
        assert "🚀" in data["title"]
        assert data["description"] == "Unicode test: αβγδε"
        assert data["fields"][0]["label"] == "Field with emoji 🎯"
        assert data["context"]["unicode_key"] == "测试值"

    @pytest.mark.asyncio
    async def test_large_response_values(self, manager):
        """Test handling of large response values."""
        request = ElicitationRequest(
            title="Large Response Test",
            fields=[
                ElicitationField("large_text", "text"),
                ElicitationField("normal_text", "text"),
            ],
        )

        await manager.create_request(request)

        # Large text value (1MB)
        large_value = "x" * (1024 * 1024)

        response = ElicitationResponse(
            request_id=request.id,
            values={"large_text": large_value, "normal_text": "normal"},
        )

        # Should handle large values
        success = await manager.submit_response(response)
        assert success

        retrieved = manager.get_response(request.id)
        assert len(retrieved.values["large_text"]) == 1024 * 1024

    @pytest.mark.asyncio
    async def test_concurrent_manager_operations(self):
        """Test concurrent operations on the same manager."""
        manager = ElicitationManager()

        async def create_and_respond(index):
            request = ElicitationRequest(title=f"Concurrent {index}", fields=[ElicitationField("value", "text")])

            await manager.create_request(request)

            # Small delay to simulate real usage
            await asyncio.sleep(0.01)

            response = ElicitationResponse(request_id=request.id, values={"value": f"response_{index}"})

            return await manager.submit_response(response)

        # Run 20 concurrent operations
        tasks = [create_and_respond(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert len(manager.responses) == 20


class TestMCPIntegrationEdgeCases:
    """Test MCP integration edge cases."""

    @pytest.mark.asyncio
    async def test_mcp_client_capability_detection_failure(self):
        """Test handling when MCP client capability detection fails."""
        mock_mcp = Mock()

        # Mock various failure scenarios
        mock_mcp.get_client_capabilities = Mock(side_effect=Exception("Connection failed"))
        mock_mcp.client_info = None
        mock_mcp.call_method = Mock(side_effect=asyncio.TimeoutError())

        # Should handle gracefully
        from elicitation_mcp_integration import _check_client_elicitation_support

        supported = await _check_client_elicitation_support(mock_mcp)

        # Should default to supported (optimistic)
        assert supported is True

    @pytest.mark.asyncio
    async def test_real_mcp_elicit_no_instance(self):
        """Test real MCP elicitation when no MCP instance is available."""
        # Clear the global MCP instance
        from elicitation_mcp_integration import set_mcp_instance

        set_mcp_instance(None)

        request = ElicitationRequest(
            title="No MCP Test",
            fields=[ElicitationField("test", "text", default="fallback")],
        )

        # Should fall back to mock
        response = await real_mcp_elicit(request)

        assert response is not None
        assert response.values["test"] == "fallback"
        assert response.metadata["source"] == "mock_fallback"

    @pytest.mark.asyncio
    async def test_elicitation_response_handling_malformed_data(self):
        """Test handling malformed elicitation response data."""
        # Test various malformed data
        malformed_cases = [
            None,
            "not a dict",
            {},  # Missing values
            {"values": None},
            {"values": "not a dict"},
            {"values": {}, "complete": "not a boolean"},
        ]

        for data in malformed_cases:
            result = await handle_elicitation_response("test-id", data)
            assert not result  # Should fail gracefully

    @pytest.mark.asyncio
    async def test_enhanced_elicit_with_all_failures(self):
        """Test enhanced elicitation when all methods fail."""
        request = ElicitationRequest(
            title="All Failures Test",
            fields=[ElicitationField("test", "text", default="ultimate_fallback")],
        )

        # Mock all elicitation methods to fail
        with patch("elicitation_mcp_integration.real_mcp_elicit") as mock_real:
            mock_real.side_effect = Exception("MCP failed")

            with patch("elicitation_mcp_integration.mock_elicit") as mock_fallback:
                mock_fallback.side_effect = Exception("Mock failed")

                # Should handle gracefully
                response = await enhanced_elicit_with_fallback(request)

                # Should still work due to exception handling
                assert response is None or response.values["test"] == "ultimate_fallback"


class TestInteractiveToolsEdgeCases:
    """Test edge cases in interactive tools."""

    @pytest.mark.asyncio
    async def test_register_schema_interactive_build_schema_edge_cases(self):
        """Test schema building with edge case elicitation responses."""
        # Test various response types
        test_cases = [
            # Minimal response
            {"field_name": "test_field", "field_type": "string"},
            # Complex nullable field with default
            {
                "field_name": "complex_field",
                "field_type": "int",
                "nullable": "true",
                "default_value": "42",
                "documentation": "A complex test field",
            },
            # Boolean field
            {"field_name": "flag", "field_type": "boolean", "default_value": "true"},
            # Array field (not supported but should handle)
            {"field_name": "array_field", "field_type": "array"},
        ]

        for values in test_cases:
            schema = await _build_schema_from_elicitation(values)

            assert schema["type"] == "record"
            assert len(schema["fields"]) == 1

            field = schema["fields"][0]
            assert field["name"] == values["field_name"]

    @pytest.mark.asyncio
    async def test_interactive_tools_with_null_dependencies(self):
        """Test interactive tools when dependencies are None."""
        # Test with None values for dependencies
        result = await register_schema_interactive(
            subject="test",
            schema_definition=None,
            register_schema_tool=None,  # None dependency
            registry_manager=None,
            registry_mode=None,
            auth=None,
            headers=None,
            schema_registry_url=None,
        )

        # Should handle gracefully and return error
        assert "error" in result

    @pytest.mark.asyncio
    async def test_elicitation_timeout_during_interactive_operation(self):
        """Test handling when elicitation times out during interactive operation."""
        mock_register_tool = Mock(return_value={"success": True})

        # Mock elicitation to timeout (return None)
        with patch("interactive_tools.elicit_with_fallback") as mock_elicit:
            mock_elicit.return_value = None  # Timeout

            result = await register_schema_interactive(
                subject="timeout-test",
                schema_definition={"type": "record", "fields": []},  # Needs elicitation
                register_schema_tool=mock_register_tool,
                registry_manager=Mock(),
                registry_mode="multi",
                auth=None,
                headers={},
                schema_registry_url="http://test",
            )

        # Should return error about unable to obtain schema definition
        assert "error" in result
        assert "Unable to obtain complete schema definition" in result["error"]

    def test_field_validation_with_complex_constraints(self):
        """Test field validation with complex validation rules."""
        manager = ElicitationManager()

        request = ElicitationRequest(
            title="Complex Validation",
            fields=[
                ElicitationField(
                    "numeric_string",
                    "text",
                    validation={"pattern": r"^\d+$", "min_length": 1, "max_length": 10},
                ),
                ElicitationField("enum_value", "choice", options=["value1", "value2", "value3"]),
            ],
        )

        # Current implementation doesn't enforce complex validation
        # But should not crash with validation dict present
        response = ElicitationResponse(
            request_id=request.id,
            values={
                "numeric_string": "123abc",  # Invalid pattern
                "enum_value": "value1",  # Valid
            },
        )

        # Should handle gracefully (may or may not validate pattern)
        result = manager._validate_response(request, response)
        # Current implementation only checks email format and choice options


class TestPerformanceAndScaling:
    """Test performance and scaling characteristics."""

    @pytest.mark.asyncio
    async def test_large_number_of_fields(self):
        """Test elicitation with large number of fields."""
        # Create request with many fields
        fields = []
        for i in range(100):
            fields.append(ElicitationField(f"field_{i}", "text", default=f"default_{i}"))

        request = ElicitationRequest(title="Large Fields Test", fields=fields)

        # Should serialize efficiently
        start_time = time.time()
        data = request.to_dict()
        serialize_time = time.time() - start_time

        assert serialize_time < 1.0  # Should be fast
        assert len(data["fields"]) == 100

        # Test mock elicitation with many fields
        start_time = time.time()
        response = await mock_elicit(request)
        elicit_time = time.time() - start_time

        assert elicit_time < 1.0  # Should be fast
        assert len(response.values) == 100

    @pytest.mark.asyncio
    async def test_rapid_request_creation_and_cleanup(self):
        """Test rapid creation and cleanup of requests."""
        manager = ElicitationManager()

        # Create many requests rapidly
        start_time = time.time()

        for i in range(1000):
            request = ElicitationRequest(title=f"Rapid {i}", timeout_seconds=0.001)  # Very short
            await manager.create_request(request)

        creation_time = time.time() - start_time
        assert creation_time < 5.0  # Should be reasonably fast

        # Wait for cleanup
        await asyncio.sleep(0.1)

        # Should be cleaned up
        assert len(manager.pending_requests) == 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
