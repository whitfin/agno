from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.weaviate import Weaviate
from agno.vectordb.search import SearchType
from agno.vectordb.weaviate.index import VectorIndex, Distance

vector_db = Weaviate(
    collection="vectors",
	@@ -14,7 +14,7 @@

# Create Knowledge Instance with Weaviate
knowledge = Knowledge(
    name="Basic SDK Knowledge Base", 
    description="Agno 2.0 Knowledge Implementation with Weaviate",
    vector_store=vector_db,
)