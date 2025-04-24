from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from agno.document import Document
from agno.document.reader.docx_reader import DocxReader
from agno.knowledge.agent import AgentKnowledge
from agno.utils.log import logger


class DocxKnowledgeBase(AgentKnowledge):
    path: Optional[Union[str, Path]] = None
    formats: List[str] = [".doc", ".docx"]
    reader: DocxReader = DocxReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over doc/docx files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """
        if self.path is None:
            raise ValueError("Path is not set")

        _file_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _file_path.exists() and _file_path.is_dir():
            for _file in _file_path.glob("**/*"):
                if _file.suffix in self.formats:
                    yield self.reader.read(file=_file)
        elif _file_path.exists() and _file_path.is_file() and _file_path.suffix in self.formats:
            yield self.reader.read(file=_file_path)

    @property
    async def async_document_lists(self) -> AsyncIterator[List[Document]]:
        """Async version of document_lists.

        Returns:
            AsyncIterator[List[Document]]: Async iterator yielding list of documents
        """
        if self.path is None:
            raise ValueError("Path is not set")

        _file_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _file_path.exists() and _file_path.is_dir():
            for _file in _file_path.glob("**/*"):
                if _file.suffix in self.formats:
                    docs = await self.reader.async_read(file=_file)
                    if docs:
                        yield docs
        elif _file_path.exists() and _file_path.is_file() and _file_path.suffix in self.formats:
            docs = await self.reader.async_read(file=_file_path)
            if docs:
                yield docs

    def load_docx(
        self,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        _file_path = Path(path) if isinstance(path, str) else path

        # Validate file and prepare collection in one step
        if not self.prepare_load(_file_path, self.formats, metadata, recreate):
            return

        # Read documents
        try:
            documents = self.reader.read(file=_file_path)
        except Exception as e:
            logger.exception(f"Failed to read documents from file {_file_path}: {e}")
            return

        # Process documents
        self.process_documents(
            documents=documents,
            metadata=metadata,
            upsert=upsert,
            skip_existing=skip_existing,
            source_info=str(_file_path),
        )

    async def aload_docx(
        self,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        _file_path = Path(path) if isinstance(path, str) else path

        # Validate file and prepare collection in one step
        if not await self.aprepare_load(_file_path, self.formats, metadata, recreate):
            return

        # Read documents
        try:
            documents = await self.reader.async_read(file=_file_path)
        except Exception as e:
            logger.exception(f"Failed to read documents from file {_file_path}: {e}")
            return

        # Process documents
        await self.aprocess_documents(
            documents=documents,
            metadata=metadata,
            upsert=upsert,
            skip_existing=skip_existing,
            source_info=str(_file_path),
        )
