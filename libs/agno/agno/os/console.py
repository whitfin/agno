from typing import AsyncIterator, Callable, Iterator, List, Optional
from agno.agent.agent import Agent
from agno.models.base import Model
from agno.run.response import RunResponse, RunResponseEvent
from agno.tools.function import Function


class Console(Agent):
    model: Optional[Model] = None
    
    def __init__(self, model: Optional[Model] = None):
        super().__init__(model=model, 
                         name="Console",
                         instructions=[
                             "You are a helpful assistant for the AgentOS application.",
                             "You can answer questions and help with tasks.",
                             "When asked to run an agent, team or workflow, make sure you have enough information to do so.",
                         ])
        
    
    def initialize(self, api_functions: List[Function]):
        self.tools = api_functions
        
    async def execute(self, message: str) -> RunResponse:
        response = await self.arun(message)
        return response
    
    async def print(self, message: str):
        await self.aprint_response(message, show_message=False)