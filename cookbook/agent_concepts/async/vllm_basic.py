import asyncio

from agno.agent import Agent
from agno.models.vllm import Vllm

"""Async agent concept example using vLLM.

Mirrors `basic.py` in this directory but swaps the model provider to vLLM and
uses the TinyLlama 1.1-B model so it can run on CPU.

Start vLLM before running:

    python -m vllm.entrypoints.openai.api_server \
        --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
        --dtype float32
"""

agent = Agent(
    model=Vllm(id="TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
    description="You help people with their health and fitness goals.",
    instructions=["Recipes should be under 5 ingredients"],
    markdown=True,
)

# Print a response asynchronously
asyncio.run(agent.aprint_response("Share a breakfast recipe.")) 