from agno.agent import Agent
from agno.os import AgentOS
from agno.os.connectors import KnowledgeConnector
from agno.document import Document

from agno.knowledge.knowledge import Knowledge
from agno.document.local_document_store import LocalDocumentStore
from agno.models.openai import OpenAIChat
from agno.vectordb.pgvector import PgVector
from agno.db.postgres.postgres import PostgresDb

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

document_store = LocalDocumentStore(
    name="local_document_store",
    description="Local document store",
    storage_path="tmp/documents",
)

documents_db = PostgresDb(
    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    knowledge_table="knowledge_documents",
)
vector_store = PgVector(
    table_name="pdf_documents",
    db_url=db_url,
)

# Create knowledge base
knowledge = Knowledge(
    name="My Knowledge Base", 
    description="A simple knowledge base",
    document_store=document_store,
    documents_db=documents_db,
    vector_store=vector_store,
)

# Add a document
# doc = Document(content="Hello worlds", name="greetings")
# doc_id = knowledge.add_document(doc) 

basic_agent = Agent(
    name="Basic Agent",
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    add_datetime_to_instructions=True,
    markdown=True,
)

agent_os = AgentOS(
    name="Example App: Knowledge Agent",
    description="Example app for basic agent with knowledge capabilities",
    os_id="knowledge-demo",
    agents=[
        basic_agent,
    ],
    apps=[KnowledgeConnector(knowledge=knowledge)],
    interfaces=[
        # Playground(),
    ],
)
app = agent_os.get_app()

if __name__ == "__main__":
    """ Run your AgentOS:
    Now you can interact with your knowledge base using the API. Examples:
    - http://localhost:8001/knowledge/{id}/documents
    - http://localhost:8001/knowledge/{id}/documents/123
    - http://localhost:8001/knowledge/{id}/documents?agent_id=123
    - http://localhost:8001/knowledge/{id}/documents?limit=10&page=0&sort_by=created_at&sort_order=desc
    """
    agent_os.serve(app="knowledge_connector:app", reload=True)
