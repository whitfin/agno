from typing import Union

from agno.storage_v2.session.agent import AgentSession
from agno.storage_v2.session.team import TeamSession
from agno.storage_v2.session.workflow import WorkflowSession

Session = Union[AgentSession, TeamSession, WorkflowSession]

__all__ = [
    "AgentSession",
    "TeamSession",
    "WorkflowSession",
    "Session",
]
