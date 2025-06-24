from typing import List
from fastapi import APIRouter

from agno.os.schema import (
    AppsResponse,
    ConfigResponse,
    AgentResponse,
    ConsolePrompt,
    ConsolePromptResponse,
    ConsolePromptToolResponse,
    InterfaceResponse,
    ConnectorResponse,
    TeamResponse,
    WorkflowResponse
)

def get_base_router(
    os: "AgentOS",
) -> APIRouter:
    router = APIRouter(tags=["Built-In"])

    @router.get("/status", description="Get the status of the running AgentOS")
    async def status():
        return {"status": "available"}

    @router.get("/config", 
                description="Get the configuration/spec of the running AgentOS",
                response_model=ConfigResponse, 
                response_model_exclude_none=True)
    async def config() -> ConfigResponse:
        app_response = AppsResponse(
                session=[ConnectorResponse(type=app.type, name=app.name, version=app.version, route=app.router_prefix) for app in os.apps if app.type == "session"],
                knowledge=[ConnectorResponse(type=app.type, name=app.name, version=app.version, route=app.router_prefix) for app in os.apps if app.type == "knowledge"],
                memory=[ConnectorResponse(type=app.type, name=app.name, version=app.version, route=app.router_prefix) for app in os.apps if app.type == "memory"],
                eval=[ConnectorResponse(type=app.type, name=app.name, version=app.version, route=app.router_prefix) for app in os.apps if app.type == "eval"],
            )
        
        app_response.session = app_response.session or None
        app_response.knowledge = app_response.knowledge or None
        app_response.memory = app_response.memory or None
        app_response.eval = app_response.eval or None
        
        return ConfigResponse(
            os_id=os.os_id,
            name=os.name,
            description=os.description,
            interfaces=[InterfaceResponse(type=interface.type, version=interface.version, route=interface.router_prefix) for interface in os.interfaces],
            apps=app_response,
        )

    @router.get("/agents", 
                description="Get the list of agents available in the AgentOS",
                response_model=List[AgentResponse],
                response_model_exclude_none=True)
    async def get_agents():
        if os.agents is None:
            return []

        return [
            AgentResponse.from_agent(agent)
            for agent in os.agents
        ]

    @router.get("/teams", 
                description="Get the list of teams available in the AgentOS",
                response_model=List[TeamResponse],
                response_model_exclude_none=True)
    async def get_teams():
        if os.teams is None:
            return []

        return [
            TeamResponse.from_team(team)
            for team in os.teams
        ]

    @router.get("/workflows", 
                description="Get the list of workflows available in the AgentOS",
                response_model=List[WorkflowResponse],
                response_model_exclude_none=True)
    async def get_workflows():
        if os.workflows is None:
            return []

        return [
            WorkflowResponse(
                workflow_id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
            )
            for workflow in os.workflows
        ]

    return router


def get_console_router(
    console: "Console",
) -> APIRouter:
    router = APIRouter(prefix="/console", tags=["Console"])

    @router.post("/prompt", 
                 description="Send a prompt to the console",
                 response_model=ConsolePromptResponse,
                 response_model_exclude_none=True)
    async def prompt(prompt: ConsolePrompt):
        response = await console.execute(prompt.message)
        return ConsolePromptResponse(
            content=response.content,
            tools=[ConsolePromptToolResponse(name=tool.tool_name, args=tool.tool_args) for tool in response.tools]
        )

    return router