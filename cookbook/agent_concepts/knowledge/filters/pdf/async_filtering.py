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
            path=Path.joinpath(Path(__file__).parent.parent, "data/cv_1.pdf"),
            metadata={
                "user_id": "jordan_mitchell",
                "document_type": "cv",
                "year": 2025,
            },
            recreate=True,
        )
    )

    asyncio.run(
        knowledge_base.aload_pdf(
            path=Path.joinpath(Path(__file__).parent.parent, "data/cv_2.pdf"),
            metadata={"user_id": "taylor_brooks", "document_type": "cv", "year": 2025},
        )
    )

    asyncio.run(
        agent.aprint_response(
            "Tell me about jordan mitchell",
            knowledge_filters={"user_id": "jordan_mitchell"},
            markdown=True,
            stream=True,
        )
    )
