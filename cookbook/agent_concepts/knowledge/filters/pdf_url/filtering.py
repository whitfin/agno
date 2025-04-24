from agno.agent import Agent
from agno.document import Document
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.qdrant import Qdrant

# Collection name
COLLECTION_NAME = "recipes"

# Initialize Qdrant vector database
vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    vector_db=vector_db,
)

knowledge_base.load_url(
    url="https://agno-public.s3.amazonaws.com/recipes/thai_recipes_short.pdf",
    metadata={"cuisine": "Thai", "source": "Thai Cookbook"},
    recreate=False,  # only use at the first run, True/False
)

knowledge_base.load_url(
    url="https://agno-public.s3.amazonaws.com/recipes/cape_recipes_short_2.pdf",
    metadata={"cuisine": "Cape", "source": "Cape Cookbook"},
)


# Option 1: Filters on the Agent
# Initialize the Agent with the knowledge base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    knowledge_filters={
        "cuisine": "Thai"
    },  # This will only return information from documents associated with Thai cuisine
)
agent.print_response(
    "Tell me how to make Pad Thai",
    markdown=True,
)

# # Option 2: Filters on the run/print_response
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)
agent.print_response(
    "Tell me how to make Cape Malay Curry",
    knowledge_filters={"cuisine": "Cape"},
    markdown=True,
)
