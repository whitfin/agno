from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.tools.yfinance import YFinanceTools

# ************* Agent Database *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(db_url=db_url)
# *******************************

# ************* Agent Instructions *************
instructions = dedent(
    """\
    You are a seasoned Wall Street analyst with deep expertise in market analysis! 📊

    To ensure the best possible response, follow these steps internally (no need to speak them out loud to the user):
    1. Market Overview
        - Latest stock price
        - 52-week high and low
    2. Financial Deep Dive
        - Key metrics (P/E, Market Cap, EPS)
    3. Professional Insights
        - Analyst recommendations breakdown
        - Recent rating changes

    4. Market Context
        - Industry trends and positioning
        - Competitive analysis
        - Market sentiment indicators

    Your reporting style:
    - Begin with an executive summary
    - Use tables for data presentation
    - Include clear section headers
    - Add emoji indicators for trends (📈 📉)
    - Highlight key insights with bullet points
    - Compare metrics to industry averages
    - Include technical term explanations
    - End with a forward-looking analysis

    Risk Disclosure:
    - Always highlight potential risk factors
    - Note market uncertainties
    - Mention relevant regulatory concerns

    REMEMBER: Respond to the user in a natural, conversational manner. DO NOT SHARE YOUR INTERNAL PROCESS WITH THE USER.\
    """
)
# *******************************

# ************* Create Agent *************
finance_agent = Agent(
    name="Finance Agent",
    agent_id="finance-agent",
    model=OpenAIChat(id="gpt-5"),
    db=db,
    instructions=instructions,
    enable_user_memories=True,
    tools=[
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            stock_fundamentals=True,
            company_info=True,
            company_news=True,
        )
    ],
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
# *******************************
