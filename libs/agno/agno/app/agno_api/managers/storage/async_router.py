from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from agno.app.agno_api.managers.storage.schemas import RunSchema, SessionDetailSchema, SessionSchema
from agno.storage.base import SessionType
from agno.storage.base import Storage as StorageBase


def attach_async_routes(router: APIRouter, storage: StorageBase) -> APIRouter:
    @router.get("/sessions", response_model=List[SessionSchema], status_code=200)
    async def get_sessions(session_type: Optional[SessionType] = Query(None, alias="type")) -> List[SessionSchema]:
        if session_type is not None:
            sessions = storage.get_all_sessions(session_type=session_type)
        else:
            sessions = storage.get_all_sessions()

        return [SessionSchema.from_session(session) for session in sessions]

    @router.get("/sessions/{session_id}", response_model=SessionDetailSchema, status_code=200)
    async def get_session_by_id(
        session_id: str = Path(...),
        session_type: Optional[SessionType] = Query(None, description="Session type filter", alias="type"),
    ) -> SessionDetailSchema:
        session = storage.read_session(session_id=session_id, session_type=session_type)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")

        if session_type == SessionType.AGENT:
            return SessionDetailSchema.from_agent_session(session)
        elif session_type == SessionType.TEAM:
            return SessionDetailSchema.from_team_session(session)
        elif session_type == SessionType.WORKFLOW:
            return SessionDetailSchema.from_workflow_session(session)

        return SessionDetailSchema.from_session(session)

    @router.get("/sessions/{session_id}/runs", response_model=List[RunSchema], status_code=200)
    async def get_session_runs(
        session_id: str = Path(..., description="Session ID", alias="session-id"),
        session_type: Optional[SessionType] = Query(None, description="Session type filter", alias="type"),
    ) -> List[RunSchema]:
        session = storage.read_session(session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")

        runs = storage.get_all_runs(session_id=session_id)

        return runs

    return router
