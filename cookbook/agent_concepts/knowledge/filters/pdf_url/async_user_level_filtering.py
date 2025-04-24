import asyncio
from pathlib import Path

from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-pdf-url-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

knowledge_base = PDFUrlKnowledgeBase(
    vector_db=vector_db,
)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)


if __name__ == "__main__":
    asyncio.run(
        knowledge_base.aload_url(
            url="https://agno-public.s3.amazonaws.com/recipes/thai_recipes_short.pdf",
            metadata={"user_id": "user_1", "source": "Thai Cookbook"},
            recreate=True,  # only use at the first run, True/False
        )
    )

    asyncio.run(
        knowledge_base.aload_url(
            url="https://agno-public.s3.amazonaws.com/recipes/cape_recipes_short_2.pdf",
            metadata={"user_id": "user_2", "source": "Cape Cookbook"},
        )
    )

    asyncio.run(
        agent.aprint_response(
            "Tell me about Pad Thai and how to make it",
            knowledge_filters={"user_id": "user_2"},
            markdown=True,
            stream=True,
        )
    )
