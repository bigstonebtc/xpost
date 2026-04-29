from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tweet import Tweet, TweetStatus
from app.dependencies import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
def list_history(db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweets = (
        db.query(Tweet)
        .filter(Tweet.status == TweetStatus.posted)
        .order_by(Tweet.posted_at.desc())
        .limit(200)
        .all()
    )
    return tweets


@router.get("/stats")
def stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    from datetime import datetime, date

    today = date.today()
    queue_count = db.query(Tweet).filter(Tweet.status == TweetStatus.queued).count()
    scheduled_count = db.query(Tweet).filter(Tweet.status == TweetStatus.scheduled).count()
    today_count = (
        db.query(Tweet)
        .filter(Tweet.status == TweetStatus.posted)
        .filter(func.date(Tweet.posted_at) == today)
        .count()
    )
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
        "next_scheduled_at": next_scheduled.scheduled_at if next_scheduled else None,
    }
