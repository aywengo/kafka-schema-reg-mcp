"""
Smart Defaults Engine for Elicitation Forms

This module implements a pattern recognition and suggestion system that learns
from user behavior and organizational conventions to pre-populate elicitation forms.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from schema_registry_common import BaseRegistryManager, RegistryConfig

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """Represents a detected pattern with confidence score"""

    pattern: str
    confidence: float
    occurrences: int
    last_seen: datetime
    contexts: Set[str] = field(default_factory=set)


@dataclass
class FieldSuggestion:
    """Represents a field suggestion with metadata"""

    name: str
    type: str
    default_value: Optional[Any] = None
    confidence: float = 0.0
    source: str = "pattern"  # pattern, history, template
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SmartDefault:
    """Container for smart default values"""

    field: str
    value: Any
    confidence: float
    source: str
    reasoning: Optional[str] = None


class PatternAnalyzer:
    """Analyzes schemas and operations to detect patterns"""

    def __init__(self):
        self.naming_patterns: Dict[str, PatternMatch] = {}
        self.field_patterns: Dict[str, Counter] = defaultdict(Counter)
        self.context_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.compatibility_patterns: Dict[str, Counter] = defaultdict(Counter)

    def analyze_naming_convention(self, subjects: List[str], context: Optional[str] = None) -> Dict[str, PatternMatch]:
        """Analyze naming patterns in subject names"""
        patterns = {}

        # Common naming patterns to detect
        pattern_regexes = {
            "hyphenated": r"^[a-z]+(-[a-z]+)+$",
            "camelCase": r"^[a-z]+[A-Z][a-zA-Z]*$",
            "PascalCase": r"^[A-Z][a-zA-Z]*$",
            "snake_case": r"^[a-z]+(_[a-z]+)+$",
            "versioned": r".*[-_]v\d+$",
            "namespaced": r"^[a-z]+\.[a-z]+",
            "event_suffixed": r".*[-_](event|events)$",
            "topic_prefixed": r"^(topic|kafka)[-_].*",
        }

        # Count occurrences of each pattern
        pattern_counts = defaultdict(list)
        for subject in subjects:
            for pattern_name, regex in pattern_regexes.items():
                if re.match(regex, subject, re.IGNORECASE):
                    pattern_counts[pattern_name].append(subject)

        # Calculate confidence scores
        total_subjects = len(subjects)
        for pattern_name, matching_subjects in pattern_counts.items():
            occurrence_count = len(matching_subjects)
            confidence = occurrence_count / total_subjects if total_subjects > 0 else 0

            if confidence > 0.3:  # Only consider patterns with >30% occurrence
                patterns[pattern_name] = PatternMatch(
                    pattern=pattern_name,
                    confidence=confidence,
                    occurrences=occurrence_count,
                    last_seen=datetime.utcnow(),
                    contexts={context} if context else set(),
                )

        # Detect custom patterns (prefixes/suffixes)
        self._detect_prefix_suffix_patterns(subjects, patterns, context)

        return patterns

    def _detect_prefix_suffix_patterns(
        self, subjects: List[str], patterns: Dict[str, PatternMatch], context: Optional[str]
    ):
        """Detect common prefixes and suffixes"""
        if len(subjects) < 3:
            return

        # Find common prefixes
        prefix_counter = Counter()
        suffix_counter = Counter()

        for subject in subjects:
            # Check prefixes (3-10 characters)
            for i in range(3, min(11, len(subject))):
                prefix = subject[:i]
                if prefix.endswith(("-", "_", ".")):
                    prefix_counter[prefix] += 1

            # Check suffixes (3-10 characters)
            for i in range(3, min(11, len(subject))):
                suffix = subject[-i:]
                if suffix.startswith(("-", "_")):
                    suffix_counter[suffix] += 1

        # Add significant prefixes/suffixes as patterns
        total = len(subjects)
        for prefix, count in prefix_counter.most_common(5):
            if count >= total * 0.4:  # 40% threshold
                patterns[f"prefix:{prefix}"] = PatternMatch(
                    pattern=f"prefix:{prefix}",
                    confidence=count / total,
                    occurrences=count,
                    last_seen=datetime.utcnow(),
                    contexts={context} if context else set(),
                )

        for suffix, count in suffix_counter.most_common(5):
            if count >= total * 0.4:
                patterns[f"suffix:{suffix}"] = PatternMatch(
                    pattern=f"suffix:{suffix}",
                    confidence=count / total,
                    occurrences=count,
                    last_seen=datetime.utcnow(),
                    contexts={context} if context else set(),
                )

    def analyze_field_patterns(self, schemas: List[Dict[str, Any]]) -> Dict[str, List[FieldSuggestion]]:
        """Analyze common field patterns across schemas"""
        field_type_counter = defaultdict(Counter)
        field_metadata = defaultdict(dict)

        for schema in schemas:
            if schema.get("type") == "record" and "fields" in schema:
                for field in schema["fields"]:
                    field_name = field.get("name", "")
                    field_type = field.get("type", "")

                    # Normalize type (handle unions, nested types)
                    normalized_type = self._normalize_field_type(field_type)
                    field_type_counter[field_name][normalized_type] += 1

                    # Collect metadata
                    if field_name not in field_metadata:
                        field_metadata[field_name] = {
                            "doc": field.get("doc"),
                            "default": field.get("default"),
                            "aliases": field.get("aliases", []),
                        }

        # Generate suggestions
        suggestions = {}
        for field_name, type_counts in field_type_counter.items():
            total_occurrences = sum(type_counts.values())
            if total_occurrences >= 2:  # Field appears in at least 2 schemas
                most_common_type = type_counts.most_common(1)[0]
                confidence = most_common_type[1] / total_occurrences

                suggestions[field_name] = [
                    FieldSuggestion(
                        name=field_name,
                        type=most_common_type[0],
                        default_value=field_metadata[field_name].get("default"),
                        confidence=confidence,
                        source="pattern",
                        metadata=field_metadata[field_name],
                    )
                ]

        return suggestions

    def _normalize_field_type(self, field_type) -> str:
        """Normalize Avro field types for comparison"""
        if isinstance(field_type, str):
            return field_type
        elif isinstance(field_type, list):
            # Union type - extract non-null type
            non_null_types = [t for t in field_type if t != "null"]
            return non_null_types[0] if non_null_types else "null"
        elif isinstance(field_type, dict):
            return field_type.get("type", "complex")
        return "unknown"


class LearningEngine:
    """Learns from user interactions and feedback"""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".kafka-schema-mcp" / "smart_defaults"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.user_choices: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.feedback_scores: Dict[str, float] = defaultdict(float)
        self.context_preferences: Dict[str, Dict[str, Any]] = defaultdict(dict)

        self._load_history()

    def record_choice(self, operation: str, context: str, field: str, value: Any, accepted: bool = True):
        """Record a user's choice for future learning"""
        choice = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "context": context,
            "field": field,
            "value": value,
            "accepted": accepted,
        }

        key = f"{operation}:{context}:{field}"
        self.user_choices[key].append(choice)

        # Update feedback score
        if accepted:
            self.feedback_scores[key] = min(1.0, self.feedback_scores[key] + 0.12)
        else:
            self.feedback_scores[key] = max(0.0, self.feedback_scores[key] - 0.15)

        # Persist changes
        self._save_history()

    def get_historical_preference(self, operation: str, context: str, field: str) -> Optional[SmartDefault]:
        """Get the most likely value based on history"""
        key = f"{operation}:{context}:{field}"
        choices = self.user_choices.get(key, [])

        if not choices:
            return None

        # Get recent choices (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent_choices = [c for c in choices if datetime.fromisoformat(c["timestamp"]) > cutoff and c["accepted"]]

        if not recent_choices:
            return None

        # Find most common recent value
        value_counts = Counter(c["value"] for c in recent_choices)
        most_common = value_counts.most_common(1)[0]

        # Calculate confidence based on consistency and recency
        total_recent = len(recent_choices)
        consistency_score = most_common[1] / total_recent
        feedback_score = self.feedback_scores.get(key, 0.5)

        confidence = consistency_score * 0.7 + feedback_score * 0.3

        return SmartDefault(
            field=field,
            value=most_common[0],
            confidence=confidence,
            source="history",
            reasoning=f"Used {most_common[1]} times in last 30 days",
        )

    def update_context_preference(self, context: str, preferences: Dict[str, Any]):
        """Update preferences for a specific context"""
        self.context_preferences[context].update(preferences)
        self._save_history()

    def _load_history(self):
        """Load learning history from storage"""
        history_file = self.storage_path / "learning_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)
                    self.user_choices = defaultdict(list, data.get("choices", {}))
                    self.feedback_scores = defaultdict(float, data.get("scores", {}))
                    self.context_preferences = defaultdict(dict, data.get("preferences", {}))
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")

    def _save_history(self):
        """Save learning history to storage"""
        history_file = self.storage_path / "learning_history.json"
        try:
            data = {
                "choices": dict(self.user_choices),
                "scores": dict(self.feedback_scores),
                "preferences": dict(self.context_preferences),
                "last_updated": datetime.utcnow().isoformat(),
            }
            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")


