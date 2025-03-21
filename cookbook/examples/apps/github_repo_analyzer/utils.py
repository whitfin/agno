"""
Utility functions for the GitHub Repository Analyzer.
"""

import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

import streamlit as st

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


def ensure_output_dir(dir_name: str) -> str:
    """Ensure the output directory exists and return its path."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name


def clean_analysis_text(text: str) -> str:
    """Clean up the analysis text for better presentation"""
    if not text:
        return ""

    # Handle different formats of RunResponse objects
    if not isinstance(text, str):
        text = str(text)

    # Check if it's a RunResponse object (from its string representation)
    if text.startswith("RunResponse(content="):
        # Try to extract just the content part
        content_match = re.search(
            r"RunResponse\(content=['\"](.*?)['\"]", text, re.DOTALL
        )
        if content_match:
            text = content_match.group(1)

    # Unescape any escaped characters
    text = text.replace("\\n", "\n")
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")

    # Remove any extra quotes at the beginning and end
    text = text.strip("\"'")

    # Ensure proper markdown formatting
    # Make sure headings have space after # for proper rendering
    text = re.sub(r"(^|\n)#([^#\s])", r"\1# \2", text)
    text = re.sub(r"(^|\n)##([^#\s])", r"\1## \2", text)
    text = re.sub(r"(^|\n)###([^#\s])", r"\1### \2", text)

    # Make sure list items have space after - or * for proper rendering
    text = re.sub(r"(^|\n)-([^\s])", r"\1- \2", text)
    text = re.sub(r"(^|\n)\*([^\s])", r"\1* \2", text)

    return text


def extract_metrics(analysis_text):
    """Extract repository metrics from analysis text."""
    # Convert RunResponse to string if needed
    if not isinstance(analysis_text, str):
        analysis_text = str(analysis_text)

    metrics = {}

    # Extract basic metrics using regex patterns
    patterns = {
        "stars": r"Stars:\s*(\d+(?:,\d+)*)",
        "forks": r"Forks:\s*(\d+(?:,\d+)*)",
        "watchers": r"Watchers:\s*(\d+(?:,\d+)*)",
        "open_issues": r"Open Issues \(excluding PRs\):\s*(\d+(?:,\d+)*)",
        "open_prs": r"Open PRs:\s*(\d+(?:,\d+)*)",
        "language": r"Primary Language:\s*([\w\+\#\-\.]+)",
        "license": r"License:\s*([^\n]+)",
        "default_branch": r"Default Branch:\s*([^\n]+)",
        "created": r"Created At:\s*([^,\n]+)",
        "updated": r"Last Updated At:\s*([^,\n]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, analysis_text)
        if match:
            value = match.group(1).strip()
            # Convert numeric values to integers
            if key in ["stars", "forks", "watchers", "open_issues", "open_prs"]:
                try:
                    # Remove commas from numbers
                    value = int(value.replace(",", ""))
                except ValueError:
                    # If conversion fails, just use the string value
                    pass
            metrics[key] = value

    return metrics


def load_favorites(output_dir: str) -> List[str]:
    """Load favorites from a file."""
    favorites_file = os.path.join(output_dir, "favorites.json")
    try:
        with open(favorites_file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_favorites(favorites: List[str], output_dir: str) -> None:
    """Save favorites to a file."""
    with open(f"{output_dir}/favorites.json", "w") as f:
        json.dump(favorites, f)


def toggle_favorite(repo_name: str, output_dir: str) -> List[str]:
    """Toggle a repository's favorite status."""
    favorites = load_favorites(output_dir)

    # Toggle favorite status
    if repo_name in favorites:
        favorites.remove(repo_name)
    else:
        favorites.append(repo_name)

    # Save updated favorites
    save_favorites(favorites, output_dir)

    return favorites


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


def restart_session():
    """Reset the session state and clear history."""
    st.session_state["analyzed_repos"] = []
    st.session_state["current_analysis"] = None
    st.rerun()


def about_widget() -> None:
    """Display the about section with application information."""
    st.sidebar.markdown("### About GitHub Repository Analyzer")
    st.sidebar.markdown("""
    This tool provides insights into GitHub repositories using the Agno framework.
    
    ### Features
    - Repository metrics analysis
    - Issue and PR insights
    - Community health evaluation
    
    Built with:
    - 🚀 Agno
    - 💫 Streamlit
    - 🔍 GitHub API
    """)


def sidebar_widget() -> None:
    """Display the sidebar widget with common controls."""
    st.sidebar.markdown("#### 🛠️ Utilities")
    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.sidebar.button("🔄 New Analysis", use_container_width=True):
            restart_session()

    with col2:
        if st.sidebar.button("📊 Export Data", use_container_width=True):
            st.sidebar.info("Export coming soon!")
