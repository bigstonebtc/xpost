from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.start()


def _execute_post(tweet_id: int):
    from app.database import SessionLocal
    from app.models.tweet import Tweet, TweetStatus
    from app.services.poster import post_tweet

    db = SessionLocal()
    try:
        tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
        if not tweet or tweet.status != TweetStatus.scheduled:
            return
        x_id = post_tweet(tweet.content)
        tweet.status = TweetStatus.posted
        tweet.posted_at = datetime.now(timezone.utc)
        tweet.x_tweet_id = x_id
        db.commit()
    except Exception as e:
        print(f"投稿エラー tweet_id={tweet_id}: {e}")
    finally:
        db.close()


def schedule_tweet(tweet_id: int, run_at: datetime):
    scheduler.add_job(
        _execute_post,
        trigger="date",
        run_date=run_at,
        args=[tweet_id],
        id=f"tweet_{tweet_id}",
        replace_existing=True,
    )
