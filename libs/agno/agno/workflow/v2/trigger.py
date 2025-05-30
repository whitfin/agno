from enum import Enum

class TriggerType(str, Enum):
    """Types of workflow triggers"""
    MANUAL = "manual"
    AGENTIC = "agentic"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