class SmartDefaultsEngine:
    """Main engine for generating smart defaults"""

    def __init__(self, registry_manager: Optional[BaseRegistryManager] = None):
        self.registry_manager = registry_manager
        self.pattern_analyzer = PatternAnalyzer()
        self.learning_engine = LearningEngine()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

        # Standard templates for common operations
        self.templates = self._load_templates()

    async def suggest_defaults(
        self, operation: str, context: Optional[str] = None, existing_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SmartDefault]:
        """Generate smart defaults for an operation"""
        cache_key = f"{operation}:{context}:{str(existing_data)}"

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_defaults = self._cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_defaults

        # Generate defaults
        defaults = {}

        # 1. Get template-based defaults
        template_defaults = self._get_template_defaults(operation, context)
        defaults.update(template_defaults)

        # 2. Get pattern-based defaults
        if self.registry_manager and context:
            pattern_defaults = await self._get_pattern_defaults(operation, context)
            # Pattern defaults override template defaults
            defaults.update(pattern_defaults)

        # 3. Get history-based defaults (highest priority)
        history_defaults = self._get_history_defaults(operation, context)
        defaults.update(history_defaults)

        # 4. Apply existing data overrides
        if existing_data:
            for field, value in existing_data.items():
                if value is not None:
                    defaults[field] = SmartDefault(
                        field=field, value=value, confidence=1.0, source="provided", reasoning="User provided value"
                    )

            # Add field suggestions if record type is provided
            if "record_type" in existing_data and operation in ["create_schema", "create_schema_field"]:
                record_type = existing_data["record_type"]
                field_suggestions = self.get_field_suggestions(record_type)
                if field_suggestions:
                    # Convert to dictionary format expected by elicitation system
                    suggestions_dict = {}
                    for suggestion in field_suggestions:
                        suggestions_dict[suggestion.name] = [suggestion]
                    defaults["_field_suggestions"] = suggestions_dict

        # Cache results
        self._cache[cache_key] = (datetime.utcnow(), defaults)

        return defaults

    def _get_template_defaults(self, operation: str, context: Optional[str]) -> Dict[str, SmartDefault]:
        """Get defaults from predefined templates"""
        defaults = {}

        # Common defaults for all operations
        common_defaults = {
            "schema_type": SmartDefault(
                field="schema_type",
                value="AVRO",
                confidence=0.8,
                source="template",
                reasoning="Most common schema type",
            )
        }

        # Operation-specific defaults
        operation_defaults = {
            "create_schema": {
                "compatibility": SmartDefault(
                    field="compatibility",
                    value="BACKWARD",
                    confidence=0.7,
                    source="template",
                    reasoning="Recommended for safe schema evolution",
                )
            },
            "create_schema_field": {
                "compatibility": SmartDefault(
                    field="compatibility",
                    value="BACKWARD",
                    confidence=0.7,
                    source="template",
                    reasoning="Recommended for safe schema evolution",
                )
            },
            "create_context": {
                "description": SmartDefault(
                    field="description",
                    value=f'Schema context for {context or "project"}',
                    confidence=0.5,
                    source="template",
                    reasoning="Generated description",
                )
            },
            "migrate_schema": {
                "preserve_ids": SmartDefault(
                    field="preserve_ids",
                    value=True,
                    confidence=0.8,
                    source="template",
                    reasoning="Maintains consistency across environments",
                ),
                "dry_run": SmartDefault(
                    field="dry_run",
                    value=True,
                    confidence=0.9,
                    source="template",
                    reasoning="Safety first - preview changes",
                ),
            },
            "export_global": {
                "include_config": SmartDefault(
                    field="include_config",
                    value=True,
                    confidence=0.8,
                    source="template",
                    reasoning="Include configuration for complete export",
                ),
                "include_metadata": SmartDefault(
                    field="include_metadata",
                    value=True,
                    confidence=0.8,
                    source="template",
                    reasoning="Include metadata for complete export",
                ),
                "include_versions": SmartDefault(
                    field="include_versions",
                    value="all",
                    confidence=0.7,
                    source="template",
                    reasoning="Include all versions for complete backup",
                ),
            },
        }

        # Apply common defaults
        defaults.update(common_defaults)

        # Apply operation-specific defaults
        if operation in operation_defaults:
            defaults.update(operation_defaults[operation])

        # Environment-specific adjustments
        if context:
            if "prod" in context.lower() or "production" in context.lower():
                defaults["compatibility"] = SmartDefault(
                    field="compatibility",
                    value="FULL",
                    confidence=0.6,
                    source="template",
                    reasoning="Stricter compatibility for production",
                )
            elif "dev" in context.lower() or "development" in context.lower():
                defaults["compatibility"] = SmartDefault(
                    field="compatibility",
                    value="NONE",
                    confidence=0.5,
                    source="template",
                    reasoning="Flexible compatibility for development",
                )

        return defaults

    async def _get_pattern_defaults(self, operation: str, context: str) -> Dict[str, SmartDefault]:
        """Get defaults based on detected patterns"""
        defaults = {}

        try:
            # Get subjects in context
            subjects = await self.registry_manager.list_subjects(context=context)

            if subjects:
                # Analyze naming patterns
                naming_patterns = self.pattern_analyzer.analyze_naming_convention(subjects, context)

                # Generate subject name suggestion
                if naming_patterns and operation in ["create_schema", "register_schema"]:
                    # Find the strongest pattern
                    strongest_pattern = max(naming_patterns.values(), key=lambda p: p.confidence)

                    # Generate suggested name based on pattern
                    suggested_name = self._generate_name_from_pattern(strongest_pattern.pattern, context)

                    if suggested_name:
                        defaults["subject"] = SmartDefault(
                            field="subject",
                            value=suggested_name,
                            confidence=strongest_pattern.confidence * 0.8,
                            source="pattern",
                            reasoning=f"Based on {strongest_pattern.pattern} pattern",
                        )

                # Analyze field patterns for schema creation
                if operation in ["create_schema", "create_schema_field"]:
                    # Get a few schemas to analyze
                    sample_schemas = []
                    for subject in subjects[:5]:  # Analyze first 5 schemas
                        try:
                            schema_data = await self.registry_manager.get_schema(subject, context=context)
                            if schema_data and "schema" in schema_data:
                                schema_dict = json.loads(schema_data["schema"])
                                sample_schemas.append(schema_dict)
                        except:
                            pass

                    if sample_schemas:
                        field_suggestions = self.pattern_analyzer.analyze_field_patterns(sample_schemas)
                        # Store for elicitation use
                        defaults["_field_suggestions"] = field_suggestions

        except Exception as e:
            logger.warning(f"Failed to analyze patterns: {e}")

        return defaults

    def _get_history_defaults(self, operation: str, context: Optional[str]) -> Dict[str, SmartDefault]:
        """Get defaults based on user history"""
        defaults = {}

        # Common fields to check for each operation
        operation_fields = {
            "create_schema": ["subject", "compatibility", "schema_type"],
            "create_context": ["description", "owner", "environment"],
            "migrate_schema": ["preserve_ids", "dry_run", "migrate_all_versions"],
            "export_global": ["include_config", "include_metadata", "include_versions"],
        }

        fields_to_check = operation_fields.get(operation, [])

        for field in fields_to_check:
            historical_default = self.learning_engine.get_historical_preference(operation, context or "global", field)
            if historical_default and historical_default.confidence > 0.5:
                defaults[field] = historical_default

        return defaults

    def _generate_name_from_pattern(self, pattern: str, context: str) -> Optional[str]:
        """Generate a name suggestion based on pattern"""
        # This is a simplified example - could be enhanced
        if pattern.startswith("prefix:"):
            prefix = pattern.split(":", 1)[1]
            return f"{prefix}new-schema"
        elif pattern.startswith("suffix:"):
            suffix = pattern.split(":", 1)[1]
            return f"new-schema{suffix}"
        elif pattern == "hyphenated":
            return f"{context}-new-schema"
        elif pattern == "event_suffixed":
            return f"{context}-event"

        return None

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load operation templates"""
        # Could be loaded from configuration file
        return {
            "create_schema": {
                "required_fields": ["subject", "schema_definition"],
                "optional_fields": ["compatibility", "schema_type"],
            },
            "create_context": {
                "required_fields": ["context"],
                "optional_fields": ["description", "owner", "environment", "tags"],
            },
        }

    def record_user_choice(self, operation: str, context: str, field: str, value: Any, accepted: bool = True):
        """Record user's choice for learning"""
        self.learning_engine.record_choice(operation, context, field, value, accepted)

    @lru_cache(maxsize=100)
    def get_field_suggestions(self, record_type: str) -> List[FieldSuggestion]:
        """Get common field suggestions for a record type"""
        # Common fields by record type
        common_fields = {
            "event": [
                FieldSuggestion("id", "string", confidence=0.9),
                FieldSuggestion("timestamp", "long", confidence=0.9),
                FieldSuggestion("eventType", "string", confidence=0.8),
                FieldSuggestion("version", "string", default_value="1.0", confidence=0.7),
            ],
            "entity": [
                FieldSuggestion("id", "string", confidence=0.9),
                FieldSuggestion("createdAt", "long", confidence=0.8),
                FieldSuggestion("updatedAt", "long", confidence=0.8),
                FieldSuggestion("version", "int", default_value=1, confidence=0.7),
            ],
            "command": [
                FieldSuggestion("commandId", "string", confidence=0.9),
                FieldSuggestion("timestamp", "long", confidence=0.9),
                FieldSuggestion("userId", "string", confidence=0.7),
                FieldSuggestion("correlationId", "string", confidence=0.6),
            ],
        }

        return common_fields.get(record_type, [])


# Singleton instance
_smart_defaults_engine: Optional[SmartDefaultsEngine] = None


def get_smart_defaults_engine(registry_manager: Optional[BaseRegistryManager] = None) -> SmartDefaultsEngine:
    """Get or create the singleton SmartDefaultsEngine instance"""
    global _smart_defaults_engine
    if _smart_defaults_engine is None:
        _smart_defaults_engine = SmartDefaultsEngine(registry_manager)
    return _smart_defaults_engine
