"""
Smart Defaults Integration with Elicitation System

This module integrates the Smart Defaults Engine with the MCP elicitation system,
enhancing elicitation forms with intelligent suggestions based on patterns and history.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Dict, List, Optional, Tuple

from elicitation import (
    ElicitationField,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationType,
    create_context_metadata_elicitation,
    create_export_preferences_elicitation,
    create_migration_preferences_elicitation,
    create_schema_field_elicitation,
)
from schema_registry_common import BaseRegistryManager
from smart_defaults import (
    FieldSuggestion,
    SmartDefault,
    SmartDefaultsEngine,
    get_smart_defaults_engine,
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedElicitationField(ElicitationField):
    """Extended ElicitationField with smart default support"""

    suggested_value: Optional[Any] = None
    suggestion_confidence: Optional[float] = None
    suggestion_source: Optional[str] = None
    suggestion_reasoning: Optional[str] = None
    allow_rejection: bool = True


class SmartDefaultsElicitationEnhancer:
    """Enhances elicitation requests with smart defaults"""

    def __init__(self, registry_manager: Optional[BaseRegistryManager] = None):
        self.smart_defaults_engine = get_smart_defaults_engine(registry_manager)
        self.registry_manager = registry_manager

    async def enhance_elicitation_request(
        self,
        request: ElicitationRequest,
        operation: str,
        context: Optional[str] = None,
        existing_data: Optional[Dict[str, Any]] = None,
    ) -> ElicitationRequest:
        """Enhance an elicitation request with smart defaults"""

        # Get smart defaults for this operation
        defaults = await self.smart_defaults_engine.suggest_defaults(
            operation=operation, context=context, existing_data=existing_data
        )

        # Enhance fields with suggestions
        enhanced_fields = []
        for field in request.fields:
            enhanced_field = self._enhance_field_with_defaults(field, defaults)
            enhanced_fields.append(enhanced_field)

        # Add field suggestions for schema creation
        if operation in ["create_schema", "create_schema_field"] and "_field_suggestions" in defaults:
            field_suggestions = defaults["_field_suggestions"]
            self._add_field_suggestion_metadata(request, field_suggestions)

        # Update request fields
        request.fields = enhanced_fields

        # Add smart defaults metadata to context
        if request.context is None:
            request.context = {}
        request.context["smart_defaults_enabled"] = True
        request.context["suggestion_count"] = len([d for d in defaults.values() if isinstance(d, SmartDefault)])

        # Enhance title and description
        request.title = self._enhance_title(request.title, defaults)
        request.description = self._enhance_description(request.description, defaults)

        return request

    def _enhance_field_with_defaults(
        self, field: ElicitationField, defaults: Dict[str, SmartDefault]
    ) -> ElicitationField:
        """Enhance a single field with smart default suggestion"""

        if field.name in defaults:
            smart_default = defaults[field.name]

            # Create enhanced field
            enhanced = EnhancedElicitationField(
                name=field.name,
                type=field.type,
                label=field.label,
                description=field.description,
                required=field.required,
                default=field.default,
                options=field.options,
                validation=field.validation,
                placeholder=field.placeholder,
                suggested_value=smart_default.value,
                suggestion_confidence=smart_default.confidence,
                suggestion_source=smart_default.source,
                suggestion_reasoning=smart_default.reasoning,
            )

            # Update default value with suggestion if confidence is high
            if smart_default.confidence >= 0.7:
                enhanced.default = smart_default.value

            # Enhance description with suggestion info
            if enhanced.description:
                enhanced.description += (
                    f" (Suggested: {smart_default.value} - {int(smart_default.confidence * 100)}% confidence)"
                )
            else:
                enhanced.description = (
                    f"Suggested: {smart_default.value} - {int(smart_default.confidence * 100)}% confidence"
                )

            # Update placeholder with suggestion if no default
            if not enhanced.default and enhanced.placeholder:
                enhanced.placeholder = f"{enhanced.placeholder} (suggestion: {smart_default.value})"

            return enhanced

        return field

    def _enhance_title(self, title: str, defaults: Dict[str, SmartDefault]) -> str:
        """Enhance request title with smart defaults info"""
        suggestion_count = len([d for d in defaults.values() if isinstance(d, SmartDefault)])
        if suggestion_count > 0:
            return f"{title} (with {suggestion_count} smart suggestions)"
        return title

    def _enhance_description(self, description: Optional[str], defaults: Dict[str, SmartDefault]) -> Optional[str]:
        """Enhance request description with smart defaults summary"""
        high_confidence_count = len(
            [d for d in defaults.values() if isinstance(d, SmartDefault) and d.confidence >= 0.7]
        )

        if high_confidence_count > 0:
            suffix = f"\n\n💡 Smart Defaults: {high_confidence_count} high-confidence suggestions based on patterns and history."
            if description:
                return description + suffix
            else:
                return suffix.strip()

        return description

    def _add_field_suggestion_metadata(
        self, request: ElicitationRequest, field_suggestions: Dict[str, List[FieldSuggestion]]
    ):
        """Add field suggestion metadata to request context"""
        if not request.context:
            request.context = {}

        # Convert field suggestions to simple format
        suggestions_list = []
        for field_name, suggestions in field_suggestions.items():
            for suggestion in suggestions:
                suggestions_list.append(
                    {
                        "field": suggestion.name,
                        "type": suggestion.type,
                        "confidence": suggestion.confidence,
                        "default": suggestion.default_value,
                        "metadata": suggestion.metadata,
                    }
                )

        # Sort by confidence
        suggestions_list.sort(key=lambda x: x["confidence"], reverse=True)

        # Add to context
        request.context["field_suggestions"] = suggestions_list[:10]  # Top 10 suggestions

    async def process_response_feedback(
        self, response: ElicitationResponse, request: ElicitationRequest, operation: str, context: Optional[str] = None
    ):
        """Process user feedback from elicitation response"""

        if not request.context or not request.context.get("smart_defaults_enabled"):
            return

        # Find enhanced fields with suggestions
        for field in request.fields:
            if isinstance(field, EnhancedElicitationField) and field.suggested_value is not None:
                user_value = response.values.get(field.name)
                suggested_value = field.suggested_value

                # Determine if user accepted the suggestion
                accepted = user_value == suggested_value

                # Record the choice
                self.smart_defaults_engine.record_user_choice(
                    operation=operation,
                    context=context or "global",
                    field=field.name,
                    value=user_value,
                    accepted=accepted,
                )

                if accepted:
                    logger.debug(
                        f"User accepted suggestion for {field.name}: {suggested_value} "
                        f"(confidence: {field.suggestion_confidence})"
                    )
                else:
                    logger.debug(
                        f"User rejected suggestion for {field.name}. "
                        f"Suggested: {suggested_value}, Chose: {user_value}"
                    )
            else:
                # For regular fields in smart defaults-enabled requests, record user choices
                user_value = response.values.get(field.name)
                if user_value is not None:
                    # Record the choice without suggestion comparison
                    self.smart_defaults_engine.record_user_choice(
                        operation=operation,
                        context=context or "global",
                        field=field.name,
                        value=user_value,
                        accepted=True,  # No suggestion to compare against
                    )


# Enhanced elicitation creation functions with smart defaults


async def create_enhanced_schema_field_elicitation(
    enhancer: SmartDefaultsElicitationEnhancer,
    context: Optional[str] = None,
    existing_fields: Optional[List[str]] = None,
    record_type: Optional[str] = None,
) -> ElicitationRequest:
    """Create an enhanced schema field elicitation with smart defaults"""

    # Create base request
    request = create_schema_field_elicitation(context, existing_fields)

    # Get field suggestions if record type is known
    existing_data = {}
    if record_type:
        existing_data["record_type"] = record_type

        # Get common field suggestions
        field_suggestions = enhancer.smart_defaults_engine.get_field_suggestions(record_type)
        if field_suggestions:
            # Add suggested fields to options
            field_names = [fs.name for fs in field_suggestions[:5]]  # Top 5
            existing_data["suggested_field_names"] = field_names

    # Enhance with smart defaults
    enhanced_request = await enhancer.enhance_elicitation_request(
        request=request, operation="create_schema_field", context=context, existing_data=existing_data
    )

    return enhanced_request


async def create_enhanced_migration_elicitation(
    enhancer: SmartDefaultsElicitationEnhancer,
    source_registry: str,
    target_registry: str,
    context: Optional[str] = None,
    previous_migrations: Optional[List[Dict[str, Any]]] = None,
) -> ElicitationRequest:
    """Create an enhanced migration preferences elicitation"""

    # Create base request
    request = create_migration_preferences_elicitation(source_registry, target_registry, context)

    # Add previous migration data if available
    existing_data = {}
    if previous_migrations:
        # Analyze previous migrations for patterns
        existing_data["previous_migration_count"] = len(previous_migrations)
        existing_data["common_settings"] = _analyze_migration_patterns(previous_migrations)

    # Enhance with smart defaults
    enhanced_request = await enhancer.enhance_elicitation_request(
        request=request, operation="migrate_schema", context=context, existing_data=existing_data
    )

    return enhanced_request


async def create_enhanced_context_metadata_elicitation(
    enhancer: SmartDefaultsElicitationEnhancer, context_name: str, similar_contexts: Optional[List[str]] = None
) -> ElicitationRequest:
    """Create an enhanced context metadata elicitation"""

    # Create base request
    request = create_context_metadata_elicitation(context_name)

    # Analyze context name for environment hints
    existing_data = {}
    context_lower = context_name.lower()
    if "prod" in context_lower:
        existing_data["detected_environment"] = "production"
    elif "staging" in context_lower or "stage" in context_lower:
        existing_data["detected_environment"] = "staging"
    elif "dev" in context_lower:
        existing_data["detected_environment"] = "development"
    elif "test" in context_lower:
        existing_data["detected_environment"] = "testing"

    # Add similar context data
    if similar_contexts:
        existing_data["similar_contexts"] = similar_contexts[:3]  # Top 3

    # Enhance with smart defaults
    enhanced_request = await enhancer.enhance_elicitation_request(
        request=request, operation="create_context", context=context_name, existing_data=existing_data
    )

    return enhanced_request


async def create_enhanced_export_elicitation(
    enhancer: SmartDefaultsElicitationEnhancer,
    operation_type: str,
    context: Optional[str] = None,
    previous_exports: Optional[List[Dict[str, Any]]] = None,
) -> ElicitationRequest:
    """Create an enhanced export preferences elicitation"""

    # Create base request
    request = create_export_preferences_elicitation(operation_type)

    # Analyze previous exports
    existing_data = {}
    if previous_exports:
        # Find most common export settings
        format_counts = {}
        compression_counts = {}

        for export in previous_exports:
            fmt = export.get("format", "json")
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

            comp = export.get("compression", "none")
            compression_counts[comp] = compression_counts.get(comp, 0) + 1

        # Set most common as suggestions
        if format_counts:
            most_common_format = max(format_counts, key=format_counts.get)
            existing_data["preferred_format"] = most_common_format

        if compression_counts:
            most_common_compression = max(compression_counts, key=compression_counts.get)
            existing_data["preferred_compression"] = most_common_compression

    # Enhance with smart defaults
    # Normalize operation name to avoid double "export" prefix
    operation_name = operation_type if operation_type.startswith("export_") else f"export_{operation_type}"
    enhanced_request = await enhancer.enhance_elicitation_request(
        request=request, operation=operation_name, context=context, existing_data=existing_data
    )

    return enhanced_request


def _analyze_migration_patterns(migrations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze migration patterns to find common settings"""
    patterns = {
        "preserve_ids": True,  # Count how often IDs are preserved
        "dry_run": True,  # Count how often dry run is used
        "migrate_all_versions": False,  # Count how often all versions are migrated
    }

    # Count occurrences
    preserve_count = sum(1 for m in migrations if m.get("preserve_ids", True))
    dry_run_count = sum(1 for m in migrations if m.get("dry_run", True))
    all_versions_count = sum(1 for m in migrations if m.get("migrate_all_versions", False))

    total = len(migrations)
    if total > 0:
        # Set based on majority
        patterns["preserve_ids"] = preserve_count > total / 2
        patterns["dry_run"] = dry_run_count > total / 2
        patterns["migrate_all_versions"] = all_versions_count > total / 2

    return patterns


