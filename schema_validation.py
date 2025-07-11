#!/usr/bin/env python3
"""
Schema Validation Utilities for Kafka Schema Registry MCP Server

Provides validation utilities and decorators for implementing structured
tool output per MCP 2025-06-18 specification.

Features:
- JSON Schema validation for tool outputs
- Graceful error handling with backward compatibility
- Validation logging and monitoring
- Decorator for easy integration with existing tools
"""

import asyncio
import functools
import logging
import warnings
from typing import Any, Callable, Dict, Optional, Union

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError

    # Suppress deprecation warning for RefResolver temporarily
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from jsonschema.validators import RefResolver

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    ValidationError = Exception

from schema_definitions import get_tool_schema

# Configure logging
logger = logging.getLogger(__name__)

# Local draft-07 schema to avoid network requests
DRAFT_07_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "http://json-schema.org/draft-07/schema#",
    "title": "Core schema meta-schema",
    "definitions": {
        "schemaArray": {"type": "array", "minItems": 1, "items": {"$ref": "#"}},
        "nonNegativeInteger": {"type": "integer", "minimum": 0},
        "nonNegativeIntegerDefault0": {"allOf": [{"$ref": "#/definitions/nonNegativeInteger"}, {"default": 0}]},
        "simpleTypes": {"enum": ["array", "boolean", "integer", "null", "number", "object", "string"]},
        "stringArray": {"type": "array", "items": {"type": "string"}, "uniqueItems": True, "default": []},
    },
    "type": ["object", "boolean"],
    "properties": {
        "$id": {"type": "string", "format": "uri-reference"},
        "$schema": {"type": "string", "format": "uri"},
        "$ref": {"type": "string", "format": "uri-reference"},
        "$comment": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "default": True,
        "readOnly": {"type": "boolean", "default": False},
        "examples": {"type": "array", "items": True},
        "multipleOf": {"type": "number", "exclusiveMinimum": 0},
        "maximum": {"type": "number"},
        "exclusiveMaximum": {"type": "number"},
        "minimum": {"type": "number"},
        "exclusiveMinimum": {"type": "number"},
        "maxLength": {"$ref": "#/definitions/nonNegativeInteger"},
        "minLength": {"$ref": "#/definitions/nonNegativeIntegerDefault0"},
        "pattern": {"type": "string", "format": "regex"},
        "additionalItems": {"$ref": "#"},
        "items": {"anyOf": [{"$ref": "#"}, {"$ref": "#/definitions/schemaArray"}], "default": True},
        "maxItems": {"$ref": "#/definitions/nonNegativeInteger"},
        "minItems": {"$ref": "#/definitions/nonNegativeIntegerDefault0"},
        "uniqueItems": {"type": "boolean", "default": False},
        "contains": {"$ref": "#"},
        "maxProperties": {"$ref": "#/definitions/nonNegativeInteger"},
        "minProperties": {"$ref": "#/definitions/nonNegativeIntegerDefault0"},
        "required": {"$ref": "#/definitions/stringArray"},
        "additionalProperties": {"$ref": "#"},
        "definitions": {"type": "object", "additionalProperties": {"$ref": "#"}, "default": {}},
        "properties": {"type": "object", "additionalProperties": {"$ref": "#"}, "default": {}},
        "patternProperties": {
            "type": "object",
            "additionalProperties": {"$ref": "#"},
            "propertyNames": {"format": "regex"},
            "default": {},
        },
        "dependencies": {
            "type": "object",
            "additionalProperties": {"anyOf": [{"$ref": "#"}, {"$ref": "#/definitions/stringArray"}]},
        },
        "propertyNames": {"$ref": "#"},
        "const": True,
        "enum": {"type": "array", "items": True, "minItems": 1, "uniqueItems": True},
        "type": {
            "anyOf": [
                {"$ref": "#/definitions/simpleTypes"},
                {"type": "array", "items": {"$ref": "#/definitions/simpleTypes"}, "minItems": 1, "uniqueItems": True},
            ]
        },
        "format": {"type": "string"},
        "contentMediaType": {"type": "string"},
        "contentEncoding": {"type": "string"},
        "if": {"$ref": "#"},
        "then": {"$ref": "#"},
        "else": {"$ref": "#"},
        "allOf": {"$ref": "#/definitions/schemaArray"},
        "anyOf": {"$ref": "#/definitions/schemaArray"},
        "oneOf": {"$ref": "#/definitions/schemaArray"},
        "not": {"$ref": "#"},
    },
    "default": True,
}


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""

    def __init__(
        self,
        message: str,
        validation_error: Optional[Exception] = None,
        data: Optional[Any] = None,
    ):
        super().__init__(message)
        self.validation_error = validation_error
        self.data = data


