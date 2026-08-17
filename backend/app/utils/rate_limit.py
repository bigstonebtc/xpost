import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.logger import app_logger as logger

LIMITS = {"anthropic": 500, "x_api": 100}
WINDOW = timedelta(hours=1)

_lock = threading.Lock()
_timestamps: dict[str, list[datetime]] = defaultdict(list)


class RateLimitExceeded(Exception):
    def __init__(self, api_type: str, reset_at: datetime):
        self.api_type = api_type
        self.reset_at = reset_at
        super().__init__(f"API rate limit exceeded: {api_type}")


def _prune(api_type: str, now: datetime) -> list[datetime]:
    cutoff = now - WINDOW
    timestamps = [ts for ts in _timestamps[api_type] if ts > cutoff]
    _timestamps[api_type] = timestamps
    return timestamps


def would_allow(api_type: str) -> tuple[bool, datetime | None]:
    """記録はせず、現時点で呼び出し可能かどうかだけを確認する（事前チェック用）。"""
    limit = LIMITS.get(api_type)
    if limit is None:
        return True, None
    now = datetime.now(timezone.utc)
    with _lock:
        timestamps = _prune(api_type, now)
        if len(timestamps) >= limit:
            return False, min(timestamps) + WINDOW
    return True, None


def check_and_record(api_type: str) -> None:
    """呼び出し直前に使う。上限内なら1回分を記録し、上限超過なら RateLimitExceeded を送出する。
    チェックと記録を同一ロック内で行うことで、並行呼び出しでの上限超過を防ぐ。"""
    limit = LIMITS.get(api_type)
    if limit is None:
        return

    now = datetime.now(timezone.utc)
    with _lock:
        timestamps = _prune(api_type, now)
        if len(timestamps) >= limit:
            reset_at = min(timestamps) + WINDOW
            logger.warning(f"API rate limit exceeded: {api_type} ({len(timestamps)}/{limit})")
            raise RateLimitExceeded(api_type, reset_at)
        _timestamps[api_type].append(now)


def get_usage(api_type: str) -> dict:
    limit = LIMITS.get(api_type)
    if limit is None:
        return {"used": 0, "limit": None}
    now = datetime.now(timezone.utc)
    with _lock:
        used = len(_prune(api_type, now))
    return {"used": used, "limit": limit}


def minutes_until_reset(reset_at: datetime) -> int:
    now = datetime.now(timezone.utc)
    return max(1, int((reset_at - now).total_seconds() // 60) + 1)


_LABELS = {"anthropic": "Anthropic API", "x_api": "X API"}


def format_message(api_type: str, reset_at: datetime) -> str:
    label = _LABELS.get(api_type, api_type)
    limit = LIMITS.get(api_type)
    mins = minutes_until_reset(reset_at)
    return f"{label}の呼び出し上限（1時間{limit}回）に達しました。{mins}分後に利用可能です。"
