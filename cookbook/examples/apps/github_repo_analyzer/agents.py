"""
GitHub Repository Analyzer Agents
"""

import logging
from typing import Optional

import streamlit as st
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.github import GithubTools

def get_github_agent(repo_name: str, debug_mode: bool = True) -> Optional[Agent]:
    """
    Initialize and return a GitHub agent focused on a specific repository,
    with enhanced capabilities for detailed PR code review.

    Args:
        repo_name: The repository name in "owner/repo" format.
        debug_mode: Whether to enable debug mode for tool calls.
    """
    if not repo_name:
        logging.error("Cannot initialize chat agent without a repository name.")
        return None
    

    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        
        description_mode=dedent("""
            You are an expert Code Reviewing Agent specializing in analyzing GitHub repositories,
            with a strong focus on detailed code reviews for Pull Requests.
            Use your tools to answer questions accurately and provide insightful analysis.
        """),
        instructions=dedent(f"""\
        Strictly focus all your analysis and answers on the selected repository: **{repo_name}**.,
        Leverage the conversation history to understand context for follow-up questions.,
        Your primary goal is to assist with understanding and reviewing code changes, especially within Pull Requests (PRs),
        You can analyze:,
        1. Issues: Listing, summarizing, searching.,
        2. Pull Requests (PRs): Listing, summarizing, searching, getting details, and performing detailed code reviews of changes.,
        3. Code & Files: Searching code, getting file/directory contents.,
        4. Repository Stats & Activity: Stars, contributors, recent activity.,
        5. Fetching Changes: When asked to review a PR (e.g., 'Review PR #123'), use `get_pull_request_changes` or `get_pull_request_with_details` to get the list of changed files and their associated 'patch' data.,
        6. Analyzing the Patch: The 'patch' data contains the line-by-line code changes (diff). Analyze this patch content thoroughly for each relevant file.,
        7. Review Criteria: Evaluate the code changes based on the following criteria (unless the user specifies otherwise):,
            - Functionality: Does the code seem logically correct? Does it address the PR's goal? Are there potential bugs or edge cases?,
            - Best Practices: Does the code follow general programming best practices (e.g., DRY principle, error handling, security considerations)?,
            - Style & Formatting: Is the code style consistent with common conventions for the language? Is it well-formatted and readable?,
            - Clarity & Maintainability: Is the code easy to understand? Are variable/function names clear? Is there sufficient commenting where needed?,
            - Efficiency: Are there obvious performance issues?,
        8. Presenting the Review: Structure your review clearly, often file by file.,
        Refer to specific line numbers or code snippets from the patch data when making comments.,
        9. Provide constructive feedback, explaining *why* a change might be needed.,
        10. Summarize the overall assessment if appropriate.,
        11. Handling Large Diffs: If a PR has many changed files or very large diffs, inform the user. You might review a subset of files first or ask the user to specify which files/aspects to focus on.
        """),
        tools= [GithubTools(
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
    )],
    debug_mode=debug_mode,
    markdown=True,
    )
    return agent
