from agno.storage_v2.postgres import PostgresDB

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

db = PostgresDB(db_url=db_url, agent_sessions_table_name="agent_sessions")

# agent = Agent()
# agent.print_response("Hello")
