from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, get_engine, session_for
from app.logger import system_logger
from app.services.image_cleanup import cleanup_orphaned_images
from app.routers import auth, tweets, queue, history
from app.routers import news as news_router
from app.routers import settings as settings_router
from app.routers import prompts as prompts_router
from app.routers import images as images_router
from app.routers import apikeys as apikeys_router
from app.routers import posting as posting_router
from app.routers import rate_limit as rate_limit_router
from app.routers import features as features_router
from app.routers import tor as tor_router
from app.user_registry import load_all_users, users_config

# モデルを全てインポートしてcreate_allに認識させる
import app.models  # noqa: F401


def _recover_scheduled_tweets(user_id: str) -> None:
    from app.models.tweet import Tweet, TweetStatus
    from app.services.scheduler import schedule_tweet

    db = session_for(user_id)
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
            schedule_tweet(user_id, tweet.id, run_at)
            system_logger.info(f"user={user_id} tweet_id={tweet.id} を再スケジュール: {run_at}")
    finally:
        db.close()


def _seed_news_data(user_id: str) -> None:
    from app.models.news import NewsSource, FetchSchedule, NewsSettings

    db = session_for(user_id)
    try:
        if db.query(NewsSource).count() == 0:
            # ===== 旧プリセット（一時無効化 / 復活可能） =====
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

        if db.query(FetchSchedule).count() == 0:
            for slot, hour, enabled in [(1, 7, True), (2, 12, True), (3, 17, True), (4, 21, False)]:
                db.add(FetchSchedule(slot_number=slot, hour=hour, is_enabled=enabled))

        if db.query(NewsSettings).count() == 0:
            db.add(NewsSettings(fetch_limit_per_run=20))

        db.commit()
    finally:
        db.close()


def _ensure_news_sources_v2(user_id: str) -> None:
    """旧プリセットを無効化し、Google News / はてなブックマークソースを用意する（冪等）"""
    from app.models.news import NewsSource

    db = session_for(user_id)
    try:
        db.query(NewsSource).filter(NewsSource.is_preset == True).update({"is_enabled": False})

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

        db.commit()
    finally:
        db.close()


def _seed_posting_settings(user_id: str) -> None:
    from app.models.posting import PostingSettings

    db = session_for(user_id)
    try:
        if db.query(PostingSettings).count() == 0:
            db.add(PostingSettings(daily_schedule_limit=10))
            db.commit()
    finally:
        db.close()


def _init_user(user_id: str) -> None:
    from app.services import posting_mode
    from app.services.scheduler import setup_news_fetch_jobs

    cfg = users_config[user_id]
    engine = get_engine(user_id)
    Base.metadata.create_all(bind=engine)

    _seed_news_data(user_id)
    _ensure_news_sources_v2(user_id)
    _seed_posting_settings(user_id)
    _recover_scheduled_tweets(user_id)

    system_logger.info(
        f"user={user_id} 初期化完了 posting_mode={posting_mode.get_mode(user_id)} "
        f"legacy_news_feature_enabled={cfg.legacy_news_feature_enabled}"
    )
    if cfg.legacy_news_feature_enabled:
        setup_news_fetch_jobs(user_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loaded = load_all_users()
    system_logger.info(f"読み込んだユーザー: {loaded or '(なし)'}")

    for user_id in loaded:
        try:
            _init_user(user_id)
        except Exception as e:
            system_logger.error(f"user={user_id} の初期化に失敗しました（このユーザーは利用不可）: {e}")

    cleanup_orphaned_images()
    yield


app = FastAPI(title="xpost API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://160.251.142.37",
        "https://160.251.142.37",
    ],
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
app.include_router(images_router.router)
app.include_router(apikeys_router.router)
app.include_router(posting_router.router)
app.include_router(rate_limit_router.router)
app.include_router(features_router.router)
app.include_router(tor_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
