import logging
from os import getenv
from typing import Optional

from rich.logging import RichHandler
from rich.text import Text

LOGGER_NAME = "agno"
TEAM_LOGGER_NAME = f"{LOGGER_NAME}-team"

# Define custom styles for different log sources
LOG_STYLES = {
    "agent": {
        "debug": "green",
        "info": "blue",
    },
    "team": {
        "debug": "magenta",
        "info": "steel_blue1",
    }
}

class ColoredRichHandler(RichHandler):
    def __init__(self, *args, source_type: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_type = source_type

    def get_level_text(self, record: logging.LogRecord) -> Text:
        level_name = record.levelname.lower()
        if self.source_type and self.source_type in LOG_STYLES:
            if level_name in LOG_STYLES[self.source_type]:
                color = LOG_STYLES[self.source_type][level_name]
                return Text(record.levelname, style=color)
        return super().get_level_text(record)

def get_logger(logger_name: str, source_type: Optional[str] = None) -> logging.Logger:
    # https://rich.readthedocs.io/en/latest/reference/logging.html#rich.logging.RichHandler
    # https://rich.readthedocs.io/en/latest/logging.html#handle-exceptions
    rich_handler = ColoredRichHandler(
        show_time=False,
        rich_tracebacks=False,
        show_path=True if getenv("AGNO_API_RUNTIME") == "dev" else False,
        tracebacks_show_locals=False,
        source_type=source_type or "agent",
    )
    rich_handler.setFormatter(
        logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]",
        )
    )

    _logger = logging.getLogger(logger_name)
    _logger.addHandler(rich_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    return _logger


logger: logging.Logger = get_logger(LOGGER_NAME, source_type="agent")

team_logger: logging.Logger = get_logger(TEAM_LOGGER_NAME, source_type="team")

def set_log_level_to_debug(source_type: Optional[str] = None):
    _logger = logging.getLogger(LOGGER_NAME if source_type is None else f"{LOGGER_NAME}-{source_type}")
    _logger.setLevel(logging.DEBUG)


def set_log_level_to_info(source_type: Optional[str] = None):
    _logger = logging.getLogger(LOGGER_NAME if source_type is None else f"{LOGGER_NAME}-{source_type}")
    _logger.setLevel(logging.INFO)


def center_header(message: str, symbol: str = "*") -> str:
    try:
        import shutil
        terminal_width = shutil.get_terminal_size().columns
    except Exception:
        terminal_width = 80  # fallback width

    header = f" {message} "
    return f"{header.center(terminal_width-10, symbol)}"
