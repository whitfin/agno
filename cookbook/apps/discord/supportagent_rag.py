"""This cookbook shows how to implement Agentic RAG with Reasoning.
1. Run: `pip install agno anthropic cohere lancedb tantivy sqlalchemy` to install the dependencies
2. Export your ANTHROPIC_API_KEY and CO_API_KEY
3. Run: `python cookbook/agent_concepts/agentic_search/agentic_rag_with_reasoning.py` to run the agent
"""

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.url import UrlKnowledge
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agno.app.discord.client import DiscordClient
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.tools.slack import SlackTools
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.manager import MemoryManager
from agno.memory.v2.memory import Memory

from agno.storage.sqlite import SqliteStorage



agent_storage = SqliteStorage(
    table_name="agent_sessions", db_file="tmp/persistent_memory.db"
)
memory_db = SqliteMemoryDb(table_name="memory", db_file="tmp/memory.db")

umemory = Memory(
    db=memory_db,
    memory_manager=MemoryManager(
        memory_capture_instructions="""\
                        Collect User's name,
                        Collect the informstion of the issue the user is facing,
                        Collect information about the users goal with the project
                    """,
        model=Claude(id="claude-3-7-sonnet-latest"),
    ),
)
umemory.clear()


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
    memory=umemory,
    enable_agentic_memory=True,
    # search_knowledge=True gives the Agent the ability to search on demand
    # search_knowledge is True by default
    search_knowledge=True,
    tools=[SlackTools()],
    instructions=[
        "You are an user support agent for Agno, help them by sending links of the docs section related to their question",
        "Always send issues with message_url to the slack channel (C086X7SA6BA) to notify Agno developers",
        "Always search your knowledge before answering the question.",
        "If unable to help, tell the team in the slack channel by tagging @U08MWE4QXEF and let the user know that the team will help them"
    ],
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
    debug_mode=True,
)

if __name__ == "__main__":
    # Load the knowledge base, comment after first run
    #agno_docs.load(recreate=True)
    DiscordClient(docs_agent)