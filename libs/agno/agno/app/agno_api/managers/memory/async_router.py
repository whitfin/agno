from typing import List

from fastapi import HTTPException, Path
from fastapi.routing import APIRouter

from agno.app.agno_api.managers.memory.schemas import UserMemorySchema
from agno.memory import Memory


def attach_async_routes(router: APIRouter, memory: Memory) -> APIRouter:
    @router.get("/memories", response_model=List[UserMemorySchema], status_code=200)
    async def get_memories() -> List[UserMemorySchema]:
        user_memories = memory.get_user_memories()
        if not user_memories:
            return []

        return [UserMemorySchema.from_memory(user_memory) for user_memory in user_memories]

    @router.get("/memories/{memory_id}", response_model=UserMemorySchema, status_code=200)
    async def get_memory(memory_id: str = Path()) -> UserMemorySchema:
        user_memory = memory.get_user_memory(memory_id=memory_id)
        if not user_memory:
            raise HTTPException(status_code=404, detail=f"Memory with ID {memory_id} not found")

        return UserMemorySchema.from_memory(user_memory)

    @router.post("/memories", response_model=UserMemorySchema, status_code=200)
    async def create_memory(payload: UserMemorySchema) -> UserMemorySchema:
        user_memory = memory.upsert_user_memory(memory=payload)
        if not user_memory:
            raise HTTPException(status_code=400, detail="Failed to create memory")
        return UserMemorySchema.from_memory(user_memory)

    @router.put("/memories/{memory_id}", response_model=UserMemorySchema, status_code=200)
    async def update_memory(payload: UserMemorySchema) -> UserMemorySchema:
        user_memory = memory.upsert_user_memory(memory=payload)
        if not user_memory:
            raise HTTPException(status_code=400, detail="Failed to update memory")

        return UserMemorySchema.from_memory(user_memory)

    @router.delete("/memories/{memory_id}", status_code=204)
    async def delete_memory(memory_id: str = Path()) -> None:
        memory.delete_user_memory(memory_id=memory_id)

    return router
