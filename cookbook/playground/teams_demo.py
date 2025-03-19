from agno.playground import Playground, serve_playground_app
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.storage.postgres import PostgresStorage

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    agent_id="web_agent",
    instructions=[
        "You are an experienced web researcher and news analyst! 🔍",
    ],
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    agent_id="finance_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)
    ],
    instructions=[
        "You are a skilled financial analyst with expertise in market data! 📊",
        "Follow these steps when analyzing financial data:",
        "Start with the latest stock price, trading volume, and daily range",
        "Present detailed analyst recommendations and consensus target prices",
        "Include key metrics: P/E ratio, market cap, 52-week range",
        "Analyze trading patterns and volume trends",
        
    ],
    show_tool_calls=True,
    markdown=True,
)

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

agent_team = Team(
    name="Financial News Team",
    description="A team of agents that search the web for financial news and analyze it.",
    members=[web_agent, finance_agent],
    model=OpenAIChat(id="gpt-4o"),
    mode="route",
    team_id="financial_news_team",
    success_criteria=dedent("""\
        A comprehensive financial news report with clear sections and data-driven insights.
    """),
    instructions=[
        "You are the lead editor of a prestigious financial news desk! 📰",
    ],
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
    send_team_context_to_members=True,
    send_team_member_interactions_to_members=False,
    update_team_context=True,
    show_members_responses=True,
    debug_mode=True,
    storage=PostgresStorage(table_name="financial_news_team", db_url=db_url),

)

app = Playground(
    teams=[agent_team],
).get_app()

if __name__ == "__main__":
    serve_playground_app("teams_demo:app", reload=True)

