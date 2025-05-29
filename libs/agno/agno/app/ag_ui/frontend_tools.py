"""Frontend tool support for AG-UI protocol.

This module provides utilities for handling frontend-only tools that are executed
on the client side rather than the server side.
"""

from typing import Any, Dict, Optional, List
import json
from agno.utils.log import logger


class FrontendToolHandler:
    """Handles execution of frontend-only tools.
    
    Frontend tools are defined in the UI and their execution happens on the client side.
    The backend just needs to acknowledge the tool call and return a placeholder response.
    """
    
    @staticmethod
    def create_handler(tool_name: str):
        """Create a handler function for a frontend tool.
        
        Args:
            tool_name: Name of the frontend tool
            
        Returns:
            A function that can be used as the tool's entrypoint
        """
        def frontend_tool_handler(**kwargs) -> str:
            """Generic handler for frontend tools."""
            logger.debug(f"Frontend tool '{tool_name}' called with args: {kwargs}")
            
            # Return appropriate responses based on common frontend tool patterns
            if tool_name == "update_steps":
                steps = kwargs.get("steps", [])
                return f"Updated UI with {len(steps)} steps"
            
            elif tool_name == "start_step":
                step_name = kwargs.get("step_name", "")
                return f"UI notified: Starting '{step_name}'"
            
            elif tool_name == "complete_step":
                step_name = kwargs.get("step_name", "")
                return f"UI notified: Completed '{step_name}'"
            
            elif tool_name == "setBackgroundColor":
                color = kwargs.get("color", "")
                return f"UI updated: Background color set to {color}"
            
            elif tool_name == "updateState":
                return "UI state updated"
            
            elif tool_name == "displayChart":
                chart_type = kwargs.get("type", "chart")
                return f"UI rendered: {chart_type}"
            
            elif tool_name == "showNotification":
                message = kwargs.get("message", "")
                return f"UI notification shown: {message}"
            
            elif tool_name == "navigateTo":
                path = kwargs.get("path", "")
                return f"UI navigated to: {path}"
            
            elif tool_name == "generate_haiku":
                return "Haiku displayed in UI"
            
            else:
                # Generic response for unknown frontend tools
                return f"Frontend tool '{tool_name}' executed"
        
        return frontend_tool_handler
    
    @staticmethod
    def is_frontend_tool(tool: Any) -> bool:
        """Check if a tool is a frontend-only tool.
        
        A tool is considered frontend-only if:
        1. It has _frontend_only=True attribute
        2. It has no entrypoint (entrypoint=None)
        3. Its name matches known frontend tool patterns
        
        Args:
            tool: Tool object to check
            
        Returns:
            True if the tool is frontend-only
        """
        # Check for explicit frontend-only marker
        if hasattr(tool, '_frontend_only') and tool._frontend_only:
            return True
        
        # Check if tool has no entrypoint (common for frontend tools)
        if hasattr(tool, 'entrypoint') and tool.entrypoint is None:
            return True
        
        # Check for known frontend tool name patterns
        if hasattr(tool, 'name'):
            frontend_tool_patterns = [
                'update_steps', 'start_step', 'complete_step',
                'setBackgroundColor', 'updateState', 'displayChart',
                'showNotification', 'navigateTo', 'generate_haiku'
            ]
            if tool.name in frontend_tool_patterns:
                return True
        
        return False
    
    @staticmethod
    def should_emit_as_tool_call(tool: Any) -> bool:
        """Check if a tool should be emitted as a tool call event rather than executed.
        
        This is specifically for frontend tools that need to trigger frontend handlers.
        
        Args:
            tool: Tool object to check
            
        Returns:
            True if the tool should be emitted as a tool call event
        """
        return FrontendToolHandler.is_frontend_tool(tool)
    
    @staticmethod
    def ensure_tool_has_entrypoint(tool: Any) -> None:
        """Ensure a tool has a proper entrypoint.
        
        If the tool is frontend-only and lacks an entrypoint, this adds one.
        
        Args:
            tool: Tool object to process
        """
        if not hasattr(tool, 'entrypoint'):
            return
        
        if tool.entrypoint is None and not FrontendToolHandler.is_frontend_tool(tool):
            tool_name = getattr(tool, 'name', 'unknown')
            logger.debug(f"Adding entrypoint to frontend-only tool: {tool_name}")
            tool.entrypoint = FrontendToolHandler.create_handler(tool_name)
            tool._frontend_only = True
    
    @staticmethod
    def extract_tools_for_frontend(tools_data: List[Any]) -> List[Dict[str, Any]]:
        """Extract frontend tool calls from AGno tool data.
        
        This processes tool call data and extracts the frontend tools that should
        be sent to the frontend as tool call events.
        
        Args:
            tools_data: List of tool call data from AGno response
            
        Returns:
            List of frontend tool call dictionaries
        """
        frontend_tools = []
        
        for tool_info in tools_data:
            if isinstance(tool_info, dict):
                tool_name = tool_info.get("tool_name", "")
                
                # Check if this is a frontend tool by name or structure
                if tool_name in ['update_steps', 'start_step', 'complete_step']:
                    frontend_tools.append({
                        "tool_call_id": tool_info.get("tool_call_id", ""),
                        "tool_name": tool_name,
                        "tool_args": tool_info.get("tool_args", {}),
                        "is_frontend_tool": True
                    })
        
        return frontend_tools
    
    @staticmethod
    def create_tool_call_events(tool_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tool call events for a frontend tool.
        
        Args:
            tool_data: Tool call data dictionary
            
        Returns:
            List of event dictionaries for the tool call
        """
        tool_call_id = tool_data.get("tool_call_id", "")
        tool_name = tool_data.get("tool_name", "")
        tool_args = tool_data.get("tool_args", {})
        
        events = []
        
        # Tool call start event
        events.append({
            "type": "TOOL_CALL_START",
            "tool_call_id": tool_call_id,
            "tool_call_name": tool_name
        })
        
        # Tool call args event
        args_str = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
        events.append({
            "type": "TOOL_CALL_ARGS", 
            "tool_call_id": tool_call_id,
            "delta": args_str
        })
        
        # Tool call end event
        events.append({
            "type": "TOOL_CALL_END",
            "tool_call_id": tool_call_id
        })
        
        return events