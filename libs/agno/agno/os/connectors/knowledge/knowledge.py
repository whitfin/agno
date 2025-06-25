import logging
from typing import Optional
from uuid import uuid4

from fastapi.routing import APIRouter

from agno.os.connectors.base import BaseConnector
from agno.os.connectors.knowledge.router import attach_sync_routes
from agno.knowledge.knowledge import Knowledge  

logger = logging.getLogger(__name__)


class KnowledgeConnector(BaseConnector):
    type = "knowledge"

    router: APIRouter

    def __init__(self, knowledge: Knowledge, name: Optional[str] = None):
        self.name = name
        self.knowledge = knowledge

    def get_router(self, index: int) -> APIRouter:
        if not self.name:
            self.name = f"Knowledge Connector {index}"
        
        self.router_prefix = f"/knowledge/v1"

        # Cannot be overridden
        self.router = APIRouter(prefix=self.router_prefix, tags=["Knowledge"])

        self.router = attach_sync_routes(router=self.router, knowledge=self.knowledge)

        return self.router

