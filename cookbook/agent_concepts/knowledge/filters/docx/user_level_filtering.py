"""
User-Level Knowledge Filtering Example

This cookbook demonstrates how to use knowledge filters to restrict knowledge base searches to specific users, document types, or any other metadata attributes.

Key concepts demonstrated:
1. Loading documents with user-specific metadata
2. Filtering knowledge base searches by user ID
3. Combining multiple filter criteria
4. Comparing results across different filter combinations

You can pass filter's in the following ways:-
1. If you pass on Agent only, we use that for all runs
2. If you pass on run/print_response only, we use that for that run
3. If you pass on both, we override with the filters passed on run/print_response for that run
"""

from pathlib import Path

from agno.agent import Agent
from agno.knowledge.docx import DocxKnowledgeBase
from agno.vectordb.qdrant import Qdrant

# Set a unique collection name to avoid conflicts with other examples
COLLECTION_NAME = "cookbook-user-filtering"

# Initialize the vector database
vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the DocxKnowledgeBase with the vector database
knowledge_base = DocxKnowledgeBase(
    vector_db=vector_db,
)

# Step 1: Load documents with user-specific metadata
# ------------------------------------------------------------------------------
# When loading documents, we can attach metadata that will be used for filtering
# This metadata can include user IDs, document types, dates, or any other attributes

# Load first document with user_1 metadata
knowledge_base.load_docx(
    path=Path("data/docs"),
    metadata={"user_id": "user_1", "document_type": "resume", "year": 2024},
    recreate=True,  # Set to True only for the first run, then set to False
)

# Load second document with user_2 metadata
knowledge_base.load_docx(
    path=Path("data/docs"),
    metadata={"user_id": "user_2", "document_type": "resume", "year": 2024},
)

# Load second document with user_2 metadata
knowledge_base.load_docx(
    path=Path("data/docs"),
    metadata={"user_id": "user_3", "document_type": "resume", "year": 2024},
)

# Load second document with user_2 metadata
knowledge_base.load_docx(
    path=Path("data/docs"),
    metadata={"user_id": "user_4", "document_type": "resume", "year": 2024},
)

# Load second document with user_2 metadata
knowledge_base.load_docx(
    path=Path("data/docs"),
    metadata={"user_id": "user_5", "document_type": "resume", "year": 2024},
)

# Initialize the Agent with the knowledge base
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    # knowledge_filters={"user_id": "user_1"},
)

# Step 2: Query the knowledge base with different filter combinations
# ------------------------------------------------------------------------------
# Uncomment the example you want to run

# This will only return information from documents associated with user_1
agent.print_response(
    "Ask anything about this document",
    knowledge_filters={"user_id": "user_2"},
    markdown=True,
)

# Example 2: Filter by a different user_id
# This will only return information from documents associated with user_2
# agent.print_response(
#     "Ask anything about this document",
#     knowledge_filters={"user_id": "user_2"},
#     markdown=True,
# )
