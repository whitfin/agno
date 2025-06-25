from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, cast
from agno.agent.agent import Agent
from agno.models.base import Model
from agno.os.connectors.base import BaseConnector
from agno.run.response import RunResponse, RunResponseEvent
from agno.team.team import Team
from agno.tools.function import Function
from agno.workflow.workflow import Workflow


class Console(Agent):
    model: Optional[Model] = None
    
    _agents: List[Agent] = []
    _teams: List[Team] = []
    _workflows: List[Workflow] = []
    _apps: List[BaseConnector] = []
    
    def __init__(self, model: Optional[Model] = None):
        super().__init__(model=model, 
                         name="Console",
                         instructions=[
                             "You are a helpful assistant for the AgentOS application.",
                             "You can answer questions and help with tasks.",
                             "When asked to run an agent, team or workflow, make sure you have enough information to do so.",
                         ])
        
    
    def initialize(self, os: "AgentOS"):
        from agno.os.app import AgentOS
        os = cast(AgentOS, os)
        self._agents = os.agents
        self._teams = os.teams
        self.workflows = os.workflows
        self.apps = os.apps
        self.tools = [
            self.get_agents,
            self.get_teams,
            self.get_workflows,
        ]
        
    async def execute(self, message: str) -> RunResponse:
        response = await self.arun(message)
        return response
    
    async def print(self, message: str):
        await self.aprint_response(message, show_message=False)
        
    ### Built In Tools ###
    def get_agents(self) -> List[Dict[str, Any]]:
        return [agent.to_dict() for agent in self.agents]
    
    def get_teams(self) -> List[Dict[str, Any]]:
        return [team.to_dict() for team in self.teams]
    
    def get_workflows(self) -> List[Dict[str, Any]]:
        return [workflow.to_dict() for workflow in self.workflows]
    
    