import logging

from fastapi.routing import APIRouter

from agno.app.agno_api.base import BaseInterface
from agno.app.agno_api.managers.memory.async_router import attach_async_routes
from agno.app.agno_api.managers.memory.sync_router import attach_sync_routes
from agno.db.base import BaseDb

logger = logging.getLogger(__name__)


class MemoryManager(BaseInterface):
    type = "memory"

    router: APIRouter

    def __init__(self, db: BaseDb):
        self.db = db

    def get_router(self, use_async: bool = True) -> APIRouter:
        # Cannot be overridden
        prefix: str = "/memory"
        version: str = "/v1"
        self.router = APIRouter(prefix=prefix + version, tags=["Memory"])

        if use_async:
            self.router = attach_async_routes(router=self.router, db=self.db)
        else:
            self.router = attach_sync_routes(router=self.router, db=self.db)

        return self.router
