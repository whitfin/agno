from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=["Always include sources"],
    expected_output=dedent("""\
    ## {title}

    {Answer to the user's question}
    """),
    markdown=True,
)


finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)
    ],
    instructions=["Use tables to display data"],
    expected_output=dedent("""\
    ## {title}

    {Answer to the user's question}
    """),
    markdown=True,
)

agent_team = Team(
    name="Agent Team",
    mode="proxy",
    model=OpenAIChat("gpt-4o"),
    members=[web_agent, finance_agent],
    markdown=True,
    debug_mode=True,
)

agent_team.print_response(
    "What is the latest news on NVidia?"
)
