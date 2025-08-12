from enum import Enum

from pydantic import BaseModel


class WorkflowAction(Enum):
    respond_directly = "respond_directly"
    continue_workflow = "continue_workflow"
    ask_for_more_information = "ask_for_more_information"


class WorkflowResponse(BaseModel):
    action: WorkflowAction
    content: str