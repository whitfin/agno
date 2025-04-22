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
    metadata={"user_id": "user_1", "source": "Thai Cookbook"},
    recreate=False,
)

knowledge_base.load_url(
    url="https://agno-public.s3.amazonaws.com/recipes/cape_recipes_short_2.pdf",
    metadata={"user_id": "user_2", "source": "Cape Cookbook"},
    recreate=False,
)


# Create agent with the knowledge base
agent = Agent(knowledge=knowledge_base, show_tool_calls=True)

# print("\nFiltered search example:")
# search_results = knowledge_base.search(
#     query="Tell me about how to make Pad Thai",
#     filters={"meta_data.user_id": "user_2"}
# )

# if search_results:
#     for i, doc in enumerate(search_results):
#         print(f"\n--- Result {i+1} ---")
#         print(f"Name: {doc.name}")
#         print(f"Metadata: {doc.meta_data}")
#         # Print first 500 characters of content
#         print(f"Content:\n{doc.content[:5000]}...")
#         print("-" * 20)  # Separator
# else:
#     print("No results found for the specified filter and query.")

agent.print_response(
    "List down the ingredients to make Pad Thai",
    knowledge_filters={"meta_data.user_id": "user_1"},
    markdown=True,
)
