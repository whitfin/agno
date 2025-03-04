import pytest
from typing import List
from pydantic import BaseModel

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools


class Article(BaseModel):
    title: str
    summary: str
    sources: List[str]


def test_coordinator_team_task_delegation():
    searcher = Agent(
        name="Web Searcher",
        role="Search the web",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="Search for relevant web content"
    )

    summarizer = Agent(
        name="Summarizer",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Create concise summaries"
    )

    team = Team(
        name="Research Team",
        mode="coordinator",
        model=OpenAIChat(id="gpt-4o"),
        members=[searcher, summarizer],
        instructions=[
            "Coordinate research and summarization tasks",
            "Ensure high quality output"
        ],
        response_model=Article
    )

    response = team.run("Research the latest developments in quantum computing")

    assert isinstance(response.content, Article)
    assert response.content.title is not None
    assert response.content.summary is not None
    assert len(response.content.sources) > 0


def test_coordinator_team_sequential_tasks():
    researcher = Agent(
        name="HN Researcher",
        model=OpenAIChat(id="gpt-4o"),
        tools=[HackerNewsTools()],
        instructions="Find relevant HackerNews posts"
    )

    analyzer = Agent(
        name="Content Analyzer",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Analyze and synthesize findings"
    )

    fact_checker = Agent(
        name="Fact Checker",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Verify information accuracy"
    )

    team = Team(
        name="Sequential Team",
        mode="coordinator",
        model=OpenAIChat(id="gpt-4o"),
        members=[researcher, analyzer, fact_checker],
        instructions=[
            "Coordinate sequential research, analysis, and verification",
            "Each agent should build on previous work"
        ],
        send_team_context_to_members=True
    )

    response = team.run("Research and verify claims about a new AI breakthrough")

    assert response.content is not None
    assert len(response.member_responses) == 3
    assert all(r.content is not None for r in response.member_responses)


def test_coordinator_team_with_success_criteria():
    agent_1 = Agent(
        name="Researcher",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="Research specific claims"
    )

    agent_2 = Agent(
        name="Validator",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Validate research findings"
    )

    team = Team(
        name="Validation Team",
        mode="coordinator",
        model=OpenAIChat(id="gpt-4o"),
        members=[agent_1, agent_2],
        instructions="Coordinate research and validation",
        success_criteria="All claims must be validated with sources",
        send_team_context_to_members=True,
        update_team_context=True
    )

    response = team.run("Research and validate claims about quantum supremacy")

    assert response.content is not None
    assert "sources" in str(response.content).lower()
    assert len(response.member_responses) == 2 