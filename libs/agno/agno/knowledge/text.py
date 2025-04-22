from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from agno.document import Document
from agno.document.reader.text_reader import TextReader
from agno.knowledge.agent import AgentKnowledge
from agno.utils.log import log_debug, log_info, logger


class TextKnowledgeBase(AgentKnowledge):
    path: Union[str, Path] = None
    formats: List[str] = [".txt"]
    reader: TextReader = TextReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over text files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        _file_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _file_path.exists() and _file_path.is_dir():
            for _file in _file_path.glob("**/*"):
                if _file.suffix in self.formats:
                    yield self.reader.read(file=_file)
        elif _file_path.exists() and _file_path.is_file() and _file_path.suffix in self.formats:
            yield self.reader.read(file=_file_path)

    @property
    async def async_document_lists(self) -> AsyncIterator[List[Document]]:
        """Asynchronously iterate over text files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            AsyncIterator[List[Document]]: AsyncIterator yielding list of documents
        """
        _file_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _file_path.exists() and _file_path.is_dir():
            for _file in _file_path.glob("**/*"):
                if _file.suffix in self.formats:
                    yield await self.reader.async_read(file=_file)
        elif _file_path.exists() and _file_path.is_file() and _file_path.suffix in self.formats:
            yield await self.reader.async_read(file=_file_path)

    def load_text(
        self,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        """Load documents from a single text file with specific metadata into the vector DB."""

        _file_path = Path(path) if isinstance(path, str) else path

        if not _file_path.exists():
            log_debug.error(f"File not found: {_file_path}")
            return

        if _file_path.suffix not in self.formats:
            log_debug.error(f"Unsupported file format: {_file_path.suffix}")
            return

        if self.vector_db is None:
            log_debug.warning("Cannot load file: No vector db provided.")
            return

        # Ensure collection exists or recreate if requested
        if recreate:
            log_info(f"Recreating collection '{self.vector_db.collection}' before loading {_file_path}.")
            self.vector_db.drop()

        if not self.vector_db.exists():
            log_info(f"Collection '{self.vector_db.collection}' does not exist. Creating.")
            self.vector_db.create()

        try:
            documents = self.reader.read(file=_file_path)
            if not documents:
                logger.warning(f"No documents were read from file: {_file_path}")
                return
        except Exception as e:
            logger.exception(f"Failed to read documents from file {_file_path}: {e}")
            return

        log_info(f"Loading {len(documents)} documents from {_file_path} with metadata: {metadata}")

        # Decide loading strategy: upsert or insert (with optional skip)
        if upsert and self.vector_db.upsert_available():
            log_debug(f"Upserting {len(documents)} documents.")
            self.vector_db.upsert(documents=documents, filters=metadata)
        else:
            documents_to_insert = documents
            if skip_existing:
                log_debug("Filtering out existing documents before insertion.")
                documents_to_insert = self.filter_existing_documents(documents)

            if documents_to_insert:
                log_debug(f"Inserting {len(documents_to_insert)} new documents.")
                self.vector_db.insert(documents=documents_to_insert, filters=metadata)
            else:
                log_info("No new documents to insert after filtering.")

        log_info(f"Finished loading documents from {_file_path}.")
