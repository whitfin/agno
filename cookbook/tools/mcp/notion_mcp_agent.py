"""
Notion MCP Agent - Manages your documents

This example shows how to use the Agno MCP tools to interact with your Notion workspace.

1. Start by setting up a new internal integration in Notion: https://www.notion.so/profile/integrations
2. Export your new Notion key: `export NOTION_API_KEY=ntn_****`
3. Connect your relevant Notion pages to the integration. To do this, you'll need to visit that page, and click on the 3 dots, and select "Connect to integration".

Dependencies: pip install agno mcp openai

Usage:
  python cookbook/tools/mcp/notion_mcp_agent.py
"""

import asyncio
import json
import os
from textwrap import dedent
from typing import Any, Dict, List, Optional, Union

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from pydantic import BaseModel, Field


class StoryFacts(BaseModel):
    id: str = Field(..., description="ID of the Notion page")
    title: str = Field(..., description="Title of the story")
    village: str = Field(..., description="Village where the story takes place")
    main_character: str = Field(..., description="Main character of the story")
    inciting_event: str = Field(..., description="Inciting event of the story")
    portal_discovery: str = Field(..., description="Discovery of the portal")
    outcome: str = Field(..., description="Outcome of the story")
    facts: List[str] = Field(
        ..., description="List of key factual statements about the story content"
    )


async def run_agent():
    token = os.getenv("NOTION_API_KEY")
    if not token:
        raise ValueError(
            "Missing Notion API key: provide --NOTION_API_KEY or set NOTION_API_KEY environment variable"
        )

    command = "npx"
    args = ["-y", "@notionhq/notion-mcp-server"]
    env = {
        "OPENAPI_MCP_HEADERS": json.dumps(
            {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
        )
    }
    server_params = StdioServerParameters(command=command, args=args, env=env)

    async with MCPTools(server_params=server_params) as mcp_tools:
        agent = Agent(
            name="NotionDocsAgent",
            model=OpenAIChat(id="gpt-4o"),
            tools=[mcp_tools],
            description="Agent to extract key facts from a Notion-hosted story",
            response_model=StoryFacts,
            instructions=dedent("""\
                Extract the key factual statements from the story on a Notion page:
                Use the available MCP tools to extract the key facts from the story.
                Read the story and identify discrete facts (e.g., main character, setting, inciting event, portal discovery, outcome).
                Output a JSON StoryFacts object with:
                   id: the page ID
                   title: the story title
                   facts: an ordered list of key fact statements extracted from the story text
                Respond with valid JSON only, no extra text.
            """),
            use_json_mode=True,
            show_tool_calls=True,
            debug_mode=True,
        )

        await agent.aprint_response(
            message="Extract key facts from the story on the Notion page with title 'Short story'",
            stream=True,
        )


if __name__ == "__main__":
    asyncio.run(run_agent())
