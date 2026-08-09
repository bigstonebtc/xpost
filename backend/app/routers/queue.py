import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import posting_logger
from app.models.tweet import Tweet, TweetStatus
from app.models.posting import PostingSettings
from app.services.scheduler import schedule_tweet
from app.utils.rate_limit import RateLimitExceeded, format_message

router = APIRouter(prefix="/queue", tags=["queue"])

JST = ZoneInfo("Asia/Tokyo")


class TweetUpdate(BaseModel):
    content: str


def _find_available_datetime(base_dt: datetime, daily_limit: int, db: Session) -> datetime:
    """daily_limit 未満のスケジュール件数になる日を探して base_dt の時刻で返す"""
    candidate = base_dt
    while True:
        day_jst = candidate.astimezone(JST).date()
        day_start = datetime(day_jst.year, day_jst.month, day_jst.day, tzinfo=JST).astimezone(timezone.utc)
        day_end = day_start + timedelta(days=1)
        count = db.query(Tweet).filter(
            Tweet.status == TweetStatus.scheduled,
            Tweet.scheduled_at >= day_start,
            Tweet.scheduled_at < day_end,
        ).count()
        if count < daily_limit:
            return candidate
        candidate += timedelta(days=1)


def _random_daytime_schedule(hours: int = 24) -> datetime:
    now_jst = datetime.now(JST)
    end_window = now_jst + timedelta(hours=hours)
    slots = []
    t = now_jst.replace(second=0, microsecond=0) + timedelta(minutes=1)
    while t <= end_window:
        if 7 <= t.hour < 20:
            slots.append(t)
        t += timedelta(minutes=1)
    if not slots:
        return datetime.now(timezone.utc) + timedelta(hours=1)
    return random.choice(slots).astimezone(timezone.utc)


@router.get("/")
def list_queue(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import asc, nulls_last
    tweets = (
        db.query(Tweet)
        .filter(Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled]))
        .order_by(
            case((Tweet.status == TweetStatus.queued, 0), else_=1),
            nulls_last(asc(Tweet.scheduled_at)),
            Tweet.id.asc()
        )
        .all()
    )
    return tweets


@router.post("/{tweet_id}/post")
def post_tweet_now(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.services.poster import post_tweet as _post_to_x
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    try:
        image_path = tweet.image_path
        started_at = time.monotonic()
        x_id = _post_to_x(tweet.content, image_path)
        elapsed = time.monotonic() - started_at
        tweet.status = TweetStatus.posted
        tweet.posted_at = datetime.now(timezone.utc)
        tweet.x_tweet_id = x_id
        tweet.image_path = None
        db.commit()
        if image_path:
            Path(image_path).unlink(missing_ok=True)
        posting_logger.info(f"posted tweet_id={tweet_id} x_id={x_id} in {elapsed:.1f}s")
        return {"ok": True, "x_tweet_id": x_id}
    except RateLimitExceeded as e:
        db.rollback()
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))
    except Exception as e:
        db.rollback()
        posting_logger.error(f"posting failed tweet_id={tweet_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tweet_id}/schedule")
def schedule_tweet_post(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.models.news import NewsSettings
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    ns = db.query(NewsSettings).first()
    mode = ns.schedule_mode if ns else "120min"

    if mode == "24h_daytime":
        base_dt = _random_daytime_schedule(24)
    elif mode == "72h":
        base_dt = _random_daytime_schedule(72)
    elif mode == "120h":
        base_dt = _random_daytime_schedule(120)
    else:
        delay_minutes = random.randint(1, 120)
        base_dt = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

    ps = db.query(PostingSettings).first()
    daily_limit = ps.daily_schedule_limit if ps else 10
    scheduled_at = _find_available_datetime(base_dt, daily_limit, db)

    tweet.status = TweetStatus.scheduled
    tweet.scheduled_at = scheduled_at
    db.commit()
    schedule_tweet(tweet_id, scheduled_at)

    return {"scheduled_at": scheduled_at}


@router.post("/{tweet_id}/discard")
def discard_tweet(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(
        Tweet.id == tweet_id,
        Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled])
    ).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    image_path = tweet.image_path
    tweet.status = TweetStatus.discarded
    tweet.image_path = None
    db.commit()
    if image_path:
        Path(image_path).unlink(missing_ok=True)
    return {"ok": True}


@router.put("/{tweet_id}")
def edit_tweet(tweet_id: int, body: TweetUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    if len(body.content) > 280:
        raise HTTPException(status_code=400, detail="280文字を超えています")
    tweet.content = body.content
    db.commit()
    return tweet


@router.delete("/")
def clear_queue(db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Tweet).filter(Tweet.status == TweetStatus.queued).delete()
    db.commit()
    return {"ok": True}
