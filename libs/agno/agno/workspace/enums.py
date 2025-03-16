from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    agent_app_aws = "agent-app-aws"
    agent_api_aws = "agent-api-aws"
