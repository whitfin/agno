"""Run `pip install ddgs sqlalchemy llama-api-client` to install dependencies."""

from agno.agent import Agent
from agno.models.meta import Llama
from agno.storage.postgres import PostgresStorage
from agno.tools.duckduckgo import DuckDuckGoTools

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

agent = Agent(
    model=Llama(id="Llama-4-Maverick-17B-128E-Instruct-FP8"),
    storage=PostgresStorage(table_name="agent_sessions", db_url=db_url),
    tools=[DuckDuckGoTools()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
