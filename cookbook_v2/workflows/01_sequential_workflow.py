from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.postgres import PostgresStorage
from agno.workflow.v2.workflow import Workflow, WorkflowSessionV2
from rich.pretty import pprint

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

gather_requirements_agent = Agent(
    name="Gather Requirements Agent",
    model=OpenAIChat(id="gpt-4.1"),
    instructions="Your job is to gather requirements for the report",
)
write_report_agent = Agent(
    name="Write Report Agent",
    model=OpenAIChat(id="gpt-4.1"),
    instructions="Your job is to write the report based on the requirements",
)

# Create and use workflow
if __name__ == "__main__":
    content_creation_workflow = Workflow(
        name="Content Creation Workflow",
        session_id="test_session_2",
        storage=PostgresStorage(
            table_name="workflow_v2",
            db_url=db_url,
            mode="workflow_v2",
        ),
        steps=[gather_requirements_agent, write_report_agent],
    )
    session: WorkflowSessionV2 = content_creation_workflow.read_from_storage()
    pprint(session)
    # content_creation_workflow.print_response(
    #     message="AI trends in 2024",
    #     markdown=True,
    #     stream=True,
    # )
