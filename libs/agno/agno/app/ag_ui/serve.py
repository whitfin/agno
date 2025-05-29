"""Convenience utilities for serving AG-UI backends.

This module provides helper functions to quickly spin up AG-UI-compatible
FastAPI applications using uvicorn, with sensible defaults for development
and production environments.

Example:
    Basic usage with an agent::
    
        from agno.agent import Agent
        from agno.app.ag_ui import AGUIApp, serve_agui_app
        
        agent = Agent(name="MyAssistant")
        app = AGUIApp(agent=agent).get_app()
        serve_agui_app(app)  # Starts server on http://localhost:7777
        
    Custom configuration::
    
        serve_agui_app(
            app,
            host="0.0.0.0",  # Listen on all interfaces
            port=8080,        # Custom port
            reload=True,      # Enable hot reload for development
            log_level="debug" # Verbose logging
        )
"""

from __future__ import annotations

import os
from typing import Union, Optional, Dict, Any

from fastapi import FastAPI

from agno.app.fastapi.serve import serve_fastapi_app
from agno.utils.log import logger

__all__ = ["serve_agui_app", "AGUIServerConfig"]


class AGUIServerConfig:
    """Configuration for AG-UI server.
    
    This class provides default configuration values that can be
    overridden via environment variables or constructor arguments.
    
    Environment variables:
        - AGUI_HOST: Server host (default: localhost)
        - AGUI_PORT: Server port (default: 7777)
        - AGUI_RELOAD: Enable hot reload (default: false)
        - AGUI_LOG_LEVEL: Uvicorn log level (default: info)
        - AGUI_WORKERS: Number of worker processes (default: 1)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reload: Optional[bool] = None,
        log_level: Optional[str] = None,
        workers: Optional[int] = None,
        **kwargs: Any
    ):
        """Initialize server configuration.
        
        Args:
            host: Server host address
            port: Server port number
            reload: Enable hot reload for development
            log_level: Uvicorn log level
            workers: Number of worker processes
            **kwargs: Additional uvicorn configuration
        """
        self.host = host or os.getenv("AGUI_HOST", "localhost")
        self.port = port or int(os.getenv("AGUI_PORT", "7777"))
        self.reload = reload if reload is not None else os.getenv("AGUI_RELOAD", "false").lower() == "true"
        self.log_level = log_level or os.getenv("AGUI_LOG_LEVEL", "info")
        self.workers = workers or int(os.getenv("AGUI_WORKERS", "1"))
        self.extra_kwargs = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for uvicorn.
        
        Returns:
            Dictionary of uvicorn configuration options
        """
        config = {
            "host": self.host,
            "port": self.port,
            "reload": self.reload,
            "log_level": self.log_level,
        }
        
        # Only add workers if not using reload
        if not self.reload and self.workers > 1:
            config["workers"] = self.workers
        
        # Merge extra kwargs
        config.update(self.extra_kwargs)
        
        return config
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"AGUIServerConfig("
            f"host='{self.host}', "
            f"port={self.port}, "
            f"reload={self.reload}, "
            f"log_level='{self.log_level}', "
            f"workers={self.workers}"
            f")"
        )


def serve_agui_app(
    app: Union[str, FastAPI],
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: Optional[bool] = None,
    log_level: Optional[str] = None,
    workers: Optional[int] = None,
    config: Optional[AGUIServerConfig] = None,
    **kwargs: Any
) -> None:
    """Run an AG-UI FastAPI application with uvicorn.
    
    This function provides sensible defaults for AG-UI applications while
    allowing full customization of the uvicorn server configuration.
    
    Args:
        app: FastAPI application instance or module:app string
        host: Server host address (default: localhost)
        port: Server port (default: 7777)
        reload: Enable hot reload for development
        log_level: Uvicorn log level (info, debug, warning, error)
        workers: Number of worker processes (ignored if reload=True)
        config: Pre-configured AGUIServerConfig instance
        **kwargs: Additional arguments passed to uvicorn
        
    Examples:
        Basic usage::
        
            from agno.app.ag_ui import AGUIApp
            from agno.agent import Agent
            
            agent = Agent(name="Assistant")
            app = AGUIApp(agent=agent).get_app()
            serve_agui_app(app)
            
        With custom configuration::
        
            config = AGUIServerConfig(
                host="0.0.0.0",
                port=8080,
                log_level="debug"
            )
            serve_agui_app(app, config=config)
            
        Production deployment::
        
            serve_agui_app(
                "myapp:app",  # Module string for multiprocessing
                host="0.0.0.0",
                port=80,
                workers=4,
                log_level="warning"
            )
    
    Note:
        The default port 7777 is chosen to match the AG-UI frontend
        development server expectations. In production, you may want
        to use standard ports like 80 or 443 with a reverse proxy.
    """
    # Use provided config or create new one
    if config is None:
        config = AGUIServerConfig(
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            workers=workers,
            **kwargs
        )
    
    # Log server configuration
    logger.info(f"Starting AG-UI server with configuration: {config}")
    
    # Get configuration dictionary
    server_config = config.to_dict()
    
    # Log startup information
    protocol = "https" if server_config.get("ssl_keyfile") else "http"
    bind_host = server_config["host"]
    display_host = "localhost" if bind_host in ("0.0.0.0", "127.0.0.1") else bind_host
    
    logger.info(
        f"AG-UI backend will be available at: "
        f"{protocol}://{display_host}:{server_config['port']}/api/copilotkit"
    )
    
    if server_config.get("reload"):
        logger.info("Hot reload is enabled - suitable for development only")
    
    # Delegate to the generic FastAPI server function
    serve_fastapi_app(app, **server_config)
