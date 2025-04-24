"""
Utility functions for the GitHub Repository Analyzer.
"""

import json
import logging
from typing import Dict, List, Optional

import streamlit as st
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

def sidebar_widget() -> None:
    """Renders the sidebar for configuration and example queries."""
    with st.sidebar:
        st.header("Configuration")

        st.markdown("**GitHub Token**")
        token_input = st.text_input(
            "Enter your GitHub Personal Access Token (needed for most queries):",
            type="password",
            key="github_token_input",
            value=st.session_state.get("github_token", ""),
            help="Allows the agent to access GitHub API, including your private/org data."
        )
        st.markdown(
            "[How to create a GitHub PAT?](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic)",
            unsafe_allow_html=True,
        )

        # Update session state if token input changes
        current_token_in_state = st.session_state.get("github_token")
        if token_input != current_token_in_state and (token_input or current_token_in_state is not None):
            st.session_state.github_token = token_input if token_input else None
            logger.info(f"GitHub token updated via sidebar input {'(cleared)' if not token_input else ''}.")
            # No need to clear repo list/selection anymore
            st.session_state.agent = None # Force re-initialization of agent with new/cleared token
            st.rerun()

        st.markdown("---")
        st.markdown("### Example Queries")

        example_queries = [
            "Fetch all my repositories",
            "Analyze 'tensorflow/tensorflow' repo",
            "Get star count for 'agno-agi/agno'",
            "List open issues in 'microsoft/vscode'",
            "Summarize 'agno-agi/agno' repo"
        ]

        if 'sidebar_query' not in st.session_state:
            st.session_state.sidebar_query = None

        for query in example_queries:
            sanitized_query = query.lower().replace(' ', '_').replace('/', '_').replace('#', 'num').replace("'", "")
            button_key = f"btn_{sanitized_query}"
            if st.button(query, key=button_key, use_container_width=True):
                logger.info(f"Sidebar button clicked: {query}")
                st.session_state.sidebar_query = query
                st.rerun()

        st.markdown("---")
        about_widget() # Keep about section

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