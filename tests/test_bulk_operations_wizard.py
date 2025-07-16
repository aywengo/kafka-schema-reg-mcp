"""
Tests for Bulk Operations Wizard
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from bulk_operations_wizard import BulkOperationPreview, BulkOperationsWizard, BulkOperationType


class TestBulkOperationsWizard:
    """Test suite for BulkOperationsWizard"""

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry client"""
        registry = Mock()
        registry.list_subjects = AsyncMock(
            return_value=["test-schema-1", "test-schema-2", "prod-schema-1", "deprecated-schema-1", "old-schema-1"]
        )
        return registry

    @pytest.fixture
    def mock_elicitation(self):
        """Create mock elicitation manager"""
        elicitation = Mock()
        elicitation.elicit = AsyncMock()
        elicitation.show_info = AsyncMock()
        return elicitation

    @pytest.fixture
    def mock_task_manager(self):
        """Create mock task manager"""
        task_manager = Mock()
        task_manager.create_task = AsyncMock(return_value="task-123")
        task_manager.update_progress = AsyncMock()
        task_manager.complete_task = AsyncMock()
        task_manager.fail_task = AsyncMock()
        task_manager.get_task_status = AsyncMock(return_value={"status": "completed", "processed": 5, "total_items": 5})
        return task_manager

    @pytest.fixture
    def mock_batch_ops(self):
        """Create mock batch operations"""
        return Mock()

    @pytest.fixture
    def wizard(self, mock_registry, mock_elicitation, mock_task_manager, mock_batch_ops):
        """Create wizard instance with mocks"""
        return BulkOperationsWizard(mock_registry, mock_elicitation, mock_task_manager, mock_batch_ops)

    @pytest.mark.asyncio
    async def test_wizard_initialization(self, wizard):
        """Test wizard initialization"""
        assert wizard.registry is not None
        assert wizard.elicitation is not None
        assert wizard.task_manager is not None
        assert wizard.batch_ops is not None
        assert len(wizard._operation_handlers) == 4

    @pytest.mark.asyncio
    async def test_start_wizard_with_operation_type(self, wizard):
        """Test starting wizard with pre-selected operation type"""
        # Mock the handler
        mock_handler = AsyncMock(return_value={"status": "success"})
        wizard._operation_handlers[BulkOperationType.CLEANUP] = mock_handler

        result = await wizard.start_wizard(BulkOperationType.CLEANUP)

        assert result["status"] == "success"
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_wizard_without_operation_type(self, wizard):
        """Test starting wizard without operation type (elicits from user)"""
        # Mock elicitation response
        wizard.elicitation.elicit.return_value = {"operation_type": "cleanup"}

        # Mock the handler
        mock_handler = AsyncMock(return_value={"status": "success"})
        wizard._operation_handlers[BulkOperationType.CLEANUP] = mock_handler

        result = await wizard.start_wizard()

        assert result["status"] == "success"
        wizard.elicitation.elicit.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_selection_simple(self, wizard):
        """Test simple schema selection"""
        # Mock elicitation response
        wizard.elicitation.elicit.return_value = {"selected_schemas": ["test-schema-1", "test-schema-2"]}

        result = await wizard._elicit_schema_selection("Select schemas")

        assert len(result) == 2
        assert "test-schema-1" in result
        assert "test-schema-2" in result

    @pytest.mark.asyncio
    async def test_schema_selection_with_patterns(self, wizard):
        """Test schema selection with pattern matching"""
        # Mock elicitation response with pattern
        wizard.elicitation.elicit.return_value = {"selected_schemas": ["test-*", "prod-schema-1"]}

        result = await wizard._elicit_schema_selection("Select schemas", allow_patterns=True)

        # Should expand test-* pattern
        assert "test-schema-1" in result
        assert "test-schema-2" in result
        assert "prod-schema-1" in result
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_preview_generation(self, wizard):
        """Test preview generation"""
        items = ["schema1", "schema2", "schema3"]
        params = {"update_type": "compatibility", "level": "BACKWARD"}

        preview = await wizard._generate_preview(BulkOperationType.SCHEMA_UPDATE, items, params)

        assert isinstance(preview, BulkOperationPreview)
        assert preview.total_count == 3
        assert preview.estimated_duration == 1.5  # 0.5 seconds per item
        assert len(preview.affected_items) == 3

    @pytest.mark.asyncio
    async def test_preview_with_warnings(self, wizard):
        """Test preview generation with warnings"""
        # Large batch
        items = ["schema" + str(i) for i in range(150)]
        params = {}

        preview = await wizard._generate_preview(BulkOperationType.CLEANUP, items, params)

        assert len(preview.warnings) >= 2  # Large batch warning + destructive op warning
        assert any("Large batch size" in w for w in preview.warnings)
        assert any("destructive" in w for w in preview.warnings)

    @pytest.mark.asyncio
    async def test_confirmation_flow(self, wizard):
        """Test confirmation workflow"""
        preview = BulkOperationPreview(
            affected_items=[{"name": "test"}], total_count=1, changes_summary={}, estimated_duration=0.5
        )

        # Mock elicitation responses
        wizard.elicitation.elicit.side_effect = [
            {"show_preview": False},  # Don't show preview
            {"proceed": True},  # Confirm operation
        ]

        result = await wizard._confirm_operation(preview)

        assert result is True
        assert wizard.elicitation.elicit.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_operation_success(self, wizard):
        """Test successful operation execution"""
        items = ["schema1", "schema2"]
        params = {"batch_size": 2, "create_backup": False}
        preview = Mock()

        # Mock process_batch to return success
        wizard._process_batch = AsyncMock(return_value={"batch_size": 2, "success": 2, "failed": 0, "errors": []})

        result = await wizard._execute_bulk_operation(BulkOperationType.SCHEMA_UPDATE, items, params, preview)

        assert result["status"] == "success"
        assert result["processed"] == 2
        assert "task_id" in result
        wizard.task_manager.create_task.assert_called_once()
        wizard.task_manager.complete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_operation_with_error_and_rollback(self, wizard):
        """Test operation execution with error and rollback"""
        items = ["schema1", "schema2"]
        params = {"rollback_on_error": True}
        preview = Mock()

        # Mock process_batch to raise error
        wizard._process_batch = AsyncMock(side_effect=Exception("Test error"))
        wizard._rollback_operation = AsyncMock()

        result = await wizard._execute_bulk_operation(BulkOperationType.SCHEMA_UPDATE, items, params, preview)

        assert result["status"] == "failed"
        assert "Test error" in result["error"]
        wizard._rollback_operation.assert_called_once()
        wizard.task_manager.fail_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_consumer_impact_detection(self, wizard):
        """Test consumer impact detection for cleanup operations"""
        items = ["schema1"]
        params = {"cleanup_type": "deprecated"}

        preview = await wizard._generate_preview(BulkOperationType.CLEANUP, items, params)

        assert preview.consumer_impact is not None
        assert "active_consumers" in preview.consumer_impact
        assert "consumer_groups" in preview.consumer_impact

    @pytest.mark.asyncio
    async def test_batch_processing(self, wizard):
        """Test batch processing with delays"""
        items = ["schema" + str(i) for i in range(5)]
        params = {"batch_size": 2, "delay_between_batches": 0.1, "create_backup": False}
        preview = Mock()

        wizard._process_batch = AsyncMock(return_value={"success": 2})

        start_time = datetime.now()
        await wizard._execute_bulk_operation(BulkOperationType.SCHEMA_UPDATE, items, params, preview)
        duration = (datetime.now() - start_time).total_seconds()

        # Should have 3 batches (2+2+1) with 2 delays
        assert wizard._process_batch.call_count == 3
        assert duration >= 0.2  # At least 2 delays of 0.1s

    @pytest.mark.asyncio
    async def test_bulk_cleanup_workflow(self, wizard):
        """Test complete bulk cleanup workflow"""
        # Mock all elicitation responses
        wizard.elicitation.elicit.side_effect = [
            {"cleanup_type": "deprecated"},  # Cleanup type
            {"selected_schemas": ["deprecated-schema-1"]},  # Schema selection
            {"check_consumers": True},  # Consumer check option
            {"force": False},  # Force option
            {"consumer_action": "skip"},  # Consumer impact action
            {"show_preview": False},  # Don't show preview
            {"proceed": True},  # Confirm operation
        ]

        # Mock other methods
        wizard._generate_preview = AsyncMock(
            return_value=BulkOperationPreview(
                affected_items=[{"name": "deprecated-schema-1"}],
                total_count=1,
                changes_summary={},
                estimated_duration=0.5,
                consumer_impact={"active_consumers": 1},
            )
        )

        wizard._execute_bulk_operation = AsyncMock(return_value={"status": "success", "processed": 1})

        result = await wizard._handle_bulk_cleanup()

        assert result["status"] == "success"
        assert wizard.elicitation.elicit.call_count == 7

    @pytest.mark.asyncio
    async def test_operation_cancellation(self, wizard):
        """Test operation cancellation"""
        # Mock confirmation to return False
        wizard.elicitation.elicit.side_effect = [
            {"show_preview": False},  # Don't show preview
            {"proceed": False},  # Don't proceed
        ]

        wizard._elicit_schema_selection = AsyncMock(return_value=["test"])
        wizard._elicit_update_type = AsyncMock(return_value="compatibility")
        wizard._elicit_update_parameters = AsyncMock(return_value={})
        wizard._generate_preview = AsyncMock(
            return_value=BulkOperationPreview(
                affected_items=[{"name": "test"}], total_count=1, changes_summary={}, estimated_duration=0.5
            )
        )

        result = await wizard._handle_bulk_schema_update()

        assert result["status"] == "cancelled"
        assert result["reason"] == "User cancelled operation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
