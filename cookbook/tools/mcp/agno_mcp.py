import asyncio
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools


async def run_agent(message: str) -> None:
    async with MCPTools(
        transport="streamable-http", url="https://docs-v2.agno.com/mcp"
    ) as agno_tools:
        agent = Agent(
            model=OpenAIChat(id="gpt-5"),
            tools=[agno_tools],
        )
        await agent.aprint_response(input=message, stream=True, markdown=True)


if __name__ == "__main__":
    asyncio.run(run_agent("What is Agno?"))
