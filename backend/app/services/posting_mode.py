"""投稿モード（tor / direct）の実行時保持。

.env の POSTING_MODE をデフォルト値として起動時に読み込み、Web UI からの
切り替えはメモリ上でのみ保持する（DBには保存しない）。コンテナ再起動で
必ず .env の値（DEFAULT_POSTING_MODE）に戻る。
"""
from app.config import settings

VALID_MODES = ("tor", "direct")

DEFAULT_POSTING_MODE = settings.posting_mode if settings.posting_mode in VALID_MODES else "tor"
_current_mode = DEFAULT_POSTING_MODE


def get_mode() -> str:
    return _current_mode


def get_default_mode() -> str:
    return DEFAULT_POSTING_MODE


def set_mode(mode: str) -> None:
    global _current_mode
    if mode not in VALID_MODES:
        raise ValueError(f"invalid posting mode: {mode}")
    _current_mode = mode
