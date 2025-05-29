from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Tool for generating haikus (frontend-only tool)
generate_haiku_tool = Function(
    name="generate_haiku",
    description=(
        "Generate a traditional 3-line haiku in Japanese with English translation. "
        "This tool MUST be called to create any haiku."
    ),
    parameters={
        "type": "object",
        "properties": {
            "japanese": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Three-line haiku in Japanese (one string per line).",
            },
            "english": {
                "type": "array",
                "items": {"type": "string"},
                "description": "English translation (one string per line).",
            }
        },
        "required": ["japanese", "english"],
        "additionalProperties": False
    },
    # No entrypoint - this is a frontend-only tool
)

# Simple haiku generator agent
HaikuGeneratorAgent = Agent(
    name="HaikuGenerator",
    model=OpenAIChat(id="gpt-4o"),
    description="Haiku generator that outputs through the generate_haiku tool.",
    instructions=(
        "You are a haiku generator assistant. Your ONLY function is to create haikus using the generate_haiku tool.\n\n"
        "IMPORTANT RULES:\n"
        "1. You MUST ALWAYS use the generate_haiku tool to create haikus\n"
        "2. NEVER write haikus directly in your response\n"
        "3. NEVER provide haikus as plain text\n"
        "4. When asked for a haiku, immediately call the generate_haiku tool\n"
        "5. The tool requires two arrays: japanese (3 lines) and english (3 lines)\n"
        "6. Follow the traditional 5-7-5 syllable pattern\n"
        "7. After calling the tool, provide a brief acknowledgment like 'I've generated a haiku for you.'\n"
        "8. Only call the generate_haiku tool ONCE per request. Do not repeat tool calls.\n\n"
        "Remember: Use the tool ONCE and then respond with acknowledgment."
    ),
    tools=[generate_haiku_tool],
    markdown=True,
) 