from pathlib import Path

from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-json"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the JSONKnowledgeBase
knowledge_base = JSONKnowledgeBase(
    vector_db=vector_db,
)

# Load individual JSON files with metadata
knowledge_base.load_json(
    path=Path("data/docs"),
    metadata={"user_id": "user_1"},
    recreate=True,  # only use at the first run, True/False
)

knowledge_base.load_json(
    path=Path("data/docs"),
    metadata={"user_id": "user_2"},
)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)

agent.print_response(
    "Ask anything from the user_1 document",
    knowledge_filters={"user_id": "user_1"},
    markdown=True,
)
