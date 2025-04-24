import nest_asyncio
from os import getenv
import streamlit as st
from agno.utils.log import logger
from agents import get_github_chat_agent
from prompts import SIDEBAR_EXAMPLE_QUERIES
from utils import (
    CUSTOM_CSS,
    about_widget,
    add_message,
    get_combined_repositories,
    sidebar_widget,
)

nest_asyncio.apply()
st.set_page_config(
    page_title="🐙 GitHub Repo Chat",
    page_icon="🐙",
    layout="wide",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def main() -> None:
    ####################################################################
    # App header
    ####################################################################
    st.markdown("<h1 class='main-header'>🐙 GitHub Repo Chat</h1>", unsafe_allow_html=True)
    st.markdown("Interact with any GitHub repository")

    # --- Session State Initialization ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_repo" not in st.session_state:
        st.session_state.selected_repo = None
    if "github_token" not in st.session_state:
        st.session_state.github_token = getenv("GITHUB_ACCESS_TOKEN")
        if not st.session_state.github_token:
            logger.warning("GITHUB_ACCESS_TOKEN environment variable not set.")
        else:
            logger.info("GITHUB_ACCESS_TOKEN found in environment.")
    if "repo_list" not in st.session_state:
        st.session_state.repo_list = []
    if "agent" not in st.session_state:
        st.session_state.agent = None  # Initialize agent later

    ####################################################################
    # Initialize Agent
    ####################################################################
    # Initialize the agent only if a repository is selected and the agent isn't already initialized.
    if st.session_state.selected_repo and not st.session_state.agent:
        # Crucially, check for the token *before* attempting to initialize the agent.
        if not st.session_state.github_token:
            st.error(
                "GitHub token (GITHUB_ACCESS_TOKEN env var) is missing. Agent cannot function without it."
            )
            # Use st.stop() to halt execution if the token is missing, preventing downstream errors.
            st.stop()

        # Proceed with agent initialization only if the token exists.
        logger.info(f"Initializing agent for repository: {st.session_state.selected_repo}")
        with st.spinner(f"Initializing agent for {st.session_state.selected_repo}..."):
            st.session_state.agent = get_github_chat_agent(
                st.session_state.selected_repo, debug_mode=True
            )

            # Check if agent initialization was successful.
            if not st.session_state.agent:
                # Provide user feedback if initialization failed.
                st.error("Failed to initialize the AI agent. Please check the logs for more details.")
                # Optionally, log the failure event more explicitly if needed.
                logger.error("Agent initialization failed.")
                # Consider if st.stop() is appropriate here if the app cannot proceed without an agent.
                # For now, we'll allow the app to continue but show the error.
            else:
                logger.info("Agent initialized successfully.")

    # --- Main Chat Interface ---
    if st.session_state.selected_repo:
        st.markdown(f"### Chatting about: `{st.session_state.selected_repo}`")
    else:
        st.info("👈 Please select a repository from the sidebar to start chatting.")

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input(
        "Ask something about the repository..."
        if st.session_state.selected_repo
        else "Please select a repository first",
        disabled=not st.session_state.selected_repo,
    ):
        logger.info(f"User input received: {prompt}")
        # Add user message to chat history using the utility function
        add_message("user", prompt)
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare query for the agent
        full_query = prompt
        logger.info(f"Query prepared for agent: {full_query}")

        # Get assistant response
        if st.session_state.agent:
            with st.spinner("Thinking..."):
                try:
                    logger.info("Running agent...")
                    result = st.session_state.agent.run(full_query)
                    assistant_response = (
                        str(result.content) if hasattr(result, "content") else str(result)
                    )
                    logger.info(f"Agent raw response: {assistant_response}")

                    # Display assistant response in chat message container
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)
                    # Add assistant response to chat history using the utility function
                    add_message("assistant", assistant_response)

                except Exception as e:
                    logger.error(f"Error during agent execution: {e}", exc_info=True)
                    st.error(f"An error occurred: {e}")
                    # Optionally add error message to chat
                    error_message = f"Sorry, I encountered an error: {e}"
                    with st.chat_message("assistant"):
                        st.markdown(error_message)
                    # Add error message to chat history
                    add_message("assistant", error_message)
        else:
            # Handle cases where the agent is not available when the user tries to chat
            logger.warning("Agent run skipped: Agent not initialized or failed to initialize.")
            # Check if the reason is the missing token (which should ideally be caught earlier)
            if not st.session_state.github_token:
                # This error might be redundant if st.stop() was called during initialization,
                # but serves as a fallback.
                st.error(
                    "Agent cannot run because the GitHub token (GITHUB_ACCESS_TOKEN env var) is missing."
                )
            elif not st.session_state.selected_repo:
                 # This state should ideally not be reachable due to the chat_input disable logic,
                 # but included for robustness.
                 st.error("Please select a repository first.")
            else:
                 # General error if agent failed initialization for other reasons.
                st.error("Agent is not initialized. Please check configuration and logs.")

    ####################################################################
    # Sidebar
    ####################################################################
    sidebar_widget()

if __name__ == "__main__":
    main()
