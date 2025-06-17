from agno.agent import Agent
from agno.app.agno_api import AgnoAPI
from agno.app.agno_api.interfaces.playground import Playground
from agno.app.agno_api.managers.session.session import SessionManager
from agno.db.postgres.postgres import PostgresDb
from agno.memory import Memory
from agno.models.openai import OpenAIChat

db_url = "postgresql+psycopg://ai:ai@localhost:5432/ai"

db = PostgresDb(
    db_url=db_url,
    agent_session_table="agent_sessions",
    team_session_table="team_sessions",
    workflow_session_table="workflow_sessions",
)
memory = Memory(db=db)

basic_agent = Agent(
    name="Basic Agent",
    model=OpenAIChat(id="gpt-4o"),
    memory=memory,
    add_datetime_to_instructions=True,
    markdown=True,
)

agno_client = AgnoAPI(
    name="Example App: Basic Agent",
    description="Example app for basic agent with playground capabilities",
    app_id="basic-app",
    agents=[basic_agent],
    interfaces=[Playground()],
    managers=[SessionManager(db=db)],
)

app = agno_client.get_app()

if __name__ == "__main__":
    agno_client.serve(app="session_manager:app", reload=True)
