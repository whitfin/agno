from typing import Iterator, List, Optional
from agno.models.base import Model
from agno.run.response import RunResponseEvent
from agno.tools.function import Function
from agno.utils.log import log_error, log_exception, log_info


class Console:
    model: Optional[Model] = None
    
    _tools: Optional[List[Function]] = None
    

    def __init__(self, model: Optional[Model] = None):
        self.model = model
        if self.model is None:
            try:
                from agno.models.openai import OpenAIChat
            except ModuleNotFoundError as e:
                log_exception(e)
                log_error(
                    "Agno agents use `openai` as the default model provider. "
                    "Please provide a `model` or install `openai`."
                )
                exit(1)

            log_info("Setting Consoledefault model to OpenAI Chat")
            self.model = OpenAIChat(id="gpt-4o")
    
    def initialize(self):
        pass
        
    
    
        
        
        
    def run(self, message: str) -> Iterator[RunResponseEvent]:
        