from agno.document.reader.base import Reader
from typing import Union, List, Any, IO
from pathlib import Path
from agno.document import Document


class OmniReader(Reader):
    """Reader class that can read all types of documents"""

    def read(self, file: Union[Path, IO[Any]]) -> List[Document]:
        pass

    async def async_read(self, file: Union[Path, IO[Any]]) -> List[Document]:
        pass