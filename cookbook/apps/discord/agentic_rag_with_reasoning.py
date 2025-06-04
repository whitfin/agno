"""This cookbook shows how to implement Agentic RAG with Reasoning.
1. Run: `pip install agno anthropic cohere lancedb tantivy sqlalchemy` to install the dependencies
2. Export your ANTHROPIC_API_KEY and CO_API_KEY
3. Run: `python cookbook/agent_concepts/agentic_search/agentic_rag_with_reasoning.py` to run the agent
"""

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.url import UrlKnowledge
from agno.models.anthropic import Claude
from agno.reranker.cohere import CohereReranker
from agno.tools.reasoning import ReasoningTools
from agno.app.discord.client import DiscordClient
from agno.vectordb.lancedb import LanceDb, SearchType

# Create a knowledge base, loaded with documents from a URL
agno_docs = UrlKnowledge(
    urls=["https://docs.agno.com/llms-full.txt"],
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="agno_docs",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(dimensions=768),
    ),
)
docs_agent = Agent(
    model=Claude(id="claude-3-7-sonnet-latest"),
    # Agentic RAG is enabled by default when `knowledge` is provided to the Agent.
    knowledge=agno_docs,
    # search_knowledge=True gives the Agent the ability to search on demand
    # search_knowledge is True by default
    search_knowledge=True,
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "Include sources in your response.",
        "Always search your knowledge before answering the question.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    # Load the knowledge base, comment after first run
    # agno_docs.load(recreate=True)
    DiscordClient(docs_agent)