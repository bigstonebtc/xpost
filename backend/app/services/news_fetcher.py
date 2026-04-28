import time
import json
import traceback
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Optional

import feedparser
import anthropic

from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    s = _HTMLStripper()
    s.feed(text)
    return s.get_text().strip()


def _is_recent(published_at: Optional[datetime]) -> bool:
    if published_at is None:
        return True
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return (now - published_at) < timedelta(hours=48)


def _keyword_filter(title: str, summary: str, include_kws: list[str], exclude_kws: list[str]) -> bool:
    text = (title + " " + (summary or "")).lower()
    for kw in exclude_kws:
        if kw.lower() in text:
            return False
    if not include_kws:
        return True
    return any(kw.lower() in text for kw in include_kws)


def _ai_relevance_check(title: str, summary: str) -> bool:
    prompt = (
        "以下の記事が「自由主義・相続税廃止・私有財産権・規制緩和」を訴えるXアカウントの\n"
        "投稿素材として関連性があるか判定してください。\n\n"
        f"タイトル：{title}\n"
        f"概要：{summary or '（概要なし）'}\n\n"
        '以下のJSONのみ返答：\n{"relevant": true/false}'
    )
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        result = json.loads(text)
        return bool(result.get("relevant", False))
    except Exception as e:
        print(f"[news_fetcher] AI判定エラー: {e}")
        return False


def fetch_and_process() -> dict:
    from app.database import SessionLocal
    from app.models.news import NewsSource, NewsKeyword, NewsItem
    from app.services.writer import generate_tweet_from_news

    db = SessionLocal()
    try:
        sources = db.query(NewsSource).filter(NewsSource.is_enabled == True).all()
        include_kws = [kw.keyword for kw in db.query(NewsKeyword).filter(NewsKeyword.type == "include").all()]
        exclude_kws = [kw.keyword for kw in db.query(NewsKeyword).filter(NewsKeyword.type == "exclude").all()]

        stats = {"fetched": 0, "skipped_old": 0, "skipped_duplicate": 0,
                 "skipped_keyword": 0, "skipped_ai": 0, "added_pending": 0}

        for source in sources:
            try:
                feed = feedparser.parse(source.url)
            except Exception as e:
                print(f"[news_fetcher] RSS取得エラー {source.url}: {e}")
                continue

            for entry in feed.entries:
                title = _strip_html(entry.get("title", ""))
                url = entry.get("link", "")
                summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))

                published_at = None
                if getattr(entry, "published_parsed", None):
                    published_at = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed), tz=timezone.utc
                    )

                if not url or not title:
                    continue

                if not _is_recent(published_at):
                    stats["skipped_old"] += 1
                    continue

                stats["fetched"] += 1

                existing = db.query(NewsItem).filter(NewsItem.url == url).first()
                if existing:
                    stats["skipped_duplicate"] += 1
                    continue

                if not _keyword_filter(title, summary, include_kws, exclude_kws):
                    stats["skipped_keyword"] += 1
                    continue

                ai_relevant = _ai_relevance_check(title, summary)

                if not ai_relevant:
                    stats["skipped_ai"] += 1
                    db.add(NewsItem(
                        title=title,
                        url=url,
                        summary=summary[:1000] if summary else None,
                        source_id=source.id,
                        published_at=published_at,
                        ai_relevant=False,
                        status="skipped",
                    ))
                    db.flush()
                    continue

                tweet_text = generate_tweet_from_news(title, summary)
                db.add(NewsItem(
                    title=title,
                    url=url,
                    summary=summary[:1000] if summary else None,
                    source_id=source.id,
                    published_at=published_at,
                    ai_relevant=True,
                    tweet_text=tweet_text,
                    status="pending",
                ))
                db.flush()
                stats["added_pending"] += 1

        db.commit()
        return stats

    except Exception as e:
        db.rollback()
        print(f"[news_fetcher] エラー: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()
