"""投稿モード（tor / direct）の実行時保持。

env.conf の POSTING_MODE をデフォルト値として使い、Web UI からの切り替えは
ユーザーごとにメモリ上でのみ保持する（DBには保存しない）。コンテナ再起動で
必ず env.conf の値（デフォルト値）に戻る。
"""
from app.user_registry import get_user_config

VALID_MODES = ("tor", "direct")

# user_id -> 実行時に切り替えられた投稿モード。未設定ならenv.confの値を使う。
_current_mode: dict[str, str] = {}


def _default_mode(user_id: str) -> str:
    cfg = get_user_config(user_id)
    mode = cfg.posting_mode if cfg else "tor"
    return mode if mode in VALID_MODES else "tor"


def get_mode(user_id: str) -> str:
    return _current_mode.get(user_id, _default_mode(user_id))


def get_default_mode(user_id: str) -> str:
    return _default_mode(user_id)


def set_mode(user_id: str, mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(f"invalid posting mode: {mode}")
    _current_mode[user_id] = mode
