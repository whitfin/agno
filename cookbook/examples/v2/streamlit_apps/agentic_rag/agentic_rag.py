"""🤖 Agentic RAG Agent v2.0 - Your AI Knowledge Assistant with Enhanced Primitives!

This enhanced version demonstrates how to build a sophisticated RAG (Retrieval Augmented Generation) system using
Agno v2 primitives including the new Knowledge, Memory, and Storage systems.

The agent can:
- Process and understand documents from multiple sources (PDFs, websites, text files)
- Build a searchable knowledge base using the enhanced v2 Knowledge system
- Maintain conversation context and memory across sessions using Memory v2
- Provide relevant citations and sources for its responses
- Generate summaries and extract key insights
- Answer follow-up questions and clarifications

Key v2 improvements:
- Enhanced Knowledge system with document_store and vector_store separation
- Advanced Memory system with pluggable backends and user memory management
- Improved Storage system with better session management
- Better document processing with DocumentV2 and metadata support
- Multiple database backend support (PostgreSQL, SQLite, Redis, MongoDB)
- Enhanced knowledge readers for different file types
- Hybrid search capabilities for better relevance
- Advanced session management with unified session tables
- Custom memory managers for RAG-specific memory capture
- Enhanced session summaries with document context
- Agentic memory management for intelligent memory updates

Example queries to try:
- "What are the key points from this document?"
- "Can you summarize the main arguments and supporting evidence?"
- "What are the important statistics and findings?"
- "How does this relate to [topic X]?"
- "What are the limitations or gaps in this analysis?"
- "Can you explain [concept X] in more detail?"
- "What other sources support or contradict these claims?"

The agent uses:
- Vector similarity search for relevant document retrieval
- Advanced memory system for contextual responses and user preferences
- Citation tracking for source attribution
- Dynamic knowledge base updates with enhanced metadata
- Intelligent memory management for document preferences and insights
- Session summaries that capture document analysis patterns

View the README for instructions on how to run the application.
"""

from typing import Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb

from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.memory.memory import Memory, MemoryManager
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.utils.log import logger
from agno.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Enhanced Memory Manager for RAG-specific memory capture
rag_memory_manager = MemoryManager(
    model=OpenAIChat(id="gpt-4o-mini"),
    memory_capture_instructions="""
    IMPORTANT: Focus on capturing user preferences and insights related to document analysis and knowledge work.
    
    Capture memories about:
    - Document types and formats the user prefers to work with
    - Topics and subject areas of interest to the user
    - Analysis patterns and research methodologies the user likes
    - Specific questions or information the user frequently seeks
    - User's expertise level in different domains
    - Preferred citation styles and reference formats
    - Document organization and categorization preferences
    - Follow-up questions and deeper exploration patterns
    
    DO NOT capture:
    - Specific document contents or sensitive information
    - Temporary session details or one-time queries
    - System prompts or technical instructions
    
    Format memories as actionable insights that help personalize future document analysis.
    """,
)

