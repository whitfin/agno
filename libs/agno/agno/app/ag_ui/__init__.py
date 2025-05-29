"""AG-UI (CopilotKit) integration for AGno.

This package provides seamless integration between AGno agents/teams
and the AG-UI frontend framework (CopilotKit).

Key components:
    - AGUIApp: FastAPI application configured for AG-UI
    - serve_agui_app: Convenience function to run AG-UI backends
    - get_router: Low-level router factory for custom integrations

Example:
    Quick start with an agent::
    
        from agno.agent import Agent
        from agno.app.ag_ui import AGUIApp, serve_agui_app
        
        # Create agent
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant"
        )
        
        # Create and run AG-UI app
        app = AGUIApp(agent=agent).get_app()
        serve_agui_app(app)
        
    Production deployment::
    
        from agno.app.ag_ui import AGUIApp, AGUIAppSettings
        
        settings = AGUIAppSettings(
            app_name="Production AG-UI",
            enable_cors=True,
            cors_origins=["https://myapp.com"],
            max_message_size=20 * 1024 * 1024  # 20MB
        )
        
        app = AGUIApp(
            agent=agent,
            settings=settings
        ).get_app()
"""

from .app import AGUIApp, AGUIAppSettings
from .router import get_router
from .serve import serve_agui_app, AGUIServerConfig

__all__ = [
    # Main application class
    "AGUIApp",
    "AGUIAppSettings",
    
    # Server utilities
    "serve_agui_app",
    "AGUIServerConfig",
    
    # Low-level router
    "get_router",
]

__version__ = "0.1.0" 