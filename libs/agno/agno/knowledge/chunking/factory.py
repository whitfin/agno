from typing import Any, Dict, List

from agno.knowledge.chunking.strategy import ChunkingStrategy

class ChunkerFactory:
    """Factory for creating and managing chunkers with lazy loading."""

    @classmethod
    def get_all_chunker_keys(cls) -> List[str]:
        """Get all available chunker keys."""
        chunker_keys = []
        for attr_name in dir(cls):
            if (attr_name.startswith("_get_") and 
                attr_name.endswith("_chunker") and 
                attr_name != "_get_chunker_info"):  # Exclude utility methods
                chunker_key = attr_name[5:-8]  # Remove "_get_" prefix and "_chunker" suffix
                chunker_keys.append(chunker_key)
        
        # Also include all available chunking strategy types
        try:
            from agno.knowledge.chunking.strategy import ChunkingStrategyType
            
            # Map strategy types to chunker keys
            strategy_to_key_mapping = {
                ChunkingStrategyType.AGENTIC_CHUNKING: "agentic",
                ChunkingStrategyType.DOCUMENT_CHUNKING: "document", 
                ChunkingStrategyType.RECURSIVE_CHUNKING: "recursive",
                ChunkingStrategyType.SEMANTIC_CHUNKING: "semantic",
                ChunkingStrategyType.FIXED_SIZE_CHUNKING: "fixed",
                ChunkingStrategyType.ROW_CHUNKING: "row",
                ChunkingStrategyType.MARKDOWN_CHUNKING: "markdown",
            }
            
            # Add strategy-based keys (avoid duplicates)
            for strategy_type, key in strategy_to_key_mapping.items():
                if key not in chunker_keys:
                    chunker_keys.append(key)
                    
        except ImportError:
            # If strategy module is not available, just return factory method keys
            pass
            
        return sorted(chunker_keys)

    @classmethod
    def _get_chunker_info(cls, key: str) -> Dict[str, Any]:
        """Get information about a chunker."""
        return {
            "id": key,
            "name": key,
            "description": "Uses an agent to chunk the text",
        }

    @classmethod
    def _get_agentic_chunker(cls) -> ChunkingStrategy:
        """Get agentic chunker instance."""
        from agno.knowledge.chunking.agentic import AgenticChunking
        # AgenticChunking only accepts model and max_chunk_size parameters
        return AgenticChunking()
    