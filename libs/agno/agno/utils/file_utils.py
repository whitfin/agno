# Common file formatting utility for embedding files into chat messages
import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional, Sequence
from urllib.parse import urlparse

from agno.media import File
from agno.utils.log import log_debug, log_error


def _get_mime_type(file: File, filename: str) -> str:
    """Determine MIME type from File object or filename."""
    return file.mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _format_file_inline(file: File) -> Optional[Dict[str, Any]]:
    """
    Inline-embed a file as a base64 data URL.
    Supports URL, local filepath, and raw content.
    """
    try:
        # Determine content source
        if file.url:
            result = file.file_url_content
            if not result:
                log_error(f"Failed to fetch file from URL: {file.url}")
                return None
            content, mime_type = result
            filename = Path(urlparse(file.url).path).name or "file"
        elif file.filepath:
            path = Path(file.filepath)
            if not path.is_file():
                log_error(f"File not found: {path}")
                return None
            content = path.read_bytes()
            filename = path.name
            mime_type = _get_mime_type(file, filename)
        elif file.content is not None:
            # Ensure bytes
            if isinstance(file.content, bytes):
                content = file.content
            else:
                content = str(file.content).encode("utf-8")
            filename = getattr(file, "filename", "file")
            mime_type = _get_mime_type(file, filename)
        else:
            return None

        # Encode to base64 data URL
        encoded = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded}"
        return {"type": "file", "file": {"filename": filename, "file_data": data_url}}
    except Exception as e:
        log_error(f"Error formatting file inline: {e}")
        return None


def _process_with_reader(file: File) -> Optional[list[dict[str, str]]]:
    """
    Process file using its assigned reader.
    This is the highest priority method - if a reader is present, we use it.
    """
    if not getattr(file, "reader", None):
        return None

    reader_cls = file.reader.__class__.__name__
    log_debug(f"Using reader {reader_cls} on {file.filepath or file.url}")
    try:
        docs = file.reader.read(file.filepath)  # type: ignore
        content_parts = []
        for doc in reversed(docs):
            snippet = (doc.content or "").strip().replace("\n", " ")
            log_debug(f"Reader {reader_cls} produced doc id={doc.id}, snippet='{snippet}...'")
            content_parts.append({"type": "text", "text": doc.content or ""})
        return content_parts
    except Exception as e:
        log_error(f"Error reading with {reader_cls}: {e}")
        return None


def _auto_detect_reader(file: File) -> None:
    """Auto-detect and apply appropriate reader based on file type."""
    if getattr(file, "reader", None) is None and getattr(file, "filepath", None):
        path_lower = str(file.filepath).lower()
        if path_lower.endswith(".pdf"):
            try:
                from agno.document.reader.pdf_reader import PDFReader

                file.reader = PDFReader()
                log_debug(f"Auto-applied PDFReader for {file.filepath}")
            except ImportError as e:
                log_error(f"Failed to import PDFReader for {file.filepath}: {e}")
        elif path_lower.endswith(".csv"):
            try:
                from agno.document.reader.csv_reader import CSVReader

                file.reader = CSVReader()
                log_debug(f"Auto-applied CSVReader for {file.filepath}")
            except ImportError as e:
                log_error(f"Failed to import CSVReader for {file.filepath}: {e}")
        elif path_lower.endswith(".docx"):
            try:
                from agno.document.reader.docx_reader import DocxReader

                file.reader = DocxReader()
                log_debug(f"Auto-applied DocxReader for {file.filepath}")
            except ImportError as e:
                log_error(f"Failed to import DocxReader for {file.filepath}: {e}")
        elif path_lower.endswith(".json"):
            try:
                from agno.document.reader.json_reader import JSONReader

                file.reader = JSONReader()
                log_debug(f"Auto-applied JSONReader for {file.filepath}")
            except ImportError as e:
                log_error(f"Failed to import JSONReader for {file.filepath}: {e}")
        elif path_lower.endswith((".txt", ".md")):
            try:
                from agno.document.reader.text_reader import TextReader

                file.reader = TextReader()
                log_debug(f"Auto-applied TextReader for {file.filepath}")
            except ImportError as e:
                log_error(f"Failed to import TextReader for {file.filepath}: {e}")


def handle_files_for_message(message_dict: dict[str, Any], files: Sequence[File], model: Any) -> None:
    """
    Process attached File objects on a chat message following strict precedence:
    1. If file.reader present → extract text using reader
    2. If model supports attachments → use native file upload
    3. Default to inline base64 embedding

    Modifies message_dict in-place.
    """
    # Initialize content list
    content = message_dict.get("content")
    if isinstance(content, str):
        message_dict["content"] = [{"type": "text", "text": content}]
    elif content is None:
        message_dict["content"] = []

    for file in files:
        log_debug(f"Processing file: {file.filepath or file.url}")

        # Step 1: Try reader-based processing (highest priority)
        if reader_content := _process_with_reader(file):
            message_dict["content"].extend(reader_content)
            continue

        # Step 3: Auto-detect and apply reader if no explicit handling yet
        _auto_detect_reader(file)
        if reader_content := _process_with_reader(file):
            message_dict["content"].extend(reader_content)
            continue

        # Step 4: Fallback to inline embedding (lowest priority)
        log_debug(f"Falling back to inline embed for {file.filepath or file.url}")
        if inline_content := _format_file_inline(file):
            message_dict["content"].insert(0, inline_content)
