from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app.routers import auth, tweets, queue, history
from app.routers import news as news_router
from app.routers import settings as settings_router
from app.routers import prompts as prompts_router
from app.routers import documents as documents_router

# モデルを全てインポートしてcreate_allに認識させる
import app.models  # noqa: F401


def _recover_scheduled_tweets():
    from app.models.tweet import Tweet, TweetStatus
    from app.services.scheduler import schedule_tweet

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pending = db.query(Tweet).filter(Tweet.status == TweetStatus.scheduled).all()
        for tweet in pending:
            run_at = tweet.scheduled_at
            if run_at is None:
                run_at = now + timedelta(minutes=1)
            elif run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=timezone.utc)
            if run_at <= now:
                run_at = now + timedelta(minutes=1)
            schedule_tweet(tweet.id, run_at)
            print(f"[startup] tweet_id={tweet.id} を再スケジュール: {run_at}")
    finally:
        db.close()


def _migrate_db():
    migrations = [
        ("tweets", "source_type", "VARCHAR(20) DEFAULT 'manual'"),
        ("tweets", "news_item_id", "INTEGER"),
        ("news_settings", "news_prompt_file", "VARCHAR(255) DEFAULT 'news_comment.prompt'"),
    ]
    with engine.connect() as conn:
        for table, col, definition in migrations:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=:tbl AND column_name=:col"
            ), {"tbl": table, "col": col})
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {definition}"))
                conn.commit()
                print(f"[migration] {table}.{col} を追加しました")


_DEFAULT_RELEVANCE_PROMPT = (
    "以下の記事が「自由主義・相続税廃止・私有財産権・規制緩和」を訴えるXアカウントの\n"
    "投稿素材として関連性があるか判定してください。\n\n"
    "タイトル：{title}\n"
    "概要：{summary}\n\n"
    '以下のJSONのみ返答：\n{"relevant": true/false}'
)


def _seed_news_data():
    from app.models.news import NewsSource, FetchSchedule, NewsSettings

    db = SessionLocal()
    try:
        if db.query(NewsSource).count() == 0:
            presets = [
                ("NHK経済", "https://www.nhk.or.jp/rss/news/cat4.xml", "経済", True),
                ("産経ニュース", "https://www.sankei.com/economy/rss/", "経済", True),
                ("日経電子版（無料）", "https://www.nikkei.com/rss/news.rss", "経済・税制", True),
                ("東洋経済オンライン", "https://toyokeizai.net/list/feed/rss", "経済", True),
                ("Yahoo!ニュース経済", "https://news.yahoo.co.jp/rss/categories/business.xml", "経済", False),
                ("財務省プレスリリース", "https://www.mof.go.jp/rss/", "税制", True),
            ]
            for name, url, category, enabled in presets:
                db.add(NewsSource(name=name, url=url, category=category, is_enabled=enabled))
            print("[seed] news_sources を初期化しました")

        if db.query(FetchSchedule).count() == 0:
            for slot, hour, enabled in [(1, 7, True), (2, 12, True), (3, 17, True), (4, 21, False)]:
                db.add(FetchSchedule(slot_number=slot, hour=hour, is_enabled=enabled))
            print("[seed] fetch_schedules を初期化しました")

        if db.query(NewsSettings).count() == 0:
            db.add(NewsSettings(fetch_limit_per_run=20, relevance_prompt=_DEFAULT_RELEVANCE_PROMPT))
            print("[seed] news_settings を初期化しました")

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _seed_news_data()
    _recover_scheduled_tweets()
    from app.services.scheduler import setup_news_fetch_jobs
    setup_news_fetch_jobs()
    yield


app = FastAPI(title="xpost API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tweets.router)
app.include_router(queue.router)
app.include_router(history.router)
app.include_router(news_router.router)
app.include_router(settings_router.router)
app.include_router(prompts_router.router)
app.include_router(documents_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
