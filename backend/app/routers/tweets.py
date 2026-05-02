from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tweet import Tweet, TweetStatus
from app.services.writer import generate_tweets
from app.dependencies import get_current_user

router = APIRouter(prefix="/tweets", tags=["tweets"])


class GenerateRequest(BaseModel):
    prompt_file: str


@router.post("/generate")
def generate(body: GenerateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
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

    try:
        new_tweets = generate_tweets(history, body.prompt_file)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    for content in new_tweets:
        db.add(Tweet(content=content, status=TweetStatus.queued))
    db.commit()

    return {"generated": len(new_tweets)}
