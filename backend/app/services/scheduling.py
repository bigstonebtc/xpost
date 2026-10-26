"""スケジュール平準化（日ごとの件数の偏り防止）の中核ロジック。

queue.py（新規割り当て・全件リスケジュール）と history.py（ダッシュボード表示）の
両方から共通で使うため、ここに切り出す。
"""
import random
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.tweet import Tweet, TweetStatus

JST = ZoneInfo("Asia/Tokyo")

WEEKEND_LIMIT_REDUCTION = 3
SCHEDULE_DAYS_MIN = 5
SCHEDULE_DAYS_MAX = 14
DEFAULT_SCHEDULE_DAYS = 10

_DAY_START_HOUR = 7
_DAY_END_HOUR = 21


def daily_limit_for(day: date, weekday_limit: int) -> int:
    """指定日（JSTの暦日）の上限を返す。土日は平日の上限-3（下限1）。祝日は考慮しない。"""
    if day.weekday() >= 5:  # 5=土, 6=日
        return max(1, weekday_limit - WEEKEND_LIMIT_REDUCTION)
    return weekday_limit


def random_time_in_day(day: date) -> datetime:
    """指定したJST暦日の7:00〜21:00の範囲で完全ランダムな時刻を返す（UTC aware）。"""
    start = datetime(day.year, day.month, day.day, _DAY_START_HOUR, 0, tzinfo=JST)
    window_minutes = (_DAY_END_HOUR - _DAY_START_HOUR) * 60
    offset_minutes = random.randint(0, window_minutes - 1)
    return (start + timedelta(minutes=offset_minutes)).astimezone(timezone.utc)


def _scheduled_count_on(day: date, db: Session) -> int:
    day_start = datetime(day.year, day.month, day.day, tzinfo=JST).astimezone(timezone.utc)
    day_end = day_start + timedelta(days=1)
    return db.query(Tweet).filter(
        Tweet.status == TweetStatus.scheduled,
        Tweet.scheduled_at >= day_start,
        Tweet.scheduled_at < day_end,
    ).count()


def pick_weighted_day(schedule_days: int, weekday_limit: int, db: Session) -> date | None:
    """予約対象日（明日から schedule_days-1 日間）の中から、空き枠を重みとして1日を抽選する。
    空き枠が1件もない場合は None を返す（今日は対象に含めない）。"""
    today = datetime.now(JST).date()
    candidates = []
    weights = []
    for i in range(1, schedule_days):
        day = today + timedelta(days=i)
        limit = daily_limit_for(day, weekday_limit)
        available = limit - _scheduled_count_on(day, db)
        if available > 0:
            candidates.append(day)
            weights.append(available)

    if not candidates:
        return None
    return random.choices(candidates, weights=weights, k=1)[0]


def schedule_one(schedule_days: int, weekday_limit: int, db: Session) -> datetime | None:
    """新規に1件分の予約日時を決める。割り当て可能な空き枠が無い場合は None を返す。"""
    day = pick_weighted_day(schedule_days, weekday_limit, db)
    if day is None:
        return None
    return random_time_in_day(day)
