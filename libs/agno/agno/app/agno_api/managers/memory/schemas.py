from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UserMemorySchema(BaseModel):
    memory_id: str
    memory: str
    topics: Optional[List[str]]
    last_updated: Optional[datetime]

    @classmethod
    def from_dict(cls, memory_dict: Dict[str, Any]) -> "UserMemorySchema":
        return cls(
            memory_id=memory_dict["memory_id"],
            memory=memory_dict["memory"]["memory"],
            topics=memory_dict["memory"]["topics"],
            last_updated=memory_dict["last_updated"],
        )


class UserMemoryCreateSchema(BaseModel):
    """Define the payload expected for creating a new user memory"""

    memory: str
    user_id: str
    topics: Optional[List[str]] = None
