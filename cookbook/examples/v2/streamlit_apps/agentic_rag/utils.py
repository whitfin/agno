from typing import Any, Dict, List, Optional

import streamlit as st
from agentic_rag import get_agentic_rag_agent
from agno.agent import Agent
from agno.models.response import ToolExecution
from agno.utils.log import logger


def add_message(
    role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Safely add a message to the session state"""
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {"role": role, "content": content, "tool_calls": tool_calls}
    )



def export_chat_history():
    """Export chat history as markdown"""
    if "messages" in st.session_state:
        chat_text = "# Agentic RAG Agent v2.0 - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
            if msg.get("tool_calls"):
                chat_text += "#### Tools Used:\n"
                for tool in msg["tool_calls"]:
                    if isinstance(tool, dict):
                        tool_name = tool.get("name", "Unknown Tool")
                    else:
                        tool_name = getattr(tool, "name", "Unknown Tool")
                    chat_text += f"- {tool_name}\n"
        return chat_text
    return ""


def display_tool_calls(tool_calls_container, tools: List[ToolExecution]):
    """Display tool calls in a streamlit container with expandable sections.

    Args:
        tool_calls_container: Streamlit container to display the tool calls
        tools: List of tool call dictionaries containing name, args, content, and metrics
    """
    if not tools:
        return

    with tool_calls_container.container():
        for tool_call in tools:
            # Handle different tool call formats
            _tool_name = tool_call.tool_name or "Unknown Tool"
            _tool_args = tool_call.tool_args or {}
            _content = tool_call.result or ""
            _metrics = tool_call.metrics or {}

            # Create enhanced title with query and timing
            base_title = _tool_name.replace('_', ' ').title() if _tool_name else 'Tool Call'
            
            # Extract query from tool args
            query = ""
            if isinstance(_tool_args, dict) and "query" in _tool_args:
                query = _tool_args["query"]
            elif isinstance(_tool_args, str):
                # Try to extract query from string args
                try:
                    import json
                    args_dict = json.loads(_tool_args)
                    if "query" in args_dict:
                        query = args_dict["query"]
                except:
                    pass
            
            # Extract timing from metrics
            timing = ""
            if isinstance(_metrics, dict) and "time" in _metrics:
                timing = f" [completed in {_metrics['time']:.4f}s]"
            elif hasattr(_metrics, 'time') and _metrics.time:
                timing = f" [completed in {_metrics.time:.4f}s]"
            
            # Format the title
            if query:
                title = f"🛠️ {base_title}(query=\"{query[:50]}{'...' if len(query) > 50 else ''}\"){timing}"
            else:
                title = f"🛠️ {base_title}{timing}"

            with st.expander(title, expanded=False):
                if isinstance(_tool_args, dict) and "query" in _tool_args:
                    st.code(_tool_args["query"], language="sql")
                # Handle string arguments
                elif isinstance(_tool_args, str) and _tool_args:
                    try:
                        # Try to parse as JSON
                        import json

                        args_dict = json.loads(_tool_args)
                        st.markdown("**Arguments:**")
                        st.json(args_dict)
                    except:
                        # If not valid JSON, display as string
                        st.markdown("**Arguments:**")
                        st.markdown(f"```\n{_tool_args}\n```")
                # Handle dict arguments
                elif _tool_args and _tool_args != {"query": None}:
                    st.markdown("**Arguments:**")
                    st.json(_tool_args)

                if _content:
                    st.markdown("**Results:**")
                    if isinstance(_content, (dict, list)):
                        st.json(_content)
                    else:
                        try:
                            st.json(_content)
                        except Exception:
                            st.markdown(_content)

                if _metrics:
                    st.markdown("**Metrics:**")
                    st.json(
                        _metrics if isinstance(_metrics, dict) else _metrics.to_dict()
                    )


def rename_session_widget(agent: Agent) -> None:
    """Rename the current session of the agent and save to storage"""

    container = st.sidebar.container()

    # Initialize session_edit_mode if needed
    if "session_edit_mode" not in st.session_state:
        st.session_state.session_edit_mode = False

    if st.sidebar.button("✎ Rename Session"):
        st.session_state.session_edit_mode = True
        st.rerun()

    if st.session_state.session_edit_mode:
        new_session_name = st.sidebar.text_input(
            "Enter new name:",
            value=agent.session_name,
            key="session_name_input",
        )
        if st.sidebar.button("Save", type="primary"):
            if new_session_name:
                agent.rename_session(new_session_name)
                st.session_state.session_edit_mode = False
                st.rerun()


def session_selector_widget(agent: Agent, model_id: str) -> None:
    """Display a session selector in the sidebar"""

    # In v2, session storage is handled internally by the Memory system
    if hasattr(agent, "memory") and agent.memory and hasattr(agent.memory, "db"):
        from agno.db.base import SessionType

        # Get sessions filtered by user_id and agent_id (component_id)
        agent_sessions = agent.memory.db.get_sessions(
            session_type=SessionType.AGENT,
            user_id=agent.user_id,
            component_id=agent.agent_id
        )
        logger.debug(f"Found {len(agent_sessions)} agent sessions for user_id={agent.user_id}, agent_id={agent.agent_id}")

        session_options = []
        for session in agent_sessions:
            session_id = session.session_id
            session_name = (
                session.session_data.get("session_name", None)
                if session.session_data
                else None
            )
            display_name = session_name if session_name else session_id
            session_options.append({"id": session_id, "display": display_name})

        if session_options:
            selected_session = st.sidebar.selectbox(
                "Session",
                options=[s["display"] for s in session_options],
                key="session_selector",
            )
            # Find the selected session ID
            selected_session_id = next(
                s["id"] for s in session_options if s["display"] == selected_session
            )

            if (
                st.session_state.get("agentic_rag_agent_session_id")
                != selected_session_id
            ):
                logger.info(
                    f"---*--- Loading {model_id} run: {selected_session_id} ---*---"
                )

                try:
                    new_agent = get_agentic_rag_agent(
                        model_id=model_id,
                        session_id=selected_session_id,
                    )

                    st.session_state["agentic_rag_agent"] = new_agent
                    st.session_state["agentic_rag_agent_session_id"] = (
                        selected_session_id
                    )

                    st.session_state["messages"] = []

                    selected_session_obj = next(
                        (
                            s
                            for s in agent_sessions
                            if s.session_id == selected_session_id
                        ),
                        None,
                    )

                    # For v2 memory system, use the agent's memory to load chat history
                    if (
                        selected_session_obj
                        and hasattr(new_agent, "memory")
                        and new_agent.memory is not None
                    ):
                        try:
                            # Load session using v2 memory system
                            # Get messages from the session's runs
                            if (
                                hasattr(selected_session_obj, "runs")
                                and selected_session_obj.runs
                            ):
                                seen_messages = set()

                                for run in selected_session_obj.runs:
                                    # Handle v2 memory run structure
                                    if (
                                        hasattr(run, "message")
                                        and run.message is not None
                                    ):
                                        msg_role = run.message.role
                                        msg_content = run.message.content

                                        if msg_content and msg_role != "system":
                                            msg_id = f"{msg_role}:{msg_content}"
                                            if msg_id not in seen_messages:
                                                seen_messages.add(msg_id)
                                                add_message(msg_role, msg_content)

                                    if (
                                        hasattr(run, "response")
                                        and run.response is not None
                                    ):
                                        msg_content = run.response.content
                                        if msg_content:
                                            msg_id = f"assistant:{msg_content}"
                                            if msg_id not in seen_messages:
                                                seen_messages.add(msg_id)
                                                tool_calls = getattr(
                                                    run.response, "tools", None
                                                )
                                                add_message(
                                                    "assistant", msg_content, tool_calls
                                                )
                        except Exception as e:
                            logger.error(f"Error loading v2 session history: {str(e)}")
                            # Fallback to basic session loading
                            pass

                    st.rerun()
                except Exception as e:
                    logger.error(f"Error switching sessions: {str(e)}")
                    st.sidebar.error(f"Error loading session: {str(e)}")
        else:
            st.sidebar.info("No saved sessions available.")


def about_widget() -> None:
    """Display an about section in the sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.markdown("""
    This Agentic RAG Assistant v2.0 helps you analyze documents and web content using natural language queries with enhanced v2 primitives.

    Built with:
    - 🚀 Agno v2 (Knowledge, Memory, Storage)
    - 💫 Streamlit
    - 🧠 Advanced Memory System
    - 📚 Enhanced Knowledge Base
    """)


CUSTOM_CSS = """
    <style>
    /* Main Styles */
   .main-title {
        text-align: center;
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding: 1em 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
        margin: 0.2em 0;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .chat-container {
        border-radius: 15px;
        padding: 1em;
        margin: 1em 0;
        background-color: #f5f5f5;
    }
    .tool-result {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1em;
        margin: 1em 0;
        border-left: 4px solid #3B82F6;
    }
    .status-message {
        padding: 1em;
        border-radius: 10px;
        margin: 1em 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
    }
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .chat-container {
            background-color: #2b2b2b;
        }
        .tool-result {
            background-color: #1e1e1e;
        }
    }
    </style>
"""
