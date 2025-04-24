from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from agno.document import Document
from agno.document.reader.pdf_reader import PDFUrlImageReader, PDFUrlReader
from agno.knowledge.agent import AgentKnowledge
from agno.utils.log import log_debug, log_info, logger


class PDFUrlKnowledgeBase(AgentKnowledge):
    urls: List[str] = []
    formats: List[str] = [".pdf"]
    reader: Union[PDFUrlReader, PDFUrlImageReader] = PDFUrlReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDF urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for url in self.urls:
            if url.endswith(".pdf"):
                yield self.reader.read(url=url)
            else:
                logger.error(f"Unsupported URL: {url}")

    @property
    async def async_document_lists(self) -> AsyncIterator[List[Document]]:
        """Iterate over PDF urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.
        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for url in self.urls:
            if url.endswith(".pdf"):
                yield await self.reader.async_read(url=url)
            else:
                logger.error(f"Unsupported URL: {url}")

    def load_url(
        self,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        """Load documents from a single URL with specific metadata into the vector DB.

        Args:
            url (str): URL of the PDF to load.
            metadata (Optional[Dict[str, Any]]): Metadata to associate with documents from this URL.
                                                This will be merged into the 'meta_data' field of each document.
            recreate (bool): If True, drops and recreates the collection before loading. Defaults to False.
            upsert (bool): If True, upserts documents (insert or update). Requires vector_db support. Defaults to False.
            skip_existing (bool): If True and not upserting, skips documents that already exist based on content hash. Defaults to True.
        """
        if not url.endswith(".pdf"):
            logger.error(f"Unsupported URL provided to load_url: {url}")
            return

        if not self.prepare_load(url, self.formats, metadata, recreate, is_url=True):
            return

        try:
            documents = self.reader.read(url=url)
            if not documents:
                logger.warning(f"No documents were read from URL: {url}")
                return
        except Exception as e:
            logger.exception(f"Failed to read documents from URL {url}: {e}")
            return

        # Process documents
        self.process_documents(
            documents=documents,
            metadata=metadata,
            upsert=upsert,
            skip_existing=skip_existing,
            source_info=str(url),
        )

    async def aload_url(
        self,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
        recreate: bool = False,
        upsert: bool = False,
        skip_existing: bool = True,
    ) -> None:
        if not url.endswith(".pdf"):
            logger.error(f"Unsupported URL provided to load_url: {url}")
            return

        if not await self.aprepare_load(url, self.formats, metadata, recreate, is_url=True):
            return

        try:
            documents = await self.reader.async_read(url=url)
            if not documents:
                logger.warning(f"No documents were read from URL: {url}")
                return
        except Exception as e:
            logger.exception(f"Failed to read documents from URL {url}: {e}")
            return

        # Process documents
        await self.aprocess_documents(
            documents=documents,
            metadata=metadata,
            upsert=upsert,
            skip_existing=skip_existing,
            source_info=str(url),
        )
