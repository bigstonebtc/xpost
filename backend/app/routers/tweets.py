from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tweet import Tweet, TweetStatus
from app.services.writer import generate_tweets
from app.dependencies import get_current_user

router = APIRouter(prefix="/tweets", tags=["tweets"])


@router.post("/generate")
def generate(db: Session = Depends(get_db), _=Depends(get_current_user)):
    queue_count = db.query(Tweet).filter(Tweet.status == TweetStatus.queued).count()
    if queue_count >= 100:
        raise HTTPException(status_code=400, detail="キューが上限（100件）に達しています")

    posted_tweets = (
        db.query(Tweet.content)
        .filter(Tweet.status == TweetStatus.posted)
        .order_by(Tweet.posted_at.desc())
        .limit(50)
        .all()
    )
    history = [t.content for t in posted_tweets]

    new_tweets = generate_tweets(history)
    for content in new_tweets:
        db.add(Tweet(content=content, status=TweetStatus.queued))
    db.commit()

    return {"generated": len(new_tweets)}
