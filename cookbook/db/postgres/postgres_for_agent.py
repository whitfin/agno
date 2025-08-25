<<<<<<< HEAD:cookbook/db/postgres/postgres_for_agent.py
"""Use Postgres as the database for an agent.

Run `pip install openai` to install dependencies."""
=======
"""Run `pip install ddgs sqlalchemy openai` to install dependencies."""
>>>>>>> 6901605678366bab6617a4cda9d874d8118bef13:cookbook/storage/postgres_storage/postgres_storage_for_agent.py

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.tools.duckduckgo import DuckDuckGoTools

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

db = PostgresDb(db_url=db_url)

agent = Agent(
    db=db,
    tools=[DuckDuckGoTools()],
    add_history_to_context=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
