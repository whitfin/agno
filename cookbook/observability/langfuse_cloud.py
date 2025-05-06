"""Agent with Langfuse for observability

Install dependencies: `pip install langfuse openai duckduckgo-search agno`

Create your account at https://cloud.langfuse.com

Remember to export LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_HOST.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.observability.langfuse import LangfuseObservability
from agno.tools.duckduckgo import DuckDuckGoTools

agent_with_langfuse = Agent(
    name="Agent with Langfuse",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    observability=LangfuseObservability(),
    show_tool_calls=True,
    markdown=True,
)

if __name__ == "__main__":
    agent_with_langfuse.print_response(
        "Share a news story from NYC and SF.", stream=True
    )
