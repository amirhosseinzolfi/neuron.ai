import logging, os, json, time
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from rich.logging import RichHandler
from rich.console import Console

# Single shared console instance
CONSOLE = Console()

class JSONLineFormatter(logging.Formatter):
    """Simple JSON line formatter for structured logs."""
    def format(self, record):
        payload = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in (
            "name","msg","args","levelname","levelno","pathname","filename","module",
            "exc_info","exc_text","stack_info","lineno","funcName","created","msecs",
            "relativeCreated","thread","threadName","processName","process"
        )}
        if extras:
            payload["extra"] = extras
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            # fallback to a minimal JSON
            return json.dumps({"timestamp": time.time(), "level": record.levelname, "message": record.getMessage()})

def write_structured_event(event: Dict[str, Any], jsonl_path: Optional[str] = None):
    """Append an arbitrary JSON event to a JSONL file (best-effort)."""
    try:
        event.setdefault("ts", time.time())
        if not jsonl_path:
            # default path inside this package
            jsonl_path = os.path.join(os.path.dirname(__file__), "logs", "blue_ai_logs.jsonl")
        os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
        with open(jsonl_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        # do not raise from logging helper; best-effort only
        try:
            logging.getLogger("rich_logging").debug(f"Failed to write structured event: {e}")
        except Exception:
            pass

def setup_logging(name: str = "app", jsonl_path: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure RichHandler for terminal output and optionally a RotatingFileHandler
    writing JSON lines to jsonl_path. Returns the logger with `name`.
    Idempotent: won't add duplicate handlers.
    """
    root_logger = logging.getLogger()
    # Add RichHandler to root logger once
    if not any(isinstance(h, RichHandler) for h in root_logger.handlers):
        rich_handler = RichHandler(rich_tracebacks=True)
        rich_handler.setLevel(level)
        root_logger.setLevel(level)
        root_logger.addHandler(rich_handler)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if jsonl_path:
        os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
        abs_path = os.path.abspath(jsonl_path)
        has_file_handler = False
        for h in logger.handlers:
            if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == abs_path:
                has_file_handler = True
                break
        if not has_file_handler:
            json_handler = RotatingFileHandler(abs_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
            json_handler.setFormatter(JSONLineFormatter())
            json_handler.setLevel(level)
            logger.addHandler(json_handler)

    return logger

# Compatibility shims for modules expecting these names
def init_logging(jsonl_path: Optional[str] = None, level: int = logging.INFO):
    """
    Backwards-compatible initializer used by some modules (telegram_handlers).
    Returns the default/root logger.
    """
    # configure root and default file if provided
    setup_logging("app", jsonl_path=jsonl_path, level=level)
    return logging.getLogger("app")

def get_console() -> Console:
    return CONSOLE

def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)