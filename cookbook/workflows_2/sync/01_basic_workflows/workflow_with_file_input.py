from pathlib import Path

from agno.agent import Agent
from agno.media import File
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.workflow.v2.step import Step
from agno.workflow.v2.workflow import Workflow

# Define agents
read_agent = Agent(
    name="Agent",
    model=Claude(id="claude-sonnet-4-20250514"),
    role="Read the contents of the attached file.",
)

summarize_agent = Agent(
    name="Summarize Agent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "Summarize the contents of the attached file.",
    ],
)

# Define steps
read_step = Step(
    name="Read Step",
    agent=read_agent,
)

summarize_step = Step(
    name="Summarize Step",
    agent=summarize_agent,
)

content_creation_workflow = Workflow(
    name="Content Creation Workflow",
    description="Automated content creation from blog posts to social media",
    storage=SqliteStorage(
        table_name="workflow_v2",
        db_file="tmp/workflow_v2.db",
        mode="workflow_v2",
    ),
    steps=[read_step, summarize_step],
)

# Create and use workflow
if __name__ == "__main__":
    content_creation_workflow.print_response(
        message="Summarize the contents of the attached file.",
        files=[
            File(url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf")
        ],
        markdown=True,
    )
