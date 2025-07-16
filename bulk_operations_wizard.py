"""
Bulk Operations Wizard for Schema Registry Admin Tasks

This module provides an interactive wizard that uses elicitation to safely execute
operations across multiple schemas or contexts, making admin tasks more efficient
and less error-prone.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from elicitation import ElicitationManager, ElicitationRequest
from schema_registry_common import RegistryClient
from task_management import AsyncTaskManager
# from batch_operations import BatchOperations  # Not needed for now

logger = logging.getLogger(__name__)


class BulkOperationType(Enum):
    """Supported bulk operation types"""

    SCHEMA_UPDATE = "schema_update"
    MIGRATION = "migration"
    CLEANUP = "cleanup"
    CONFIGURATION = "configuration"


@dataclass
class BulkOperationConfig:
    """Configuration for a bulk operation"""

    operation_type: BulkOperationType
    dry_run: bool = True
    batch_size: int = 10
    delay_between_batches: float = 1.0
    create_backup: bool = True
    rollback_on_error: bool = True
    progress_callback: Optional[callable] = None


@dataclass
class BulkOperationPreview:
    """Preview of changes that will be made"""

    affected_items: List[Dict[str, Any]]
    total_count: int
    changes_summary: Dict[str, Any]
    estimated_duration: float
    warnings: List[str] = field(default_factory=list)
    consumer_impact: Optional[Dict[str, Any]] = None


class BulkOperationsWizard:
    """
    Interactive wizard for bulk operations on Schema Registry
    """

    def __init__(
        self,
        registry_manager,
        elicitation_manager: ElicitationManager,
        task_manager: AsyncTaskManager,
        batch_operations,
    ):
        self.registry = registry_manager
        self.elicitation = elicitation_manager
        self.task_manager = task_manager
        self.batch_ops = batch_operations
        self._operation_handlers = self._register_handlers()

    def _register_handlers(self) -> Dict[BulkOperationType, callable]:
        """Register operation handlers"""
        return {
            BulkOperationType.SCHEMA_UPDATE: self._handle_bulk_schema_update,
            BulkOperationType.MIGRATION: self._handle_bulk_migration,
            BulkOperationType.CLEANUP: self._handle_bulk_cleanup,
            BulkOperationType.CONFIGURATION: self._handle_bulk_configuration,
        }

    async def start_wizard(self, operation_type: Optional[BulkOperationType] = None) -> Dict[str, Any]:
        """
        Start the bulk operations wizard

        Args:
            operation_type: Pre-selected operation type, or None to prompt user

        Returns:
            Operation result
        """
        # Select operation type if not provided
        if not operation_type:
            operation_type = await self._elicit_operation_type()

        # Get operation handler
        handler = self._operation_handlers.get(operation_type)
        if not handler:
            raise ValueError(f"Unknown operation type: {operation_type}")

        # Execute the operation workflow
        return await handler()

    async def _elicit_operation_type(self) -> BulkOperationType:
        """Elicit operation type from user"""
        request = ElicitationRequest(
            request_id=f"bulk_op_type_{datetime.now().timestamp()}",
            elicitation_type="select",
            prompt="What type of bulk operation would you like to perform?",
            options=[
                {
                    "value": op.value,
                    "label": op.value.replace("_", " ").title(),
                    "description": self._get_operation_description(op),
                }
                for op in BulkOperationType
            ],
        )

        response = await self.elicitation.elicit(request)
        return BulkOperationType(response["value"])

    def _get_operation_description(self, op_type: BulkOperationType) -> str:
        """Get description for operation type"""
        descriptions = {
            BulkOperationType.SCHEMA_UPDATE: "Update compatibility settings, naming conventions, or metadata across multiple schemas",
            BulkOperationType.MIGRATION: "Move schemas between contexts or registries",
            BulkOperationType.CLEANUP: "Remove deprecated schemas, clean up test schemas, or purge old versions",
            BulkOperationType.CONFIGURATION: "Apply security policies, retention policies, or access controls",
        }
        return descriptions.get(op_type, "")

    async def _handle_bulk_schema_update(self) -> Dict[str, Any]:
        """Handle bulk schema update operations"""
        # Step 1: Select schemas
        schemas = await self._elicit_schema_selection("Select schemas to update", allow_patterns=True)

        # Step 2: Select update type
        update_type = await self._elicit_update_type()

        # Step 3: Get update parameters
        update_params = await self._elicit_update_parameters(update_type)

        # Step 4: Preview changes
        preview = await self._generate_preview(BulkOperationType.SCHEMA_UPDATE, schemas, update_params)

        # Step 5: Confirm operation
        if not await self._confirm_operation(preview):
            return {"status": "cancelled", "reason": "User cancelled operation"}

        # Step 6: Execute operation
        return await self._execute_bulk_operation(BulkOperationType.SCHEMA_UPDATE, schemas, update_params, preview)

    async def _handle_bulk_migration(self) -> Dict[str, Any]:
        """Handle bulk migration operations"""
        # Step 1: Select source and target
        source_target = await self._elicit_migration_source_target()

        # Step 2: Select schemas to migrate
        schemas = await self._elicit_schema_selection(
            "Select schemas to migrate", context=source_target["source_context"]
        )

        # Step 3: Migration options
        migration_options = await self._elicit_migration_options()

        # Step 4: Preview migration
        preview = await self._generate_preview(
            BulkOperationType.MIGRATION, schemas, {**source_target, **migration_options}
        )

        # Step 5: Confirm operation
        if not await self._confirm_operation(preview):
            return {"status": "cancelled", "reason": "User cancelled operation"}

        # Step 6: Execute migration
        return await self._execute_bulk_operation(
            BulkOperationType.MIGRATION, schemas, {**source_target, **migration_options}, preview
        )

    async def _handle_bulk_cleanup(self) -> Dict[str, Any]:
        """Handle bulk cleanup operations"""
        # Step 1: Select cleanup type
        cleanup_type = await self._elicit_cleanup_type()

        # Step 2: Select items to clean up
        items = await self._elicit_cleanup_items(cleanup_type)

        # Step 3: Cleanup options
        cleanup_options = await self._elicit_cleanup_options(cleanup_type)

        # Step 4: Preview cleanup
        preview = await self._generate_preview(
            BulkOperationType.CLEANUP, items, {"cleanup_type": cleanup_type, **cleanup_options}
        )

        # Step 5: Safety check for active consumers
        if preview.consumer_impact:
            action = await self._elicit_consumer_impact_action(preview.consumer_impact)
            if action == "cancel":
                return {"status": "cancelled", "reason": "Active consumers detected"}
            cleanup_options["consumer_action"] = action

        # Step 6: Confirm operation
        if not await self._confirm_operation(preview, extra_warnings=True):
            return {"status": "cancelled", "reason": "User cancelled operation"}

        # Step 7: Execute cleanup
        return await self._execute_bulk_operation(
            BulkOperationType.CLEANUP, items, {"cleanup_type": cleanup_type, **cleanup_options}, preview
        )

    async def _handle_bulk_configuration(self) -> Dict[str, Any]:
        """Handle bulk configuration operations"""
        # Step 1: Select configuration type
        config_type = await self._elicit_configuration_type()

        # Step 2: Select target schemas/contexts
        targets = await self._elicit_configuration_targets(config_type)

        # Step 3: Configuration parameters
        config_params = await self._elicit_configuration_parameters(config_type)

        # Step 4: Preview configuration changes
        preview = await self._generate_preview(
            BulkOperationType.CONFIGURATION, targets, {"config_type": config_type, **config_params}
        )

        # Step 5: Confirm operation
        if not await self._confirm_operation(preview):
            return {"status": "cancelled", "reason": "User cancelled operation"}

        # Step 6: Execute configuration
        return await self._execute_bulk_operation(
            BulkOperationType.CONFIGURATION, targets, {"config_type": config_type, **config_params}, preview
        )

    async def _elicit_schema_selection(
        self, prompt: str, context: Optional[str] = None, allow_patterns: bool = False
    ) -> List[str]:
        """Elicit schema selection from user"""
        # Get available schemas
        schemas = await self.registry.list_subjects(context=context)

        options = [{"value": s, "label": s} for s in schemas]

        if allow_patterns:
            options.extend(
                [
                    {"value": "test-*", "label": "All test schemas (test-*)"},
                    {"value": "deprecated-*", "label": "All deprecated schemas (deprecated-*)"},
                    {"value": "old-*", "label": "All old schemas (old-*)"},
                    {"value": "*", "label": "All schemas"},
                ]
            )

        request = ElicitationRequest(
            request_id=f"schema_selection_{datetime.now().timestamp()}",
            elicitation_type="multi_select",
            prompt=prompt,
            options=options,
            metadata={"max_selections": len(options)},
        )

        response = await self.elicitation.elicit(request)
        selected = response["values"]

        # Expand patterns if needed
        if allow_patterns:
            expanded = []
            for selection in selected:
                if "*" in selection:
                    pattern = selection.replace("*", "")
                    if selection == "*":
                        expanded.extend(schemas)
                    else:
                        expanded.extend([s for s in schemas if s.startswith(pattern)])
                else:
                    expanded.append(selection)
            return list(set(expanded))

        return selected

    async def _generate_preview(
        self, operation_type: BulkOperationType, items: List[Any], params: Dict[str, Any]
    ) -> BulkOperationPreview:
        """Generate preview of bulk operation"""
        # This is a simplified preview generation
        # In a real implementation, this would analyze the actual changes

        preview = BulkOperationPreview(
            affected_items=[{"name": item, "type": "schema"} for item in items],
            total_count=len(items),
            changes_summary={
                "operation": operation_type.value,
                "parameters": params,
                "estimated_api_calls": len(items) * 2,  # Rough estimate
            },
            estimated_duration=len(items) * 0.5,  # 0.5 seconds per item estimate
        )

        # Check for warnings
        if len(items) > 100:
            preview.warnings.append(f"Large batch size ({len(items)} items) may take significant time")

        if operation_type == BulkOperationType.CLEANUP:
            preview.warnings.append("This operation is destructive and cannot be undone")

        # Check consumer impact for relevant operations
        if operation_type in [BulkOperationType.CLEANUP, BulkOperationType.MIGRATION]:
            # In a real implementation, this would check actual consumer groups
            preview.consumer_impact = {
                "active_consumers": 3,
                "consumer_groups": ["group1", "group2", "group3"],
                "last_offset_commit": "5 minutes ago",
            }

        return preview

    async def _confirm_operation(self, preview: BulkOperationPreview, extra_warnings: bool = False) -> bool:
        """Confirm operation with user"""
        # Build confirmation message
        message_parts = [
            f"This operation will affect {preview.total_count} items.",
            f"Estimated duration: {preview.estimated_duration:.1f} seconds.",
        ]

        if preview.warnings:
            message_parts.append("\nWarnings:")
            for warning in preview.warnings:
                message_parts.append(f"  - {warning}")

        if preview.consumer_impact:
            message_parts.append(f"\nActive consumers detected: {preview.consumer_impact['active_consumers']}")

        message = "\n".join(message_parts)

        # Show preview details
        preview_request = ElicitationRequest(
            request_id=f"preview_{datetime.now().timestamp()}",
            elicitation_type="confirm",
            prompt=message + "\n\nWould you like to see a detailed preview?",
            metadata={"default": True},
        )

        show_preview = await self.elicitation.elicit(preview_request)

        if show_preview["confirmed"]:
            # Show detailed preview
            await self._show_detailed_preview(preview)

        # Final confirmation
        confirm_request = ElicitationRequest(
            request_id=f"confirm_operation_{datetime.now().timestamp()}",
            elicitation_type="confirm",
            prompt="Do you want to proceed with this operation?",
            metadata={"default": False, "require_explicit": extra_warnings},
        )

        response = await self.elicitation.elicit(confirm_request)
        return response["confirmed"]

    async def _show_detailed_preview(self, preview: BulkOperationPreview) -> None:
        """Show detailed preview to user"""
        # In a real implementation, this would format and display
        # the preview data in a user-friendly way
        details = {
            "affected_items": preview.affected_items[:10],  # Show first 10
            "total_shown": min(10, len(preview.affected_items)),
            "total_items": preview.total_count,
            "changes": preview.changes_summary,
        }

        await self.elicitation.show_info("Detailed Preview", json.dumps(details, indent=2))

    async def _execute_bulk_operation(
        self, operation_type: BulkOperationType, items: List[Any], params: Dict[str, Any], preview: BulkOperationPreview
    ) -> Dict[str, Any]:
        """Execute the bulk operation"""
        # Create task for tracking
        task_id = await self.task_manager.create_task(
            name=f"Bulk {operation_type.value}",
            total_items=len(items),
            metadata={"operation_type": operation_type.value, "parameters": params, "preview": preview.__dict__},
        )

        try:
            # Create backup if required
            if params.get("create_backup", True):
                await self._create_backup(items, operation_type)

            # Execute operation in batches
            batch_size = params.get("batch_size", 10)
            results = []

            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]

                # Update progress
                await self.task_manager.update_progress(
                    task_id, processed=i, message=f"Processing batch {i//batch_size + 1}"
                )

                # Process batch
                batch_result = await self._process_batch(operation_type, batch, params)
                results.append(batch_result)

                # Delay between batches
                if i + batch_size < len(items):
                    await asyncio.sleep(params.get("delay_between_batches", 1.0))

            # Complete task
            await self.task_manager.complete_task(
                task_id, result={"status": "success", "total_processed": len(items), "batch_results": results}
            )

            return {"status": "success", "task_id": task_id, "processed": len(items), "results": results}

        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")

            # Handle rollback if required
            if params.get("rollback_on_error", True):
                await self._rollback_operation(operation_type, items, params)

            await self.task_manager.fail_task(task_id, error=str(e))

            return {"status": "failed", "task_id": task_id, "error": str(e)}

    async def _create_backup(self, items: List[Any], operation_type: BulkOperationType) -> str:
        """Create backup before bulk operation"""
        # In a real implementation, this would create actual backups
        backup_id = f"backup_{operation_type.value}_{datetime.now().timestamp()}"
        logger.info(f"Created backup: {backup_id} for {len(items)} items")
        return backup_id

    async def _process_batch(
        self, operation_type: BulkOperationType, batch: List[Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single batch of items"""
        # This would be implemented based on the specific operation type
        # For now, return a mock result
        return {"batch_size": len(batch), "success": len(batch), "failed": 0, "errors": []}

    async def _rollback_operation(
        self, operation_type: BulkOperationType, items: List[Any], params: Dict[str, Any]
    ) -> None:
        """Rollback a failed operation"""
        logger.info(f"Rolling back {operation_type.value} operation for {len(items)} items")
        # Implementation would depend on operation type and backup strategy

    # Additional elicitation methods would be implemented here...
    async def _elicit_update_type(self) -> str:
        """Elicit the type of update to perform"""
        request = ElicitationRequest(
            request_id=f"update_type_{datetime.now().timestamp()}",
            elicitation_type="select",
            prompt="What would you like to update?",
            options=[
                {"value": "compatibility", "label": "Compatibility Settings"},
                {"value": "naming", "label": "Naming Conventions"},
                {"value": "metadata", "label": "Schema Metadata"},
            ],
        )
        response = await self.elicitation.elicit(request)
        return response["value"]

    async def _elicit_update_parameters(self, update_type: str) -> Dict[str, Any]:
        """Elicit parameters for the update"""
        # This would be expanded based on update type
        return {"update_type": update_type}

    async def _elicit_consumer_impact_action(self, impact: Dict[str, Any]) -> str:
        """Elicit action for consumer impact"""
        request = ElicitationRequest(
            request_id=f"consumer_action_{datetime.now().timestamp()}",
            elicitation_type="select",
            prompt=f"Active consumers detected ({impact['active_consumers']} consumers). How should we proceed?",
            options=[
                {"value": "wait", "label": "Wait for consumers to catch up"},
                {"value": "force", "label": "Force operation (may disrupt consumers)"},
                {"value": "skip", "label": "Skip schemas with active consumers"},
                {"value": "cancel", "label": "Cancel operation"},
            ],
        )
        response = await self.elicitation.elicit(request)
        return response["value"]


# Export the wizard class
__all__ = ["BulkOperationsWizard", "BulkOperationType", "BulkOperationConfig"]
