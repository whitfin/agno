from enum import Enum


class ContentType(str, Enum):
    """Enum for content types supported by knowledge readers."""


    WEBSITE = "website"
    TEXT = "text"
    TOPIC = "topic"
    YOUTUBE = "youtube"

    # Document file extensions
    PDF = ".pdf"
    TXT = ".txt"
    MARKDOWN = ".md"
    DOCX = ".docx"
    DOC = ".doc"
    JSON = ".json"

    # Spreadsheet file extensions
    CSV = ".csv"
    XLSX = ".xlsx"
    XLS = ".xls"

    # URL-based content types
    URL_PDF = "url_pdf"
    URL_DOCX = "url_docx"
    URL_DOC = "url_doc"
    URL_JSON = "url_json"
    URL_MD = "url_md"
    URL_TXT = "url_txt"
    URL_CSV = "url_csv"
    URL_XML = "url_xml"
    URL_HTML = "url_html"
    URL_HTM = "url_htm"
    URL_RTF = "url_rtf"
    URL_FILE = "url_file"
    URL_XLSX = "url_xlsx"
    URL_XLS = "url_xls"
    


def get_content_type_enum(content_type_str: str) -> ContentType:
    """Convert a content type string to ContentType enum."""
    return ContentType(content_type_str)
