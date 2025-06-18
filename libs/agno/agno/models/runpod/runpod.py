from dataclasses import dataclass
from os import getenv
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse

try:
    import runpod
    from runpod import Endpoint
except ImportError:
    raise ImportError("`runpod` not installed. Please install using `pip install runpod`")


@dataclass
class RunPod(Model):
    endpoint_id: str
    api_key: Optional[str] = None
    timeout: int = 300

    def __post_init__(self):
        super().__post_init__()
        
        # Set API key
        self.api_key = self.api_key or getenv("RUNPOD_API_KEY")
        if self.api_key:
            runpod.api_key = self.api_key

    def invoke(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Any:
        """Send messages to RunPod endpoint and get response."""
        
        input_data = self._format_messages(messages)
        
        # Call the endpoint
        endpoint = Endpoint(self.endpoint_id)
        response = endpoint.run_sync(input_data, timeout=self.timeout)
        
        return response

    def _format_messages(self, messages: List[Message]) -> Dict[str, Any]:
        """Convert Agno messages to RunPod endpoint input format."""
        
        # Simple approach: try common patterns
        # 1. If last message is from user, send as prompt/input
        if messages and messages[-1].role == "user":
            return {"input": messages[-1].content}
        
        # 2. Format as chat messages for chat-style endpoints  
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content or ""
            })
        
        return {"input": {"messages": formatted_messages}}

    def parse_provider_response(
        self,
        response: Any,
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
    ) -> ModelResponse:
        """Parse RunPod response into ModelResponse."""
        
        model_response = ModelResponse()
        
        # Handle common response formats
        if isinstance(response, str):
            model_response.content = response
        elif isinstance(response, dict):
            # Try common keys
            content = (
                response.get("output") or 
                response.get("text") or 
                response.get("content") or
                response.get("generated_text") or
                str(response)
            )
            model_response.content = content
        else:
            model_response.content = str(response)
        
        model_response.role = "assistant"
        return model_response
