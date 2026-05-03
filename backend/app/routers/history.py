from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tweet import Tweet, TweetStatus

router = APIRouter(prefix="/history", tags=["history"])

JST = ZoneInfo("Asia/Tokyo")


def _jst_day_range(offset_days: int = 0):
    """JST基準で offset_days 前の日の開始・終了をUTCで返す"""
    now_jst = datetime.now(JST)
    day_start_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset_days)
    day_end_jst = day_start_jst + timedelta(days=1)
    return day_start_jst.astimezone(timezone.utc), day_end_jst.astimezone(timezone.utc)


@router.get("/")
def list_history(
    filter: str = Query(default="today"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Tweet).filter(Tweet.status == TweetStatus.posted)

    if filter == "today":
        start, end = _jst_day_range(0)
        q = q.filter(Tweet.posted_at >= start, Tweet.posted_at < end)
    elif filter == "yesterday":
        start, end = _jst_day_range(1)
        q = q.filter(Tweet.posted_at >= start, Tweet.posted_at < end)
    elif filter == "month":
        now_jst = datetime.now(JST)
        month_start = now_jst.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        q = q.filter(Tweet.posted_at >= month_start)
    # "all" → フィルタなし（上限 500 件）

    return q.order_by(Tweet.posted_at.desc()).limit(500).all()


@router.get("/stats")
def stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    today_start, tomorrow_start = _jst_day_range(0)
    yesterday_start, _ = _jst_day_range(1)
    now_jst = datetime.now(JST)
    month_start = now_jst.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    queue_count = db.query(Tweet).filter(Tweet.status == TweetStatus.queued).count()
    scheduled_count = db.query(Tweet).filter(Tweet.status == TweetStatus.scheduled).count()

    posted = db.query(Tweet).filter(Tweet.status == TweetStatus.posted)
    today_count = posted.filter(Tweet.posted_at >= today_start, Tweet.posted_at < tomorrow_start).count()
    yesterday_count = posted.filter(Tweet.posted_at >= yesterday_start, Tweet.posted_at < today_start).count()
    month_count = posted.filter(Tweet.posted_at >= month_start).count()
    total_count = posted.count()

    next_scheduled = (
        db.query(Tweet)
        .filter(Tweet.status == TweetStatus.scheduled)
        .order_by(Tweet.scheduled_at.asc())
        .first()
    )
    return {
        "queue_count": queue_count,
        "scheduled_count": scheduled_count,
        "today_posted": today_count,
        "yesterday_posted": yesterday_count,
        "month_posted": month_count,
        "total_posted": total_count,
        "next_scheduled_at": next_scheduled.scheduled_at if next_scheduled else None,
    }
