from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, cast
from agno.agent.agent import Agent
from agno.models.base import Model
from agno.os.interfaces.base import BaseInterface
from agno.os.managers.base import BaseManager
from agno.os.utils import get_agent_by_id, get_team_by_id
from agno.run.response import RunResponse, RunResponseEvent
from agno.team.team import Team
from agno.tools.function import Function
from agno.workflow.workflow import Workflow


class Console(Agent):
    model: Optional[Model] = None
    
    _os: "AgentOS" = None
    _agents: List[Agent] = []
    _teams: List[Team] = []
    _workflows: List[Workflow] = []
    _apps: List[BaseManager] = []
    _interfaces: List[BaseInterface] = []
    
    def __init__(self, model: Optional[Model] = None):
        super().__init__(model=model, 
                         name="Console",
                         instructions=[
                             "You are a helpful assistant for the AgentOS application.",
                             "You can answer questions and help with tasks.",
                             "When asked to run an agent, team or workflow, make sure you have enough information to do so.",
                             "When given a request, consider the capabilities of the configured agents, teams, workflows, and run the appropriate agent/team/workflow with the user's request.",
                         ],
                         add_history_to_messages=True)
        
    
    def initialize(self, os: "AgentOS"):
        from agno.os.app import AgentOS
        os = cast(AgentOS, os)
        
        self._os = os
        self._agents = os.agents
        self._teams = os.teams
        self._workflows = os.workflows
        self._apps = os.apps
        self._interfaces = os.interfaces
        
        self.tools = [
            self.get_agents,
            self.get_teams,
            self.get_workflows,
            self.get_os_overview,
            self.run_agent,
            self.run_team,
        ]
        
    async def execute(self, message: str) -> RunResponse:
        response = await self.arun(message)
        return response
    
    async def print(self, message: str):
        await self.aprint_response(message, show_message=False)
        
    ### Built In Tools ###
    async def get_agents(self) -> List[Dict[str, Any]]:
        """
        Get the list of agents available in the AgentOS
        """
        return [agent.to_dict() for agent in self._agents] if self._agents else []
    
    async def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get the list of teams available in the AgentOS
        """
        return [team.to_dict() for team in self._teams] if self._teams else []
    
    async def get_workflows(self) -> List[Dict[str, Any]]:
        """
        Get the list of workflows available in the AgentOS
        """
        return [workflow.to_dict() for workflow in self._workflows] if self._workflows else []
    
    async def get_os_overview(self) -> List[Dict[str, Any]]:
        """
        Get the overview of the AgentOS.
        This includes the list of agents, teams, workflows, and available apps and interfaces.
        Apps can include knowledge, memory, session, eval, etc.
        Interfaces can include whatsapp, slack, etc.
        """
        result_dict = {
            "id": self._os.os_id,
            "name": self._os.name,
            "description": self._os.description,
            "agents": await self.get_agents(),
            "teams": await self.get_teams(),
            "workflows": await self.get_workflows(),
            "apps": [app.to_dict() for app in self._apps] if self._apps else [],
            "interfaces": [interface.to_dict() for interface in self._interfaces] if self._interfaces else [],
        }
        result_dict = {k: v for k, v in result_dict.items() if v}
        return result_dict
    
    async def run_agent(self, agent_id: str, message: str) -> RunResponse:
        """
        Run an agent with a message.
        
        Args:
            agent_id: The id of the agent to run.
            message: The message/prompt to run the agent with.
            
        Returns:
            The run response from the agent.
        """
        agent = get_agent_by_id(agent_id, self._agents)
        if agent is None:
            raise Exception(f"Agent with id {agent_id} not found")
        
        return await agent.arun(message)
    
    async def run_team(self, team_id: str, message: str) -> RunResponse:
        """
        Run a team with a message.
        
        Args:
            team_id: The id of the team to run.
            message: The message/prompt to run the team with.
            
        Returns:
            The run response from the team.
        """
        team = get_team_by_id(team_id, self._teams)
        if team is None:
            raise Exception(f"Team with id {team_id} not found")
        
        return await team.arun(message)
    
    ### Memory Tools ###
    async def get_memories(self) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    async def create_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    async def update_memory(self, memory_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    ### Knowledge Tools ###
    async def get_documents(self) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        # TODO: Implement this
        pass
    
    ### Session Tools ###
    async def get_sessions_for_agent(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get the list of sessions for an agent.
        
        Args:
            agent_id: The id of the agent to get sessions for.
            limit: The number of sessions to return.
            
        Returns:
            The list of sessions for the agent.
        """
        # TODO: Implement this
        pass
    
    async def get_sessions_for_team(self, team_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get the list of sessions for a team.
        
        Args:
            team_id: The id of the team to get sessions for.
            limit: The number of sessions to return.
            
        Returns:
            The list of sessions for the team.
        """
        # TODO: Implement this
        pass
    
    async def get_agent_runs_for_session(self, session_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get the list of runs for an agent session.
        
        Args:
            session_id: The id of the session to get runs for.
            limit: The number of runs to return.
            
        Returns:
            The list of runs for the session.
        """
        # TODO: Implement this
        pass
    
    async def get_team_runs_for_session(self, session_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get the list of runs for a team session.
        
        Args:
            session_id: The id of the session to get runs for.
            limit: The number of runs to return.
            
        Returns:
            The list of runs for the session.
        """
        # TODO: Implement this
        pass
    