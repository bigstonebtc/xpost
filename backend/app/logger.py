import logging
import logging.handlers
from pathlib import Path

from app.paths import logs_dir

_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_user_loggers: dict[tuple[str, str], logging.Logger] = {}


def _file_handler(directory: Path, filename: str) -> logging.Handler:
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        directory / filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(_FORMATTER)
    return handler


def get_logger(user_id: str, category: str = "app") -> logging.Logger:
    """ユーザーごとに隔離されたログファイル（/home/<user>/xpost/logs/）に出力するロガーを返す。
    category: "app" | "generation" | "posting" | "news"
    category!="app" のロガーは専用ログ（例: posting.log）と app.log の両方に出力する。"""
    key = (user_id, category)
    cached = _user_loggers.get(key)
    if cached is not None:
        return cached

    logger = logging.getLogger(f"xpost.user.{user_id}.{category}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    directory = logs_dir(user_id)
    if category != "app":
        logger.addHandler(_file_handler(directory, f"{category}.log"))
    logger.addHandler(_file_handler(directory, "app.log"))

    _user_loggers[key] = logger
    return logger


def _console_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(_FORMATTER)
    logger.addHandler(handler)
    return logger


# 特定ユーザーに属さないプロセス全体のイベント（起動処理、全ユーザー共有のTor再起動等）用。
# ファイルには書かず標準出力のみ（`docker compose logs backend` で確認する）。
system_logger = _console_logger("xpost.system")
