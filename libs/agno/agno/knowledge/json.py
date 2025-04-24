import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from agno.document import Document
from agno.document.reader.json_reader import JSONReader
from agno.knowledge.agent import AgentKnowledge
from agno.utils.log import log_debug, log_info, logger


class JSONKnowledgeBase(AgentKnowledge):
    path: Optional[Union[str, Path]] = None
    reader: JSONReader = JSONReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over Json files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """
        _json_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _json_path.exists() and _json_path.is_dir():
            for _json in _json_path.glob("*.json"):
                yield self.reader.read(path=_json)
        elif _json_path.exists() and _json_path.is_file() and _json_path.suffix == ".json":
            yield self.reader.read(path=_json_path)

    @property
    async def async_document_lists(self) -> AsyncIterator[List[Document]]:
        """Asynchronously iterate over Json files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            AsyncIterator[List[Document]]: Async iterator yielding list of documents
        """
        _json_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _json_path.exists() and _json_path.is_dir():
            json_files = list(_json_path.glob("*.json"))

            tasks = [self.reader.async_read(path=json_file) for json_file in json_files]
            if tasks:
                results = await asyncio.gather(*tasks)
                for result in results:
                    yield result

        elif _json_path.exists() and _json_path.is_file() and _json_path.suffix == ".json":
            result = await self.reader.async_read(path=_json_path)
            yield result

    def load_json(
        self,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        _file_path = Path(path) if isinstance(path, str) else path

        if not _file_path.exists():
            logger.error(f"File not found: {_file_path}")
            return

        if _file_path.suffix != ".json":
            logger.error(f"Unsupported file format: {_file_path.suffix}")
            return

        if self.vector_db is None:
            logger.warning("Cannot load file: No vector db provided.")
            return

        # Track metadata structure for filter extraction
        self.track_metadata_structure(metadata)

        # Ensure collection exists or recreate if requested
        if recreate:
            log_info(f"Recreating collection '{self.vector_db.collection}' before loading {_file_path}.")
            self.vector_db.drop()

        if not self.vector_db.exists():
            log_info(f"Collection '{self.vector_db.collection}' does not exist. Creating.")
            self.vector_db.create()

        try:
            documents = self.reader.read(path=_file_path)
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

    async def aload_json(
        self,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        _file_path = Path(path) if isinstance(path, str) else path

        if not _file_path.exists():
            logger.error(f"File not found: {_file_path}")
            return

        if _file_path.suffix != ".json":
            logger.error(f"Unsupported file format: {_file_path.suffix}")
            return

        if self.vector_db is None:
            logger.warning("Cannot load file: No vector db provided.")
            return

        # Track metadata structure for filter extraction
        self.track_metadata_structure(metadata)

        # Ensure collection exists or recreate if requested
        if recreate:
            log_info(f"Recreating collection '{self.vector_db.collection}' before loading {_file_path}.")
            await self.vector_db.async_drop()

        if not await self.vector_db.async_exists():
            log_info(f"Collection '{self.vector_db.collection}' does not exist. Creating.")
            await self.vector_db.async_create()

        try:
            documents = await self.reader.async_read(path=_file_path)
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
            await self.vector_db.async_upsert(documents=documents, filters=metadata)
        else:
            documents_to_insert = documents
            if skip_existing:
                log_debug("Filtering out existing documents before insertion.")
                documents_to_insert = self.filter_existing_documents(documents)

            if documents_to_insert:
                log_debug(f"Inserting {len(documents_to_insert)} new documents.")
                await self.vector_db.async_insert(documents=documents_to_insert, filters=metadata)
            else:
                log_info("No new documents to insert after filtering.")

        log_info(f"Finished loading documents from {_file_path}.")
