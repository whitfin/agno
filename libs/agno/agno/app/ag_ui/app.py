"""AG-UI FastAPI application helper.

This module provides the AGUIApp class, which extends FastAPIApp with
AG-UI-specific functionality, including automatic router configuration
and proper URL prefix handling for CopilotKit integration.

Example:
    Basic usage with an agent::
    
        from agno.agent import Agent
        from agno.app.ag_ui import AGUIApp
        
        # Create an agent
        agent = Agent(
            name="MyAssistant",
            instructions="You are a helpful assistant"
        )
        
        # Create AG-UI app
        agui_app = AGUIApp(agent=agent)
        
        # Get FastAPI instance
        app = agui_app.get_app()
        
    With a team::
    
        from agno.team import Team
        from agno.app.ag_ui import AGUIApp
        
        team = Team(name="SupportTeam", agents=[...])
        agui_app = AGUIApp(team=team)
        app = agui_app.get_app()
        
    Custom configuration::
    
        from agno.app.settings import APIAppSettings
        
        settings = APIAppSettings(
            app_name="My AG-UI Backend",
            app_version="1.0.0"
        )
        agui_app = AGUIApp(
            agent=agent,
            settings=settings
        )
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agno.agent.agent import Agent
from agno.app.fastapi.app import FastAPIApp
from agno.app.settings import APIAppSettings
from agno.team.team import Team
from agno.utils.log import logger

from .router import get_router as get_agui_router

__all__ = ["AGUIApp", "AGUIAppSettings"]


class AGUIAppSettings(APIAppSettings):
    """Extended settings specific to AG-UI applications.
    
    This class extends the base API settings with AG-UI-specific
    configuration options.
    """
    
    # AG-UI specific settings
    enable_cors: bool = True
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Frontend integration settings
    frontend_url: Optional[str] = None
    api_prefix: str = "/api/copilotkit"
    
    # Feature flags
    enable_state_management: bool = True
    enable_tool_injection: bool = True
    enable_session_persistence: bool = True
    
    # Performance settings
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    stream_timeout: int = 300  # 5 minutes
    
    def __init__(self, **kwargs):
        """Initialize AG-UI settings with defaults."""
        super().__init__(**kwargs)
        
        # Auto-configure CORS origins based on frontend URL
        if self.frontend_url and self.cors_origins == ["*"]:
            self.cors_origins = [self.frontend_url]


class AGUIApp(FastAPIApp):
    """FastAPI application configured for AG-UI (CopilotKit) integration.
    
    This class extends FastAPIApp with:
    - Automatic AG-UI router configuration
    - CORS middleware for frontend integration
    - Health check and metadata endpoints
    - Session management utilities
    - Error handling optimized for AG-UI
    
    Attributes:
        agent: Optional AGno agent instance
        team: Optional AGno team instance
        settings: Application settings
        api_app: FastAPI application instance
    """

    def __init__(
        self,
        *,
        agent: Optional[Agent] = None,
        team: Optional[Team] = None,
        settings: Optional[Union[APIAppSettings, AGUIAppSettings]] = None,
        api_app: Optional[FastAPI] = None,
        router: Optional[APIRouter] = None,
    ) -> None:
        """Initialize AG-UI application.
        
        Args:
            agent: AGno agent to expose via AG-UI
            team: AGno team to expose via AG-UI
            settings: Application settings (AGUIAppSettings recommended)
            api_app: Pre-configured FastAPI instance
            router: Custom router (rarely needed)
            
        Raises:
            ValueError: If neither agent nor team is provided
        """
        # Convert settings to AGUIAppSettings if needed
        if settings and not isinstance(settings, AGUIAppSettings):
            agui_settings = AGUIAppSettings(**settings.model_dump())
        else:
            agui_settings = settings or AGUIAppSettings()
        
        super().__init__(
            agent=agent,
            team=team,
            settings=agui_settings,
            api_app=api_app,
            router=router,
        )

        # Internal AG-UI router (without prefix)
        self._agui_router: Optional[APIRouter] = None
        
        # Track active sessions for monitoring
        self._active_sessions: Dict[str, Any] = {}
        
        # Log initialization
        entity_type = "agent" if agent else "team"
        entity_name = getattr(agent or team, "name", "Unknown")
        logger.info(
            f"Initialized AG-UI app with {entity_type}: {entity_name}"
        )

    @property
    def agui_settings(self) -> AGUIAppSettings:
        """Get AG-UI specific settings."""
        return self.settings  # type: ignore

    def get_router(self) -> APIRouter:
        """Get the AG-UI router instance.
        
        This override ensures we use the AG-UI-specific router
        instead of the generic FastAPI router.
        
        Returns:
            APIRouter configured for AG-UI
        """
        if self._agui_router is None:
            self._agui_router = get_agui_router(
                agent=self.agent, 
                team=self.team
            )
            self._add_utility_endpoints(self._agui_router)
        return self._agui_router

    def get_async_router(self) -> APIRouter:
        """Get async-compatible router.
        
        AG-UI router endpoints are already async-compatible,
        so we return the same router instance.
        
        Returns:
            The same router as get_router()
        """
        return self.get_router()
    
    def _add_utility_endpoints(self, router: APIRouter) -> None:
        """Add utility endpoints to the router.
        
        These endpoints provide health checks, metadata, and
        session management capabilities.
        
        Args:
            router: Router to add endpoints to
        """
        @router.get("/health")
        async def health_check():
            """Health check endpoint for monitoring."""
            return {
                "status": "healthy",
                "service": "ag-ui-backend",
                "agent": self.agent.name if self.agent else None,
                "team": self.team.name if self.team else None,
                "active_sessions": len(self._active_sessions)
            }
        
        @router.get("/info")
        async def get_info():
            """Get information about the AG-UI backend."""
            entity = self.agent or self.team
            return {
                "type": "agent" if self.agent else "team",
                "name": entity.name if entity else None,
                "description": getattr(entity, "description", None),
                "capabilities": {
                    "streaming": True,
                    "state_management": self.agui_settings.enable_state_management,
                    "tool_injection": self.agui_settings.enable_tool_injection,
                    "session_persistence": self.agui_settings.enable_session_persistence,
                },
                "settings": {
                    "max_message_size": self.agui_settings.max_message_size,
                    "stream_timeout": self.agui_settings.stream_timeout,
                }
            }
        
        @router.get("/sessions")
        async def list_sessions():
            """List active sessions (for monitoring/debugging)."""
            return {
                "sessions": list(self._active_sessions.keys()),
                "count": len(self._active_sessions)
            }
        
        @router.delete("/sessions/{session_id}")
        async def clear_session(session_id: str):
            """Clear a specific session."""
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
                return {"status": "cleared", "session_id": session_id}
            return JSONResponse(
                status_code=404,
                content={"error": "Session not found"}
            )

    def get_app(
        self, 
        use_async: bool = True, 
        prefix: str = "/api/copilotkit"
    ) -> FastAPI:
        """Get configured FastAPI application instance.
        
        This method creates a fully-configured FastAPI app with:
        - AG-UI router mounted at the specified prefix
        - CORS middleware (if enabled)
        - Error handlers
        - Request size limits
        
        Args:
            use_async: Whether to use async endpoints (always True for AG-UI)
            prefix: URL prefix for AG-UI endpoints
            
        Returns:
            Configured FastAPI application
            
        Example:
            >>> agui_app = AGUIApp(agent=my_agent)
            >>> app = agui_app.get_app()
            >>> # Now you can run: uvicorn app:app
        """
        # Get base app from parent
        app = super().get_app(use_async=True, prefix=prefix)
        
        # Add CORS middleware if enabled
        if self.agui_settings.enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.agui_settings.cors_origins,
                allow_credentials=self.agui_settings.cors_allow_credentials,
                allow_methods=self.agui_settings.cors_allow_methods,
                allow_headers=self.agui_settings.cors_allow_headers,
            )
            logger.info(
                f"CORS enabled for origins: {self.agui_settings.cors_origins}"
            )
        
        # Add global exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            """Handle uncaught exceptions gracefully."""
            logger.exception("Unhandled exception in AG-UI backend")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(exc) if self.settings.debug else "An error occurred",
                    "type": type(exc).__name__
                }
            )
        
        # Add request size limit middleware
        @app.middleware("http")
        async def limit_request_size(request: Request, call_next):
            """Enforce request size limits."""
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > self.agui_settings.max_message_size:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "Request too large",
                                "max_size": self.agui_settings.max_message_size
                            }
                        )
                except ValueError:
                    pass
            
            response = await call_next(request)
            return response
        
        # Add session tracking middleware
        @app.middleware("http")
        async def track_sessions(request: Request, call_next):
            """Track active sessions for monitoring."""
            if request.url.path.startswith(f"{prefix}/run"):
                # Extract session ID from request if available
                try:
                    body = await request.body()
                    request._body = body  # Cache body for reuse
                    
                    import json
                    data = json.loads(body) if body else {}
                    session_id = (
                        data.get("threadId") or 
                        data.get("session_id") or
                        data.get("sessionId")
                    )
                    
                    if session_id:
                        self._active_sessions[session_id] = {
                            "last_activity": None,  # Would use datetime.now()
                            "request_count": self._active_sessions.get(
                                session_id, {}
                            ).get("request_count", 0) + 1
                        }
                except Exception:
                    pass
            
            response = await call_next(request)
            return response
        
        # Log app configuration
        logger.info(
            f"AG-UI app configured with prefix: {prefix}, "
            f"CORS: {self.agui_settings.enable_cors}"
        )
        
        return app
    
    def create_test_client(self, **kwargs) -> Any:
        """Create a test client for the AG-UI app.
        
        This is useful for testing AG-UI backends.
        
        Args:
            **kwargs: Arguments passed to TestClient
            
        Returns:
            FastAPI TestClient instance
            
        Example:
            >>> client = agui_app.create_test_client()
            >>> response = client.post("/api/copilotkit/run", json={...})
        """
        from fastapi.testclient import TestClient
        
        app = self.get_app()
        return TestClient(app, **kwargs)