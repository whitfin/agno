from typing import List

from fastapi import Path
from fastapi.routing import APIRouter

from agno.app.agno_api.managers.memory.schemas import MemorySchema
from agno.db.base import BaseDb


def attach_sync_routes(router: APIRouter, db: BaseDb) -> APIRouter:
    @router.get("/memories", response_model=List[MemorySchema], status_code=200)
    def get_memories() -> List[MemorySchema]:
        return db.get_memories()

    @router.get("/memories/{memory_id}", response_model=MemorySchema, status_code=200)
    def get_memory(memory_id: str = Path()) -> MemorySchema:
        return db.get_memory(memory_id=memory_id)

    @router.post("/memories", response_model=MemorySchema, status_code=200)
    def create_memory(memory: MemorySchema) -> MemorySchema:
        return db.create_memory(memory=memory)

    @router.put("/memories/{memory_id}", response_model=MemorySchema, status_code=200)
    def update_memory(memory: MemorySchema, memory_id: str = Path()) -> MemorySchema:
        return db.update_memory(memory_id=memory_id, memory=memory)

    @router.delete("/memories/{memory_id}", status_code=200)
    def delete_memory(memory_id: str = Path()) -> None:
        return db.delete_memory(memory_id=memory_id)

    return router
