import asyncio
from pathlib import Path

from agno.agent import Agent
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-pdf-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

knowledge_base = PDFKnowledgeBase(
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
        knowledge_base.aload_pdf(
            path=Path("data/docs"),
            metadata={"user_id": "user_1", "document_type": "Resume"},
            recreate=True,
        )
    )

    asyncio.run(
        knowledge_base.aload_pdf(
            path=Path("data/docs"),
            metadata={"user_id": "user_2", "document_type": "Resume"},
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
