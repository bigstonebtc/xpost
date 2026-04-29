from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.news import NewsItem, NewsSource
from app.models.tweet import Tweet, TweetStatus
from app.services.writer import generate_tweet_from_news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/")
def list_news(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = (
        db.query(NewsItem, NewsSource.name.label("source_name"))
        .outerjoin(NewsSource, NewsItem.source_id == NewsSource.id)
        .filter(NewsItem.status == "pending")
        .order_by(NewsItem.fetched_at.desc())
        .all()
    )
    result = []
    for item, source_name in items:
        d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        d["source_name"] = source_name
        result.append(d)
    return result


@router.post("/fetch")
def fetch_news(background_tasks: BackgroundTasks, _=Depends(get_current_user)):
    from app.services.news_fetcher import fetch_and_process
    background_tasks.add_task(fetch_and_process)
    return {"message": "取得を開始しました"}


@router.post("/{item_id}/add-to-queue")
def add_to_queue(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(NewsItem).filter(NewsItem.id == item_id, NewsItem.status == "pending").first()
    if not item:
        raise HTTPException(status_code=404, detail="記事が見つかりません")

    tweet_text = generate_tweet_from_news(item.title, item.summary or "")
    item.tweet_text = tweet_text

    content = tweet_text + "\n" + item.url
    tweet = Tweet(
        content=content,
        status=TweetStatus.queued,
        source_type="news",
        news_item_id=item.id,
    )
    db.add(tweet)
    item.status = "queued"
    db.commit()
    db.refresh(tweet)
    return tweet


@router.post("/{item_id}/skip")
def skip_news(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(NewsItem).filter(NewsItem.id == item_id, NewsItem.status == "pending").first()
    if not item:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    item.status = "skipped"
    db.commit()
    return {"ok": True}


@router.post("/{item_id}/regenerate")
def regenerate_tweet(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(NewsItem).filter(NewsItem.id == item_id, NewsItem.status == "pending").first()
    if not item:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    tweet_text = generate_tweet_from_news(item.title, item.summary or "")
    item.tweet_text = tweet_text
    db.commit()
    return {"tweet_text": tweet_text}
