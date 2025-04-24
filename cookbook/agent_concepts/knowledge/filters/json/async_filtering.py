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
    # Comment out after first run
    asyncio.run(
        knowledge_base.aload_json(
            path=Path("data/docs"),
            metadata={"user_id": "user_1", "document_type": "resume"},
            recreate=True,  # only use at the first run, True/False
        )
    )

    asyncio.run(
        knowledge_base.aload_json(
            path=Path("data/docs"),
            metadata={"user_id": "user_2", "document_type": "resume"},
        )
    )

    asyncio.run(
        agent.aprint_response(
            "Ask anything about doc_1",
            knowledge_filters={"user_id": "kausmos"},
            markdown=True,
            stream=True,
        )
    )
