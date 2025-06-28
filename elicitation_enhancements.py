#!/usr/bin/env python3
"""
Enhanced Schema Registry Elicitation Capabilities

This module extends the base elicitation framework with advanced validation,
type checking, and user experience enhancements for Schema Registry operations.

Features:
- Advanced field validation with context-aware error messages
- Smart default suggestions based on schema patterns
- Multi-step elicitation for complex operations
- Integration with schema introspection
- Progress tracking and user guidance
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from elicitation import (
    ElicitationField,
    ElicitationManager,
    ElicitationRequest,
    ElicitationResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of field validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class EnhancedFieldValidator:
    """Enhanced validation for elicitation fields."""

    # Common validation patterns
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    URL_PATTERN = re.compile(
        r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
    )
    IPV4_PATTERN = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )

    # Schema field type mappings
    AVRO_TYPES = {
        "null",
        "boolean",
        "int",
        "long",
        "float",
        "double",
        "bytes",
        "string",
        "array",
        "map",
        "union",
        "record",
        "enum",
        "fixed",
    }
    JSON_SCHEMA_TYPES = {
        "null",
        "boolean",
        "object",
        "array",
        "number",
        "string",
        "integer",
    }

    @classmethod
    def validate_field_value(cls, field: ElicitationField, value: Any) -> ValidationResult:
        """Validate a field value against its definition."""
        errors = []
        warnings = []

        # Check required fields
        if field.required and (value is None or value == ""):
            errors.append(f"Field '{field.name}' is required")
            return ValidationResult(False, errors, warnings)

        # Skip validation for optional empty fields
        if not field.required and (value is None or value == ""):
            return ValidationResult(True, errors, warnings)

        # Convert value to string for pattern matching
        str_value = str(value) if value is not None else ""

        # Type-specific validation
        if field.type == "email":
            if not cls.EMAIL_PATTERN.match(str_value):
                errors.append(f"Invalid email format: {str_value}")

        elif field.type == "url":
            if not cls.URL_PATTERN.match(str_value):
                errors.append(f"Invalid URL format: {str_value}")

        elif field.type == "ipv4":
            if not cls.IPV4_PATTERN.match(str_value):
                errors.append(f"Invalid IPv4 address: {str_value}")

        elif field.type == "choice":
            if field.options and str_value not in field.options:
                errors.append(f"Value '{str_value}' not in allowed options: {field.options}")

        elif field.type == "number":
            try:
                float(str_value)
            except (ValueError, TypeError):
                errors.append(f"Value '{str_value}' is not a valid number")

        elif field.type == "integer":
            try:
                int(str_value)
            except (ValueError, TypeError):
                errors.append(f"Value '{str_value}' is not a valid integer")

        # Custom validation rules
        if field.validation:
            cls._apply_custom_validation(field, str_value, errors, warnings)

        # Schema-specific validation
        if field.name in ["field_type", "schema_type"]:
            cls._validate_schema_type(str_value, errors, warnings)

        return ValidationResult(len(errors) == 0, errors, warnings)

    @classmethod
    def _apply_custom_validation(cls, field: ElicitationField, value: str, errors: List[str], warnings: List[str]):
        """Apply custom validation rules."""
        validation = field.validation

        if "min_length" in validation:
            min_len = validation["min_length"]
            if len(value) < min_len:
                errors.append(f"Field '{field.name}' must be at least {min_len} characters")

        if "max_length" in validation:
            max_len = validation["max_length"]
            if len(value) > max_len:
                errors.append(f"Field '{field.name}' must be at most {max_len} characters")

        if "pattern" in validation:
            pattern = re.compile(validation["pattern"])
            if not pattern.match(value):
                errors.append(f"Field '{field.name}' does not match required pattern")

        if "min_value" in validation:
            try:
                num_val = float(value)
                if num_val < validation["min_value"]:
                    errors.append(f"Field '{field.name}' must be at least {validation['min_value']}")
            except (ValueError, TypeError):
                pass  # Already handled by type validation

        if "max_value" in validation:
            try:
                num_val = float(value)
                if num_val > validation["max_value"]:
                    errors.append(f"Field '{field.name}' must be at most {validation['max_value']}")
            except (ValueError, TypeError):
                pass

    @classmethod
    def _validate_schema_type(cls, value: str, errors: List[str], warnings: List[str]):
        """Validate schema type values."""
        if value.lower() in cls.AVRO_TYPES:
            return  # Valid Avro type
        elif value.lower() in cls.JSON_SCHEMA_TYPES:
            warnings.append(f"Type '{value}' is JSON Schema format, consider Avro equivalent")
        else:
            warnings.append(f"Unknown schema type '{value}', ensure it's valid for your schema system")


class EnhancedElicitationManager(ElicitationManager):
    """Enhanced elicitation manager with additional features."""

    def __init__(self):
        super().__init__()
        self.validation_stats = {
            "total_validations": 0,
            "validation_failures": 0,
            "common_errors": {},
        }
        self.performance_stats = {
            "total_requests": 0,
            "avg_response_time": 0.0,
            "timeout_rate": 0.0,
        }

    async def submit_response(self, response: ElicitationResponse) -> bool:
        """Submit response with enhanced validation."""
        start_time = datetime.utcnow()

        try:
            # Get the original request
            if response.request_id not in self.pending_requests:
                logger.warning(f"No pending request found for ID {response.request_id}")
                return False

            request = self.pending_requests[response.request_id]

            # Enhanced validation
            validation_result = self._validate_response_enhanced(request, response)

            if not validation_result.is_valid:
                logger.warning(f"Validation failed for request {response.request_id}: {validation_result.errors}")
                self._update_validation_stats(validation_result.errors)
                return False

            # Log warnings
            if validation_result.warnings:
                logger.info(f"Validation warnings for request {response.request_id}: {validation_result.warnings}")

            # Call parent implementation
            success = await super().submit_response(response)

            # Update performance stats
            response_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_performance_stats(response_time, success)

            return success

        except Exception as e:
            logger.error(f"Error in enhanced response submission: {str(e)}")
            return False

    def _validate_response_enhanced(
        self, request: ElicitationRequest, response: ElicitationResponse
    ) -> ValidationResult:
        """Enhanced validation with detailed error reporting."""
        all_errors = []
        all_warnings = []

        self.validation_stats["total_validations"] += 1

        # Validate each field
        for field in request.fields:
            value = response.values.get(field.name)

            result = EnhancedFieldValidator.validate_field_value(field, value)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        # Additional business logic validation
        self._validate_business_rules(request, response, all_errors, all_warnings)

        is_valid = len(all_errors) == 0
        if not is_valid:
            self.validation_stats["validation_failures"] += 1

        return ValidationResult(is_valid, all_errors, all_warnings)

    def _validate_business_rules(
        self,
        request: ElicitationRequest,
        response: ElicitationResponse,
        errors: List[str],
        warnings: List[str],
    ):
        """Apply business logic validation rules."""
        # Schema registration rules
        if "field_name" in response.values and "field_type" in response.values:
            field_name = response.values["field_name"]
            field_type = response.values["field_type"]

            # Check naming conventions
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", field_name):
                warnings.append(f"Field name '{field_name}' should follow camelCase or snake_case convention")

            # Check for reserved keywords
            reserved_keywords = {
                "type",
                "namespace",
                "name",
                "fields",
                "items",
                "values",
                "symbols",
            }
            if field_name.lower() in reserved_keywords:
                warnings.append(f"Field name '{field_name}' is a reserved keyword, consider using a different name")

        # Migration preferences rules
        if "preserve_ids" in response.values and "conflict_resolution" in response.values:
            preserve_ids = response.values["preserve_ids"]
            conflict_resolution = response.values["conflict_resolution"]

            if preserve_ids == "false" and conflict_resolution == "skip":
                warnings.append("Not preserving IDs with 'skip' conflict resolution may cause issues")

        # Export preferences rules
        if "format" in response.values and "compression" in response.values:
            format_type = response.values["format"]
            compression = response.values["compression"]

            if format_type == "csv" and compression != "none":
                warnings.append("CSV export with compression may not be supported by all tools")

    def _update_validation_stats(self, errors: List[str]):
        """Update validation statistics."""
        for error in errors:
            # Extract error type
            error_type = error.split(":")[0] if ":" in error else error.split(" ")[0]
            self.validation_stats["common_errors"][error_type] = (
                self.validation_stats["common_errors"].get(error_type, 0) + 1
            )

    def _update_performance_stats(self, response_time: float, success: bool):
        """Update performance statistics."""
        self.performance_stats["total_requests"] += 1

        # Update average response time
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_response_time"]
        self.performance_stats["avg_response_time"] = (current_avg * (total - 1) + response_time) / total

        # Update timeout rate (if response_time > reasonable threshold)
        if response_time > 30.0:  # 30 seconds considered slow
            timeouts = self.performance_stats.get("slow_responses", 0) + 1
            self.performance_stats["slow_responses"] = timeouts
            self.performance_stats["timeout_rate"] = timeouts / total

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validation_stats.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()

    async def cleanup_expired_requests(self, max_age_hours: int = 24) -> int:
        """Clean up old expired requests to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_count = 0

        expired_ids = []
        for request_id, request in self.pending_requests.items():
            if request.created_at < cutoff_time:
                expired_ids.append(request_id)

        for request_id in expired_ids:
            self._cleanup_request(request_id)
            expired_count += 1

        # Also clean up old responses
        old_response_ids = []
        for request_id, response in self.responses.items():
            if response.timestamp < cutoff_time:
                old_response_ids.append(request_id)

        for request_id in old_response_ids:
            del self.responses[request_id]
            expired_count += 1

        logger.info(f"Cleaned up {expired_count} expired elicitation requests/responses")
        return expired_count


