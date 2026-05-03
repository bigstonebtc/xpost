import math
import time
import json
import socket
import traceback
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Optional

import feedparser
import anthropic

from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)

DEFAULT_PROMPT = (
    "以下の記事が「自由主義・相続税廃止・私有財産権・規制緩和」を訴えるXアカウントの\n"
    "投稿素材として関連性があるか判定してください。\n\n"
    "タイトル：{title}\n"
    "概要：{summary}\n\n"
    '以下のJSONのみ返答：\n{"relevant": true/false}'
)


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


def _ai_relevance_check(title: str, summary: str, prompt_template: str) -> bool:
    prompt = prompt_template.replace("{title}", title).replace("{summary}", summary or "（概要なし）")
    try:
        # プリフィルで {"relevant": まで固定し、確実にJSONを返させる
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": '{"relevant":'},
            ],
        )
        rest = message.content[0].text.strip()
        text = '{"relevant":' + rest
        result = json.loads(text)
        return bool(result.get("relevant", False))
    except Exception as e:
        print(f"[news_fetcher] AI判定エラー: {e}, rest={repr(locals().get('rest', ''))}")
        return False


def fetch_and_process() -> dict:
    from app.database import SessionLocal
    from app.models.news import NewsSource, NewsSettings, NewsItem
    from app.services.writer import generate_tweet_from_news

    db = SessionLocal()
    try:
        sources = db.query(NewsSource).filter(NewsSource.is_enabled == True).all()
        if not sources:
            return {"fetched": 0, "skipped_old": 0, "skipped_duplicate": 0,
                    "skipped_ai": 0, "added_pending": 0}

        ns = db.query(NewsSettings).first()
        total_limit = ns.fetch_limit_per_run if ns else 20
        prompt_template = ns.relevance_prompt if ns else DEFAULT_PROMPT
        news_prompt_file = ns.news_prompt_file if ns else "news_comment.prompt"

        limit_per_source = math.ceil(total_limit / len(sources))

        stats = {"fetched": 0, "skipped_old": 0, "skipped_duplicate": 0,
                 "skipped_ai": 0, "added_pending": 0}

        for source in sources:
            try:
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(15)
                try:
                    feed = feedparser.parse(source.url)
                finally:
                    socket.setdefaulttimeout(old_timeout)
            except Exception as e:
                print(f"[news_fetcher] RSS取得エラー {source.url}: {e}")
                continue

            count_this_source = 0
            for entry in feed.entries:
                if count_this_source >= limit_per_source:
                    break

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

                existing = db.query(NewsItem).filter(NewsItem.url == url).first()
                if existing:
                    stats["skipped_duplicate"] += 1
                    continue

                stats["fetched"] += 1
                count_this_source += 1

                ai_relevant = _ai_relevance_check(title, summary, prompt_template)

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

                tweet_text = generate_tweet_from_news(title, summary, prompt_file=news_prompt_file)
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
