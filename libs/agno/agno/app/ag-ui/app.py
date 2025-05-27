"""AG-UI FastAPI application helper.

Usage:
```
from agno.app.ag_ui.app import AGUIApp
from agno.agent.builtins import EchoAgent

agent = EchoAgent()
app = AGUIApp(agent=agent).get_app()
```
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI

from agno.agent.agent import Agent
from .router import get_router as get_agui_router
from agno.app.fastapi.app import FastAPIApp
from agno.app.settings import APIAppSettings
from agno.team.team import Team


class AGUIApp(FastAPIApp):
    """FastAPIApp derivative pre-configured with CopilotKit router."""

    def __init__(
        self,
        *,
        agent: Optional[Agent] = None,
        team: Optional[Team] = None,
        settings: Optional[APIAppSettings] = None,
        api_app: Optional[FastAPI] = None,
        router: Optional[APIRouter] = None,
    ) -> None:
        super().__init__(
            agent=agent,
            team=team,
            settings=settings,
            api_app=api_app,
            router=router,
        )

        # Internal CopilotKit router (without prefix). Keep separate from outer prefix router.
        self._copilot_router: Optional[APIRouter] = None

    # override to inject our router
    def get_router(self) -> APIRouter:
        if self._copilot_router is None:
            self._copilot_router = get_agui_router(agent=self.agent, team=self.team)
        return self._copilot_router

    # Ensure async-mode server builds also use CopilotKit router
    def get_async_router(self) -> APIRouter:  # type: ignore[override]
        # Reuse the synchronous router; endpoint functions themselves may be async.
        return self.get_router()

    # ------------------------------------------------------------------
    # FastAPI application factory
    # ------------------------------------------------------------------

    def get_app(self, use_async: bool = True, prefix: str = "/api/agui"):
        """Return a fully-configured FastAPI application instance.

        This override simply changes the **default** URL prefix from the
        generic ``/v1`` (defined in :pyclass:`~agno.app.fastapi.app.FastAPIApp`)
        to the AG-UI-specific ``/api/agui`` so that the backend aligns with
        the rewrite rule configured in the Dojo front-end
        (``next.config.ts``).

        The *prefix* argument remains customisable; callers can still supply
        a different value if required.
        """

        # Delegate the heavy lifting to the parent implementation while
        # injecting our AG-UI-specific default prefix.
        return super().get_app(use_async=use_async, prefix=prefix)
