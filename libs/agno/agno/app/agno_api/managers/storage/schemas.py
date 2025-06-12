from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from agno.storage.session import AgentSession, Session


class SessionSchema(BaseModel):
    session_id: str
    title: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def from_session(cls, session: Session) -> "SessionSchema":
        return cls(
            session_id=session.session_id,
            title="",  # TODO: session title?
            created_at=datetime.fromtimestamp(session.created_at) if session.created_at else None,
            updated_at=datetime.fromtimestamp(session.updated_at) if session.updated_at else None,
        )


class SessionDetailSchema(BaseModel):
    user_id: Optional[str]
    agent_session_id: str
    workspace_id: Optional[str]
    session_id: str
    agent_id: Optional[str]
    agent_data: Optional[dict]  # type
    agent_sessions: list
    response_latency_avg: Optional[float]
    total_tokens: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def from_agent_session(cls, session: AgentSession) -> "SessionDetailSchema":
        # TODO: check empty fields
        return cls(
            user_id=session.user_id,
            agent_session_id=session.session_id,
            workspace_id=None,
            session_id=session.session_id,
            agent_id=session.agent_id if session.agent_id else None,
            agent_data=session.agent_data,
            agent_sessions=[],
            response_latency_avg=0,
            total_tokens=0,
            created_at=datetime.fromtimestamp(session.created_at) if session.created_at else None,
            updated_at=datetime.fromtimestamp(session.updated_at) if session.updated_at else None,
        )


class RunSchema(BaseModel):
    run_id: str
    agent_session_id: str
    workspace_id: Optional[str]
    user_id: Optional[str]
    run_data: dict  # TODO: type
    run_review: Optional[dict]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
