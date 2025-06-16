from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from agno.memory import Memory


class MemorySchema(BaseModel):
    memory_id: str
    memory: str
    topics: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    @classmethod
    def from_memory(cls, memory: Memory) -> "MemorySchema":
        return cls(
            memory_id=memory.memory_id,
            memory=memory.memory,
            topics=memory.topics,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )
