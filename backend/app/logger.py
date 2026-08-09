import logging
import logging.handlers
import os

LOG_DIR = "/app/logs"


def _setup_logger(name: str, filename: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        f"{LOG_DIR}/{filename}",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    app_handler = logging.handlers.RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    logger.addHandler(app_handler)

    logger.propagate = False
    return logger


generation_logger = _setup_logger("generation", "generation.log")
posting_logger    = _setup_logger("posting",    "posting.log")
news_logger       = _setup_logger("news",       "news.log")
