import asyncio
from pathlib import Path

from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-json-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

knowledge_base = JSONKnowledgeBase(
    vector_db=vector_db,
)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)


if __name__ == "__main__":
    asyncio.run(
        knowledge_base.aload_json(
            path=Path.joinpath(Path(__file__).parent.parent, "data/cv_1.json"),
            metadata={
                "user_id": "jordan_mitchell",
                "document_type": "cv",
                "year": 2025,
            },
            recreate=True,
        )
    )

    asyncio.run(
        knowledge_base.aload_json(
            path=Path.joinpath(Path(__file__).parent.parent, "data/cv_2.json"),
            metadata={"user_id": "taylor_brooks", "document_type": "cv", "year": 2025},
        )
    )

    asyncio.run(
        agent.aprint_response(
            "Tell me about jordan mitchell's cv",
            knowledge_filters={"user_id": "jordan_mitchell"},
            markdown=True,
            stream=True,
        )
    )
