import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("/app/logs")

_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _make_handler(filename: str) -> logging.Handler:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(_FORMATTER)
    return handler


_app_handler = _make_handler("app.log")


def setup_logger(name: str, filename: str | None = None) -> logging.Logger:
    """名前付きロガーを初期化する。filename を渡すと専用ログにも出力し、
    すべてのロガーは app.log にも集約される。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    if filename:
        logger.addHandler(_make_handler(filename))
    logger.addHandler(_app_handler)

    return logger


app_logger = setup_logger("app")
generation_logger = setup_logger("generation", "generation.log")
posting_logger = setup_logger("posting", "posting.log")
news_logger = setup_logger("news", "news.log")
