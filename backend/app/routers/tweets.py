import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tweet import Tweet, TweetStatus
from app.services.writer import generate_tweets
from app.services.news_search import search_news_for_tweet
from app.dependencies import get_current_user
from app.utils.rate_limit import RateLimitExceeded, format_message, would_allow

router = APIRouter(prefix="/tweets", tags=["tweets"])

_ATTACHED_URL_RE = re.compile(r"(?:^|\n)(https?://\S+)\s*$")


class GenerateRequest(BaseModel):
    prompt_file: Optional[str] = None


@router.post("/generate")
def generate(body: GenerateRequest = GenerateRequest(), db: Session = Depends(get_db), _=Depends(get_current_user)):
    queue_count = db.query(Tweet).filter(Tweet.status == TweetStatus.queued).count()
    if queue_count >= 100:
        raise HTTPException(status_code=400, detail="キューが上限（100件）に達しています")

    allowed, reset_at = would_allow("anthropic")
    if not allowed:
        raise HTTPException(status_code=429, detail=format_message("anthropic", reset_at))

    posted_tweets = (
        db.query(Tweet.content)
        .filter(Tweet.status == TweetStatus.posted)
        .order_by(Tweet.posted_at.desc())
        .limit(50)
        .all()
    )
    history = [t.content for t in posted_tweets]

    new_tweets = generate_tweets(history, prompt_file=body.prompt_file)
    for content in new_tweets:
        db.add(Tweet(content=content, status=TweetStatus.queued))
    db.commit()

    return {"generated": len(new_tweets)}


class NewsSearchRequest(BaseModel):
    search_pattern: Optional[int] = None
    exclude_urls: list[str] = []


def _get_queued_tweet(tweet_id: int, db: Session) -> Tweet:
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    return tweet


@router.post("/{tweet_id}/news/search")
def search_news(tweet_id: int, body: NewsSearchRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = _get_queued_tweet(tweet_id, db)
    if _ATTACHED_URL_RE.search(tweet.content):
        raise HTTPException(status_code=400, detail="既にニュースURLが付与されています。先に削除してください。")

    try:
        return search_news_for_tweet(
            tweet.content,
            search_pattern=body.search_pattern,
            exclude_urls=body.exclude_urls,
        )
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))


class NewsAttachRequest(BaseModel):
    url: str


@router.post("/{tweet_id}/news/attach")
def attach_news(tweet_id: int, body: NewsAttachRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = _get_queued_tweet(tweet_id, db)
    if _ATTACHED_URL_RE.search(tweet.content):
        raise HTTPException(status_code=400, detail="既にニュースURLが付与されています")
    if not body.url.startswith("http"):
        raise HTTPException(status_code=400, detail="不正なURLです")

    new_content = tweet.content.rstrip() + "\n" + body.url
    if len(new_content) > 280:
        raise HTTPException(status_code=400, detail="URLを追加すると280文字を超えます。ツイート本文を短くしてください。")

    tweet.content = new_content
    db.commit()
    db.refresh(tweet)
    return tweet


@router.delete("/{tweet_id}/news")
def remove_news(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = _get_queued_tweet(tweet_id, db)
    match = _ATTACHED_URL_RE.search(tweet.content)
    if not match:
        raise HTTPException(status_code=404, detail="付与されたニュースURLが見つかりません")

    tweet.content = tweet.content[:match.start()].rstrip()
    db.commit()
    db.refresh(tweet)
    return tweet
