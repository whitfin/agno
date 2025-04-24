"""
User-Level Knowledge Filtering with JSON CV Data

This cookbook demonstrates how to use knowledge filters to retrieve information
from specific user resumes stored as JSON files. It shows how to filter by
user_id, experience level, and location.

Key concepts demonstrated:
1. Loading JSON documents with user-specific metadata
2. Filtering knowledge base searches by user ID
3. Combining multiple filter criteria
4. Creating specialized queries based on filtered data

You can pass filters in the following ways:
1. If you pass on Agent only, we use that for all runs
2. If you pass on run/print_response only, we use that for that run
3. If you pass on both, we override with the filters passed on run/print_response for that run
"""

from pathlib import Path

from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.qdrant import Qdrant

# Set a unique collection name to avoid conflicts with other examples
COLLECTION_NAME = "cookbook-cv-json-filtering"

# Initialize the vector database
vector_db = Qdrant(collection=COLLECTION_NAME, url="http://localhost:6333")

# Initialize the JSONKnowledgeBase with the vector database
knowledge_base = JSONKnowledgeBase(
    vector_db=vector_db,
)

# Step 1: Load CV documents with user-specific metadata
# ------------------------------------------------------------------------------
# When loading documents, we can attach metadata that will be used for filtering
# This metadata can include user IDs, experience levels, locations, or any other attributes

# Load CV files with appropriate metadata for filtering
knowledge_base.load_json(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_1.json"),
    metadata={"user_id": "jordan_mitchell",
              "experience_level": "entry", "location": "San Francisco"},
    recreate=True,  # Set to True only for the first run, then set to False
)

knowledge_base.load_json(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_2.json"),
    metadata={"user_id": "taylor_brooks",
              "experience_level": "mid", "location": "Austin"},
)

knowledge_base.load_json(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_3.json"),
    metadata={"user_id": "morgan_lee",
              "experience_level": "senior", "location": "Seattle"},
)

knowledge_base.load_json(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_4.json"),
    metadata={"user_id": "casey_jordan",
              "experience_level": "mid", "location": "Denver"},
)

knowledge_base.load_json(
    path=Path.joinpath(Path(__file__).parent.parent, "data/cv_5.json"),
    metadata={"user_id": "alex_rivera",
              "experience_level": "principal", "location": "New York"},
)

# Step 2: Query the knowledge base with different filter combinations
# ------------------------------------------------------------------------------
# Uncomment the example you want to run

# Option 1: Filters on the Agent
# This approach sets filters at the agent level, applying to all queries
agent_with_filters = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    knowledge_filters={
        "user_id": "alex_rivera"
    },  # This will only return information from documents associated with Alex Rivera
)
agent_with_filters.print_response(
    "Tell me about Alex Rivera's experience and skills",
    markdown=True,
)

# Option 2: Filters on the run/print_response
# This approach applies filters at the query level, useful for one-time specific queries
# agent = Agent(
#     knowledge=knowledge_base,
#     search_knowledge=True,
# )
# agent.print_response(
#     "I have a position for a software engineer. Tell me about Taylor Brooks as a candidate.",
#     knowledge_filters={"user_id": "taylor_brooks"},
#     markdown=True,
# )
