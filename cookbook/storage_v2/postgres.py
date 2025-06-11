from agno.storage_v2.postgres import PostgresDb

db_url = "postgresql+psycopg://ai:ai@localhost:5432/ai"

db = PostgresDb(db_url=db_url, agent_sessions_table_name="agent_sessions")

# agent = Agent()
# agent.print_response("Hello")
