from pathlib import Path

from agno.agent import Agent
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.qdrant import Qdrant

COLLECTION_NAME = "resume-txt-test"

vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the TextKnowledgeBase
knowledge_base = TextKnowledgeBase(
    vector_db=vector_db,
    num_documents=5,
)

# Step 1: Load documents with user-specific metadata
# ------------------------------------------------------------------------------
# When loading documents, we can attach metadata that will be used for filtering
# This metadata can include user IDs, document types, dates, or any other attributes

# Load first document with user_1 metadata
knowledge_base.load_text(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_1.txt"),
    metadata={"user_id": "jordan_mitchell", "document_type": "cv", "year": 2025},
    recreate=True,  # Set to True only for the first run, then set to False
)

# Load second document with user_2 metadata
knowledge_base.load_text(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_2.txt"),
    metadata={"user_id": "taylor_brooks", "document_type": "cv", "year": 2025},
)

# Load second document with user_3 metadata
knowledge_base.load_text(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_3.txt"),
    metadata={"user_id": "morgan_lee", "document_type": "cv", "year": 2025},
)

# Load second document with user_4 metadata
knowledge_base.load_text(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_4.txt"),
    metadata={"user_id": "casey_jordan", "document_type": "cv", "year": 2025},
)

# Load second document with user_5 metadata
knowledge_base.load_text(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_5.txt"),
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
