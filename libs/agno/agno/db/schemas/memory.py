from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class SummaryRow(BaseModel):
    """Session Summary Row that is stored in the database"""

    id: Optional[str] = None
    summary: Dict[str, Any]
    user_id: Optional[str] = None
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def generate_id(self) -> "SummaryRow":
        if self.id is None:
            from uuid import uuid4

            self.id = str(uuid4())
        return self

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude={"last_updated"})
        _dict["last_updated"] = self.last_updated.isoformat() if self.last_updated else None
        return _dict


@dataclass
class UserMemory:
    """Model for User Memories"""

    memory: str
    memory_id: Optional[str] = None
    topics: Optional[List[str]] = None
    user_id: Optional[str] = None
    input: Optional[str] = None
    last_updated: Optional[datetime] = None

    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    workflow_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "memory_id": self.memory_id,
            "memory": self.memory,
            "topics": self.topics,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "input": self.input,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "team_id": self.team_id,
            "workflow_id": self.workflow_id,
        }
        return {k: v for k, v in _dict.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserMemory":
        # last_updated = data.get("last_updated")
        # if last_updated:
        #     data["last_updated"] = datetime.fromisoformat(last_updated)
        return cls(**data)