# Performance optimization helpers
class ElicitationCache:
    """Cache for commonly used elicitation patterns."""

    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
        self.access_count = {}

    def get_cached_response(self, request_signature: str) -> Optional[Dict[str, Any]]:
        """Get cached response for similar requests."""
        if request_signature in self.cache:
            self.access_count[request_signature] = self.access_count.get(request_signature, 0) + 1
            return self.cache[request_signature]
        return None

    def cache_response(self, request_signature: str, response_values: Dict[str, Any]):
        """Cache a response for future use."""
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.max_size:
            # Remove least accessed item
            least_used = min(self.access_count, key=self.access_count.get)
            del self.cache[least_used]
            del self.access_count[least_used]

        self.cache[request_signature] = response_values
        self.access_count[request_signature] = 1

    def generate_signature(self, request: ElicitationRequest) -> str:
        """Generate a signature for caching purposes."""
        # Create signature based on request structure, not instance
        field_sigs = [f"{f.name}:{f.type}:{f.required}" for f in request.fields]
        return f"{request.type.value}:{request.title}:{':'.join(sorted(field_sigs))}"


# Error recovery helpers
async def recover_from_elicitation_failure(
    original_request: ElicitationRequest,
    failure_reason: str,
    fallback_values: Optional[Dict[str, Any]] = None,
) -> ElicitationResponse:
    """Recover from elicitation failures with intelligent fallbacks."""

    logger.warning(f"Elicitation failure for '{original_request.title}': {failure_reason}")

    # Use provided fallback values or generate intelligent defaults
    if fallback_values:
        response_values = fallback_values
    else:
        response_values = {}

        for field in original_request.fields:
            if field.default is not None:
                response_values[field.name] = field.default
            elif field.type == "choice" and field.options:
                # Use first option as fallback
                response_values[field.name] = field.options[0]
            elif field.type == "confirmation":
                # Conservative default
                response_values[field.name] = "false"
            elif field.type in ["text", "email", "url"]:
                response_values[field.name] = field.placeholder or ""
            elif field.type in ["integer", "number"]:
                response_values[field.name] = "0"
            elif field.type == "boolean":
                response_values[field.name] = "false"
            else:
                response_values[field.name] = ""

    return ElicitationResponse(
        request_id=original_request.id,
        values=response_values,
        complete=True,
        metadata={
            "source": "failure_recovery",
            "failure_reason": failure_reason,
            "auto_generated": True,
            "recovery_timestamp": datetime.utcnow().isoformat(),
        },
    )


# Export enhanced manager as default
enhanced_elicitation_manager = EnhancedElicitationManager()
