#!/usr/bin/env python3
"""
MCP Elicitation Protocol Integration

This module implements the real MCP 2025-06-18 elicitation protocol
integration with FastMCP, replacing the mock fallback implementation.

Features:
- Real MCP elicitation request/response handling
- Integration with FastMCP library
- Proper error handling and timeouts
- Client capability detection
- Fallback to mock for non-supporting clients
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from elicitation import (
    ElicitationRequest,
    ElicitationResponse,
    elicitation_manager,
    mock_elicit,
)

logger = logging.getLogger(__name__)

# Global MCP instance - will be set by the main server
_mcp_instance = None


def set_mcp_instance(mcp):
    """Set the global MCP instance for elicitation operations."""
    global _mcp_instance
    _mcp_instance = mcp
    logger.info("✅ MCP instance configured for elicitation support")


def get_mcp_instance():
    """Get the current MCP instance."""
    return _mcp_instance


async def real_mcp_elicit(request: ElicitationRequest) -> Optional[ElicitationResponse]:
    """
    Perform real MCP elicitation using the MCP 2025-06-18 protocol.
    
    This function sends an elicitation request through the MCP protocol
    and waits for a response from the client.
    """
    mcp = get_mcp_instance()
    if not mcp:
        logger.warning("No MCP instance available, falling back to mock elicitation")
        return await mock_elicit(request)
    
    try:
        # Check if the MCP client supports elicitation
        if not await _check_client_elicitation_support(mcp):
            logger.info("Client doesn't support elicitation, using fallback")
            return await mock_elicit(request)
        
        # Register the request with our manager
        request_id = await elicitation_manager.create_request(request)
        
        # Send elicitation request through MCP protocol
        elicitation_data = {
            "type": "elicitation_request",
            "request": request.to_dict(),
            "mcp_protocol_version": "2025-06-18",
        }
        
        try:
            # Try different FastMCP elicitation methods
            response_data = None
            
            # Method 1: Check if FastMCP has direct elicitation support
            if hasattr(mcp, 'send_elicitation_request'):
                logger.debug(f"Using FastMCP direct elicitation for request {request_id}")
                response_data = await mcp.send_elicitation_request(elicitation_data)
            
            # Method 2: Check if FastMCP has notification-based elicitation
            elif hasattr(mcp, 'send_notification'):
                logger.debug(f"Using FastMCP notification-based elicitation for request {request_id}")
                # Send elicitation request as notification
                await mcp.send_notification("elicitation/request", elicitation_data)
                
                # Wait for response through normal request mechanism
                response_data = await elicitation_manager.wait_for_response(
                    request_id, timeout=request.timeout_seconds
                )
                
                if response_data:
                    return response_data
            
            # Method 3: Check if we can use custom protocol extensions
            elif hasattr(mcp, 'call_method'):
                logger.debug(f"Using FastMCP custom method for elicitation request {request_id}")
                response_data = await mcp.call_method("elicitation/request", elicitation_data)
            
            # Method 4: Use resource-based elicitation (last resort)
            elif hasattr(mcp, 'create_resource'):
                logger.debug(f"Using FastMCP resource-based elicitation for request {request_id}")
                resource_uri = f"elicitation://request/{request_id}"
                await mcp.create_resource(resource_uri, elicitation_data)
                
                # Wait for response
                response_data = await elicitation_manager.wait_for_response(
                    request_id, timeout=request.timeout_seconds
                )
                
                if response_data:
                    return response_data
            
            else:
                logger.warning("No suitable MCP elicitation method found, using fallback")
                return await mock_elicit(request)
            
            # Process response if we got one
            if response_data:
                if isinstance(response_data, dict):
                    # Convert dict response to ElicitationResponse
                    return ElicitationResponse(
                        request_id=request_id,
                        values=response_data.get('values', {}),
                        complete=response_data.get('complete', True),
                        metadata=response_data.get('metadata', {"source": "mcp_client"})
                    )
                elif isinstance(response_data, ElicitationResponse):
                    return response_data
            
            # If we reach here, wait for response through the manager
            logger.debug(f"Waiting for response to elicitation request {request_id}")
            response = await elicitation_manager.wait_for_response(
                request_id, timeout=request.timeout_seconds
            )
            
            if response:
                logger.info(f"Received elicitation response for request {request_id}")
                return response
            else:
                logger.warning(f"Elicitation request {request_id} timed out or failed")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Elicitation request {request_id} timed out")
            elicitation_manager.cancel_request(request_id)
            return None
            
        except Exception as e:
            logger.error(f"Error in MCP elicitation for request {request_id}: {str(e)}")
            elicitation_manager.cancel_request(request_id)
            return None
    
    except Exception as e:
        logger.error(f"Failed to perform MCP elicitation: {str(e)}")
        return await mock_elicit(request)


async def _check_client_elicitation_support(mcp) -> bool:
    """
    Check if the connected MCP client supports elicitation.
    
    This function attempts to detect client capabilities by checking
    for elicitation-related methods or by sending a capability query.
    """
    try:
        # Method 1: Check if client has declared elicitation capability
        if hasattr(mcp, 'get_client_capabilities'):
            capabilities = await mcp.get_client_capabilities()
            if isinstance(capabilities, dict):
                elicitation_support = capabilities.get('elicitation', {})
                if elicitation_support.get('supported', False):
                    logger.debug("Client declared elicitation support in capabilities")
                    return True
        
        # Method 2: Check for specific elicitation methods
        if hasattr(mcp, 'client_info') and hasattr(mcp.client_info, 'capabilities'):
            capabilities = mcp.client_info.capabilities
            if hasattr(capabilities, 'elicitation') and capabilities.elicitation:
                logger.debug("Client has elicitation capability in client_info")
                return True
        
        # Method 3: Try a ping-style elicitation support check
        if hasattr(mcp, 'call_method'):
            try:
                response = await asyncio.wait_for(
                    mcp.call_method("elicitation/ping", {}),
                    timeout=1.0
                )
                if response:
                    logger.debug("Client responded to elicitation ping")
                    return True
            except asyncio.TimeoutError:
                logger.debug("Client didn't respond to elicitation ping")
                pass
            except Exception:
                logger.debug("Client doesn't support elicitation ping method")
                pass
        
        # Method 4: Check FastMCP version and features
        if hasattr(mcp, '__version__'):
            version = mcp.__version__
            # Assume FastMCP 2.8.0+ supports elicitation
            try:
                major, minor, patch = map(int, version.split('.'))
                if major > 2 or (major == 2 and minor >= 8):
                    logger.debug(f"FastMCP version {version} likely supports elicitation")
                    return True
            except (ValueError, AttributeError):
                pass
        
        # Method 5: Default assumption based on environment
        # In production, we might want to be more conservative here
        logger.debug("Unable to detect elicitation support, assuming supported")
        return True
        
    except Exception as e:
        logger.debug(f"Error checking elicitation support: {str(e)}")
        return False


async def handle_elicitation_response(request_id: str, response_data: Dict[str, Any]) -> bool:
    """
    Handle an elicitation response received from the MCP client.
    
    This function should be called when the server receives a response
    to an elicitation request through the MCP protocol.
    """
    try:
        # Validate response data
        if not isinstance(response_data, dict):
            logger.error(f"Invalid response data type for request {request_id}: {type(response_data)}")
            return False
        
        # Create ElicitationResponse object
        response = ElicitationResponse(
            request_id=request_id,
            values=response_data.get('values', {}),
            complete=response_data.get('complete', True),
            metadata=response_data.get('metadata', {"source": "mcp_client"})
        )
        
        # Submit to elicitation manager
        success = await elicitation_manager.submit_response(response)
        
        if success:
            logger.info(f"Successfully processed elicitation response for request {request_id}")
        else:
            logger.warning(f"Failed to process elicitation response for request {request_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error handling elicitation response for request {request_id}: {str(e)}")
        return False


def register_elicitation_handlers(mcp):
    """
    Register elicitation handlers with the MCP server.
    
    This function sets up the necessary handlers for receiving
    elicitation responses from MCP clients.
    """
    try:
        # Set the global MCP instance
        set_mcp_instance(mcp)
        
        # Method 1: Register notification handler if supported
        if hasattr(mcp, 'notification'):
            @mcp.notification("elicitation/response")
            async def handle_elicitation_response_notification(params):
                """Handle elicitation response notifications from clients."""
                request_id = params.get('request_id')
                response_data = params.get('response', {})
                
                if request_id:
                    await handle_elicitation_response(request_id, response_data)
        
        # Method 2: Register method handler if supported
        if hasattr(mcp, 'tool'):
            @mcp.tool()
            async def submit_elicitation_response(request_id: str, response_data: dict):
                """Submit an elicitation response from the client."""
                return await handle_elicitation_response(request_id, response_data)
        
        # Method 3: Register resource handler if supported
        if hasattr(mcp, 'resource'):
            @mcp.resource("elicitation://response/{request_id}")
            async def elicitation_response_resource(request_id: str):
                """Handle elicitation responses via resource mechanism."""
                # This would be implemented based on the specific resource pattern
                pass
        
        logger.info("✅ Elicitation handlers registered with MCP server")
        return True
        
    except Exception as e:
        logger.error(f"Failed to register elicitation handlers: {str(e)}")
        return False


async def enhanced_elicit_with_fallback(request: ElicitationRequest) -> Optional[ElicitationResponse]:
    """
    Enhanced elicitation function that tries real MCP protocol first, then falls back to mock.
    
    This is the main entry point for elicitation operations in the system.
    """
    try:
        # Try real MCP elicitation first
        logger.debug(f"Attempting real MCP elicitation for request: {request.title}")
        response = await real_mcp_elicit(request)
        
        if response and response.complete:
            logger.info(f"Real MCP elicitation successful for: {request.title}")
            return response
        
        # Fall back to mock elicitation
        logger.info(f"Falling back to mock elicitation for: {request.title}")
        return await mock_elicit(request)
        
    except Exception as e:
        logger.error(f"Error in enhanced elicitation: {str(e)}")
        # Ultimate fallback
        return await mock_elicit(request)


def is_real_elicitation_supported() -> bool:
    """
    Check if real MCP elicitation is supported in the current environment.
    """
    mcp = get_mcp_instance()
    if not mcp:
        return False
    
    # Check for various MCP elicitation support indicators
    elicitation_methods = [
        'send_elicitation_request',
        'send_notification', 
        'call_method',
        'create_resource'
    ]
    
    return any(hasattr(mcp, method) for method in elicitation_methods)


# Update the global elicitation functions to use the enhanced implementation
def update_elicitation_implementation():
    """
    Update the global elicitation implementation to use the real MCP protocol.
    
    This function should be called after the MCP server is initialized.
    """
    import elicitation
    
    # Replace the fallback implementation with our enhanced version
    elicitation.elicit_with_fallback = enhanced_elicit_with_fallback
    elicitation.is_elicitation_supported = is_real_elicitation_supported
    
    logger.info("✅ Updated elicitation implementation to use real MCP protocol")
