"""
Smart Defaults Initialization Module

This module handles the initialization of smart defaults when the MCP server starts.
It should be imported and called from the main server file.
"""

import logging
from typing import Optional

from schema_registry_common import BaseRegistryManager
from smart_defaults_config import get_config
from smart_defaults_integration import enable_smart_defaults_globally

logger = logging.getLogger(__name__)


def initialize_smart_defaults(registry_manager: Optional[BaseRegistryManager] = None) -> bool:
    """
    Initialize the smart defaults system for the MCP server.

    This function:
    1. Loads configuration from environment or file
    2. Validates the configuration
    3. Enables smart defaults globally if configured
    4. Sets up the registry manager connection

    Args:
        registry_manager: Optional registry manager instance

    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    try:
        # Load configuration
        config = get_config()

        # Check if smart defaults are enabled
        if not config.enabled:
            logger.info("Smart Defaults are disabled in configuration")
            return True  # Not an error, just disabled

        logger.info("Initializing Smart Defaults system...")

        # Validate configuration
        issues = config.validate()
        if issues:
            logger.warning(f"Smart Defaults configuration has issues: {issues}")
            # Continue with warnings, don't fail

        # Enable smart defaults globally
        enable_smart_defaults_globally(registry_manager)

        # Log configuration summary
        logger.info(f"Smart Defaults initialized with settings:")
        logger.info(f"  - Pattern Recognition: {'enabled' if config.enable_pattern_recognition else 'disabled'}")
        logger.info(f"  - Learning Engine: {'enabled' if config.enable_learning else 'disabled'}")
        logger.info(f"  - Field Suggestions: {'enabled' if config.enable_field_suggestions else 'disabled'}")
        logger.info(f"  - Storage Path: {config.learning_storage_path}")
        logger.info(
            f"  - Confidence Thresholds: suggestion={config.min_confidence_for_suggestion}, auto-fill={config.min_confidence_for_auto_fill}"
        )
        logger.info(
            f"  - Privacy: anonymize={'yes' if config.anonymize_values else 'no'}, excluded_fields={len(config.excluded_fields)}"
        )

        logger.info("✅ Smart Defaults system initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Smart Defaults: {e}")
        logger.info("Server will continue without Smart Defaults")
        return False


def get_smart_defaults_status() -> dict:
    """
    Get the current status of the smart defaults system.

    Returns:
        dict: Status information including enabled features and statistics
    """
    try:
        config = get_config()

        return {
            "enabled": config.enabled,
            "features": {
                "pattern_recognition": config.enable_pattern_recognition,
                "learning": config.enable_learning,
                "field_suggestions": config.enable_field_suggestions,
                "caching": config.enable_caching,
                "multi_step_learning": config.enable_multi_step_learning,
            },
            "configuration": {
                "storage_path": str(config.learning_storage_path),
                "retention_days": config.learning_retention_days,
                "confidence_thresholds": {
                    "suggestion": config.min_confidence_for_suggestion,
                    "auto_fill": config.min_confidence_for_auto_fill,
                    "high_confidence": config.high_confidence_threshold,
                },
                "privacy": {
                    "anonymize": config.anonymize_values,
                    "excluded_fields_count": len(config.excluded_fields),
                    "excluded_contexts_count": len(config.excluded_contexts),
                },
            },
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


# Usage example for main server file:
#
# from smart_defaults_init import initialize_smart_defaults
#
# # During server startup:
# if initialize_smart_defaults(registry_manager):
#     logger.info("Smart Defaults are available")
# else:
#     logger.warning("Smart Defaults could not be initialized")
