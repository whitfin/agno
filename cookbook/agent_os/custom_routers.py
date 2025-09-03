"""
Example AgentOS app with custom routers.
"""

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.anthropic import Claude
from agno.os import AgentOS
from agno.tools.duckduckgo import DuckDuckGoTools
from fastapi import APIRouter, FastAPI

# Setup the database
db = PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai")

# Setup basic agents, teams and workflows
web_research_agent = Agent(
    name="Web Research Agent",
    model=Claude(id="claude-sonnet-4-0"),
    db=db,
    tools=[DuckDuckGoTools()],
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
)

# Custom FastAPI app with custom router
custom_app = FastAPI()
router = APIRouter()


@router.post("/customers")
async def get_customers():
    return [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
        },
        {
            "id": 2,
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
        },
    ]


custom_app.include_router(router)


# Setup our AgentOS app
agent_os = AgentOS(
    description="Example app with custom routers",
    agents=[web_research_agent],
    fastapi_app=custom_app,
)
app = agent_os.get_app()


if __name__ == "__main__":
    """Run our AgentOS.

    You can see the configuration and available apps at:
    http://localhost:7777/config

    """
    agent_os.serve(app="custom_routers:app", reload=True)
