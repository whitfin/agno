from dataclasses import dataclass
from os import getenv
from typing import Optional
from agno.models.openai.like import OpenAILike


@dataclass
class Vllm(OpenAILike):
    """
    Use any model served by `vllm.entrypoints.openai.api_server`
    (OpenAI-compatible REST).  Example:

        $ python -m vllm.entrypoints.openai.api_server \
            --model /path/llama-3-8b-instruct-q4_K_M \
            --port 8000

        from agno.models.vllm import Vllm
        model = Vllm(id="llama-3-8b-instruct-q4_K_M")
    """

    # Agno metadata
    id: str = "not-provided"
    name: str = "vLLM"
    provider: str = "vLLM"

    # REST endpoint params
    api_key: Optional[str] = getenv("VLLM_API_KEY", "not-required")
    base_url: str = getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    max_tokens: int = 1024