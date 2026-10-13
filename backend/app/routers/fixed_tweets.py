from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import asc, nulls_first
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import get_logger
from app.models.fixed_tweet import FixedTweet
from app.routers.queue import _add_content_to_queue

router = APIRouter(prefix="/fixed-tweets", tags=["fixed-tweets"])


class FixedTweetCreate(BaseModel):
    content: str


class FixedTweetUpdate(BaseModel):
    content: str


def _get_fixed_tweet(fixed_tweet_id: int, db: Session) -> FixedTweet:
    item = db.query(FixedTweet).filter(FixedTweet.id == fixed_tweet_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="固定文面が見つかりません")
    return item


@router.get("/")
def list_fixed_tweets(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(FixedTweet)
        .order_by(nulls_first(asc(FixedTweet.last_used_at)), FixedTweet.id.asc())
        .all()
    )


@router.post("/", status_code=201)
def create_fixed_tweet(body: FixedTweetCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="本文を入力してください")

    item = FixedTweet(content=body.content)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{fixed_tweet_id}")
def update_fixed_tweet(fixed_tweet_id: int, body: FixedTweetUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="本文を入力してください")

    item = _get_fixed_tweet(fixed_tweet_id, db)
    item.content = body.content
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{fixed_tweet_id}", status_code=204)
def delete_fixed_tweet(fixed_tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = _get_fixed_tweet(fixed_tweet_id, db)
    db.delete(item)
    db.commit()


@router.post("/{fixed_tweet_id}/queue")
def queue_fixed_tweet(fixed_tweet_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    item = _get_fixed_tweet(fixed_tweet_id, db)

    tweet = _add_content_to_queue(db, item.content)

    item.last_used_at = datetime.now(timezone.utc)
    item.use_count += 1
    db.commit()

    get_logger(user).info(f"fixed_tweet_id={fixed_tweet_id} をキューへ投入しました（tweet_id={tweet.id}）")
    return tweet
