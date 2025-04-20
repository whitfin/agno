"""
GitHub Repository Analyzer Agents
"""

import logging
from typing import Optional

import streamlit as st
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.github import GithubTools

from prompts import AGENT_DESCRIPTION, AGENT_INSTRUCTIONS


def get_github_agent(repo_name: str, debug_mode: bool = True) -> Optional[Agent]:
    """
    Initialize and return a GitHub agent focused on a specific repository,
    with enhanced capabilities for detailed PR code review.

    Args:
        repo_name: The repository name in "owner/repo" format.
        debug_mode: Whether to enable debug mode for tool calls.

    Returns:
        Initialized Agent for chat, or None if initialization fails.
    """
    if not repo_name:
        logging.error("Cannot initialize chat agent without a repository name.")
        return None

    github_tools = GithubTools(
        search_repositories=True,
        list_repositories=True,
        get_repository=True,
        list_pull_requests=True,
        get_pull_request=True,
        get_pull_request_changes=True,
        list_branches=True,
        get_pull_request_count=True,
        get_pull_requests=True,
        get_pull_request_comments=True,
        get_pull_request_with_details=True,
        list_issues=True,
        get_issue=True,
        list_issue_comments=True,
    )

    logging.info(f"Initializing chat agent for repository: {repo_name}")
    try:
        # Format the repository name into the description and instructions
        formatted_description = AGENT_DESCRIPTION.format(repo_name=repo_name)
        formatted_instructions = [
            instruction.format(repo_name=repo_name)
            for instruction in AGENT_INSTRUCTIONS
        ]

        agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description=formatted_description,
            instructions=formatted_instructions,
            tools=[github_tools],
            debug_mode=debug_mode,
            markdown=True,
        )
        logging.info(f"Chat agent for {repo_name} initialized successfully.")
        return agent
    except Exception as e:
        logging.error(
            f"Failed to initialize chat agent for {repo_name}: {e}", exc_info=True
        )
        st.error(f"Error initializing agent: {e}")
        return None