# Integration with existing elicitation system

_smart_defaults_enhancer: Optional[SmartDefaultsElicitationEnhancer] = None


def get_smart_defaults_enhancer(
    registry_manager: Optional[BaseRegistryManager] = None,
) -> SmartDefaultsElicitationEnhancer:
    """Get or create the singleton enhancer instance"""
    global _smart_defaults_enhancer
    if _smart_defaults_enhancer is None:
        _smart_defaults_enhancer = SmartDefaultsElicitationEnhancer(registry_manager)
    return _smart_defaults_enhancer


async def enhance_elicitation_with_smart_defaults(
    request: ElicitationRequest,
    operation: str,
    context: Optional[str] = None,
    registry_manager: Optional[BaseRegistryManager] = None,
) -> ElicitationRequest:
    """Convenience function to enhance any elicitation request with smart defaults"""
    enhancer = get_smart_defaults_enhancer(registry_manager)
    return await enhancer.enhance_elicitation_request(request, operation, context)


# Monkey-patch the existing elicitation module to use smart defaults
def enable_smart_defaults_globally(registry_manager: Optional[BaseRegistryManager] = None):
    """Enable smart defaults for all elicitation requests globally"""
    import elicitation

    # Store original functions
    original_functions = {
        "create_schema_field_elicitation": elicitation.create_schema_field_elicitation,
        "create_migration_preferences_elicitation": elicitation.create_migration_preferences_elicitation,
        "create_context_metadata_elicitation": elicitation.create_context_metadata_elicitation,
        "create_export_preferences_elicitation": elicitation.create_export_preferences_elicitation,
    }

    enhancer = get_smart_defaults_enhancer(registry_manager)

    # Replace with enhanced versions
    async def enhanced_schema_field(*args, **kwargs):
        base_request = original_functions["create_schema_field_elicitation"](*args, **kwargs)
        return await enhancer.enhance_elicitation_request(base_request, "create_schema_field", kwargs.get("context"))

    async def enhanced_migration(*args, **kwargs):
        base_request = original_functions["create_migration_preferences_elicitation"](*args, **kwargs)
        return await enhancer.enhance_elicitation_request(base_request, "migrate_schema", kwargs.get("context"))

    async def enhanced_context(*args, **kwargs):
        base_request = original_functions["create_context_metadata_elicitation"](*args, **kwargs)
        context_name = args[0] if args else kwargs.get("context_name", "")
        return await enhancer.enhance_elicitation_request(base_request, "create_context", context_name)

    async def enhanced_export(*args, **kwargs):
        base_request = original_functions["create_export_preferences_elicitation"](*args, **kwargs)
        operation_type = args[0] if args else kwargs.get("operation_type", "")
        # Normalize operation name to avoid double "export" prefix
        operation_name = operation_type if operation_type.startswith("export_") else f"export_{operation_type}"
        return await enhancer.enhance_elicitation_request(base_request, operation_name, None)

    # Apply patches
    elicitation.create_schema_field_elicitation = enhanced_schema_field
    elicitation.create_migration_preferences_elicitation = enhanced_migration
    elicitation.create_context_metadata_elicitation = enhanced_context
    elicitation.create_export_preferences_elicitation = enhanced_export

    logger.info("✅ Smart defaults enabled globally for elicitation requests")
