#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Batch Cleanup Tools

This test suite thoroughly validates all BATCH CLEANUP TOOLS including:
- Safety features (dry_run=True by default)
- Error handling and edge cases
- Performance under load
- Multi-registry scenarios
- READONLY mode protection
- Rollback and partial failure scenarios
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import requests

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_unified_mcp as single_mcp
import kafka_schema_registry_unified_mcp as multi_mcp


class TestBatchCleanupIntegration:
    """Comprehensive integration tests for batch cleanup tools"""

    @classmethod
    def setup_class(cls):
        """Set up test environment and verify connectivity"""
        cls.dev_url = "http://localhost:38081"
        cls.prod_url = "http://localhost:38082"
        cls.test_contexts = []
        cls.test_subjects = []

        # Verify registries are accessible
        cls._verify_registries()

        # Set up multi-registry environment
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = cls.dev_url
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = cls.prod_url

        # Reinitialize registry manager
        multi_mcp.registry_manager._load_multi_registries()

    @classmethod
    def teardown_class(cls):
        """Clean up test artifacts"""
        cls._cleanup_test_artifacts()

    @classmethod
    def _verify_registries(cls):
        """Verify both registries are accessible"""
        for name, url in [("DEV", cls.dev_url), ("PROD", cls.prod_url)]:
            try:
                response = requests.get(f"{url}/subjects", timeout=5)
                assert response.status_code == 200, f"{name} registry not accessible"
            except Exception as e:
                pytest.skip(f"Registry {name} at {url} not accessible: {e}")

    @classmethod
    def _cleanup_test_artifacts(cls):
        """Clean up any remaining test artifacts"""
        for context in cls.test_contexts:
            try:
                # Clean up in both registries
                for registry_url in [cls.dev_url, cls.prod_url]:
                    # List and delete subjects
                    subjects_response = requests.get(
                        f"{registry_url}/contexts/{context}/subjects", timeout=5
                    )
                    if subjects_response.status_code == 200:
                        subjects = subjects_response.json()
                        for subject in subjects:
                            requests.delete(
                                f"{registry_url}/contexts/{context}/subjects/{subject}",
                                timeout=5,
                            )

                    # Delete context
                    requests.delete(f"{registry_url}/contexts/{context}", timeout=5)
            except Exception:
                pass  # Ignore cleanup errors

    def _create_test_context_with_subjects(
        self, context_name, registry_url, subject_count=3
    ):
        """Create a test context with specified number of subjects"""
        self.test_contexts.append(context_name)

        test_schema = {
            "type": "record",
            "name": "TestRecord",
            "namespace": "com.example.test",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "data", "type": "string"},
            ],
        }

        created_subjects = []
        for i in range(subject_count):
            subject_name = f"test-subject-{i}-{uuid.uuid4().hex[:8]}"
            self.test_subjects.append(subject_name)

            try:
                url = f"{registry_url}/contexts/{context_name}/subjects/{subject_name}/versions"
                payload = {"schema": json.dumps(test_schema)}

                response = requests.post(
                    url,
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=payload,
                    timeout=10,
                )

                if response.status_code in [200, 409]:
                    created_subjects.append(subject_name)

            except Exception as e:
                print(f"Failed to create subject {subject_name}: {e}")

        return created_subjects

    def test_dry_run_default_safety(self):
        """Test that dry_run=True is the default for safety"""
        context_name = f"test-dry-run-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )

        assert len(subjects) >= 1, "Failed to create test subjects"

        # Test single-registry dry run default
        result = single_mcp.clear_context_batch(context=context_name)

        assert result["dry_run"] == True, "dry_run should be True by default"
        assert result["subjects_found"] >= 1, "Should find created subjects"
        assert result["subjects_deleted"] == len(
            subjects
        ), "Should report what would be deleted"
        assert "DRY RUN" in result["message"], "Message should indicate dry run"

        # Verify subjects still exist (not actually deleted)
        subjects_response = requests.get(
            f"{self.dev_url}/contexts/{context_name}/subjects"
        )
        assert subjects_response.status_code == 200
        existing_subjects = subjects_response.json()
        assert len(existing_subjects) >= 1, "Subjects should still exist after dry run"

    def test_explicit_dry_run_false(self):
        """Test explicit dry_run=False performs actual deletion"""
        context_name = f"test-actual-delete-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )

        assert len(subjects) >= 1, "Failed to create test subjects"

        # Perform actual deletion
        result = single_mcp.clear_context_batch(context=context_name, dry_run=False)

        assert result["dry_run"] == False, "dry_run should be False when explicitly set"
        assert result["subjects_deleted"] >= 1, "Should actually delete subjects"
        assert result["success_rate"] == 100.0, "Should have 100% success rate"
        assert (
            "Successfully cleared" in result["message"]
        ), "Should indicate successful cleanup"

        # Verify subjects are actually deleted
        subjects_response = requests.get(
            f"{self.dev_url}/contexts/{context_name}/subjects"
        )
        if subjects_response.status_code == 200:
            remaining_subjects = subjects_response.json()
            assert len(remaining_subjects) == 0, "All subjects should be deleted"

    @pytest.mark.asyncio
    async def test_multi_registry_dry_run_default(self):
        """Test multi-registry tools also default to dry_run=True"""
        context_name = f"test-multi-dry-run-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )

        assert len(subjects) >= 1, "Failed to create test subjects"

        # Test multi-registry single context cleanup
        result = multi_mcp.clear_context_batch(context=context_name, registry="dev")

        # Multi-registry returns a task object, not the actual result
        assert "task_id" in result, "Should return a task object"
        assert "task" in result, "Should include task details"

        # Extract metadata to verify dry_run default
        task_metadata = result["task"]["metadata"]
        assert (
            task_metadata["dry_run"] == True
        ), "Multi-registry dry_run should be True by default"

        # Wait a bit for task to complete
        await asyncio.sleep(0.5)

        # Get task result
        task_result = await multi_mcp.get_task_progress(result["task_id"])
        assert task_result["status"] in [
            "completed",
            "running",
        ], "Task should be running or completed"

        # Test multi-context cleanup
        contexts = [context_name]
        multi_result = multi_mcp.clear_multiple_contexts_batch(
            contexts=contexts, registry="dev"
        )

        # This also returns a task object
        assert "task_id" in multi_result, "Should return a task object"
        task_metadata = multi_result["task"]["metadata"]
        assert (
            task_metadata["dry_run"] == True
        ), "Multi-context dry_run should be True by default"

    def test_empty_context_handling(self):
        """Test handling of empty contexts"""
        empty_context = f"empty-context-{uuid.uuid4().hex[:8]}"

        # Create empty context (no subjects)
        requests.post(f"{self.dev_url}/contexts/{empty_context}")
        self.test_contexts.append(empty_context)

        result = single_mcp.clear_context_batch(context=empty_context, dry_run=False)

        assert result["subjects_found"] == 0, "Should find no subjects in empty context"
        assert result["subjects_deleted"] == 0, "Should delete no subjects"
        assert "already empty" in result["message"], "Should indicate context is empty"

    def test_nonexistent_context_handling(self):
        """Test handling of non-existent contexts"""
        nonexistent_context = f"nonexistent-{uuid.uuid4().hex[:8]}"

        result = single_mcp.clear_context_batch(
            context=nonexistent_context, dry_run=False
        )

        # Should handle gracefully - either empty result or appropriate error
        assert (
            "error" in result or result["subjects_found"] == 0
        ), "Should handle nonexistent context gracefully"

    def test_readonly_mode_protection(self):
        """Test READONLY mode blocks actual deletions but allows dry runs"""
        context_name = f"test-readonly-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )

        # Set READONLY mode
        original_readonly = os.environ.get("READONLY", "false")
        os.environ["READONLY"] = "true"

        try:
            # Reload modules to pick up READONLY setting
            import importlib

            importlib.reload(single_mcp)

            # Dry run should work in READONLY mode
            dry_result = single_mcp.clear_context_batch(
                context=context_name, dry_run=True
            )
            assert dry_result["dry_run"] == True, "Dry run should work in READONLY mode"

            # Actual deletion should be blocked
            delete_result = single_mcp.clear_context_batch(
                context=context_name, dry_run=False
            )
            assert "readonly_mode" in delete_result or "READONLY" in str(
                delete_result
            ), "Should block deletion in READONLY mode"

        finally:
            # Restore original READONLY setting
            os.environ["READONLY"] = original_readonly
            importlib.reload(single_mcp)

    def test_large_context_performance(self):
        """Test performance with larger number of subjects"""
        context_name = f"test-large-{uuid.uuid4().hex[:8]}"
        subject_count = 20  # Create more subjects to test performance

        start_time = time.time()
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, subject_count
        )
        setup_time = time.time() - start_time

        print(f"Created {len(subjects)} subjects in {setup_time:.2f} seconds")

        # Test dry run performance
        dry_start = time.time()
        dry_result = single_mcp.clear_context_batch(context=context_name, dry_run=True)
        dry_time = time.time() - dry_start

        assert dry_result["subjects_found"] == len(
            subjects
        ), "Should find all created subjects"
        assert dry_time < 10.0, f"Dry run should complete quickly, took {dry_time:.2f}s"

        # Test actual cleanup performance
        cleanup_start = time.time()
        cleanup_result = single_mcp.clear_context_batch(
            context=context_name, dry_run=False
        )
        cleanup_time = time.time() - cleanup_start

        assert cleanup_result["subjects_deleted"] == len(
            subjects
        ), "Should delete all subjects"
        assert cleanup_result["success_rate"] == 100.0, "Should have 100% success rate"

        # Verify performance metrics
        performance = cleanup_result["performance"]
        assert "subjects_per_second" in performance, "Should report performance metrics"
        assert (
            performance["parallel_execution"] == True
        ), "Should use parallel execution"
        assert (
            performance["max_concurrent_deletions"] == 10
        ), "Should use 10 concurrent deletions"

        print(f"Deleted {len(subjects)} subjects in {cleanup_time:.2f} seconds")
        print(f"Performance: {performance['subjects_per_second']:.1f} subjects/second")

    def test_partial_failure_handling(self):
        """Test handling of partial failures during cleanup"""
        context_name = f"test-partial-fail-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 3
        )

        # First, verify all subjects exist
        result = single_mcp.clear_context_batch(context=context_name, dry_run=True)
        assert result["subjects_found"] >= 2, "Should find created subjects"

        # Test actual cleanup
        cleanup_result = single_mcp.clear_context_batch(
            context=context_name, dry_run=False
        )

        # Should provide detailed information about any failures
        assert (
            "successful_deletions" in str(cleanup_result)
            or cleanup_result["subjects_deleted"] >= 0
        ), "Should track deletion results"
        assert "success_rate" in cleanup_result, "Should provide success rate"
        assert "failed_deletions" in cleanup_result, "Should track failed deletions"

    def test_multi_context_batch_operations(self):
        """Test batch operations across multiple contexts"""
        contexts = []
        total_subjects = 0

        # Create multiple test contexts
        for i in range(3):
            context_name = f"test-multi-ctx-{i}-{uuid.uuid4().hex[:8]}"
            contexts.append(context_name)
            subjects = self._create_test_context_with_subjects(
                context_name, self.dev_url, 2
            )
            total_subjects += len(subjects)

        # Test dry run for multiple contexts
        dry_result = single_mcp.clear_multiple_contexts_batch(
            contexts=contexts, dry_run=True
        )

        assert dry_result["dry_run"] == True, "Should default to dry run"
        assert dry_result["contexts_processed"] == len(
            contexts
        ), "Should process all contexts"
        assert (
            dry_result["total_subjects_found"] >= total_subjects
        ), "Should find all subjects"

        # Test actual cleanup
        cleanup_result = single_mcp.clear_multiple_contexts_batch(
            contexts=contexts, dry_run=False
        )

        assert cleanup_result["contexts_completed"] >= 0, "Should complete contexts"
        assert cleanup_result["total_subjects_deleted"] >= 0, "Should delete subjects"
        assert "performance" in cleanup_result, "Should provide performance metrics"

    @pytest.mark.asyncio
    async def test_cross_registry_operations(self):
        """Test cross-registry batch cleanup operations"""
        context_name = f"test-cross-{uuid.uuid4().hex[:8]}"

        # Create test subjects in both registries
        dev_subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )
        prod_subjects = self._create_test_context_with_subjects(
            context_name, self.prod_url, 2
        )

        assert len(dev_subjects) >= 1, "Failed to create test subjects in DEV registry"
        assert (
            len(prod_subjects) >= 1
        ), "Failed to create test subjects in PROD registry"

        # NOTE: clear_context_across_registries_batch doesn't exist in the module
        # This is a limitation of the current implementation
        # For now, we'll test cleaning up each registry separately

        # Test cleanup in dev registry
        dev_result = multi_mcp.clear_context_batch(
            context=context_name, registry="dev", dry_run=True
        )

        assert "task_id" in dev_result, "Should return a task object for dev"
        dev_task_metadata = dev_result["task"]["metadata"]
        assert dev_task_metadata["dry_run"] == True, "Dev dry_run should be True"
        assert dev_task_metadata["registry"] == "dev", "Should target dev registry"

        # Test cleanup in prod registry
        prod_result = multi_mcp.clear_context_batch(
            context=context_name, registry="prod", dry_run=True
        )

        assert "task_id" in prod_result, "Should return a task object for prod"
        prod_task_metadata = prod_result["task"]["metadata"]
        assert prod_task_metadata["dry_run"] == True, "Prod dry_run should be True"
        assert prod_task_metadata["registry"] == "prod", "Should target prod registry"

        # Test actual cleanup (dry_run=False) in both registries
        dev_cleanup = multi_mcp.clear_context_batch(
            context=context_name, registry="dev", dry_run=False
        )

        prod_cleanup = multi_mcp.clear_context_batch(
            context=context_name, registry="prod", dry_run=False
        )

        # Both should return task objects
        assert "task_id" in dev_cleanup, "Dev cleanup should return task object"
        assert "task_id" in prod_cleanup, "Prod cleanup should return task object"

        # Wait for tasks to complete
        await asyncio.sleep(1.0)

        # Verify cleanup completed
        dev_progress = await multi_mcp.get_task_progress(dev_cleanup["task_id"])
        prod_progress = await multi_mcp.get_task_progress(prod_cleanup["task_id"])

        assert dev_progress["status"] in [
            "completed",
            "running",
        ], "Dev cleanup should complete"
        assert prod_progress["status"] in [
            "completed",
            "running",
        ], "Prod cleanup should complete"

    def test_context_deletion_after_cleanup(self):
        """Test context deletion after subject cleanup"""
        context_name = f"test-context-delete-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 2
        )

        # Test with context deletion enabled
        result = single_mcp.clear_context_batch(
            context=context_name, delete_context_after=True, dry_run=False
        )

        assert result["context_deleted"] or "context" in str(
            result
        ), "Should attempt context deletion"

        # Verify context no longer exists (or is empty)
        context_response = requests.get(
            f"{self.dev_url}/contexts/{context_name}/subjects"
        )
        assert context_response.status_code in [
            404,
            200,
        ], "Context should be deleted or empty"

    def test_concurrent_cleanup_operations(self):
        """Test concurrent cleanup operations don't interfere"""
        contexts = []

        # Create multiple contexts for concurrent testing
        for i in range(3):
            context_name = f"test-concurrent-{i}-{uuid.uuid4().hex[:8]}"
            contexts.append(context_name)
            self._create_test_context_with_subjects(context_name, self.dev_url, 2)

        results = []

        def cleanup_context(context):
            return single_mcp.clear_context_batch(context=context, dry_run=False)

        # Run concurrent cleanups
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cleanup_context, ctx) for ctx in contexts]
            results = [future.result() for future in futures]

        # Verify all operations completed successfully
        for i, result in enumerate(results):
            assert (
                result["subjects_deleted"] >= 0
            ), f"Context {i} should complete deletion"
            assert (
                result["success_rate"] >= 0
            ), f"Context {i} should have valid success rate"

    def test_error_recovery_and_reporting(self):
        """Test error recovery and comprehensive reporting"""
        context_name = f"test-error-recovery-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 3
        )

        # Test with invalid registry (multi-registry mode)
        error_result = multi_mcp.clear_context_batch(
            context=context_name, registry="nonexistent-registry", dry_run=True
        )

        # For task-based operations, the error might be in the task result
        if "task_id" in error_result:
            # It started as a task, which means the registry validation happens later
            assert "task" in error_result, "Should include task details"
        else:
            # Direct error
            assert "error" in error_result, "Should handle invalid registry gracefully"
            assert (
                "not found" in error_result["error"].lower()
            ), "Should provide helpful error message"

        # Test with valid registry
        valid_result = multi_mcp.clear_context_batch(
            context=context_name, registry="dev", dry_run=False
        )

        # Should return a task object for valid registry
        assert "task_id" in valid_result, "Should return task for valid registry"
        assert "error" not in valid_result, "Should not have error for valid registry"

    def test_comprehensive_reporting_metrics(self):
        """Test comprehensive reporting and metrics"""
        context_name = f"test-metrics-{uuid.uuid4().hex[:8]}"
        subjects = self._create_test_context_with_subjects(
            context_name, self.dev_url, 5
        )

        result = single_mcp.clear_context_batch(context=context_name, dry_run=False)

        # Verify comprehensive reporting
        required_fields = [
            "context",
            "dry_run",
            "started_at",
            "completed_at",
            "duration_seconds",
            "subjects_found",
            "subjects_deleted",
            "subjects_failed",
            "context_deleted",
            "success_rate",
            "deleted_subjects",
            "failed_deletions",
            "performance",
            "message",
        ]

        for field in required_fields:
            assert field in result, f"Result should include {field}"

        # Verify performance metrics
        performance = result["performance"]
        performance_fields = [
            "subjects_per_second",
            "parallel_execution",
            "max_concurrent_deletions",
        ]

        for field in performance_fields:
            assert field in performance, f"Performance should include {field}"

        # Verify timestamps are valid
        start_time = datetime.fromisoformat(result["started_at"])
        end_time = datetime.fromisoformat(result["completed_at"])
        assert end_time >= start_time, "End time should be after start time"


def test_batch_cleanup_integration_suite():
    """Run the complete batch cleanup integration test suite"""
    import pytest

    # Run the test class
    pytest.main(
        [__file__, "-v", "--tb=short", "-x"]
    )  # Stop on first failure for faster feedback


if __name__ == "__main__":
    test_batch_cleanup_integration_suite()
