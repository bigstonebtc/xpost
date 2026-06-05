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


def _migrate_tweets_table():
    with engine.connect() as conn:
        for col, definition in [
            ("source_type", "VARCHAR(20) DEFAULT 'manual'"),
            ("news_item_id", "INTEGER"),
        ]:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tweets' AND column_name=:col"
            ), {"col": col})
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE tweets ADD COLUMN {col} {definition}"))
                conn.commit()
                print(f"[migration] tweets.{col} を追加しました")


def _migrate_news_settings_table():
    with engine.connect() as conn:
        for col, definition in [
            ("schedule_mode", "VARCHAR(20) DEFAULT '120min'"),
            ("news_prompt_file", "VARCHAR(255) DEFAULT 'news_comment.prompt'"),
        ]:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='news_settings' AND column_name=:col"
            ), {"col": col})
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE news_settings ADD COLUMN {col} {definition}"))
                conn.commit()
                print(f"[migration] news_settings.{col} を追加しました")


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
            # ===== 旧プリセット（一時無効化 / 復活可能） =====
            # 以下のソースを復活させる場合は is_enabled=True に変更してください
            presets = [
                ("NHK経済", "https://www.nhk.or.jp/rss/news/cat4.xml", "経済", False),
                ("産経ニュース", "https://www.sankei.com/economy/rss/", "経済", False),
                ("日経電子版（無料）", "https://www.nikkei.com/rss/news.rss", "経済・税制", False),
                ("東洋経済オンライン", "https://toyokeizai.net/list/feed/rss", "経済", False),
                ("Yahoo!ニュース経済", "https://news.yahoo.co.jp/rss/categories/business.xml", "経済", False),
                ("財務省プレスリリース", "https://www.mof.go.jp/rss/", "税制", False),
            ]
            for name, url, category, enabled in presets:
                db.add(NewsSource(name=name, url=url, category=category, is_enabled=enabled, is_preset=True))
            # ===== /旧プリセット =====
            print("[seed] news_sources を初期化しました（旧プリセットは無効状態）")

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


def _migrate_news_sources_v2():
    """既存ソースを無効化し、Google News / はてなブックマークソースを追加する（冪等）"""
    from app.models.news import NewsSource

    db = SessionLocal()
    try:
        # 旧プリセット（is_preset=True）を全件無効化
        db.query(NewsSource).filter(NewsSource.is_preset == True).update({"is_enabled": False})

        # 新ソース（is_preset=False / ユーザー管理）を追加（重複チェックあり）
        new_sources = [
            ("Google News - 相続税・減税",
             "https://news.google.com/rss/search?q=%E7%9B%B8%E7%B6%9A%E7%A8%8E+%E6%B8%9B%E7%A8%8E&hl=ja&gl=JP&ceid=JP:ja",
             "経済"),
            ("Google News - 資産課税・財産権",
             "https://news.google.com/rss/search?q=%E8%B3%87%E7%94%A3%E8%AA%B2%E7%A8%8E+%E8%B2%A1%E7%94%A3%E6%A8%A9&hl=ja&gl=JP&ceid=JP:ja",
             "経済"),
            ("Google News - 規制緩和・既得権",
             "https://news.google.com/rss/search?q=%E8%A6%8F%E5%88%B6%E7%B7%A9%E5%92%8C+%E6%97%A2%E5%BE%97%E6%A8%A9&hl=ja&gl=JP&ceid=JP:ja",
             "経済"),
            ("Google News - 増税・財政",
             "https://news.google.com/rss/search?q=%E5%A2%97%E7%A8%8E+%E8%B2%A1%E6%94%BF&hl=ja&gl=JP&ceid=JP:ja",
             "経済"),
            ("はてなブックマーク - 経済",
             "https://b.hatena.ne.jp/hotentry/economics.rss",
             "経済"),
            ("はてなブックマーク - 政治",
             "https://b.hatena.ne.jp/hotentry/politics.rss",
             "政治"),
        ]
        for name, url, category in new_sources:
            exists = db.query(NewsSource).filter(NewsSource.name == name).first()
            if not exists:
                db.add(NewsSource(name=name, url=url, category=category,
                                  is_enabled=True, is_preset=False))
                print(f"[migrate_v2] ソース追加: {name}")

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_tweets_table()
    _migrate_news_settings_table()
    _seed_news_data()
    _migrate_news_sources_v2()
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


@app.get("/health")
def health():
    return {"status": "ok"}
