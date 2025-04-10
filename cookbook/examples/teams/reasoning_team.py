from pathlib import Path

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Search Agent",
    role="Handle web search requests",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=["Always include sources"],
)

finance_agent = Agent(
    name="Finance Agent",
    role="Handle financial data requests",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)
    ],
    instructions=["Use tables to display data"],
)

team_leader = Team(
    name="Reasoning Team Leader",
    mode="route",
    model=Claude(id="claude-3-7-sonnet-latest"),
    members=[
        web_agent,
        finance_agent,
    ],
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "You are a team of agents that can answer questions about the web, finance, images, audio, and files.",
        "You can use your member agents to answer the questions.",
        "if you are asked about a file, use the file analysis agent to analyze the file.",
    ],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    show_members_responses=True,
)

team_leader.print_response(
    "Hi", stream=True, stream_intermediate_steps=True, show_full_reasoning=True
)
