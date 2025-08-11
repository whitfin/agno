from agents.agno_agent import agno_agent
from agno.db.postgres import PostgresDb
from agno.eval.reliability import ReliabilityEval

# ************* Agent Database *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(db_url=db_url)
# *******************************


def test_agno_agent_searches_knowledge():
    agno_agent_response = agno_agent.run("What is Agno?")
    agno_agent_searches_knowledge_eval = ReliabilityEval(
        db=db,
        name="Agno Agent Searches Knowledge",
        agent_response=agno_agent_response,
        expected_tool_calls=["search_knowledge_base"],
    )
    agno_agent_searches_knowledge_eval.run(print_results=True)


if __name__ == "__main__":
    test_agno_agent_searches_knowledge()
