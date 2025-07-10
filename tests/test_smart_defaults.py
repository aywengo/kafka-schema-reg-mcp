"""
Unit tests for Smart Defaults functionality

Tests pattern recognition, learning engine, and elicitation integration.
"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from elicitation import ElicitationField, ElicitationRequest, ElicitationType
from smart_defaults import (
    FieldSuggestion,
    LearningEngine,
    PatternAnalyzer,
    SmartDefault,
    SmartDefaultsEngine,
    get_smart_defaults_engine,
)
from smart_defaults_integration import (
    EnhancedElicitationField,
    SmartDefaultsElicitationEnhancer,
    create_enhanced_migration_elicitation,
    create_enhanced_schema_field_elicitation,
)


class TestPatternAnalyzer:
    """Test the pattern analysis functionality"""

    def test_naming_convention_detection(self):
        """Test detection of various naming conventions"""
        analyzer = PatternAnalyzer()

        # Test hyphenated pattern
        subjects = ["user-events", "order-events", "payment-events", "inventory-updates"]
        patterns = analyzer.analyze_naming_convention(subjects, "production")

        assert "hyphenated" in patterns
        assert patterns["hyphenated"].confidence >= 0.75
        assert patterns["hyphenated"].occurrences == 4

        # Test event suffix pattern
        assert "event_suffixed" in patterns
        assert patterns["event_suffixed"].confidence >= 0.75

    def test_prefix_suffix_detection(self):
        """Test detection of common prefixes and suffixes"""
        analyzer = PatternAnalyzer()

        subjects = ["prod-user-service", "prod-order-service", "prod-payment-service", "dev-test-service"]
        patterns = analyzer.analyze_naming_convention(subjects, "mixed")

        # Should detect "prod-" prefix
        assert any(p.startswith("prefix:prod-") for p in patterns)

        # Should detect "-service" suffix
        assert any(p.startswith("suffix:-service") for p in patterns)

    def test_field_pattern_analysis(self):
        """Test analysis of common field patterns"""
        analyzer = PatternAnalyzer()

        schemas = [
            {
                "type": "record",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "userId", "type": "string"},
                ],
            },
            {
                "type": "record",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "amount", "type": "double"},
                ],
            },
        ]

        suggestions = analyzer.analyze_field_patterns(schemas)

        # Should detect common fields
        assert "id" in suggestions
        assert suggestions["id"][0].type == "string"
        assert suggestions["id"][0].confidence == 1.0  # Appears in all schemas

        assert "timestamp" in suggestions
        assert suggestions["timestamp"][0].type == "long"
        assert suggestions["timestamp"][0].confidence == 1.0


class TestLearningEngine:
    """Test the learning and feedback functionality"""

    def setup_method(self):
        """Create a temporary directory for test storage"""
        self.temp_dir = tempfile.mkdtemp()
        self.learning_engine = LearningEngine(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def test_record_and_retrieve_choice(self):
        """Test recording user choices and retrieving preferences"""
        # Record some choices
        self.learning_engine.record_choice(
            operation="create_schema", context="production", field="compatibility", value="BACKWARD", accepted=True
        )
        self.learning_engine.record_choice(
            operation="create_schema", context="production", field="compatibility", value="BACKWARD", accepted=True
        )
        self.learning_engine.record_choice(
            operation="create_schema", context="production", field="compatibility", value="FULL", accepted=False
        )

        # Retrieve preference
        preference = self.learning_engine.get_historical_preference("create_schema", "production", "compatibility")

        assert preference is not None
        assert preference.value == "BACKWARD"
        assert preference.confidence > 0.5
        assert preference.source == "history"

    def test_feedback_score_adjustment(self):
        """Test that feedback scores adjust based on acceptance"""
        # Record accepted choices
        for _ in range(5):
            self.learning_engine.record_choice(
                operation="migrate_schema", context="dev", field="dry_run", value=True, accepted=True
            )

        key = "migrate_schema:dev:dry_run"
        assert self.learning_engine.feedback_scores[key] > 0.5

        # Record rejected choices
        for _ in range(3):
            self.learning_engine.record_choice(
                operation="migrate_schema", context="dev", field="dry_run", value=True, accepted=False
            )

        assert self.learning_engine.feedback_scores[key] < 0.5

    def test_persistence(self):
        """Test that choices are persisted and can be reloaded"""
        # Record a choice
        self.learning_engine.record_choice(
            operation="create_context", context="test", field="environment", value="development", accepted=True
        )

        # Create new instance with same storage path
        new_engine = LearningEngine(Path(self.temp_dir))

        # Should load the persisted choice
        preference = new_engine.get_historical_preference("create_context", "test", "environment")

        assert preference is not None
        assert preference.value == "development"


class TestSmartDefaultsEngine:
    """Test the main smart defaults engine"""

    @pytest.mark.asyncio
    async def test_template_defaults(self):
        """Test that template-based defaults work correctly"""
        engine = SmartDefaultsEngine()

        defaults = await engine.suggest_defaults(operation="create_schema", context="production")

        # Should include template defaults
        assert "schema_type" in defaults
        assert defaults["schema_type"].value == "AVRO"
        assert defaults["schema_type"].source == "template"

        assert "compatibility" in defaults
        assert defaults["compatibility"].value == "FULL"  # Production context
        assert defaults["compatibility"].source == "template"

    @pytest.mark.asyncio
    async def test_context_specific_defaults(self):
        """Test context-specific default suggestions"""
        engine = SmartDefaultsEngine()

        # Development context
        dev_defaults = await engine.suggest_defaults(operation="create_schema", context="development")
        assert dev_defaults["compatibility"].value == "NONE"

        # Production context
        prod_defaults = await engine.suggest_defaults(operation="create_schema", context="production")
        assert prod_defaults["compatibility"].value == "FULL"

    @pytest.mark.asyncio
    async def test_existing_data_override(self):
        """Test that existing data overrides suggestions"""
        engine = SmartDefaultsEngine()

        defaults = await engine.suggest_defaults(
            operation="create_schema", context="production", existing_data={"compatibility": "BACKWARD"}
        )

        assert defaults["compatibility"].value == "BACKWARD"
        assert defaults["compatibility"].source == "provided"
        assert defaults["compatibility"].confidence == 1.0

    def test_field_suggestions_by_type(self):
        """Test common field suggestions for different record types"""
        engine = SmartDefaultsEngine()

        # Event type suggestions
        event_fields = engine.get_field_suggestions("event")
        field_names = [f.name for f in event_fields]
        assert "id" in field_names
        assert "timestamp" in field_names
        assert "eventType" in field_names

        # Entity type suggestions
        entity_fields = engine.get_field_suggestions("entity")
        field_names = [f.name for f in entity_fields]
        assert "createdAt" in field_names
        assert "updatedAt" in field_names


class TestSmartDefaultsIntegration:
    """Test integration with elicitation system"""

    @pytest.mark.asyncio
    async def test_enhance_elicitation_request(self):
        """Test that elicitation requests are properly enhanced"""
        enhancer = SmartDefaultsElicitationEnhancer()

        # Create a basic elicitation request
        request = ElicitationRequest(
            type=ElicitationType.FORM,
            title="Test Form",
            fields=[
                ElicitationField(name="compatibility", type="choice", options=["BACKWARD", "FORWARD", "FULL", "NONE"]),
                ElicitationField(name="schema_type", type="choice", options=["AVRO", "JSON", "PROTOBUF"]),
            ],
        )

        # Enhance it
        enhanced = await enhancer.enhance_elicitation_request(
            request=request, operation="create_schema", context="production"
        )

        # Check enhancements
        assert "smart_defaults_enabled" in enhanced.context
        assert enhanced.context["smart_defaults_enabled"] is True

        # Check field enhancements
        for field in enhanced.fields:
            if isinstance(field, EnhancedElicitationField):
                if field.name == "compatibility":
                    assert field.suggested_value is not None
                    assert field.suggestion_confidence is not None
                    assert field.suggestion_source is not None
                elif field.name == "schema_type":
                    assert field.suggested_value == "AVRO"

    @pytest.mark.asyncio
    async def test_feedback_processing(self):
        """Test that user feedback is processed correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = SmartDefaultsEngine()
            engine.learning_engine = LearningEngine(Path(temp_dir))
            enhancer = SmartDefaultsElicitationEnhancer()
            enhancer.smart_defaults_engine = engine

            # Create enhanced request
            request = ElicitationRequest(
                type=ElicitationType.FORM, title="Test", fields=[ElicitationField(name="test_field", type="text")]
            )

            enhanced = await enhancer.enhance_elicitation_request(
                request=request, operation="test_op", context="test_ctx"
            )

            # Simulate user response
            from elicitation import ElicitationResponse

            response = ElicitationResponse(request_id=enhanced.id, values={"test_field": "user_value"})

            # Process feedback
            await enhancer.process_response_feedback(
                response=response, request=enhanced, operation="test_op", context="test_ctx"
            )

            # Check that choice was recorded
            key = "test_op:test_ctx:test_field"
            assert key in engine.learning_engine.user_choices
            assert len(engine.learning_engine.user_choices[key]) == 1


