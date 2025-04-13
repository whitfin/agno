import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import streamlit as st
from agno.agent.agent import Agent
from agno.team import Team
from agno.utils.log import logger
from os_agent import get_llm_os


async def initialize_session_state():
    logger.info(f"---*--- Initializing session state ---*---")
    st.session_state["uagi"] = {
        "uagi": None,
        "session_id": None,
        "messages": [],
    }


async def selected_model() -> str:
    """Display a model selector in the sidebar."""
    model_options = {
        "claude-3-7-sonnet": "anthropic:claude-3-7-sonnet-latest",
        "gpt-4o": "openai:gpt-4o",
        "gemini-2.5-pro": "google:gemini-2.5-pro-preview-03-25",
        "llama-4-scout": "groq:meta-llama/llama-4-scout-17b-16e-instruct",
    }

    selected_model_key = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,  # Default to claude-3-7-sonnet
        key="model_selector",
    )
    model_id = model_options[selected_model_key]
    return model_id


async def selected_tools() -> List[str]:
    """Display a tool selector in the sidebar."""
    tool_options = {
        "Calculator": "calculator",
        "Web Search (DDG)": "ddg_search",
        "File I/O": "file_tools",
        "Shell Access": "shell_tools",
    }
    selected_tools = st.sidebar.multiselect(
        "Select Tools",
        options=list(tool_options.keys()),
        default=list(tool_options.keys()),
        key="tool_selector",
    )
    return [tool_options[tool] for tool in selected_tools]


async def selected_team_members() -> List[str]:
    """Display a selector for team members in the sidebar."""
    member_options = {
        "Data Analyst": "data_analyst",
        "Python Agent": "python_agent",
        "Research Agent": "research_agent",
        "Investment Agent": "investment_agent",
    }
    selected_members = st.sidebar.multiselect(
        "Select Members",
        options=list(member_options.keys()),
        default=list(member_options.keys()),
        key="member_selector",
    )
    return [member_options[member] for member in selected_members]


async def about_agno():
    """Show information about Agno in the sidebar"""
    with st.sidebar:
        st.markdown("### About Agno ✨")
        st.markdown("""
        Agno is a lightweight library for building Agents with memory, knowledge, tools and reasoning.

        [GitHub](https://github.com/agno-agi/agno) | [Docs](https://docs.agno.com)
        """)

        st.markdown("### Need Help?")
        st.markdown(
            "If you have any questions, catch us on [discord](https://agno.link/discord) or post in the community [forum](https://agno.link/community)."
        )


# def is_json(myjson):
#     """Check if a string is valid JSON"""
#     try:
#         json.loads(myjson)
#     except (ValueError, TypeError):
#         return False
#     return True


# def add_message(
#     role: str,
#     content: str,
#     tool_calls: Optional[List[Dict[str, Any]]] = None,
#     intermediate_steps_displayed: bool = False,
# ) -> None:
#     """Safely add a message to the session state"""
#     if "messages" not in st.session_state or not isinstance(
#         st.session_state["messages"], list
#     ):
#         st.session_state["messages"] = []
#     st.session_state["messages"].append(
#         {
#             "role": role,
#             "content": content,
#             "tool_calls": tool_calls,
#             "intermediate_steps_displayed": intermediate_steps_displayed,
#         }
#     )


# def display_tool_calls(tool_calls_container, tools):
#     """Display tool calls in a streamlit container with expandable sections.

#     Args:
#         tool_calls_container: Streamlit container to display the tool calls
#         tools: List of tool call dictionaries containing name, args, content, and metrics
#     """
#     try:
#         with tool_calls_container.container():
#             # Handle single tool_call dict case
#             if isinstance(tools, dict):
#                 tools = [tools]
#             elif not isinstance(tools, list):
#                 logger.warning(
#                     f"Unexpected tools format: {type(tools)}. Skipping display."
#                 )
#                 return

#             for tool_call in tools:
#                 # Normalize access to tool details
#                 tool_name = tool_call.get("tool_name") or tool_call.get(
#                     "name", "Unknown Tool"
#                 )
#                 tool_args = tool_call.get("tool_args") or tool_call.get("args", {})
#                 content = tool_call.get("content", None)
#                 metrics = tool_call.get("metrics", None)

#                 # Add timing information safely
#                 execution_time_str = "N/A"
#                 try:
#                     if metrics is not None and hasattr(metrics, "time"):
#                         execution_time = metrics.time
#                         if execution_time is not None:
#                             execution_time_str = f"{execution_time:.4f}s"
#                 except Exception as e:
#                     logger.error(f"Error getting tool metrics time: {str(e)}")
#                     pass  # Keep default "N/A"

