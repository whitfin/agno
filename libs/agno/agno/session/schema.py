from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

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
