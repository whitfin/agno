import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union

try:
    import streamlit as st
    from streamlit.delta_generator import DeltaGenerator
except ImportError:
    raise ImportError("Streamlit is not installed. Please install it with `pip install streamlit`")

from agno.agent import Agent
from agno.models.response import ToolExecution
from agno.utils.log import logger


class SessionMessage(TypedDict):
    """Type definition for messages stored in Streamlit session state."""

    role: str
    content: str
    tool_calls: Optional[List[ToolExecution]]


def add_message(role: str, content: str, tool_calls: Optional[List[ToolExecution]] = None) -> None:
    """Add a message to the Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    message: SessionMessage = {
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
    }
    st.session_state["messages"].append(message)


def display_tool_calls(container: DeltaGenerator, tools: List[Union[ToolExecution, Dict[str, Any]]]) -> None:
    """Display tool calls in expandable sections."""
    if not tools:
        return

    with container.container():
        for tool in tools:
            if hasattr(tool, "tool_name"):
                name = tool.tool_name or "Tool"
                args = tool.tool_args or {}
                result = tool.result or ""
            else:
                name = tool.get("tool_name") or tool.get("name") or "Tool"
                args = tool.get("tool_args") or tool.get("args") or {}
                result = tool.get("result") or tool.get("content") or ""

            with st.expander(f"🛠️ {name.replace('_', ' ')}", expanded=False):
                if args:
                    st.markdown("**Arguments:**")
                    st.json(args)

                if result:
                    st.markdown("**Result:**")
                    try:
                        if isinstance(result, str):
                            parsed_result = json.loads(result)
                        elif isinstance(result, (list, dict)):
                            parsed_result = result
                        else:
                            raise ValueError("Not JSON data")
                        st.json(parsed_result)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        st.markdown(f"```\n{result}\n```")


def load_chat_history(agent: Agent) -> None:
    """Load chat history from agent session using Agno 2.0 methods."""
    if not agent or not agent.agent_session:
        st.session_state["messages"] = []
        return

    # Additional safety check for agent session
    if not hasattr(agent, "get_chat_history"):
        logger.warning("Agent does not have get_chat_history method")
        st.session_state["messages"] = []
        return

    try:
        # Use Agno 2.0's built-in chat history method
        chat_history = agent.get_chat_history()
        st.session_state["messages"] = []

        # Check if chat history is valid
        if not chat_history:
            logger.debug("No chat history found")
            return

        # Group messages by runs to get tool executions
        if hasattr(agent.agent_session, "runs") and agent.agent_session.runs:
            run_tools_map = {
                id(run): run.tools for run in agent.agent_session.runs if hasattr(run, "tools") and run.tools
            }

            # Process chat history and match with tool executions
            for message in chat_history:
                if not message or not hasattr(message, "role") or not hasattr(message, "content"):
                    continue

                if message.role == "user":
                    add_message("user", str(message.content))
                elif message.role in ["assistant", "model"]:
                    # Find tools for this message from the runs
                    tool_executions = None
                    if hasattr(agent.agent_session, "runs") and agent.agent_session.runs:
                        for run in agent.agent_session.runs:
                            if (
                                hasattr(run, "messages")
                                and run.messages
                                and any(
                                    m and hasattr(m, "content") and m.content == message.content for m in run.messages
                                )
                                and hasattr(run, "tools")
                                and run.tools
                            ):
                                tool_executions = run.tools
                                break
                    add_message("assistant", str(message.content), tool_executions)
        else:
            for message in chat_history:
                if not message or not hasattr(message, "role") or not hasattr(message, "content"):
                    continue
                add_message(message.role, str(message.content))

        logger.debug(f"Loaded {len(st.session_state['messages'])} messages from chat history")

    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        st.session_state["messages"] = []


def session_selector_widget(agent: Agent, model_id: str, agent_name: str = "agent") -> None:
    """Display a session selector in the sidebar."""
    if not agent or not agent.db:
        st.sidebar.info("💡 Memory not configured. Sessions will not be saved.")
        return

    try:
        # Get all agent sessions
        agent_sessions = agent.db.get_sessions(
            session_type="agent",
            deserialize=True,
            sort_by="created_at",
            sort_order="desc",
        )

        if not agent_sessions:
            st.sidebar.info("🆕 No previous sessions found.")
            return

        # Create session options
        session_options = []
        for session in agent_sessions:
            if not hasattr(session, "session_id") or not session.session_id:
                continue

            session_id = session.session_id
            session_name = None

            if hasattr(session, "session_data") and session.session_data:
                session_name = session.session_data.get("session_name")

            display_name = session_name if session_name else session_id

            # Add timestamp
            if hasattr(session, "created_at") and session.created_at:
                try:
                    if isinstance(session.created_at, (int, float)):
                        timestamp = datetime.fromtimestamp(session.created_at)
                        time_str = timestamp.strftime("%m/%d %H:%M")
                        display_name = f"{display_name} ({time_str})"
                except (ValueError, TypeError, OSError):
                    pass

            session_options.append({"id": session_id, "display": display_name})

        # Display session selector
        current_session_id = st.session_state.get("session_id")
        current_index = 0

        # Find current session index
        if current_session_id:
            for i, option in enumerate(session_options):
                if option["id"] == current_session_id:
                    current_index = i
                    break

        selected_session_display = st.sidebar.selectbox(
            "Session",
            options=[s["display"] for s in session_options],
            index=current_index,
            key="session_selector",
            help="Select a previous session to continue",
        )

        # Find the selected session ID
        selected_session_id = next(s["id"] for s in session_options if s["display"] == selected_session_display)

        # Switch sessions if different
        if current_session_id != selected_session_id:
            logger.debug(f"Switching to session: {selected_session_id}")

            # Update session state to trigger session switch
            st.session_state["session_id"] = selected_session_id
            st.session_state[agent_name] = None  # Clear current agent to force reinit
            st.session_state["messages"] = []  # Clear current messages

            # Clear session-related UI state
            for key in ["session_edit_mode", "session_selector"]:
                if key in st.session_state:
                    del st.session_state[key]

            st.rerun()

        rename_session_widget(agent)
    except Exception as e:
        logger.error(f"Error in session selector: {e}")
        st.sidebar.error("Could not load sessions")


def restart_agent(agent_name: str = "agentic_rag_agent") -> None:
    """Create a new agent session using Agno 2.0 patterns."""
    logger.debug("Creating new agent session")

    current_agent = st.session_state.get(agent_name)
    if current_agent and hasattr(current_agent, "new_session"):
        try:
            current_agent.new_session()

            st.session_state["session_id"] = current_agent.session_id
            st.session_state["messages"] = []

            # Clear UI state
            for key in ["session_edit_mode", "session_selector"]:
                if key in st.session_state:
                    del st.session_state[key]

            logger.debug(f"Created new session: {current_agent.session_id}")
            st.rerun()
            return

        except Exception as e:
            logger.error(f"Error creating new session: {e}")

    st.session_state[agent_name] = None
    st.session_state["session_id"] = None
    st.session_state["messages"] = []

    for key in ["session_edit_mode", "session_selector"]:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


def rename_session_widget(agent: Agent) -> None:
    """Rename the current session."""
    if not agent or not agent.session_id:
        return

    container = st.sidebar.container()
    session_row = container.columns([3, 1], vertical_alignment="center")

    if "session_edit_mode" not in st.session_state:
        st.session_state.session_edit_mode = False

    current_name = agent.session_name or agent.session_id

    with session_row[0]:
        if st.session_state.session_edit_mode:
            new_session_name = st.text_input(
                "Session Name",
                value=current_name,
                key="session_name_input",
                label_visibility="collapsed",
            )
        else:
            st.markdown(f"**Session:** {current_name}")

    with session_row[1]:
        if st.session_state.session_edit_mode:
            if st.button("✓", key="save_session_name", type="primary"):
                if new_session_name and new_session_name.strip():
                    try:
                        success = agent.rename_session(new_session_name.strip())
                        if success:
                            agent.save_session(session_id=agent.session_id)
                            st.session_state.session_edit_mode = False
                            container.success("Renamed!")
                            st.rerun()
                        else:
                            container.error("Failed to rename session")
                    except Exception as e:
                        logger.error(f"Error renaming session: {e}")
                        container.error(f"Error: {str(e)}")
                else:
                    container.error("Please enter a valid name")
        else:
            if st.button("✎", key="edit_session_name"):
                st.session_state.session_edit_mode = True


def export_chat_history() -> str:
    """Export chat history as markdown with enhanced formatting."""
    from datetime import datetime

    if "messages" not in st.session_state or not st.session_state["messages"]:
        return "# 📚 Agentic RAG Agent - Chat History\n\n*No messages found.*\n"

    export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    chat_text = f"""# 📚 Agentic RAG Agent - Chat History