knowledge = Knowledge(
    name="Agentic RAG Knowledge Base v2",
    description="Enhanced knowledge base for RAG operations with v2 primitives",
    vector_store=PgVector(
        db_url=db_url,
        table_name="agentic_rag_documents_v2",
        schema="ai",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    max_results=10,
    valid_metadata_filters=["source", "file_type", "doc_type", "date", "author", "section", "filename", "url", "type", "file_size", "doc_id"],
)

memory = Memory(
    model=OpenAIChat(id="gpt-4o-mini"),  # Model for memory processing
    db=PostgresDb(
        db_url=db_url,
        session_table="agentic_rag_sessions_v2",
        user_memory_table="agentic_rag_user_memories_v2",
    ),
    memory_manager=rag_memory_manager,
)

try:
    knowledge.load()
    logger.info("Knowledge system v2 loaded successfully")
except Exception as e:
    logger.warning(f"Knowledge system v2 initialization warning: {str(e)}")
    # Continue anyway - the system will create tables as needed


def get_agentic_rag_agent(
    model_id: str = "openai:gpt-4o",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    provider, model_name = model_id.split(":")

    if provider == "openai":
        model = OpenAIChat(id=model_name)
    elif provider == "google":
        model = Gemini(id=model_name)
    elif provider == "anthropic":
        model = Claude(id=model_name)
    elif provider == "groq":
        model = Groq(id=model_name)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

    return Agent(
        name="agentic_rag_agent_v2",
        session_id=session_id,
        user_id=user_id,
        model=model,
        memory=memory,
        knowledge=knowledge,
        description="You are a helpful Agent called 'Agentic RAG v2.0' powered by enhanced primitives and your goal is to assist the user in the best way possible.",
        instructions=[
            "1. Knowledge Base Search (Enhanced v2):",
            "   - CRITICAL: You MUST ALWAYS start by calling the search_knowledge_base_with_agentic_filters tool before responding to any user query",
            "   - NEVER provide a response without first searching the knowledge base using the tool",
            "   - Use metadata filters to narrow down search results when appropriate",
            "   - Analyze ALL returned documents thoroughly before responding",
            "   - If multiple documents are returned, synthesize the information coherently",
            "   - Pay attention to document metadata and source information",
            "   - Use relevance scoring to prioritize the most relevant information",
            "2. External Search:",
            "   - If knowledge base search yields insufficient results, use duckduckgo_search",
            "   - Focus on reputable sources and recent information",
            "   - Cross-reference information from multiple sources when possible",
            "   - Add relevant external information to knowledge base if valuable",
            "3. Memory Management (Enhanced v2 Features):",
            "   - Leverage user memories to provide personalized responses based on past interactions",
            "   - Remember user preferences, expertise level, research patterns, and document types",
            "   - Use session summaries for context continuity across long conversations",
            "   - Build on previous conversations and learnings about user's research interests",
            "   - Adapt communication style and complexity based on user's expertise patterns",
            "   - Reference past document analysis sessions when relevant",
            "4. Agentic Memory Management:",
            "   - Actively identify and capture important user preferences about document analysis",
            "   - Update memories when user's interests or expertise evolve",
            "   - Use memory search to find relevant past interactions and insights",
            "   - Create meaningful connections between current queries and past research",
            "5. Context Management:",
            "   - Use chat history to maintain conversation continuity within sessions",
            "   - Reference previous interactions when relevant to current queries",
            "   - Keep track of user preferences and prior clarifications",
            "   - Maintain context across session boundaries using memory system",
            "   - Build on previous document analysis patterns and methodologies",
            "6. Response Quality:",
            "   - Provide specific citations and sources for claims with proper attribution",
            "   - Structure responses with clear sections and bullet points when appropriate",
            "   - Include relevant quotes from source materials with page numbers if available",
            "   - Use confidence indicators when appropriate for uncertain information",
            "   - Adapt response complexity to user's demonstrated expertise level",
            "7. User Interaction:",
            "   - Ask for clarification if the query is ambiguous or could benefit from more context",
            "   - Break down complex questions into manageable parts",
            "   - Proactively suggest related topics or follow-up questions based on past interests",
            "   - Remember and reference user's research interests and previous questions",
            "   - Suggest document organization strategies based on user's patterns",
            "8. Error Handling:",
            "   - If no relevant information is found, clearly state this and suggest alternatives",
            "   - Suggest alternative approaches or questions based on past successful interactions",
            "   - Be transparent about limitations in available information",
            "   - Offer to search external sources if knowledge base is insufficient",
            "9. Enhanced v2 Features:",
            "   - Utilize advanced document processing capabilities for better analysis",
            "   - Leverage enhanced metadata for more precise search results",
            "   - Use improved citation tracking for comprehensive source attribution",
            "   - Take advantage of hybrid search capabilities when available",
            "   - Optimize responses for different document types and formats",
            "   - Use memory insights to anticipate user needs and preferences",
        ],
        search_knowledge=True,
        read_chat_history=True,
        # Enhanced Memory Configuration
        enable_user_memories=True,  # Auto-create memories after each run
        enable_agentic_memory=True,  # Allow agent to actively manage memories
        add_memory_references=True,  # Add existing memories to agent context
        enable_session_summaries=True,  # Create session summaries
        add_session_summary_references=True,  # Add session summaries to context
        store_chat_history=True,  # Store flat message list for persistence
        tools=[DuckDuckGoTools()],
        markdown=True,
        show_tool_calls=True,
        add_history_to_messages=True,  # Add chat history to messages
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
        read_tool_call_history=True,
        num_history_runs=5,  # Increased for better context
        enable_agentic_knowledge_filters=True,  # Let agent choose filters dynamically
        add_references=False,  # Don't add references automatically - let agent search during response
        references_format="json",
    )


# Enhanced v2 utility functions with memory insights
def get_knowledge_stats():
    """Get statistics about the knowledge base"""
    try:
        # Get document count from vector store
        total_docs = knowledge.vector_store.get_count()
        
        if total_docs > 0:
            # Get sample documents to analyze types and sources
            sample_docs = knowledge.vector_store.search("", limit=min(100, total_docs))
            
            return {
                "total_documents": total_docs,
                "document_types": len(set([doc.meta_data.get("file_type", "unknown") for doc in sample_docs])),
                "sources": len(set([doc.meta_data.get("source", "unknown") for doc in sample_docs])),
            }
        else:
            return {"total_documents": 0, "document_types": 0, "sources": 0}
    except Exception as e:
        logger.warning(f"Error getting knowledge stats: {str(e)}")
        return {"error": str(e)}


def get_memory_stats():
    """Get statistics about the memory system"""
    try:
        sessions = memory.db.get_sessions(limit=100)
        return {
            "total_sessions": len(sessions),
            "memory_manager_configured": memory.memory_manager is not None,
            "session_summarizer_configured": memory.summarizer is not None,
            "database_type": type(memory.db).__name__,
        }
    except Exception as e:
        logger.warning(f"Error getting memory stats: {str(e)}")
        return {"error": str(e)}


def get_user_memory_insights(user_id: str = "default"):
    """Get insights about a specific user's memories"""
    try:
        user_memories = memory.get_user_memories(user_id=user_id)
        if not user_memories:
            return {"message": "No memories found for this user"}
        
        # Analyze memory patterns
        topics = []
        for mem in user_memories:
            if hasattr(mem, 'topics') and mem.topics:
                topics.extend(mem.topics)
        
        return {
            "total_memories": len(user_memories),
            "unique_topics": len(set(topics)),
            "common_topics": list(set(topics))[:5],  # Top 5 topics
            "memory_types": [type(mem).__name__ for mem in user_memories[:3]],  # Sample types
        }
    except Exception as e:
        logger.warning(f"Error getting user memory insights: {str(e)}")
        return {"error": str(e)}


def search_user_memories(user_id: str = "default", query: str = "", limit: int = 5):
    """Search user memories with different retrieval methods"""
    try:
        # Try semantic search first
        memories = memory.search_user_memories(
            user_id=user_id, 
            query=query, 
            limit=limit,
            retrieval_method="agentic"
        )
        
        if not memories:
            # Fallback to last_n if no semantic results
            memories = memory.search_user_memories(
                user_id=user_id, 
                limit=limit,
                retrieval_method="last_n"
            )
        
        return {
            "query": query,
            "results_count": len(memories),
            "memories": [mem.memory for mem in memories] if memories else []
        }
    except Exception as e:
        logger.warning(f"Error searching user memories: {str(e)}")
        return {"error": str(e)}


def get_document_stats():
    """Get document statistics from PgVector"""
    stats = {
        "vector_store_count": 0,
        "vector_store_error": None,
        "document_sources": []
    }
    
    # Check PgVector
    try:
        # Get document count
        stats["vector_store_count"] = knowledge.vector_store.get_count()
        
        # Get sample documents to analyze sources
        if stats["vector_store_count"] > 0:
            sample_docs = knowledge.vector_store.search("", limit=min(100, stats["vector_store_count"]))
            stats["document_sources"] = [doc.meta_data.get("source", "unknown") for doc in sample_docs]
    except Exception as e:
        stats["vector_store_error"] = str(e)
        logger.warning(f"Error getting PgVector stats: {str(e)}")
    
    return stats


if __name__ == "__main__":
    print("=== Enhanced RAG Agent v2.0 with Advanced Memory ===")
    print("Knowledge Stats:", get_knowledge_stats())
    print("Document Stats:", get_document_stats())
    print("Memory Stats:", get_memory_stats())
    print("User Memory Insights:", get_user_memory_insights())
    print("Memory Search Test:", search_user_memories(query="document analysis preferences"))
