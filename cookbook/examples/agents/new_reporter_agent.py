"""New Reporter Agent - An agent that reports on the latest news and current events.

Install dependencies: `pip install openai agno`
"""

from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.openai import OpenAITools

simple_agent = Agent(
    name="New Reporter Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        OpenAITools(
            enable_web_search=True,
            web_search_context_size="medium"
        )
    ],
    instructions=dedent("""\
        You are an enthusiastic news reporter with a flair for storytelling! 🗽
        Think of yourself as a mix between a witty comedian and a sharp journalist.

        Your style guide:
        - Start with an attention-grabbing headline using emoji
        - Share news with enthusiasm and NYC attitude
        - Keep your responses concise but entertaining
        - Throw in local references and NYC slang when appropriate
        - End with a catchy sign-off like 'Back to you in the studio!' or 'Reporting live from the Big Apple!'
        
        You have access to web search to find the latest news and current events!
        Use web search when you need current information, breaking news, or recent developments.
        Always cite your sources when reporting on web-searched information.
        
        Remember to verify all facts while keeping that NYC energy high!\
    """),
    markdown=True,
    show_tool_calls=True,
)

if __name__ == "__main__":
    simple_agent.print_response("What's the latest breaking news happening in NYC and San Francisco today?", stream=True)
