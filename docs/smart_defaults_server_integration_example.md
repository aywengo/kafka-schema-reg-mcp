"""
Example integration for Smart Defaults in the main server

This shows how to integrate smart defaults into kafka_schema_registry_unified_mcp.py
Add these lines to the main server file during initialization.
"""

# Add this import at the top of kafka_schema_registry_unified_mcp.py
from smart_defaults_init import initialize_smart_defaults, get_smart_defaults_status

# In the main server initialization (after creating registry_manager), add:
def initialize_server_features(registry_manager):
    """Initialize optional server features"""
    
    # Initialize Smart Defaults
    try:
        if initialize_smart_defaults(registry_manager):
            logger.info("✅ Smart Defaults feature is available")
        else:
            logger.info("ℹ️  Smart Defaults feature is disabled or unavailable")
    except Exception as e:
        logger.warning(f"⚠️  Smart Defaults initialization error: {e}")
        logger.info("Server will continue without Smart Defaults")
    
    # Add other feature initializations here...

# Add a tool to check smart defaults status (optional)
@mcp.tool()
async def get_smart_defaults_status_tool():
    """
    Get the current status and configuration of the Smart Defaults system.
    
    Returns information about enabled features, configuration settings,
    and current learning statistics.
    """
    try:
        status = get_smart_defaults_status()
        
        return {
            "status": "success",
            "smart_defaults": status,
            "message": "Smart Defaults status retrieved successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve Smart Defaults status"
        }

# Example of complete initialization in main():
async def main():
    """Main server initialization"""
    
    # ... existing initialization code ...
    
    # Initialize registry manager
    registry_manager = SchemaRegistryManager(...)
    
    # Initialize optional features
    initialize_server_features(registry_manager)
    
    # ... rest of server startup ...
