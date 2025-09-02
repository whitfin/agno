"""Run `pip install ddgs sqlalchemy pgvector pypdf openai anthropic` to install dependencies."""

from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.models.aws import Claude
from agno.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
knowledge_base.load(recreate=True)  # Comment out after first run

agent = Agent(
    model=Claude(id="anthropic.claude-3-5-sonnet-20240620-v1:0"),
    knowledge=knowledge_base,
    show_tool_calls=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
