from typing import Dict, List

from agno.knowledge.reader.reader_factory import ReaderFactory
from agno.knowledge.chunking.factory import ChunkerFactory
from agno.knowledge.types import ContentType
from agno.utils.log import log_debug


def get_reader_info(reader_key: str) -> Dict:
    """Get information about a reader without instantiating it."""
    # Try to create the reader to get its info, but don't cache it
    try:
        reader_factory_method = ReaderFactory._get_reader_method(reader_key)

        # Create an instance to get the class, then call class methods
        reader_instance = reader_factory_method()
        reader_class = reader_instance.__class__
        
        supported_strategies = reader_class.get_supported_chunking_strategies()
        supported_content_types = reader_class.get_supported_content_types()

        return {
            "id": reader_key,
            "name": reader_key.replace("_", " ").title() + " Reader",
            "description": f"Reads {reader_key} files",
            "chunking_strategies": [strategy.value for strategy in supported_strategies],  # Convert enums to string values
            "content_types": [ct.value for ct in supported_content_types],  # Convert enums to string values
        }
    except ImportError as e:
        # Skip readers with missing dependencies
        raise ValueError(f"Reader '{reader_key}' has missing dependencies: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unknown reader: {reader_key}. Error: {str(e)}")


def get_all_readers_info() -> List[Dict]:
    """Get information about all available readers."""
    readers_info = []
    keys = ReaderFactory.get_all_reader_keys()
    for key in keys:
        try:
            reader_info = get_reader_info(key)
            readers_info.append(reader_info)
        except ValueError as e:
            # Skip readers with missing dependencies or other issues
            # Log the error but don't fail the entire request
            log_debug(f"Skipping reader '{key}': {e}")
            continue
    return readers_info


def get_content_types_to_readers_mapping() -> Dict[str, List[str]]:
    """Get mapping of content types to list of reader IDs that support them.

    Returns:
        Dictionary mapping content type strings (ContentType enum values) to list of reader IDs.
    """
    content_type_mapping = {}
    readers_info = get_all_readers_info()

    for reader_info in readers_info:
        reader_id = reader_info["id"]
        content_types = reader_info.get("content_types", [])

        for content_type in content_types:
            if content_type not in content_type_mapping:
                content_type_mapping[content_type] = []
            content_type_mapping[content_type].append(reader_id)

    return content_type_mapping


def get_chunker_info(chunker_key: str) -> Dict:
    """Get information about a chunker without instantiating it."""
    try:
        # Try to get chunker info from the factory first
        chunker_method_name = f"_get_{chunker_key}_chunker"
        
        if hasattr(ChunkerFactory, chunker_method_name):
            # Use the factory method if it exists
            chunker_method = getattr(ChunkerFactory, chunker_method_name)
            
            # Get the chunker class to extract information
            chunker_instance = chunker_method()
            chunker_class = chunker_instance.__class__
            
            # Extract class information
            class_name = chunker_class.__name__
            docstring = chunker_class.__doc__ or f"{class_name} chunking strategy"
            
            return {
                "id": chunker_key,
                "class_name": class_name,
                "name": class_name.replace("Chunking", "").replace("Strategy", ""),
                "description": docstring.strip(),
                "factory_method": chunker_method_name
            }
        else:
            # Dynamic discovery from chunking strategies
            from agno.knowledge.chunking.strategy import ChunkingStrategyType, ChunkingStrategyFactory
            
            # Map chunker key to strategy type
            strategy_mapping = {
                "agentic": ChunkingStrategyType.AGENTIC_CHUNKING,
                "document": ChunkingStrategyType.DOCUMENT_CHUNKING,
                "recursive": ChunkingStrategyType.RECURSIVE_CHUNKING,
                "semantic": ChunkingStrategyType.SEMANTIC_CHUNKING,
                "fixed": ChunkingStrategyType.FIXED_SIZE_CHUNKING,
                "row": ChunkingStrategyType.ROW_CHUNKING,
                "markdown": ChunkingStrategyType.MARKDOWN_CHUNKING,
            }
            
            if chunker_key in strategy_mapping:
                strategy_type = strategy_mapping[chunker_key]
                
                # Create an instance to get class information
                chunker_instance = ChunkingStrategyFactory.create_strategy(strategy_type)
                chunker_class = chunker_instance.__class__
                
                # Extract class information
                class_name = chunker_class.__name__
                docstring = chunker_class.__doc__ or f"{class_name} chunking strategy"
                
                return {
                    "id": chunker_key,
                    "class_name": class_name,
                    "name": class_name.replace("Chunking", "").replace("Strategy", ""),
                    "description": docstring.strip(),
                    "strategy_type": strategy_type.value
                }
            else:
                raise ValueError(f"Unknown chunker key: {chunker_key}")
                
    except ImportError as e:
        # Skip chunkers with missing dependencies
        raise ValueError(f"Chunker '{chunker_key}' has missing dependencies: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unknown chunker: {chunker_key}. Error: {str(e)}")


def get_all_content_types() -> List[ContentType]:
    """Get all available content types as ContentType enums."""
    return list(ContentType)


def get_all_chunkers_info() -> List[Dict]:
    """Get information about all available chunkers."""
    chunkers_info = []
    keys = ChunkerFactory.get_all_chunker_keys()
    for key in keys:
        try:
            chunker_info = get_chunker_info(key)
            chunkers_info.append(chunker_info)
        except ValueError as e:
            # Skip chunkers with missing dependencies or other issues
            # Log the error but don't fail the entire request
            log_debug(f"Skipping chunker '{key}': {e}")
            continue
    return chunkers_info