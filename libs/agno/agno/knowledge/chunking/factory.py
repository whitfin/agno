from typing import Any, Dict, List

from agno.knowledge.chunking.strategy import ChunkingStrategy


class ChunkerFactory:
    """Factory for creating and managing chunkers with lazy loading."""

    @classmethod
    def get_all_chunker_keys(cls) -> List[str]:
        """Get all available chunker keys."""
        chunker_keys = []

        # Use chunking strategy enum values directly as chunker keys
        try:
            from agno.knowledge.chunking.strategy import ChunkingStrategyType

            # Add strategy enum values directly as chunker keys
            for strategy_type in ChunkingStrategyType:
                chunker_keys.append(strategy_type.value)

        except ImportError:
            # If strategy module is not available, return empty list
            pass

        return sorted(chunker_keys)
