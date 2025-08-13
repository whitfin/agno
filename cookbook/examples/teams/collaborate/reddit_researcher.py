from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.team import Team
from textwrap import dedent
import asyncio


reddit_researcher = Agent(
    name="Reddit Researcher",
    role="Research a topic on Reddit",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    add_name_to_instructions=True,
    instructions=dedent("""
    You are a Reddit researcher.
    You will be given a topic to research on Reddit.
    You will need to find the most relevant posts on Reddit.
    """),
    stream=True
)

agent_team = Team(
    name="Discussion Team",
    mode="collaborate",
    model=OpenAIChat("gpt-4o"),
    members=[
        reddit_researcher,
        # hackernews_researcher,
        # academic_paper_researcher,
        # twitter_researcher,
    ],
    instructions=[
        "You are a discussion master.",
        "You have to stop the discussion when you think the team has reached a consensus.",
    ],
    success_criteria="The team has reached a consensus.",
    enable_agentic_context=True,
    show_tool_calls=True,
    markdown=True,
    show_members_responses=True,
    stream_member_events=True
)

if __name__ == "__main__":
    async def debug_stream():
        stream = await agent_team.aprint_response(
            message="Start the discussion on the topic: 'What is the best way to learn to code?'",
            stream=True,
        )

    asyncio.run(debug_stream())