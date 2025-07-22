from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Union

from agno.models.message import Message
from agno.run.response import RunResponse, RunStatus
from agno.run.team import TeamRunResponse
from agno.session.summary import SessionSummary
from agno.media import AudioArtifact, ImageArtifact, VideoArtifact  
from agno.utils.log import log_debug, log_warning

@dataclass
class TeamMemberInteraction:
    member_name: str
    task: str
    response: Union[RunResponse, TeamRunResponse]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_name": self.member_name,
            "task": self.task,
            "response": self.response.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamMemberInteraction":
        return cls(member_name=data["member_name"], task=data["task"], response=RunResponse.from_dict(data["response"]))


@dataclass
class TeamContext:
    # List of team member interaction, represented as a request and a response
    member_interactions: List[TeamMemberInteraction] = field(default_factory=list)
    text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_interactions": [interaction.to_dict() for interaction in self.member_interactions],
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamContext":
        return cls(
            member_interactions=[
                TeamMemberInteraction.from_dict(interaction) for interaction in data["member_interactions"]
            ],
            text=data["text"],
        )



@dataclass
class TeamSession:
    """Team Session that is stored in the database"""

    # Session UUID
    session_id: str
    # ID of the team session this team session is associated with (so for sub-teams)
    team_session_id: Optional[str] = None

    # ID of the team that this session is associated with
    team_id: Optional[str] = None
    # ID of the user interacting with this team
    user_id: Optional[str] = None
    # ID of the workflow that this session is associated with
    workflow_id: Optional[str] = None

    # Team Data: agent_id, name and model
    team_data: Optional[Dict[str, Any]] = None
    # Session Data: session_name, session_state, images, videos, audio
    session_data: Optional[Dict[str, Any]] = None
    # Extra Data stored with this agent
    extra_data: Optional[Dict[str, Any]] = None
    # List of all messages in the session
    chat_history: Optional[list[Message]] = None
    # List of all runs in the session
    runs: Optional[list[TeamRunResponse]] = None
    # Summary of the session
    summary: Optional[Dict[str, Any]] = None

    # The unix timestamp when this session was created
    created_at: Optional[int] = None
    # The unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        session_dict = asdict(self)

        session_dict["chat_history"] = [msg.to_dict() for msg in self.chat_history] if self.chat_history else None
        session_dict["runs"] = [run.to_dict() for run in self.runs] if self.runs else None
        session_dict["summary"] = self.summary.to_dict() if isinstance(self.summary, SessionSummary) else self.summary

        return session_dict

    def telemetry_data(self) -> Dict[str, Any]:
        return {
            "model": self.team_data.get("model") if self.team_data else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional[TeamSession]:
        if data is None or data.get("session_id") is None:
            log_warning("TeamSession is missing session_id")
            return None

        # TODO: Account for runs inside a team that can be RunResponse
        runs = data.get("runs")
        if runs is not None and isinstance(runs[0], dict):
            runs = [TeamRunResponse.from_dict(run) for run in runs]

        chat_history = data.get("chat_history")
        if chat_history is not None and isinstance(chat_history[0], dict):
            chat_history = [Message.from_dict(msg) for msg in chat_history]

        return cls(
            session_id=data.get("session_id"),  # type: ignore
            team_id=data.get("team_id"),
            team_session_id=data.get("team_session_id"),
            user_id=data.get("user_id"),
            workflow_id=data.get("workflow_id"),
            team_data=data.get("team_data"),
            session_data=data.get("session_data"),
            extra_data=data.get("extra_data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            chat_history=chat_history,
            runs=runs,
            summary=data.get("summary"),
        )

    def add_run(self, run: TeamRunResponse):
        """Adds a RunResponse, together with some calculated data, to the runs list."""

        messages = run.messages
        for m in messages:
            if m.metrics is not None:
                m.metrics.timer = None

        if not self.runs:
            self.runs = []

        self.runs.append(run)

        log_debug("Added RunResponse to Agent Session")

    def get_messages_from_last_n_runs(
        self,
        session_id: str,
        agent_id: Optional[str] = None,
        team_id: Optional[str] = None,
        last_n: Optional[int] = None,
        skip_role: Optional[str] = None,
        skip_status: Optional[List[RunStatus]] = None,
        skip_history_messages: bool = True,
    ) -> List[Message]:
        """Returns the messages from the last_n runs, excluding previously tagged history messages.
        Args:
            session_id: The session id to get the messages from.
            agent_id: The id of the agent to get the messages from.
            team_id: The id of the team to get the messages from.
            last_n: The number of runs to return from the end of the conversation. Defaults to all runs.
            skip_role: Skip messages with this role.
            skip_status: Skip messages with this status.
            skip_history_messages: Skip messages that were tagged as history in previous runs.
        Returns:
            A list of Messages from the specified runs, excluding history messages.
        """
        if not self.runs:
            return []

        if skip_status is None:
            skip_status = [RunStatus.paused, RunStatus.cancelled, RunStatus.error]

        session_runs = self.runs
        # Filter by agent_id and team_id
        if agent_id:
            session_runs = [run for run in session_runs if hasattr(run, "agent_id") and run.agent_id == agent_id]  # type: ignore
        if team_id:
            session_runs = [run for run in session_runs if hasattr(run, "team_id") and run.team_id == team_id]  # type: ignore

        # Filter by status
        session_runs = [run for run in session_runs if hasattr(run, "status") and run.status not in skip_status]  # type: ignore

        # Filter by last_n
        runs_to_process = session_runs[-last_n:] if last_n is not None else session_runs
        messages_from_history = []
        system_message = None
        for run_response in runs_to_process:
            if not (run_response and run_response.messages):
                continue

            for message in run_response.messages:
                # Skip messages with specified role
                if skip_role and message.role == skip_role:
                    continue
                # Skip messages that were tagged as history in previous runs
                if hasattr(message, "from_history") and message.from_history and skip_history_messages:
                    continue
                if message.role == "system":
                    # Only add the system message once
                    if system_message is None:
                        system_message = message
                        messages_from_history.append(system_message)
                else:
                    messages_from_history.append(message)

        log_debug(f"Getting messages from previous runs: {len(messages_from_history)}")
        return messages_from_history

    def get_tool_calls(self, session_id: str, num_calls: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns a list of tool calls from the messages"""

        tool_calls = []
        session_runs = self.runs
        for run_response in session_runs[::-1]:
            if run_response and run_response.messages:
                for message in run_response.messages:
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_calls.append(tool_call)
                            if num_calls and len(tool_calls) >= num_calls:
                                return tool_calls
        return tool_calls

    def get_messages_for_session(
        self,
        user_role: str = "user",
        assistant_role: Optional[List[str]] = None,
        skip_history_messages: bool = True,
    ) -> List[Message]:
        """Returns a list of messages for the session that iterate through user message and assistant response."""

        if assistant_role is None:
            # TODO: Check if we still need CHATBOT as a role
            assistant_role = ["assistant", "model", "CHATBOT"]

        final_messages: List[Message] = []
        session_runs = self.runs
        for run_response in session_runs:
            if run_response and run_response.messages:
                user_message_from_run = None
                assistant_message_from_run = None

                # Start from the beginning to look for the user message
                for message in run_response.messages:
                    if hasattr(message, "from_history") and message.from_history and skip_history_messages:
                        continue
                    if message.role == user_role:
                        user_message_from_run = message
                        break

                # Start from the end to look for the assistant response
                for message in run_response.messages[::-1]:
                    if hasattr(message, "from_history") and message.from_history and skip_history_messages:
                        continue
                    if message.role in assistant_role:
                        assistant_message_from_run = message
                        break

                if user_message_from_run and assistant_message_from_run:
                    final_messages.append(user_message_from_run)
                    final_messages.append(assistant_message_from_run)
        return final_messages

    def get_session_summary(self) -> Optional[SessionSummary]:
        """Get the session summary for the session"""

        if self.summary is None:
            return None
        return self.summary

    # Chat History functions
    def get_chat_history(self) -> List[Message]:
        """Get the chat history for the session"""

        messages = []
        for run in self.runs:
            messages.extend([msg for msg in run.messages if not msg.from_history])
        self.chat_history = messages
        return messages

    # -*- Team Context Functions
    def add_interaction_to_team_context(
        self, session_id: str, member_name: str, task: str, run_response: Union[RunResponse, TeamRunResponse]
    ) -> None:
        if self.team_context is None:
            self.team_context = {}
        if session_id not in self.team_context:
            self.team_context[session_id] = TeamContext()
        self.team_context[session_id].member_interactions.append(
            TeamMemberInteraction(
                member_name=member_name,
                task=task,
                response=run_response,
            )
        )
        log_debug(f"Updated team context with member name: {member_name}")

    def set_team_context_text(self, session_id: str, text: Union[dict, str]) -> None:
        if self.team_context is None:
            self.team_context = {}
        if session_id not in self.team_context:
            self.team_context[session_id] = TeamContext()
        if isinstance(text, dict):
            if self.team_context[session_id].text is not None:
                try:
                    current_context = json.loads(self.team_context[session_id].text)  # type: ignore
                except Exception:
                    current_context = {}
            else:
                current_context = {}
            current_context.update(text)
            self.team_context[session_id].text = json.dumps(current_context)
        else:
            # If string then we overwrite the current context
            self.team_context[session_id].text = text

    def get_team_context_str(self, session_id: str) -> str:
        if not self.team_context:
            return ""
        session_team_context = self.team_context.get(session_id, None)
        if session_team_context and session_team_context.text:
            return f"<team context>\n{session_team_context.text}\n</team context>\n"
        return ""

    def get_team_member_interactions_str(self, session_id: str) -> str:
        if not self.team_context:
            return ""
        team_member_interactions_str = ""
        session_team_context = self.team_context.get(session_id, None)
        if session_team_context and session_team_context.member_interactions:
            team_member_interactions_str += "<member interactions>\n"

            for interaction in session_team_context.member_interactions:
                response_dict = interaction.response.to_dict()
                response_content = (
                    response_dict.get("content")
                    or ",".join([tool.get("content", "") for tool in response_dict.get("tools", [])])
                    or ""
                )
                team_member_interactions_str += f"Member: {interaction.member_name}\n"
                team_member_interactions_str += f"Task: {interaction.task}\n"
                team_member_interactions_str += f"Response: {response_content}\n"
                team_member_interactions_str += "\n"
            team_member_interactions_str += "</member interactions>\n"
        return team_member_interactions_str

    def get_team_context_images(self, session_id: str) -> List[ImageArtifact]:
        if not self.team_context:
            return []
        images = []
        session_team_context = self.team_context.get(session_id, None)
        if session_team_context and session_team_context.member_interactions:
            for interaction in session_team_context.member_interactions:
                if interaction.response.images:
                    images.extend(interaction.response.images)
        return images

    def get_team_context_videos(self, session_id: str) -> List[VideoArtifact]:
        if not self.team_context:
            return []
        videos = []
        session_team_context = self.team_context.get(session_id, None)
        if session_team_context and session_team_context.member_interactions:
            for interaction in session_team_context.member_interactions:
                if interaction.response.videos:
                    videos.extend(interaction.response.videos)
        return videos

    def get_team_context_audio(self, session_id: str) -> List[AudioArtifact]:
        if not self.team_context:
            return []
        audio = []
        session_team_context = self.team_context.get(session_id, None)
        if session_team_context and session_team_context.member_interactions:
            for interaction in session_team_context.member_interactions:
                if interaction.response.audio:
                    audio.extend(interaction.response.audio)
        return audio