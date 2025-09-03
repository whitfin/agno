from contextlib import asynccontextmanager

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.os import AgentOS
from agno.tools.mcp import MCPTools
from fastapi import FastAPI

# Setup your database
db = SqliteDb(db_file="agno.db")

# Define our Agent first (before the lifespan function)
agent = Agent(
    name="Agno Agent",
    model=Claude(id="claude-sonnet-4-0"),
    db=db,
    # Add the persisted session history to the context
    add_history_to_context=True,
    # Specify how many messages to add to the context
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
)


# This is required to start the MCP connection correctly in the FastAPI lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MCP connection lifecycle inside a FastAPI app"""
    global mcp_tools

    # Startup logic: connect to our MCP server
    mcp_tools = MCPTools(
        transport="streamable-http", url="https://docs-v2.agno.com/mcp"
    )
    await mcp_tools.connect()

    # Add the MCP tools to our Agent
    agent.tools = [mcp_tools]

    yield

    # Shutdown: Close MCP connection
    await mcp_tools.close()


# Create FastAPI app with lifespan
fastapi_app = FastAPI(lifespan=lifespan)

# Pass the FastAPI app to AgentOS
agent_os = AgentOS(agents=[agent], fastapi_app=fastapi_app)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="agno_mcp:app", reload=True)
