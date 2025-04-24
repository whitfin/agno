"""
Utility functions for the GitHub Repository Analyzer.
"""

import logging
from typing import Dict, List, Optional

import streamlit as st
from github import Github, GithubException
from agno.utils.log import logger

def add_message(
    role: str, content: str, tool_calls: Optional[List[Dict]] = None
) -> None:
    """Add a message to the chat history."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    message = {"role": role, "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    st.session_state["messages"].append(message)

# Predefined list of popular repositories
POPULAR_REPOS = [
    "agno-agi/agno",  # Ensure agno is included
    "facebook/react",
    "tensorflow/tensorflow",
    "microsoft/vscode",
    "torvalds/linux",
    "openai/openai-python",  # Added one more popular repo
]


def get_combined_repositories(
    token: Optional[str], user_repo_limit: int = 5
) -> list[str]:
    """
    Fetches user repositories (if token provided) and combines them with
    a predefined list of popular repositories.

    Args:
        token: Optional GitHub Personal Access Token.
        user_repo_limit: Max number of user-specific repos to fetch.

    Returns:
        A combined list of unique repository names.
    """
    user_repos = []
    if token:
        try:
            g = Github(token)
            user = g.get_user()
            logging.info(f"Authenticated as GitHub user: {user.login}")
            repos = user.get_repos(
                affiliation="owner,collaborator,organization_member",
                sort="updated",
                direction="desc",
            )

            count = 0
                if count >= user_repo_limit:
                    break
                user_repos.append(repo.full_name)
                count += 1
            logging.info(f"Fetched {len(user_repos)} user repositories: {user_repos}")
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while fetching user repositories: {e}"
            )

def sidebar_widget() -> None:
    """Renders the sidebar for repository selection and other info."""
    with st.sidebar:
        if not st.session_state.repo_list:
            with st.spinner("Fetching repositories..."):
                # Pass the token from session state (which came from env var)
                st.session_state.repo_list = get_combined_repositories(
                    st.session_state.github_token, user_repo_limit=5
                )
                if not st.session_state.repo_list:
                    st.sidebar.warning("Could not load any repositories.")

        # Repository Selection Dropdown
        if st.session_state.repo_list:
            st.header("Select Repository")
            # Ensure agno-agi/agno is the default if nothing is selected yet
            default_repo = "agno-agi/agno"
            options = st.session_state.repo_list
            try:
                # Set default index to agno-agi/agno if available, otherwise 0
                default_index = (
                    options.index(default_repo) if default_repo in options else 0
                )
            except ValueError:
                default_index = 0

            # Determine current selection index for persistence
            current_selection_index = default_index  # Start with default
            if st.session_state.selected_repo in options:
                try:
                    current_selection_index = options.index(
                        st.session_state.selected_repo
                    )
                except ValueError:
                    # Selected repo might have disappeared if token changed/expired and user repos are gone
                    st.session_state.selected_repo = None  # Reset selection
                    st.session_state.agent = None
                    logger.warning(
                        "Previously selected repo not found in current list. Resetting."
                    )
                    st.rerun()  # Rerun to reflect reset

            selected_repo = st.selectbox(
                "Choose a repository to chat with:",
                options=options,
                index=current_selection_index,
                key="repo_selector",
            )

            # Update selected repo in session state if changed
            if selected_repo != st.session_state.selected_repo:
                st.session_state.selected_repo = selected_repo
                st.session_state.messages = []  # Clear messages when repo changes
                st.session_state.agent = None  # Re-initialize agent for the new repo
                logger.info(f"Selected repository changed to: {selected_repo}")
                st.rerun()  # Rerun to clear chat and potentially update agent context

        # Show info message if token is missing
        if not st.session_state.github_token:
            st.sidebar.info(
                "Set GITHUB_ACCESS_TOKEN environment variable to see your private/org repos."
            )

        st.markdown("---")
        st.markdown("### Example Queries")
        st.markdown("""- Summarize recent activity, List open issues labeled 'bug', Show details for PR #123, Review PR #100, Who are the top contributors this month?""")

        st.markdown("---")
        about_widget() # This is already defined in this file

def about_widget() -> None:
    """Display the about section with application information."""
    st.sidebar.markdown("### About GitHub Repo Chat")
    st.sidebar.markdown("""This tool provides insights into GitHub repositories using an Agno Agent, with a focus on AI-assisted code review.

    ### Features
    - Repository metrics analysis
    - Issue and PR insights
    - Detailed PR code review based on patch analysis
    - Community health evaluation
    
    Built with:
    - 🚀 Agno
    - 💫 Streamlit
    - 🔍 GitHub API
""")

# Keep only necessary CSS styles
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #0366d6;
        font-weight: 600;
    }
    .sub-header {
        font-size: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: #2f363d;
        font-weight: 500;
    }
    .metric-card {
        background-color: #f6f8fa;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 5px solid #0366d6;
    }
    .pr-card {
        background-color: #f1f8ff;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        border-left: 5px solid #6f42c1;
    }
</style>
"""