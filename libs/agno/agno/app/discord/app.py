import logging

from fastapi.routing import APIRouter

from agno.app.base import BaseAPIApp
from agno.app.discord.async_router import get_async_router
from agno.app.discord.sync_router import get_sync_router

logger = logging.getLogger(__name__)


class DiscordAPI(BaseAPIApp):
    def get_router(self) -> APIRouter:
        return get_sync_router(agent=self.agent, team=self.team)

    def get_async_router(self) -> APIRouter:
        return get_async_router(agent=self.agent, team=self.team)
