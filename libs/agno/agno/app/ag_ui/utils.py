"""Utility functions for AG-UI router."""

import json
from typing import Any

from agno.app.ag_ui.events import BaseEvent


class CaseConverter:
    """Utility class for converting between naming conventions."""
    
    @staticmethod
    def snake_to_camel(snake_str: str) -> str:
        """Convert snake_case to camelCase.
        
        Args:
            snake_str: String in snake_case format
            
        Returns:
            String converted to camelCase
            
        Examples:
            >>> CaseConverter.snake_to_camel("hello_world")
            "helloWorld"
            >>> CaseConverter.snake_to_camel("message_id")
            "messageId"
        """
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    @classmethod
    def convert_dict_keys(cls, obj: Any) -> Any:
        """Recursively convert all snake_case keys in a dict to camelCase.
        
        Args:
            obj: Object to convert (dict, list, or primitive)
            
        Returns:
            Object with converted keys
        """
        if isinstance(obj, dict):
            return {
                cls.snake_to_camel(k): cls.convert_dict_keys(v) 
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [cls.convert_dict_keys(item) for item in obj]
        return obj


class SSEFormatter:
    """Formatter for Server-Sent Events (SSE)."""
    
    @staticmethod
    def format_event(event: BaseEvent) -> str:
        """Format an event as a Server-Sent Event.
        
        SSE format: data: <json>\\n\\n
        
        Also converts snake_case fields to camelCase for AG-UI compatibility.
        
        Args:
            event: Event to format
            
        Returns:
            SSE-formatted string
        """
        event_dict = event.model_dump(exclude_none=True)
        # Convert snake_case to camelCase for AG-UI client compatibility
        event_dict = CaseConverter.convert_dict_keys(event_dict)
        return f"data: {json.dumps(event_dict)}\n\n" 