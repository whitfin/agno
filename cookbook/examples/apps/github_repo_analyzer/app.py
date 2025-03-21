"""
GitHub Repository Analyzer App
"""

import json
import os
import re

import streamlit as st

# Import agent functionality
from agents import analyze_repository

# Import utilities
from utils import (
    CUSTOM_CSS,
    about_widget,
    clean_analysis_text,
    ensure_output_dir,
    extract_metrics,
    load_favorites,
    save_favorites,
    sidebar_widget,
    toggle_favorite,
)

# App configuration
st.set_page_config(
    page_title="GitHub Repository Analyzer",
    page_icon="📊",
    layout="wide",
)

# Add custom styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Ensure output directory exists
OUTPUT_DIR = ensure_output_dir("output")


def display_header():
    """Display the application header."""
    st.markdown(
        "<h1 class='main-header'>GitHub Repository Analyzer</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p>Analyze GitHub repositories to extract key metrics and insights</p>",
        unsafe_allow_html=True,
    )


def display_metrics(metrics):
    """Display repository metrics in a formatted way."""
    if not metrics:
        return

    st.markdown(
        "<div class='sub-header'>Repository Overview</div>", unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""<div class='metric-card'>
            <h3>{metrics.get("stars", 0)}</h3>
            <p>Stars</p>
            </div>""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""<div class='metric-card'>
            <h3>{metrics.get("forks", 0)}</h3>
            <p>Forks</p>
            </div>""",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""<div class='metric-card'>
            <h3>{metrics.get("language", "Unknown")}</h3>
            <p>Primary Language</p>
            </div>""",
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""<div class='metric-card'>
            <h3>{metrics.get("open_issues", 0)}</h3>
            <p>Open Issues</p>
            </div>""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""<div class='metric-card'>
            <h3>{metrics.get("open_prs", 0)}</h3>
            <p>Open PRs</p>
            </div>""",
            unsafe_allow_html=True,
        )


def display_analysis(analysis_text):
    """Display the analysis text in a structured way."""
    if not analysis_text:
        return

    # Split the analysis into sections based on headings
    sections = re.split(r"(?=^#\s+)", analysis_text, flags=re.MULTILINE)

    # Process each section
    for section in sections:
        if not section.strip():
            continue

        # Extract section title
        title_match = re.match(r"^#\s+(.*?)$", section, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
            # Add a subheader for the section
            st.markdown(
                f"<div class='sub-header'>{title}</div>", unsafe_allow_html=True
            )
            # Display the content without the title
            content = re.sub(r"^#\s+.*?$", "", section, flags=re.MULTILINE).strip()
            st.markdown(content)
        else:
            # If no title, just display the content
            st.markdown(section)


def display_sidebar_controls():
    """Display sidebar controls and process user input."""
    st.sidebar.markdown("### Repository")
    repo_name = st.sidebar.text_input(
        "Enter repository name (owner/repo):",
        value="agno-agi/agno",
        key="repo_name_input",
    )

    st.sidebar.markdown("### Analysis Options")
    analyze_issues = st.sidebar.checkbox("Analyze issues", value=True)
    analyze_prs = st.sidebar.checkbox("Analyze pull requests", value=True)
    advanced_metrics = st.sidebar.checkbox("Collect advanced metrics", value=True)

    run_button = st.sidebar.button(
        "🔍 Run Analysis", type="primary", use_container_width=True
    )

    # Return user selections
    return {
        "repo_name": repo_name,
        "analyze_issues": analyze_issues,
        "analyze_prs": analyze_prs,
        "analyze_community": False,  # Always false now
        "advanced_metrics": advanced_metrics,
        "run_clicked": run_button,
    }


def display_favorites():
    """Display favorite repositories in the sidebar."""
    if "favorites" not in st.session_state:
        st.session_state.favorites = load_favorites(OUTPUT_DIR)

    favorites = st.session_state.favorites
    if not favorites:
        return

    st.sidebar.markdown("### Favorites")
    for fav in favorites:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            if st.button(fav, key=f"fav_{fav}", use_container_width=True):
                run_analysis(fav, True, True, True, True)
                st.rerun()
        with col2:
            if st.button("❌", key=f"del_{fav}"):
                favorites.remove(fav)
                save_favorites(favorites, OUTPUT_DIR)
                st.session_state.favorites = favorites
                st.rerun()


def run_analysis(
    repo_name, analyze_issues, analyze_prs, analyze_community, advanced_metrics
):
    """Run the repository analysis and update session state."""
    with st.spinner(f"📊 Analyzing {repo_name}..."):
        try:
            # Run the analysis
            result = analyze_repository(
                repo_name=repo_name,
                analyze_issues=analyze_issues,
                analyze_prs=analyze_prs,
                analyze_community=analyze_community,
                collect_advanced_metrics=advanced_metrics,
            )

            # Clean the analysis text
            result["analysis"] = clean_analysis_text(result["analysis"])

            # Extract metrics
            metrics = extract_metrics(result["analysis"])
            result["metrics"] = metrics

            # Initialize the analyzed_repos list if it doesn't exist
            if "analyzed_repos" not in st.session_state:
                st.session_state.analyzed_repos = []

            # Update session state
            st.session_state.current_analysis = result

            # Add to analyzed repositories if not already there
            if repo_name not in st.session_state.analyzed_repos:
                st.session_state.analyzed_repos.append(repo_name)

            st.success(f"✅ Analysis complete for {repo_name}")

        except Exception as e:
            st.error(f"❌ Error analyzing repository: {str(e)}")
            return None


def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "analyzed_repos" not in st.session_state:
        st.session_state.analyzed_repos = []

    if "favorites" not in st.session_state:
        st.session_state.favorites = load_favorites(OUTPUT_DIR)

    if "current_analysis" not in st.session_state:
        st.session_state.current_analysis = None


def display_favorite_controls():
    """Display controls for the current repository's favorite status."""
    if not st.session_state.current_analysis:
        return

    repo_name = st.session_state.current_analysis.get("repo_name")
    is_favorite = repo_name in st.session_state.favorites

    if is_favorite:
        if st.sidebar.button("❤️ Remove from Favorites"):
            st.session_state.favorites = toggle_favorite(repo_name, OUTPUT_DIR)
            st.rerun()
    else:
        if st.sidebar.button("🤍 Add to Favorites"):
            st.session_state.favorites = toggle_favorite(repo_name, OUTPUT_DIR)
            st.rerun()


def display_example_repos():
    """Display example repositories to analyze."""
    st.info("👈 Enter a repository name and click 'Run Analysis' to get started.")

    # Show example repositories
    st.markdown("### Try these examples:")
    example_repos = [
        "facebook/react",
        "tensorflow/tensorflow",
        "microsoft/vscode",
        "agno-agi/agno",
        "denoland/deno",
        "rust-lang/rust",
    ]

    # Display in a grid of 3 columns
    cols = st.columns(3)
    for i, repo in enumerate(example_repos):
        with cols[i % 3]:
            if st.button(repo, key=f"example_{i}"):
                run_analysis(repo, True, True, True, True)
                st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Display header
    display_header()

    # Display sidebar elements
    sidebar_options = display_sidebar_controls()
    display_favorites()
    display_favorite_controls()
    sidebar_widget()
    about_widget()

    # Process analysis request if run button was clicked
    if sidebar_options["run_clicked"]:
        run_analysis(
            sidebar_options["repo_name"],
            sidebar_options["analyze_issues"],
            sidebar_options["analyze_prs"],
            sidebar_options["analyze_community"],
            sidebar_options["advanced_metrics"],
        )

    # Display current analysis if available
    if st.session_state.current_analysis:
        analysis = st.session_state.current_analysis
        display_metrics(analysis.get("metrics", {}))
        display_analysis(analysis.get("analysis", ""))

    # Display example repositories if no analysis has been run
    elif not sidebar_options["run_clicked"]:
        display_example_repos()


if __name__ == "__main__":
    main()
