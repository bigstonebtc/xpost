from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.news import NewsItem, NewsSource
from app.models.tweet import Tweet, TweetStatus
from app.services.writer import generate_tweet_from_news
from app.utils.rate_limit import RateLimitExceeded, format_message

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


@router.post("/clear-ai-skipped")
def clear_ai_skipped(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """AI判定NGの記事を削除 → 次回取得時に再判定される"""
    deleted = db.query(NewsItem).filter(
        NewsItem.status == "skipped",
        NewsItem.ai_relevant == False,
    ).delete()
    db.commit()
    return {"deleted": deleted}


@router.post("/fetch")
def fetch_news(background_tasks: BackgroundTasks, _=Depends(get_current_user)):
    from app.services.news_fetcher import fetch_and_process
    background_tasks.add_task(fetch_and_process)
    return {"message": "取得を開始しました"}


@router.get("/debug")
def fetch_debug(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """RSS到達確認・DB統計（AI判定なし）"""
    import socket
    import time as _time
    import feedparser
    from datetime import datetime, timezone, timedelta
    from app.models.news import NewsSource

    sources = db.query(NewsSource).filter(NewsSource.is_enabled == True).all()
    now = datetime.now(timezone.utc)
    source_results = []

    for source in sources:
        info = {
            "name": source.name,
            "url": source.url,
            "total_entries": 0,
            "recent_entries": 0,
            "sample_titles": [],
            "error": None,
        }
        try:
            old = socket.getdefaulttimeout()
            socket.setdefaulttimeout(15)
            try:
                feed = feedparser.parse(source.url)
            finally:
                socket.setdefaulttimeout(old)

            info["total_entries"] = len(feed.entries)
            for entry in feed.entries[:5]:
                published_at = None
                if getattr(entry, "published_parsed", None):
                    published_at = datetime.fromtimestamp(
                        _time.mktime(entry.published_parsed), tz=timezone.utc
                    )
                age_h = round((now - published_at).total_seconds() / 3600, 1) if published_at else None
                recent = (age_h is None or age_h < 48)
                if recent:
                    info["recent_entries"] += 1
                info["sample_titles"].append({
                    "title": entry.get("title", "")[:60],
                    "age_hours": age_h,
                    "recent": recent,
                })
        except Exception as e:
            info["error"] = str(e)

        source_results.append(info)

    # DBの統計
    from app.models.news import NewsItem
    db_stats = {
        "pending": db.query(NewsItem).filter(NewsItem.status == "pending").count(),
        "skipped_ai": db.query(NewsItem).filter(NewsItem.status == "skipped", NewsItem.ai_relevant == False).count(),
        "queued": db.query(NewsItem).filter(NewsItem.status == "queued").count(),
        "total": db.query(NewsItem).count(),
    }

    return {"sources": source_results, "db_stats": db_stats}


@router.post("/{item_id}/add-to-queue")
def add_to_queue(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(NewsItem).filter(NewsItem.id == item_id, NewsItem.status == "pending").first()
    if not item:
        raise HTTPException(status_code=404, detail="記事が見つかりません")

    try:
        tweet_text = generate_tweet_from_news(item.title, item.summary or "")
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))
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
    try:
        tweet_text = generate_tweet_from_news(item.title, item.summary or "")
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))
    item.tweet_text = tweet_text
    db.commit()
    return {"tweet_text": tweet_text}