#                 expander_title = f"🛠️ {tool_name.replace('_', ' ').title()}"
#                 if execution_time_str != "N/A":
#                     expander_title += f" ({execution_time_str})"

#                 with st.expander(expander_title, expanded=False):
#                     # Show query/code/command with syntax highlighting
#                     if isinstance(tool_args, dict):
#                         if "query" in tool_args:
#                             st.code(tool_args["query"], language="sql")
#                         elif "code" in tool_args:
#                             st.code(tool_args["code"], language="python")
#                         elif "command" in tool_args:
#                             st.code(tool_args["command"], language="bash")

#                     # Display arguments if they exist and are not just the code/query shown above
#                     args_to_show = {
#                         k: v
#                         for k, v in tool_args.items()
#                         if k not in ["query", "code", "command"]
#                     }
#                     if args_to_show:
#                         st.markdown("**Arguments:**")
#                         try:
#                             st.json(args_to_show)
#                         except Exception:
#                             st.write(args_to_show)  # Fallback for non-serializable args

#                     if content is not None:
#                         try:
#                             st.markdown("**Results:**")
#                             if isinstance(content, str) and is_json(content):
#                                 st.json(content)
#                             else:
#                                 st.write(content)
#                         except Exception as e:
#                             logger.debug(f"Could not display tool content: {e}")
#                             st.error("Could not display tool content.")

#     except Exception as e:
#         logger.error(f"Error displaying tool calls: {str(e)}")
#         tool_calls_container.error("Failed to display tool results")


# def restart_agent():
#     """Reset the agent and clear chat history"""
#     logger.debug("---*--- Restarting LLM OS agent ---*---")
#     st.session_state["llm_os_agent"] = None
#     st.session_state["llm_os_team"] = None
#     st.session_state["llm_os_session_id"] = None
#     st.session_state["messages"] = []
#     # Clear relevant config keys to force reinitialization with sidebar values
#     # This ensures the new agent uses the current sidebar settings
#     keys_to_clear = [
#         "cb_calculator",
#         "cb_ddg",
#         "cb_file",
#         "cb_shell",
#         "cb_data",
#         "cb_python",
#         "cb_research",
#         "cb_investment",
#         "model_selector",
#         "user_id_input",  # Clear these to re-read on rerun
#     ]
#     # for key in keys_to_clear:
#     #     if key in st.session_state:
#     #         del st.session_state[key] # Consider if clearing is needed vs. just re-reading in app.py
#     st.rerun()


# def export_chat_history():
#     """Export chat history as markdown"""
#     if "messages" in st.session_state:
#         chat_text = "# LLM OS - Chat History\n\n"
#         for msg in st.session_state["messages"]:
#             role = (
#                 "🤖 Assistant" if msg["role"] == "assistant" else "👤 User"
#             )  # Adjusted role check
#             # Safely handle content, could be None
#             content = msg.get("content", "*No content*")
#             chat_text += f"### {role}\n{content}\n\n"
#             # Optionally include tool calls (basic representation)
#             if msg.get("tool_calls"):
#                 chat_text += "**Tool Calls:**\n"
#                 for tc in msg["tool_calls"]:
#                     tool_name = tc.get("name", "Unknown Tool")
#                     tool_args = tc.get("args", {})
#                     chat_text += f"- `{tool_name}`: `{tool_args}`\n"
#                 chat_text += "\n"
#         return chat_text
#     return ""


# def about_widget() -> None:
#     """Display an about section in the sidebar"""
#     st.sidebar.markdown("---")
#     st.sidebar.markdown("### ℹ️ About")
#     st.sidebar.markdown("""
#     LLM OS: Your versatile AI assistant.

#     Built with:
#     - 🚀 Agno
#     - 💫 Streamlit
#     """)
#     st.sidebar.markdown(
#         "Build your own agents using [Agno](https://github.com/agytech/agno)!"
#     )


# def session_selector_widget(
#     team: Team, current_config: Dict[str, Any]
# ) -> Optional[str]:
#     """Display a session selector for the LLM OS Team in the sidebar.

#     Args:
#         team: The current LLM OS Team instance.
#         current_config: The current configuration dict used to initialize the team.

#     Returns:
#         The selected session ID if a change occurred, otherwise None.
#     """
#     selected_session_id_to_load = None  # Return value

#     if team.storage:
#         try:
#             agent_sessions = team.storage.get_all_sessions()
#             if not agent_sessions:
#                 st.sidebar.markdown("No past sessions found.")
#                 return None