class ValidationResult:
    """Container for validation results."""

    def __init__(
        self,
        is_valid: bool,
        data: Any,
        errors: Optional[list] = None,
        warnings: Optional[list] = None,
    ):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []
        self.warnings = warnings or []

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_response(data: Any, schema: Dict[str, Any], tool_name: str = "unknown") -> ValidationResult:
    """
    Validate response data against a JSON schema.

    Args:
        data: The data to validate
        schema: JSON Schema definition
        tool_name: Name of the tool (for logging)

    Returns:
        ValidationResult containing validation status and any errors
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.warning(f"jsonschema library not available - skipping validation for {tool_name}")
        result = ValidationResult(is_valid=True, data=data)
        result.add_warning("Schema validation skipped - jsonschema library not available")
        return result

    try:
        # Create a local resolver to avoid network requests for draft-07 schema
        resolver = RefResolver(
            base_uri="",
            referrer=schema,
            store={
                "http://json-schema.org/draft-07/schema#": DRAFT_07_SCHEMA,
                "https://json-schema.org/draft-07/schema": DRAFT_07_SCHEMA,
                "https://json-schema.org/draft-07/schema#": DRAFT_07_SCHEMA,
            },
        )

        # Create validator with local resolver
        validator = Draft7Validator(schema, resolver=resolver)

        # Validate the data
        errors = list(validator.iter_errors(data))

        if not errors:
            logger.debug(f"✅ Schema validation passed for {tool_name}")
            return ValidationResult(is_valid=True, data=data)
        else:
            # Collect error messages
            error_messages = []
            for error in errors:
                path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                error_messages.append(f"At {path}: {error.message}")

            logger.warning(f"❌ Schema validation failed for {tool_name}: {len(errors)} errors")
            for msg in error_messages:
                logger.warning(f"  - {msg}")

            return ValidationResult(is_valid=False, data=data, errors=error_messages)

    except Exception as e:
        logger.error(f"💥 Schema validation error for {tool_name}: {str(e)}")
        result = ValidationResult(is_valid=False, data=data, errors=[f"Validation error: {str(e)}"])
        return result


def structured_output(tool_name: str, strict: bool = False, fallback_on_error: bool = True):
    """
    Decorator to add structured output validation to MCP tools.
    Supports both sync and async functions.

    Args:
        tool_name: Name of the tool (used to lookup schema)
        strict: If True, raise exception on validation failure
        fallback_on_error: If True, return original data with validation warning on error

    Usage:
        @structured_output("get_schema")
        def get_schema_tool(...):
            return {...}

        @structured_output("migrate_context")
        async def migrate_context_tool(...):
            return {...}
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Call the original async function
                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {str(e)}")
                    if strict:
                        raise
                    # Return error response in structured format
                    return format_error_response(str(e), tool_name)

                # Get the schema for this tool
                schema = get_tool_schema(tool_name)

                # Validate the result
                validation_result = validate_response(result, schema, tool_name)

                if validation_result.is_valid:
                    # Add validation metadata if requested
                    if isinstance(result, dict):
                        result["_validation"] = {
                            "validated": True,
                            "tool": tool_name,
                            "warnings": validation_result.warnings,
                        }
                    return result
                else:
                    # Handle validation failure
                    if strict:
                        error_msg = f"Schema validation failed for {tool_name}: {validation_result.errors}"
                        raise SchemaValidationError(error_msg, data=result)

                    if fallback_on_error:
                        # Return original data with validation warning
                        logger.warning(f"Returning unvalidated data for {tool_name} due to validation failure")
                        if isinstance(result, dict):
                            result["_validation"] = {
                                "validated": False,
                                "tool": tool_name,
                                "errors": validation_result.errors,
                                "warnings": validation_result.warnings,
                            }
                    return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Call the original function
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {str(e)}")
                    if strict:
                        raise
                    # Return error response in structured format
                    return format_error_response(str(e), tool_name)

                # Get the schema for this tool
                schema = get_tool_schema(tool_name)

                # Validate the result
                validation_result = validate_response(result, schema, tool_name)

                if validation_result.is_valid:
                    # Add validation metadata if requested
                    if isinstance(result, dict):
                        result["_validation"] = {
                            "validated": True,
                            "tool": tool_name,
                            "warnings": validation_result.warnings,
                        }
                    return result
                else:
                    # Handle validation failure
                    if strict:
                        error_msg = f"Schema validation failed for {tool_name}: {validation_result.errors}"
                        raise SchemaValidationError(error_msg, data=result)

                    if fallback_on_error:
                        # Return original data with validation warning
                        logger.warning(f"Returning unvalidated data for {tool_name} due to validation failure")
                        if isinstance(result, dict):
                            result["_validation"] = {
                                "validated": False,
                                "tool": tool_name,
                                "errors": validation_result.errors,
                                "warnings": validation_result.warnings,
                            }
                    return result

            return wrapper

    return decorator


