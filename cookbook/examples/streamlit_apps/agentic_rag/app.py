import os
import tempfile

import nest_asyncio
import streamlit as st
from agentic_rag import get_agentic_rag_agent
from agno.agent import Agent
from agno.utils.log import logger
from agno.utils.streamlit import (
    COMMON_CSS,
    add_message,
    display_tool_calls,
    knowledge_base_info_widget,
    load_chat_history,
    rename_session_widget,
    session_selector_widget,
    utilities_widget,
)

nest_asyncio.apply()

st.set_page_config(
    page_title="Agentic RAG",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS
st.markdown(COMMON_CSS, unsafe_allow_html=True)


def initialize_agent(
    model_id: str, user_id: str = None, debug_mode: bool = True
) -> Agent:
    agent_name = "agentic_rag_agent"

    if agent_name not in st.session_state or st.session_state[agent_name] is None:
        session_id = st.session_state.get("session_id")

        agent = get_agentic_rag_agent(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode,
        )

        agent.load_session()

        st.session_state[agent_name] = agent
        st.session_state["session_id"] = agent.session_id

        logger.debug(f"Agent initialized with session: {agent.session_id}")
    else:
        agent = st.session_state[agent_name]

        if not agent.agent_session:
            agent.load_session()

    return agent


def setup_sidebar(agent: Agent, model_id: str) -> None:
    model_options = {
        "gpt-4o": "openai:gpt-4o",
        "o3-mini": "openai:o3-mini",
        "kimi-2": "groq:moonshotai/kimi-k2-instruct",
        "claude-4-sonnet": "anthropic:claude-sonnet-4-0",
    }

    selected_model = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )

    st.sidebar.markdown("#### 📚 Document Management")

    input_url = st.sidebar.text_input("Add URL to Knowledge Base")
    if input_url:
        with st.sidebar:
            with st.spinner("Processing URL..."):
                try:
                    agent.knowledge.add_content(
                        name=f"URL: {input_url}",
                        url=input_url,
                        description=f"Content from {input_url}",
                    )
                    st.success("URL added to knowledge base")
                except Exception as e:
                    st.error(f"Error processing URL: {str(e)}")

    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Add a Document (.pdf, .csv, or .txt)", key="file_upload"
    )
    if uploaded_file:
        with st.sidebar:
            with st.spinner("Processing document..."):
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{uploaded_file.name.split('.')[-1]}", delete=False
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name

                    # Add to knowledge base
                    agent.knowledge.add_content(
                        name=uploaded_file.name,
                        path=tmp_path,
                        description=f"Uploaded file: {uploaded_file.name}",
                    )

                    # Clean up
                    os.unlink(tmp_path)
                    st.success(f"{uploaded_file.name} added to knowledge base")
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")

    # Clear knowledge base
    if st.sidebar.button("Clear Knowledge Base"):
        if agent.knowledge.vector_db:
            agent.knowledge.vector_db.delete()
        st.sidebar.success("Knowledge base cleared")

    # Sample Questions
    st.sidebar.markdown("#### ❓ Sample Questions")
    if st.sidebar.button("📝 Summarize"):
        add_message(
            "user",
            "Can you summarize what is currently in the knowledge base (use `search_knowledge_base` tool)?",
        )
        st.rerun()

    # Utilities
    with st.sidebar:
        utilities_widget("agentic_rag_agent")

    # Session management
    session_selector_widget(agent, model_id, agent_name="agentic_rag_agent")

    # Knowledge base info
    knowledge_base_info_widget(agent)

    # About section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.markdown("""
    This Agentic RAG Assistant helps you analyze documents and web content using natural language queries.

    Built with:
    - 🚀 Agno
    - 💫 Streamlit
    """)

    return model_options[selected_model]


def display_chat_history() -> None:
    """Display chat messages and handle tool calls."""
    for message in st.session_state.get("messages", []):
        if message["role"] in ["user", "assistant"]:
            content = message["content"]

            # Display tool calls if they exist
            if "tool_calls" in message and message["tool_calls"]:
                display_tool_calls(st.container(), message["tool_calls"])

            # Display message content if valid
            if (
                content is not None
                and str(content).strip()
                and str(content).strip().lower() != "none"
            ):
                with st.chat_message(message["role"]):
                    st.markdown(content)


def handle_user_input(agent: Agent, user_id: str = None) -> None:
    """Handle user input and generate responses."""
    # Get user input
    if prompt := st.chat_input("👋 Ask me anything!"):
        add_message("user", prompt)
        st.rerun()

    # Generate response if last message is from user
    messages = st.session_state.get("messages", [])
    if messages and messages[-1].get("role") == "user":
        question = messages[-1]["content"]

        with st.chat_message("assistant"):
            tool_calls_container = st.empty()
            resp_container = st.empty()

            with st.spinner("🤔 Thinking..."):
                try:
                    response = ""
                    run_response = agent.run(question, stream=True)

                    for chunk in run_response:
                        # Display tool calls
                        if hasattr(chunk, "tool") and chunk.tool:
                            display_tool_calls(tool_calls_container, [chunk.tool])

                        # Display response content
                        if chunk.content is not None:
                            response += chunk.content
                            resp_container.markdown(response)

                    # Add response to messages
                    add_message("assistant", response, agent.run_response.tools)

                    # Save session
                    if agent.session_id:
                        try:
                            agent.save_session(
                                session_id=agent.session_id, user_id=user_id
                            )
                        except Exception as save_e:
                            logger.error(f"Error saving session: {save_e}")

                except Exception as e:
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)
                    st.error(error_message)


def main():
    """Main application function."""
    # App header
    st.markdown("<h1 class='main-title'>Agentic RAG</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Your intelligent research assistant powered by Agno</p>",
        unsafe_allow_html=True,
    )

    # Initialize agent
    initial_model_id = "openai:gpt-4o"
    agent = initialize_agent(initial_model_id, debug_mode=True)

    # Load chat history if needed
    if len(st.session_state.get("messages", [])) == 0:
        load_chat_history(agent)

    # Set up sidebar and get current model
    current_model_id = setup_sidebar(agent, initial_model_id)

    # Reinitialize agent if model changed
    if current_model_id != agent.model.id:
        st.session_state["agentic_rag_agent"] = None
        agent = initialize_agent(current_model_id, debug_mode=True)

    # Display chat and handle input
    display_chat_history()
    handle_user_input(agent)


if __name__ == "__main__":
    main()
