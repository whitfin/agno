import asyncio
from pathlib import Path

from agno.agent import Agent
from agno.knowledge.docx import DocxKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-docx-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the DocxKnowledgeBase
knowledge_base = DocxKnowledgeBase(
    vector_db=vector_db,
)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)


if __name__ == "__main__":
    # Comment out after first run
    asyncio.run(
        knowledge_base.aload_docx(
            path=Path("data/docs"),
            metadata={"user_id": "user_1", "document_type": "doc_1", "year": 2025},
            recreate=True,
        )
    )

    asyncio.run(
        knowledge_base.aload_docx(
            path=Path("data/srijan.docx"),
            metadata={"user_id": "user_2", "document_type": "doc_2", "year": 2025},
        )
    )

    asyncio.run(
        agent.aprint_response(
            "Ask anything from doc_1",
            knowledge_filters={"user_id": "user_1"},
            markdown=True,
            stream=True,
        )
    )
