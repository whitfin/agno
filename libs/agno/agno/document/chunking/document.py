from typing import List, Union, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy


class DocumentChunking(ChunkingStrategy):
    """A chunking strategy that splits text based on document structure like paragraphs and sections"""

    def __init__(self, chunk_size: int = 5000, overlap: int = 0, delimiters: Optional[Union[List[str], str]] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

        if delimiters is None:
            self.delimiters = ["\n\n"]
        elif isinstance(delimiters, str):
            self.delimiters = [delimiters]
        else:
            self.delimiters = list(delimiters)

    def _split_by_delimiters(self, text: str) -> List[str]:
        segments = [text]

        for delimiter in self.delimiters:
            new_segments = []
            for segment in segments:
                split_parts = segment.split(delimiter)
                new_segments.extend(split_parts)
            segments = new_segments

        return [segment for segment in segments if segment.strip()]

    def chunk(self, document: Document) -> List[Document]:
        """Split document into chunks based on document structure"""
        if len(document.content) <= self.chunk_size:
            return [document]

        # Split using the configured delimiters
        segments = self._split_by_delimiters(self.clean_text(document.content))
        chunks: List[Document] = []
        current_chunk = []
        current_size = 0
        chunk_meta_data = document.meta_data
        chunk_number = 1

        for segment in segments:
            segment = segment.strip()
            segment_size = len(segment)

            if current_size + segment_size <= self.chunk_size:
                current_chunk.append(segment)
                current_size += segment_size
            else:
                meta_data = chunk_meta_data.copy()
                meta_data["chunk"] = chunk_number
                chunk_id = None
                if document.id:
                    chunk_id = f"{document.id}_{chunk_number}"
                elif document.name:
                    chunk_id = f"{document.name}_{chunk_number}"
                meta_data["chunk_size"] = len(self.delimiters[0].join(current_chunk))
                if current_chunk:
                    chunks.append(
                        Document(
                            id=chunk_id,
                            name=document.name,
                            meta_data=meta_data,
                            content=self.delimiters[0].join(current_chunk),
                        )
                    )
                    chunk_number += 1
                current_chunk = [segment]
                current_size = segment_size

        if current_chunk:
            meta_data = chunk_meta_data.copy()
            meta_data["chunk"] = chunk_number
            chunk_id = None
            if document.id:
                chunk_id = f"{document.id}_{chunk_number}"
            elif document.name:
                chunk_id = f"{document.name}_{chunk_number}"
            meta_data["chunk_size"] = len(self.delimiters[0].join(current_chunk))
            chunks.append(
                Document(
                    id=chunk_id, name=document.name, meta_data=meta_data, content=self.delimiters[0].join(current_chunk)
                )
            )

        # Handle overlap if specified
        if self.overlap > 0:
            overlapped_chunks = []
            for i in range(len(chunks)):
                if i > 0:
                    # Add overlap from previous chunk
                    prev_text = chunks[i - 1].content[-self.overlap :]
                    meta_data = chunk_meta_data.copy()
                    meta_data["chunk"] = i + 1
                    chunk_id = None
                    if document.id:
                        chunk_id = f"{document.id}_{i + 1}"
                    elif document.name:
                        chunk_id = f"{document.name}_{i + 1}"
                    meta_data["chunk_size"] = len(prev_text + chunks[i].content)
                    if prev_text:
                        overlapped_chunks.append(
                            Document(
                                id=chunk_id,
                                name=document.name,
                                meta_data=meta_data,
                                content=prev_text + chunks[i].content,
                            )
                        )
                else:
                    overlapped_chunks.append(chunks[i])
            chunks = overlapped_chunks

        return chunks
