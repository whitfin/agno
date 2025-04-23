from pathlib import Path

from agno.agent import Agent
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "essay-txt"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the TextKnowledgeBase
knowledge_base = TextKnowledgeBase(
    vector_db=vector_db,
    num_documents=5,
)

# Load some example text with metadata
knowledge_base.load_text(
    path=Path("data/kaustubh.txt"),
    metadata={"user_id": "kausmos"},
    recreate=True,
)

knowledge_base.load_text(
    path=Path("data/srijan.txt"),
    metadata={"user_id": "srijansriv"},
    recreate=True,
)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)

agent.print_response(
    "Tell me about the what experience does Srijan have",
    knowledge_filters={"user_id": "kausmos"},
    markdown=True,
)