#             # Get session names if available, otherwise use IDs
#             session_options = []
#             for session in agent_sessions:
#                 session_id = session.session_id
#                 session_name = (
#                     session.session_data.get("session_name", None)
#                     if session.session_data
#                     else None
#                 )
#                 # Fallback to session ID if name is missing or empty
#                 display_name = session_name if session_name else session_id
#                 # Append session_id to ensure uniqueness if names clash
#                 session_options.append(
#                     {"id": session_id, "display": f"{display_name} ({session_id[:8]})"}
#                 )

#             # Sort sessions by display name (optional)
#             session_options.sort(key=lambda x: x["display"])

#             # Find the index of the current session
#             current_session_id = st.session_state.get("llm_os_session_id")
#             current_index = 0  # Default to first item
#             for i, option in enumerate(session_options):
#                 if option["id"] == current_session_id:
#                     current_index = i
#                     break

#             # Display session selector
#             selected_display_name = st.sidebar.selectbox(
#                 "Chat History",
#                 options=[s["display"] for s in session_options],
#                 index=current_index,
#                 key="session_selector",
#             )

#             # Find the selected session ID based on the display name
#             selected_session_id = next(
#                 (
#                     s["id"]
#                     for s in session_options
#                     if s["display"] == selected_display_name
#                 ),
#                 None,
#             )

#             if selected_session_id and current_session_id != selected_session_id:
#                 logger.info(
#                     f"---*--- Loading LLM OS session: {selected_session_id} ---*---"
#                 )
#                 # Store the ID to be loaded, app.py will handle re-init
#                 selected_session_id_to_load = selected_session_id
#                 st.session_state["llm_os_session_id"] = (
#                     selected_session_id_to_load  # Update state immediately
#                 )
#                 # Trigger rerun in app.py after state update
#                 st.rerun()

#         except Exception as e:
#             st.sidebar.error(f"Error loading sessions: {e}")
#             logger.error(f"Failed to get/display sessions: {e}")

#     return selected_session_id_to_load  # Will likely be None due to rerun


# def rename_session_widget(team: Team) -> None:
#     """Rename the current session of the LLM OS Team and save to storage"""
#     if not team or not team.storage or not team.team_id:
#         return  # Cannot rename without team, storage, and session ID

#     container = st.sidebar.container()
#     session_row = container.columns([3, 1], vertical_alignment="center")

#     # Initialize session_edit_mode if needed
#     if "session_edit_mode" not in st.session_state:
#         st.session_state.session_edit_mode = False

#     # Get current session details by finding it in the list of all sessions
#     current_session_data = None
#     current_name = team.team_id  # Default to ID if lookup fails
#     try:
#         all_sessions = team.storage.get_all_sessions()
#         for session in all_sessions:
#             if session.session_id == team.team_id:
#                 current_session_data = (
#                     session.session_data or {}
#                 )  # Use empty dict if None
#                 current_name = current_session_data.get("session_name", team.team_id)
#                 break
#     except Exception as e:
#         logger.error(f"Failed to get session list for rename: {e}")
#         container.warning("Could not load session details.")
#         # Allow continuing with default name (team_id)

#     with session_row[0]:
#         if st.session_state.session_edit_mode:
#             new_session_name = st.text_input(
#                 "Session Name",
#                 value=current_name,  # Use fetched name
#                 key="session_name_input",
#                 label_visibility="collapsed",
#             )
#         else:
#             st.markdown(f"**{current_name}**")  # Display fetched name

#     with session_row[1]:
#         if st.session_state.session_edit_mode:
#             if st.button(
#                 "✓", key="save_session_name", help="Save name", type="primary"
#             ):
#                 if new_session_name and new_session_name != current_name:
#                     try:
#                         # Use the fetched session data or an empty dict
#                         updated_data = (
#                             current_session_data
#                             if current_session_data is not None
#                             else {}
#                         )
#                         updated_data["session_name"] = new_session_name
#                         team.storage.update_session(
#                             team.team_id, session_data=updated_data
#                         )
#                         st.session_state.session_edit_mode = False
#                         # No success message here to avoid immediate overwrite by rerun
#                         st.rerun()  # Rerun to update selector display
#                     except Exception as e:
#                         logger.error(f"Failed to rename session: {e}")
#                         container.error("Rename failed.")
#                 else:
#                     st.session_state.session_edit_mode = (
#                         False  # Just exit edit mode if name is same or empty
#                     )
#                     st.rerun()  # Rerun even if name is unchanged to exit edit mode UI

#         else:
#             if st.button("✎", key="edit_session_name", help="Rename chat"):
#                 st.session_state.session_edit_mode = True
#                 st.rerun()
