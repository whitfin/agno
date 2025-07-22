from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


@dataclass
class SessionSummary:
    """Model for Session Summary."""

    summary: str
    topics: Optional[List[str]] = None
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "summary": self.summary,
            "topics": self.topics,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
        return {k: v for k, v in _dict.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        last_updated = data.get("last_updated")
        if last_updated:
            data["last_updated"] = datetime.fromisoformat(last_updated)
        return cls(**data)


class SessionSummaryResponse(BaseModel):
    """Model for Session Summary."""

    summary: str = Field(
        ...,
        description="Summary of the session. Be concise and focus on only important information. Do not make anything up.",
    )
    topics: Optional[List[str]] = Field(None, description="Topics discussed in the session.")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True, indent=2)


@dataclass
class SessionSummaryManager:
    """Session Summary Manager"""

    # Model used for memory management
    model: Optional[Model] = None

    # Provide the system message for the manager as a string. If not provided, a default prompt will be used.
    system_message: Optional[str] = None
    # Provide the memory capture instructions for the manager as a string. If not provided, a default prompt will be used.
    memory_capture_instructions: Optional[str] = None
    # Additional instructions for the manager
    additional_instructions: Optional[str] = None

    # Whether memories were created in the last run
    memories_updated: bool = False

    # Whether to delete memories
    delete_memories: bool = False
    # Whether to clear memories
    clear_memories: bool = False

    # The database to store memories
    db: Optional[BaseDb] = None

    debug_mode: bool = False

    