import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tweet import Tweet, TweetStatus
from app.services.scheduler import schedule_tweet

router = APIRouter(prefix="/queue", tags=["queue"])

JST = ZoneInfo("Asia/Tokyo")


class TweetUpdate(BaseModel):
    content: str


def _random_daytime_schedule() -> datetime:
    now_jst = datetime.now(JST)
    end_window = now_jst + timedelta(hours=24)
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
    tweets = (
        db.query(Tweet)
        .filter(Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled]))
        .order_by(
            case((Tweet.status == TweetStatus.scheduled, 1), else_=0),
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
        x_id = _post_to_x(tweet.content)
        tweet.status = TweetStatus.posted
        tweet.posted_at = datetime.now(timezone.utc)
        tweet.x_tweet_id = x_id
        db.commit()
        return {"ok": True, "x_tweet_id": x_id}
    except Exception as e:
        db.rollback()
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
        scheduled_at = _random_daytime_schedule()
    else:
        delay_minutes = random.randint(1, 120)
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

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
    tweet.status = TweetStatus.discarded
    db.commit()
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
