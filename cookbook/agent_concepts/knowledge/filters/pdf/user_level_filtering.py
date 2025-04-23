from pathlib import Path

from agno.agent import Agent
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-pdf-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the PDFKnowledgeBase
knowledge_base = PDFKnowledgeBase(
    vector_db=vector_db,
)

knowledge_base.load_pdf(
    path=Path("data/kaus.pdf"),
    metadata={"user_id": "user_1", "document_type": "doc_1"},
    recreate=True,  # only use at the first run, True/False
)

knowledge_base.load_pdf(
    path=Path("data/srijan.pdf"),
    metadata={"user_id": "user_2", "document_type": "doc_2"},
)

agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)

agent.print_response(
    "Ask anything about user_1 doc",
    knowledge_filters={"user_id": "user_1"},
    markdown=True,
)
