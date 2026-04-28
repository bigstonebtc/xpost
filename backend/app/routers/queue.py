from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import case
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import random
from app.database import get_db
from app.models.tweet import Tweet, TweetStatus
from app.dependencies import get_current_user
from app.services.scheduler import schedule_tweet

router = APIRouter(prefix="/queue", tags=["queue"])


class TweetUpdate(BaseModel):
    content: str


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
def post_tweet(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    delay_minutes = random.randint(1, 120)
    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    tweet.status = TweetStatus.scheduled
    tweet.scheduled_at = scheduled_at
    db.commit()

    schedule_tweet(tweet_id, scheduled_at)

    return {"scheduled_at": scheduled_at, "delay_minutes": delay_minutes}


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
