from dataclasses import dataclass
from os import getenv
from typing import Optional

from agno.models.openai.like import OpenAILike


@dataclass
class NetMind(OpenAILike):
    """
    A class for interacting with NetMind API.

    Attributes:
        id (str): The id of the NetMind model to use.
        name (str): The name of this chat model instance.
        provider (str): The provider of the model.
        api_key (str): The API key for authenticating with the NetMind API.
        base_url (str): The base url to which the requests are sent.
    """

    id: str = "Qwen/Qwen3-32B"
    name: str = "NetMind"
    provider: str = "NetMind"
    api_key: Optional[str] = getenv("NETMIND_API_KEY")
    base_url: str = "https://api.netmind.ai/inference-api/openai/v1"
