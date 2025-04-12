from agno.agent import Agent
from agno.storage.message_store.db.postgres import PgVectorMessageStore
from agno.storage.message_store.message_store import MessageStore
from agno.storage.postgres import PostgresStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

user_id = "search_user"
session_id = "search_session"

storage = PostgresStorage(
    table_name="agent_sessions",
    db_url=db_url,
)

agent = Agent(
    storage=storage,
    user_id=user_id,
    session_id=session_id,
)
# agent.print_response("I love to hike, swim and play football")

message_store = MessageStore(
    user_id=user_id,
    session_id=session_id,
    storage=storage,
    message_store_db=PgVectorMessageStore(
        table_name="search_sessions",
        db_url=db_url,
    ),
)

message_store.load()  # Comment out after first run


# Uncomment to run the agent with message store and comment out print response above
agent = Agent(
    user_id=user_id,
    session_id=session_id,
    storage=storage,
    message_store=message_store,
    search_message_store=True,
    num_of_runs_from_message_store=1,
)
agent.print_response("What do I love to do?")
