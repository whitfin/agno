import nest_asyncio
from os import getenv
import streamlit as st
from agno.utils.log import logger
from agents import get_github_agent
from utils import (
    CUSTOM_CSS,
    add_message,
    sidebar_widget,
)

nest_asyncio.apply()

st.set_page_config(
    page_title="GitHub Repo Chat",
    page_icon="👨‍💻",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    #####################################################################
    # App header
    ####################################################################
    st.markdown("<h1 class='main-header'>👨‍💻 GitHub Repo Chat</h1>", unsafe_allow_html=True)
    st.markdown("Ask questions about GitHub repositories")

    ####################################################################
    # Initialize session state
    ####################################################################
    defaults = {
        "messages": [],
        "github_token": getenv("GITHUB_ACCESS_TOKEN"),
        "agent": None,
        "sidebar_query": None,
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    ####################################################################
    # Display chat history
    ####################################################################
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    ####################################################################
    # Initialize agent
    ####################################################################
    agent = get_agent()

   

    chat_prompt = st.chat_input(
        "Ask something about GitHub..." if agent else "Please provide GitHub token first.",
        disabled=not agent,
        key="main_chat_input"
    )

    prompt_to_process = None

    if st.session_state.get("sidebar_query"):
        prompt_to_process = st.session_state.sidebar_query
        logger.info(f"Processing sidebar query: {prompt_to_process}")
        st.session_state.sidebar_query = None

    elif chat_prompt:
        prompt_to_process = chat_prompt
        logger.info(f"Processing chat input query: {prompt_to_process}")

    if prompt_to_process:
        process_user_query(agent, prompt_to_process)    

    ####################################################################
    # Sidebar
    ####################################################################
    sidebar_widget()

def get_agent():
    token_exists = st.session_state.github_token
    agent_not_initialized = st.session_state.agent is None

    if token_exists and agent_not_initialized:
        with st.spinner("Initializing agent..."):
            try:
                st.session_state.agent = get_github_agent(debug_mode=True)
                if st.session_state.agent:
                    logger.debug("Agent initialized successfully.")
                else:
                    st.error("Failed to initialize the agent. Please check the logs.")
                    logger.error("Agent initialization returned None.")
            except Exception as e:
                st.warning(f"Failed to initialize agent: {e}")
                st.session_state.agent = None

    return st.session_state.agent

def process_user_query(agent, prompt: str):
    """Handles adding user message, running agent, and displaying response/error."""
    if not agent:
        st.warning("Agent is not ready. Please ensure GitHub token is provided.")
        return

    logger.info(f"Processing query: {prompt}")
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                logger.info(f"Running agent with query: {prompt}")
                result = agent.run(prompt)
                response = str(result.content) if hasattr(result, "content") else str(result)
                logger.info(f"Agent raw response: {response}")
                st.markdown(response)
                add_message("assistant", response)
            except Exception as e:
                logger.error(f"Error during agent execution: {e}", exc_info=True)
                error_message = f"Sorry, I encountered an error: {e}"
                st.error(error_message)
                add_message("assistant", error_message)



if __name__ == "__main__":
    main()