def format_error_response(error_message: str, tool_name: str, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Format an error response according to the error schema.

    Args:
        error_message: Human-readable error message
        tool_name: Name of the tool that failed
        error_code: Optional machine-readable error code

    Returns:
        Formatted error response
    """
    response = {"error": error_message, "tool": tool_name}

    if error_code:
        response["error_code"] = error_code

    # Add metadata fields
    response["registry_mode"] = "unknown"  # Will be overridden by calling context

    return response


def validate_tool_output(tool_name: str, data: Any, strict: bool = False) -> Union[Any, Dict[str, Any]]:
    """
    Standalone function to validate tool output.

    Args:
        tool_name: Name of the tool
        data: Data to validate
        strict: If True, raise exception on validation failure

    Returns:
        Original data if valid, or error response if invalid
    """
    schema = get_tool_schema(tool_name)
    validation_result = validate_response(data, schema, tool_name)

    if validation_result.is_valid:
        return data
    else:
        if strict:
            raise SchemaValidationError(
                f"Validation failed for {tool_name}: {validation_result.errors}",
                data=data,
            )
        else:
            return format_error_response(
                f"Validation failed: {validation_result.errors[0] if validation_result.errors else 'Unknown error'}",
                tool_name,
            )


def check_schema_compatibility() -> Dict[str, Any]:
    """
    Check if the current environment supports schema validation.

    Returns:
        Status information about schema validation support
    """
    return {
        "jsonschema_available": JSONSCHEMA_AVAILABLE,
        "jsonschema_version": (getattr(jsonschema, "__version__", "unknown") if JSONSCHEMA_AVAILABLE else None),
        "supported_draft": "Draft7" if JSONSCHEMA_AVAILABLE else None,
        "validation_enabled": JSONSCHEMA_AVAILABLE,
        "recommendations": [
            (
                "Install jsonschema library for full validation support"
                if not JSONSCHEMA_AVAILABLE
                else "Schema validation fully supported"
            )
        ],
    }


# Utility functions for common validation patterns


def validate_registry_response(data: Any, registry_mode: str = "unknown") -> Any:
    """Add common registry metadata to response and validate."""
    if isinstance(data, dict):
        # Add standard metadata if not present
        if "registry_mode" not in data:
            data["registry_mode"] = registry_mode
        if "mcp_protocol_version" not in data:
            data["mcp_protocol_version"] = "2025-06-18"

    return data


def create_success_response(
    message: str, data: Optional[Dict[str, Any]] = None, registry_mode: str = "unknown"
) -> Dict[str, Any]:
    """Create a standard success response."""
    response = {
        "message": message,
        "registry_mode": registry_mode,
        "mcp_protocol_version": "2025-06-18",
    }

    if data:
        response["data"] = data

    return response


def create_error_response(
    error: str,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
    registry_mode: str = "unknown",
) -> Dict[str, Any]:
    """Create a standard error response."""
    response = {
        "error": error,
        "registry_mode": registry_mode,
        "mcp_protocol_version": "2025-06-18",
    }

    if error_code:
        response["error_code"] = error_code

    if details:
        response["details"] = details

    return response


# Export main functions
__all__ = [
    "structured_output",
    "validate_response",
    "validate_tool_output",
    "ValidationResult",
    "SchemaValidationError",
    "format_error_response",
    "check_schema_compatibility",
    "validate_registry_response",
    "create_success_response",
    "create_error_response",
    "create_local_validator",
    "get_local_resolver",
]


def create_local_validator(schema: Dict[str, Any]):
    """
    Create a JSON Schema validator with local resolver to avoid network requests.

    Args:
        schema: The JSON schema to create a validator for

    Returns:
        Draft7Validator instance with local resolver (if jsonschema available)
    """
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError("jsonschema library is not available")

    resolver = get_local_resolver(schema)
    return Draft7Validator(schema, resolver=resolver)


def get_local_resolver(schema: Dict[str, Any]):
    """
    Get a RefResolver that uses local draft-07 schema instead of network requests.

    Args:
        schema: The referrer schema

    Returns:
        RefResolver instance with local draft-07 schema (if jsonschema available)
    """
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError("jsonschema library is not available")

    return RefResolver(
        base_uri="",
        referrer=schema,
        store={
            "http://json-schema.org/draft-07/schema#": DRAFT_07_SCHEMA,
            "https://json-schema.org/draft-07/schema": DRAFT_07_SCHEMA,
            "https://json-schema.org/draft-07/schema#": DRAFT_07_SCHEMA,
        },
    )
