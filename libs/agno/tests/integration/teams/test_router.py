import pytest
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.dalle import DalleTools


def test_router_team_task_routing():
    web_agent = Agent(
        name="Web Agent",
        role="Web research",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="Search and summarize web content"
    )

    news_agent = Agent(
        name="News Agent",
        role="News research",
        model=OpenAIChat(id="gpt-4o"),
        tools=[HackerNewsTools()],
        instructions="Find relevant news articles"
    )

    image_agent = Agent(
        name="Image Agent",
        role="Image generation",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DalleTools()],
        instructions="Generate or analyze images"
    )

    team = Team(
        name="Router Team",
        mode="router",
        model=OpenAIChat(id="gpt-4o"),
        members=[web_agent, news_agent, image_agent],
        instructions="Route tasks to the most appropriate agent"
    )

    # Test web search routing
    web_response = team.run("Find information about Python programming")
    assert web_response.content is not None
    assert len(web_response.member_responses) == 1
    assert web_response.member_responses[0].agent_id == web_agent.agent_id

    # Test news routing
    news_response = team.run("What are the latest tech news stories?")
    assert news_response.content is not None
    assert len(news_response.member_responses) == 1
    assert news_response.member_responses[0].agent_id == news_agent.agent_id


def test_router_team_multiple_agents():
    researcher_1 = Agent(
        name="General Researcher",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="General web research"
    )

    researcher_2 = Agent(
        name="Tech Researcher",
        model=OpenAIChat(id="gpt-4o"),
        tools=[HackerNewsTools()],
        instructions="Tech-specific research"
    )

    team = Team(
        name="Multi-Router Team",
        mode="router",
        model=OpenAIChat(id="gpt-4o"),
        members=[researcher_1, researcher_2],
        instructions=[
            "Route complex queries to multiple agents if needed",
            "Each agent should focus on their specialty"
        ]
    )

    response = team.run("Research both general and tech perspectives on AI safety")
    
    assert response.content is not None
    assert len(response.member_responses) == 2


def test_router_team_with_model_choice():
    agent_1 = Agent(
        name="Fast Agent",
        model=OpenAIChat(id="gpt-3.5-turbo"),
        instructions="Handle simple queries"
    )

    agent_2 = Agent(
        name="Smart Agent",
        model=OpenAIChat(id="gpt-4o"),
        instructions="Handle complex queries"
    )

    team = Team(
        name="Model Router Team",
        mode="router",
        model=OpenAIChat(id="gpt-4o"),
        members=[agent_1, agent_2],
        instructions=[
            "Route simple queries to Fast Agent",
            "Route complex queries to Smart Agent"
        ]
    )

    # Test simple query routing
    simple_response = team.run("What is 2+2?")
    assert simple_response.content is not None
    assert len(simple_response.member_responses) == 1
    assert simple_response.member_responses[0].agent_id == agent_1.agent_id

    # Test complex query routing
    complex_response = team.run("Explain quantum entanglement")
    assert complex_response.content is not None
    assert len(complex_response.member_responses) == 1
    assert complex_response.member_responses[0].agent_id == agent_2.agent_id 