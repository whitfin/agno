import asyncio

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools

# Setup your database
db = SqliteDb(db_file="agno.db")


async def run_agent(message: str) -> None:
    async with MCPTools(
        transport="streamable-http", url="https://docs-v2.agno.com/mcp"
    ) as agno_mcp_server:
        agent = Agent(
            db=db,
            model=Claude(id="claude-sonnet-4-0"),
            tools=[agno_mcp_server],
            # Add the persisted session history to the context
            add_history_to_context=True,
            # Specify how many messages to add to the context
            num_history_runs=3,
            markdown=True,
        )
        # Manually set the session id so we can continue across runs
        await agent.aprint_response(input=message, stream=True, session_id="session_2")


if __name__ == "__main__":
    asyncio.run(run_agent("What was my last message?"))
    asyncio.run(run_agent("What is Agno?"))
    asyncio.run(run_agent("What was my last message?"))
