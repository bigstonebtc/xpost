from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, tweets, queue, history


def _recover_scheduled_tweets():
    from app.database import SessionLocal
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _recover_scheduled_tweets()
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


@app.get("/health")
def health():
    return {"status": "ok"}
