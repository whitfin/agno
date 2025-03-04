import pytest
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools


def test_collaborative_team_discussion():
    # Create member agents
    researcher_1 = Agent(
        name="Web Researcher",
        role="Research topics on the web",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="Find and summarize web content"
    )

    researcher_2 = Agent(
        name="HackerNews Researcher", 
        model=OpenAIChat(id="gpt-4o"),
        tools=[HackerNewsTools()],
        instructions="Find relevant HackerNews discussions"
    )

    # Create collaborative team
    team = Team(
        name="Research Team",
        mode="collaborative",
        model=OpenAIChat(id="gpt-4o"),
        members=[researcher_1, researcher_2],
        instructions=[
            "Lead a collaborative discussion between researchers",
            "Synthesize findings into a coherent response"
        ],
        success_criteria="Team reaches consensus on findings",
        send_team_context_to_members=True,
        update_team_context=True
    )

    # Test team discussion
    response = team.run("What are the latest developments in AI?")

    assert response.content is not None
    assert len(response.member_responses) == 2
    assert all(r.content is not None for r in response.member_responses)


def test_collaborative_team_with_context():
    agent_1 = Agent(
        name="Agent 1",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Provide initial thoughts"
    )

    agent_2 = Agent(
        name="Agent 2",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Build on previous thoughts"
    )

    team = Team(
        name="Context Team",
        mode="collaborative",
        model=OpenAIChat(id="gpt-4o"),
        members=[agent_1, agent_2],
        context={"topic": "AI Safety"},
        add_context=True,
        send_team_context_to_members=True,
        update_team_context=True
    )

    response = team.run("What are your thoughts on this topic?")
    
    assert response.content is not None
    assert len(response.member_responses) == 2
    assert all("AI Safety" in str(r.content) for r in response.member_responses)


def test_collaborative_team_reasoning():
    agent_1 = Agent(
        name="First Thinker",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Provide initial analysis"
    )

    agent_2 = Agent(
        name="Second Thinker",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Critique and refine analysis"
    )

    team = Team(
        name="Reasoning Team",
        mode="collaborative",
        model=OpenAIChat(id="gpt-4o"),
        members=[agent_1, agent_2],
        instructions="Guide a reasoned discussion",
        reasoning=True,
        reasoning_min_steps=2,
        reasoning_max_steps=4
    )

    response = team.run("Analyze the pros and cons of remote work")

    assert response.content is not None
    assert response.extra_data is not None
    assert response.extra_data.reasoning_steps is not None
    assert len(response.extra_data.reasoning_steps) >= 2 