from pathlib import Path

from agno.agent import Agent
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-pdf-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the PDFKnowledgeBase
knowledge_base = PDFKnowledgeBase(
    vector_db=vector_db,
)

# Step 1: Load documents with user-specific metadata
# ------------------------------------------------------------------------------
# When loading documents, we can attach metadata that will be used for filtering
# This metadata can include user IDs, document types, dates, or any other attributes

# Load first document with user_1 metadata
knowledge_base.load_pdf(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_1.pdf"),
    metadata={"user_id": "jordan_mitchell", "document_type": "cv", "year": 2025},
    recreate=True,  # Set to True only for the first run, then set to False
)

# Load second document with user_2 metadata
knowledge_base.load_pdf(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_2.pdf"),
    metadata={"user_id": "taylor_brooks", "document_type": "cv", "year": 2025},
)

# Load second document with user_2 metadata
knowledge_base.load_pdf(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_3.pdf"),
    metadata={"user_id": "morgan_lee", "document_type": "cv", "year": 2025},
)

# Load second document with user_2 metadata
knowledge_base.load_pdf(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_4.pdf"),
    metadata={"user_id": "casey_jordan", "document_type": "cv", "year": 2025},
)

# Load second document with user_2 metadata
knowledge_base.load_pdf(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_5.pdf"),
    metadata={"user_id": "alex_rivera", "document_type": "cv", "year": 2025},
)

# Step 2: Query the knowledge base with different filter combinations
# ------------------------------------------------------------------------------
# Uncomment the example you want to run

# Option 1: Filters on the Agent
# Initialize the Agent with the knowledge base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    knowledge_filters={
        "user_id": "alex_rivera"
    },  # This will only return information from documents associated with Alex Rivera
)
agent.print_response(
    "Tell me about alex rivera",
    markdown=True,
)

# # Option 2: Filters on the run/print_response
# agent = Agent(
#     knowledge=knowledge_base,
#     search_knowledge=True,
# )
# agent.print_response(
#     "I have a position for a software engineer. Tell me about alex rivera as a candidate.",
#     knowledge_filters={"user_id": "alex_rivera"},
#     markdown=True,
# )
