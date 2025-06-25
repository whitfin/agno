"""Simple example creating a session and using the AgentOS with a SessionConnector to expose it"""

import asyncio
from textwrap import dedent
from agno.agent import Agent
from agno.db.postgres.postgres import PostgresDb
from agno.document.base import Document
from agno.document.local_document_store import LocalDocumentStore
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge_base import KnowledgeBase
from agno.memory import Memory
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from agno.os.connectors import KnowledgeConnector, MemoryConnector, SessionConnector
from agno.os.interfaces import Whatsapp
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.vectordb.pgvector.pgvector import PgVector

# Setup the database
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(
    db_url=db_url,
    agent_session_table="agent_sessions",
    team_session_table="team_sessions",
    workflow_session_table="workflow_sessions",
)

# Setup the memory
memory = Memory(db=db)

document_store = LocalDocumentStore(
    name="local_document_store",
    description="Local document store",
    storage_path="tmp/documents",
)

vector_store = PgVector(
    table_name="pdf_documents",
    # Can inspect database via psql e.g. "psql -h localhost -p 5432 -U ai -d ai"
    db_url=db_url,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)

# Create knowledge base
knowledge_base = KnowledgeBase(
    name="My Knowledge Base",
    description="A simple knowledge base",
    document_store=document_store,
)

knowledge_base_2 = KnowledgeBase(
    name="My Knowledge Base 2",
    description="A simple knowledge base 2",
    document_store=document_store,
)


# Add a document
doc_1 = Document(content="Hello worlds", name="greetings")
knowledge_base.add_document(doc_1)

doc_2 = Document(content="Hello worlds 2", name="greetings 2")
knowledge_base_2.add_document(doc_2)

# Setup the agent
basic_agent = Agent(
    name="Basic Agent",
    agent_id="basic-agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=memory,
    enable_user_memories=True,
    knowledge=knowledge_base,
    markdown=True,
)


research_agent = Agent(
    name="Research Agent",
    role="Research agent",
    agent_id="research_agent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["You are a research agent"],
    tools=[DuckDuckGoTools()],
    memory=memory,
    enable_user_memories=True,
)

research_team = Team(
    name="Research Team",
    description="A team of agents that research the web",
    members=[research_agent, basic_agent],
    model=OpenAIChat(id="gpt-4o"),
    mode="coordinate",
    team_id="research_team",
    success_criteria=dedent("""\
        A comprehensive research report with clear sections and data-driven insights.
    """),
    instructions=[
        "You are the lead researcher of a research team! 🔍",
    ],
    memory=memory,
    enable_user_memories=True,
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
    enable_agentic_context=True,
)


# Setup the Agno API App
agent_os = AgentOS(
    name="Demo App",
    description="Demo app for basic agent with session, knowledge, and memory capabilities",
    os_id="demo",
    agents=[basic_agent],
    teams=[research_team],
    interfaces=[Whatsapp(agent=basic_agent)],
    apps=[
        SessionConnector(db=db, name="Session Connector"),
        KnowledgeConnector(knowledge=knowledge_base, name="Knowledge Connector 1"),
        KnowledgeConnector(knowledge=knowledge_base_2, name="Knowledge Connector 2"),
        MemoryConnector(memory=memory, name="Memory Connector"),
    ],
)
app = agent_os.get_app()


if __name__ == "__main__":
    # Simple run to generate and record a session
    agent_os.serve(app="demo:app", reload=True)
    