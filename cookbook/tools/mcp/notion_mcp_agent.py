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

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

class StoryFacts(BaseModel):
    id: str = Field(..., description="ID of the Notion page")
    title: str = Field(..., description="Title of the story")
    village: str = Field(..., description="Village where the story takes place")
    main_character: str = Field(..., description="Main character of the story")
    inciting_event: str = Field(..., description="Inciting event of the story")
    portal_discovery: str = Field(..., description="Discovery of the portal")
    outcome: str = Field(..., description="Outcome of the story")
    facts: List[str] = Field(..., description="List of key factual statements about the story content")


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
            use_json_mode=True,
            instructions=dedent("""\
                Extract the key factual statements from the story on a Notion page:
                1. Use 'API-post-search' with query=<page title> filter={'property':'object','value':'page'} to find the page ID.
                2. Use 'API-retrieve-a-page' to get the title and properties; ignore all metadata except page title.
                3. Use 'API-get-block-children' to retrieve all paragraph blocks containing story text.
                4. Read the concatenated story text and identify discrete facts (e.g., main character, setting, inciting event, portal discovery, outcome).
                5. Output a JSON StoryFacts object with:
                   id: the page ID
                   title: the story title
                   facts: an ordered list of key fact statements extracted from the story text
                Respond with valid JSON only, no extra text.
            """),
            markdown=True,
            show_tool_calls=True,
            debug_mode=True,
        )

        await agent.aprint_response(
            message="Extract key facts from the story on the Notion page Short-story-1ee7ee79d1c580108159d4b7b76bfccf",
            stream=True,
        )


if __name__ == "__main__":
    asyncio.run(run_agent())