class TestEnhancedElicitationFunctions:
    """Test the enhanced elicitation creation functions"""

    @pytest.mark.asyncio
    async def test_enhanced_schema_field_elicitation(self):
        """Test enhanced schema field elicitation with suggestions"""
        enhancer = SmartDefaultsElicitationEnhancer()

        request = await create_enhanced_schema_field_elicitation(
            enhancer=enhancer, context="production", record_type="event"
        )

        assert request.title.endswith("smart suggestions)")
        assert request.context.get("smart_defaults_enabled") is True

        # Should have field suggestions for event type
        assert "_field_suggestions" in request.context or "field_suggestions" in request.context

    @pytest.mark.asyncio
    async def test_enhanced_migration_elicitation(self):
        """Test enhanced migration preferences elicitation"""
        enhancer = SmartDefaultsElicitationEnhancer()

        # Simulate previous migrations
        previous_migrations = [
            {"preserve_ids": True, "dry_run": True, "migrate_all_versions": False},
            {"preserve_ids": True, "dry_run": False, "migrate_all_versions": False},
        ]

        request = await create_enhanced_migration_elicitation(
            enhancer=enhancer,
            source_registry="dev",
            target_registry="prod",
            context="orders",
            previous_migrations=previous_migrations,
        )

        # Should analyze previous migrations
        assert request.context.get("smart_defaults_enabled") is True

        # Check that fields have suggestions based on history
        preserve_ids_field = next((f for f in request.fields if f.name == "preserve_ids"), None)
        if preserve_ids_field and hasattr(preserve_ids_field, "suggested_value"):
            assert preserve_ids_field.suggested_value is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