**Exported:** {export_time}

"""

    for i, msg in enumerate(st.session_state["messages"], 1):
        role = "🤖 **Assistant**" if msg["role"] == "assistant" else "👤 **User**"
        content = msg.get("content", "")

        # Handle empty or None content
        if not content or content == "None":
            continue

        chat_text += f"## {role}\n\n{content}\n\n"

        # Add separator between messages (except for the last one)
        if i < len(st.session_state["messages"]):
            chat_text += "---\n\n"

    return chat_text


def utilities_widget(agent_name: str) -> None:
    """Create utilities section with new chat and export."""
    st.markdown("---")
    st.markdown("#### 🛠️ Utilities")

    if st.button("🔄 New Chat", use_container_width=True):
        restart_agent(agent_name)

    st.markdown("")

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if "session_id" in st.session_state and st.session_state["session_id"]:
        session_short = st.session_state["session_id"][:8]  # First 8 chars of session ID
        fn = f"agentic_rag_chat_{session_short}_{timestamp}.md"
    else:
        fn = f"agentic_rag_chat_{timestamp}.md"

    if st.download_button(
        "💾 Export Chat",
        export_chat_history(),
        file_name=fn,
        mime="text/markdown",
        use_container_width=True,
    ):
        st.sidebar.success("📥 Chat history exported!")


def knowledge_base_info_widget(agent: Agent) -> None:
    """Display knowledge base information."""
    if not agent.knowledge:
        st.sidebar.info("No knowledge base configured")
        return

    vector_db = getattr(agent.knowledge, "vector_db", None)
    if not vector_db:
        st.sidebar.info("No vector store configured")
        return

    try:
        doc_count = vector_db.get_count()
        if doc_count == 0:
            st.sidebar.info("💡 Upload documents to populate the knowledge base")
        else:
            st.sidebar.metric("Documents Loaded", doc_count)
    except Exception as e:
        logger.error(f"Error getting knowledge base info: {e}")
        st.sidebar.warning("Could not retrieve knowledge base information")


COMMON_CSS: str = """
    <style>
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
    }
    .stDownloadButton button {
        width: 100%;
        border-radius: 20px;
        margin: 0.2em 0;
        transition: all 0.3s ease;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px);
    }
    </style>
"""
