import asyncio
import logging
from dataclasses import dataclass
from json import loads
from os import getenv
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

import httpx

from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.models.openai.like import OpenAILike
from agno.models.response import ModelResponse

logger = logging.getLogger(__name__)


@dataclass
class Perplexity(OpenAILike):
    """Perplexity AI chat model with citation support"""

    id: str = "sonar"
    name: str = "Perplexity"
    provider: str = "Perplexity: " + id
    api_key: Optional[str] = getenv("PERPLEXITY_API_KEY")
    base_url: str = "https://api.perplexity.ai/"
    max_tokens: int = 1024
    session: Optional[httpx.AsyncClient] = None
    timeout: float = 60.0  # 60 seconds timeout

    def __post_init__(self):
        super().__post_init__()
        if not self.session:
            self.session = httpx.AsyncClient(timeout=self.timeout)

    def _prepare_chat_request(self, messages, temperature, max_tokens, stream, **kwargs):
        """Prepare request payload with Perplexity-specific parameters"""
        payload = {
            "model": self.id,
            "messages": [self._format_message(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
        }

        # Add Perplexity-specific parameters
        if "search_domain_filter" in kwargs:
            payload["search_domain_filter"] = kwargs["search_domain_filter"]
        if "search_recency_filter" in kwargs:
            payload["search_recency_filter"] = kwargs["search_recency_filter"]

        return payload

    def _process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add citations to response content if present"""
        citations = response.get("citations", [])
        if citations and "choices" in response and response["choices"]:
            original_content = response["choices"][0]["message"]["content"]
            citation_text = "\n\nSources:\n" + "\n".join(f"- {cite}" for cite in citations)
            response["choices"][0]["message"]["content"] = original_content + citation_text
        return response

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an async request to the Perplexity API"""
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is not set")

        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Remove stream from kwargs if present as it's not supported in the request method
        kwargs.pop("stream", None)

        try:
            response = await self.session.request(method, url, headers=headers, **kwargs)

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Perplexity API error (status {response.status_code}): {error_detail}")
                raise ModelProviderError(
                    f"API request failed with status {response.status_code}: {error_detail}", self.name, self.id
                )

            response_json = response.json()
            return self._process_response(response_json)

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout} seconds: {str(e)}")
            raise ModelProviderError(f"Request timed out after {self.timeout} seconds", self.name, self.id) from e
        except Exception as e:
            logger.error(f"Unexpected error calling Perplexity API: {str(e)}")
            raise ModelProviderError(str(e), self.name, self.id) from e

    def invoke(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Synchronous chat completion"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.ainvoke(messages, **kwargs))

    async def ainvoke(
        self,
        messages: List[Message],
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Enhanced chat method with citation support"""
        try:
            payload = self._prepare_chat_request(messages, temperature, max_tokens, stream, **kwargs)
            response = await self.request("post", "chat/completions", json=payload)
            return response
        except Exception as e:
            logger.error(f"Error in ainvoke: {str(e)}")
            raise ModelProviderError(str(e), self.name, self.id) from e

    def invoke_stream(self, messages: List[Message], **kwargs) -> Iterator[Dict[str, Any]]:
        """Synchronous streaming chat completion"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def _stream():
            async for chunk in self.ainvoke_stream(messages, **kwargs):
                yield chunk

        return loop.run_until_complete(_stream())

    async def ainvoke_stream(
        self,
        messages: List[Message],
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Asynchronous streaming chat completion"""
        payload = self._prepare_chat_request(messages, temperature, max_tokens, True, **kwargs)

        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with self.session.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_detail = await response.text()
                    raise ValueError(f"API request failed with status {response.status_code}: {error_detail}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data != "[DONE]":
                            try:
                                response_json = loads(data)
                                yield self._process_response(response_json)
                            except Exception as e:
                                raise ValueError(f"Failed to parse streaming response: {str(e)}\nData: {data}")
        except httpx.TimeoutException as e:
            raise ValueError(
                f"Streaming request timed out after {self.timeout} seconds. Try increasing the timeout value."
            ) from e
        except Exception as e:
            raise ValueError(f"Streaming request failed: {str(e)}") from e

    def parse_provider_response(self, response: Dict[str, Any]) -> ModelResponse:
        """Parse the raw response from Perplexity into a ModelResponse"""
        model_response = ModelResponse()
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice:
                model_response.content = choice["message"].get("content")
                model_response.role = choice["message"].get("role")
                if "function_call" in choice["message"]:
                    model_response.tool_calls = [choice["message"]["function_call"]]
        if "usage" in response:
            model_response.response_usage = response["usage"]
        return model_response

    def parse_provider_response_delta(self, response: Dict[str, Any]) -> ModelResponse:
        """Parse the streaming response from Perplexity into a ModelResponse"""
        model_response = ModelResponse()
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "delta" in choice:
                delta = choice["delta"]
                model_response.content = delta.get("content", "")
                model_response.role = delta.get("role")
                if "function_call" in delta:
                    model_response.tool_calls = [delta["function_call"]]
        if "usage" in response:
            model_response.response_usage = response["usage"]
        return model_response
