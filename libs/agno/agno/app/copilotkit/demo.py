"""Demo server entrypoint for CopilotKit backend.

Run with:
    uvicorn agno.app.copilotkit.demo:app --reload
"""
from typing import Generator
import logging, sys

# Enable debug-level logging to see backend traces
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from agno.agent.agent import Agent
from agno.models.openai.chat import OpenAIChat
from agno.app.copilotkit.app import CopilotKitApp


class GPTAgent(Agent):
    """Agent backed by OpenAI Chat model. Requires OPENAI_API_KEY env var."""

    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4o"),  # or "gpt-4o" if you have access
            description="You are a helpful AI assistant.",
            instructions="You are a helpful conversational agent. You are given a conversation history and a new message. You need to respond to the new message based on the conversation history.",
            stream=True,
        )


# Create FastAPI app instance
app = CopilotKitApp(agent=GPTAgent()).get_app(use_async=False) 