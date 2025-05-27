"""Convenience helper to run an **AG-UI** backend via `uvicorn`.

Example:
```
from agno.app.ag_ui.app import AGUIApp
from agno.agent.builtins import EchoAgent

app = AGUIApp(agent=EchoAgent()).get_app()
serve_agui_app(app, port=8888)
```
"""

from __future__ import annotations

from typing import Union

from fastapi import FastAPI

from agno.app.fastapi.serve import serve_fastapi_app


def serve_agui_app(
    app: Union[str, FastAPI],
    *,
    host: str = "localhost",
    port: int = 7777,
    reload: bool = False,
    **kwargs,
):
    """Run the given FastAPI app with sensible defaults for AG-UI."""
    serve_fastapi_app(app, host=host, port=port, reload=reload, **kwargs)
