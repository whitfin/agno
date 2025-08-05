from abc import ABC, abstractmethod
from typing import List

from agno.document.base import Document


class ChunkingStrategy(ABC):
    """Base class for chunking strategies"""

    @abstractmethod
    def chunk(self, document: Document) -> List[Document]:
        raise NotImplementedError

    def clean_text(self, text: str) -> str:
        """Clean the text by replacing multiple newlines with a single newline"""
        import re

        # Replace multiple newlines (3 or more) with double newlines to preserve paragraph boundaries
        cleaned_text = re.sub(r"\n{3,}", "\n\n", text)
        # Replace multiple spaces and tabs with a single space (preserves newlines)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        # Replace multiple carriage returns with a single carriage return
        cleaned_text = re.sub(r"\r+", "\r", cleaned_text)
        # Replace multiple form feeds with a single form feed
        cleaned_text = re.sub(r"\f+", "\f", cleaned_text)
        # Replace multiple vertical tabs with a single vertical tab
        cleaned_text = re.sub(r"\v+", "\v", cleaned_text)

        return cleaned_text
