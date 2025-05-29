"""Tool management and parsing for AG-UI router."""

import json
from typing import Any, Dict, List, Optional, Union

from agno.tools.function import Function


class ToolManager:
    """Manages tool normalization and merging operations."""
    
    @staticmethod
    def normalize_tool(tool: Any) -> Union[Function, Dict[str, Any]]:
        """Ensure tool is represented as an agno.tools.function.Function.
        
        Args:
            tool: Tool to normalize (Function, dict, or other)
            
        Returns:
            Normalized tool as Function or original dict if conversion fails
        """
        if isinstance(tool, Function):
            return tool
        
        if isinstance(tool, dict):
            try:
                return Function(**tool)
            except Exception:
                return tool
        
        return tool
    
    @staticmethod
    def get_tool_name(tool: Any) -> str:
        """Extract the name from a tool object.
        
        Args:
            tool: Tool object (Function, dict, or other)
            
        Returns:
            Tool name or string representation
        """
        if isinstance(tool, Function):
            return tool.name
        if isinstance(tool, dict):
            return tool.get("name", "")
        return str(tool)
    
    @classmethod
    def merge_tool_lists(
        cls, 
        static_tools: Optional[List[Any]], 
        dynamic_tools: Optional[List[Any]]
    ) -> List[Any]:
        """Merge two tool lists, deduplicating by name.
        
        Dynamic tools override static tools with the same name.
        
        Args:
            static_tools: Base list of tools
            dynamic_tools: Tools to overlay/override
            
        Returns:
            Merged list of normalized tools
        """
        merged: List[Any] = []
        seen_names: set[str] = set()
        
        # Handle None values
        static_tools = static_tools or []
        dynamic_tools = dynamic_tools or []
        
        # Add static tools first
        for tool in static_tools:
            norm_tool = cls.normalize_tool(tool)
            name = cls.get_tool_name(norm_tool)
            merged.append(norm_tool)
            seen_names.add(name)
        
        # Overlay dynamic tools (override on name collisions)
        for tool in dynamic_tools:
            norm_tool = cls.normalize_tool(tool)
            name = cls.get_tool_name(norm_tool)
            
            if name in seen_names:
                # Remove existing tool with same name
                merged = [t for t in merged if cls.get_tool_name(t) != name]
            
            merged.append(norm_tool)
            seen_names.add(name)
        
        return merged


class ToolCallParser:
    """Parser for various tool call formats."""
    
    @staticmethod
    def parse_string_format(tool_call_str: str) -> tuple[str, Dict[str, Any]]:
        """Parse string format tool calls.
        
        Handles formats like "function_name(arg1=val1, arg2=val2)"
        
        Args:
            tool_call_str: String representation of tool call
            
        Returns:
            Tuple of (tool_name, arguments_dict)
        """
        if "(" in tool_call_str and tool_call_str.endswith(")"):
            tool_name = tool_call_str.split("(")[0].strip()
            # For now, return the full string as arguments
            # TODO: Implement proper argument parsing
            return tool_name, {"raw": tool_call_str}
        
        try:
            # Try parsing as JSON
            parsed = json.loads(tool_call_str)
            if isinstance(parsed, dict):
                return parsed.get("name", "unknown_tool"), parsed.get("arguments", parsed)
        except json.JSONDecodeError:
            pass
        
        return "unknown_tool", {"raw": tool_call_str}
    
    @staticmethod
    def parse_dict_format(tool_call_dict: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Parse dictionary format tool calls.
        
        Handles both OpenAI format and direct format.
        
        Args:
            tool_call_dict: Dictionary representation of tool call
            
        Returns:
            Tuple of (tool_name, arguments_dict)
        """
        # AGno format with tool_name and tool_args
        if "tool_name" in tool_call_dict and "tool_args" in tool_call_dict:
            return tool_call_dict["tool_name"], tool_call_dict["tool_args"]
        
        # OpenAI format
        if "function" in tool_call_dict:
            func = tool_call_dict["function"]
            tool_name = func.get("name", "unknown_tool")
            args_str = func.get("arguments", "{}")
            
            try:
                arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                arguments = {"raw": args_str}
            
            return tool_name, arguments
        
        # Direct format
        tool_name = tool_call_dict.get("name", "unknown_tool")
        arguments = tool_call_dict.get("arguments", tool_call_dict)
        return tool_name, arguments
    
    @classmethod
    def parse(cls, tool_call_data: Any) -> tuple[str, Dict[str, Any]]:
        """Parse tool call data to extract name and arguments.
        
        Args:
            tool_call_data: Tool call in various formats
            
        Returns:
            Tuple of (tool_name, arguments_dict)
        """
        if isinstance(tool_call_data, str):
            return cls.parse_string_format(tool_call_data)
        elif isinstance(tool_call_data, dict):
            return cls.parse_dict_format(tool_call_data)
        
        return "unknown_tool", {} 