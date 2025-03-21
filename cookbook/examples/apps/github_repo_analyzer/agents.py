"""
GitHub Repository Analyzer Agents
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

import dotenv
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.github import GithubTools

# Load environment variables
dotenv.load_dotenv()


def get_github_analyzer(debug_mode=False):
    """
    Initialize and return a GitHub repository analysis agent.

    Args:
        debug_mode: Whether to enable debug mode

    Returns:
        Initialized Agent
    """
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You analyze GitHub repositories and extract precise metrics.",
        instructions=[
            "Extract stars, forks, watchers, open_issues, open_prs, language, license, default_branch",
            "For open_issues, report ONLY actual issues (not PRs)",
            "Format all values as plain numbers without commas",
            "Report 'Repository Information' with all metrics clearly labeled",
            "Include activity data such as recent commits and issue/PR trends in your analysis",
        ],
        tools=[GithubTools()],
        debug_mode=debug_mode,
        markdown=True,
    )


def analyze_repository(
    repo_name,
    analyze_issues=True,
    analyze_prs=True,
    analyze_community=True,
    collect_advanced_metrics=False,
):
    """
    Analyze a GitHub repository.

    Args:
        repo_name: The repository name in format "owner/repo"
        analyze_issues: Whether to analyze issues
        analyze_prs: Whether to analyze pull requests
        analyze_community: Whether to analyze community health
        collect_advanced_metrics: Whether to collect advanced metrics

    Returns:
        Dictionary with analysis results and advanced metrics if requested
    """
    # Initialize variables
    github_analyzer = get_github_analyzer()
    advanced_metrics = None

    # Collect advanced metrics directly from GitHub API if requested
    if collect_advanced_metrics:
        github_tools = GithubTools()
        try:
            # Get repository stats
            repo_stats = github_tools.get_repository_with_stats(repo_name)
            advanced_metrics = (
                json.loads(repo_stats) if isinstance(repo_stats, str) else repo_stats
            )

            # Manually get open issues count (excluding PRs)
            issues_data = github_tools.list_issues(repo_name=repo_name, state="open")
            issues = (
                json.loads(issues_data) if isinstance(issues_data, str) else issues_data
            )
            if isinstance(issues, list):
                advanced_metrics["actual_open_issues"] = len(issues)

            # Manually get open PRs count
            prs_data = github_tools.list_pull_requests(
                repo_name=repo_name, state="open"
            )
            prs = json.loads(prs_data) if isinstance(prs_data, str) else prs_data
            if isinstance(prs, list):
                advanced_metrics["open_pr_count"] = len(prs)

        except Exception as e:
            print(f"Error getting advanced metrics: {e}")

    # Build the analysis prompt
    prompt = build_analysis_prompt(
        repo_name, advanced_metrics, analyze_issues, analyze_prs, analyze_community
    )

    # Run the analysis
    print(f"Analyzing repository: {repo_name}")
    result = github_analyzer.run(prompt)

    # Process the analysis result
    analysis_text = (
        str(result.content)
        if hasattr(result, "content") and result.content
        else str(result)
    )

    # Return the analysis response
    return {
        "repo_name": repo_name,
        "analysis": analysis_text,
        "advanced_metrics": advanced_metrics,
    }


def build_analysis_prompt(
    repo_name,
    advanced_metrics=None,
    analyze_issues=True,
    analyze_prs=True,
    analyze_community=True,
):
    """
    Build the prompt for repository analysis.

    Args:
        repo_name: Repository name in format "owner/repo"
        advanced_metrics: Advanced metrics if available
        analyze_issues: Whether to analyze issues
        analyze_prs: Whether to analyze pull requests
        analyze_community: Whether to analyze community health

    Returns:
        Prompt string for the analysis agent
    """
    prompt = f"""Analyze GitHub repository {repo_name}. Extract these metrics as plain numbers:
- Stars
- Forks
- Watchers
- Open Issues (excluding PRs)
- Open PRs
- Primary Language
- License
- Default Branch
"""

    # Add additional information from advanced metrics if available
    if advanced_metrics and not isinstance(advanced_metrics, str):
        try:
            # Add verified counts from our advanced metrics
            prompt += f"\nVerified repository metrics from API:"
            prompt += f"\n- Stars: {advanced_metrics.get('stargazers_count', 'Not available')}"
            prompt += (
                f"\n- Forks: {advanced_metrics.get('forks_count', 'Not available')}"
            )
            prompt += f"\n- Open Issues (excluding PRs): {advanced_metrics.get('actual_open_issues', 'Not available')}"
            prompt += f"\n- Open PRs: {advanced_metrics.get('open_pr_count', 'Not available')}"

            # Add language information if available
            if "languages" in advanced_metrics:
                prompt += f"\n- Languages: {advanced_metrics['languages']}"

        except Exception as e:
            print(f"Error adding advanced metrics to prompt: {e}")

    # Add analysis sections based on flags
    prompt += "\n\nStructure your analysis with these sections using Markdown headings:"
    prompt += "\n# Repository Information"

    if analyze_issues:
        prompt += "\n# Issues Analysis"

    if analyze_prs:
        prompt += "\n# Pull Requests Analysis"

    prompt += "\n\nNOTE: GitHub API's 'open_issues_count' includes both issues and PRs. Separate these in your analysis."
    prompt += "\n\nDO NOT include Created At or Last Updated At in your analysis."

    return prompt
