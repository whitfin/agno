from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from agno.memory import UserMemory


class UserMemorySchema(BaseModel):
    memory_id: str
    memory: str
    topics: Optional[List[str]]
    last_updated: Optional[datetime]

    @classmethod
    def from_memory(cls, memory: UserMemory) -> "UserMemorySchema":
        return cls(
            memory_id=memory.memory_id,  # type: ignore
            memory=memory.memory,
            topics=memory.topics,
            last_updated=memory.last_updated,
        )
