import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from app.logger import posting_logger as logger

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.start()


def _execute_post(tweet_id: int):
    from app.database import SessionLocal
    from app.models.tweet import Tweet, TweetStatus
    from app.services.poster import post_tweet

    db = SessionLocal()
    try:
        tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
        if not tweet:
            logger.warning(f"scheduled tweet_id={tweet_id} not found")
            return
        if tweet.status != TweetStatus.scheduled:
            logger.warning(f"tweet_id={tweet_id} status is not scheduled: {tweet.status}")
            return
        logger.info(f"executing scheduled post tweet_id={tweet_id}")
        x_id = post_tweet(tweet.content, tweet.image_path)
        tweet.status = TweetStatus.posted
        tweet.posted_at = datetime.now(timezone.utc)
        tweet.x_tweet_id = x_id
        db.commit()
    except Exception as e:
        logger.error(f"scheduled post failed tweet_id={tweet_id}: {e}")
        traceback.print_exc()
        db.rollback()
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


def _run_news_fetch():
    from app.services.news_fetcher import fetch_and_process
    from app.logger import news_logger
    news_logger.info("scheduled news fetch started")
    try:
        stats = fetch_and_process()
        news_logger.info(f"scheduled news fetch completed: {stats}")
    except Exception as e:
        news_logger.error(f"scheduled news fetch failed: {e}")
        traceback.print_exc()


def setup_news_fetch_jobs():
    from app.database import SessionLocal
    from app.models.news import FetchSchedule

    db = SessionLocal()
    try:
        slots = db.query(FetchSchedule).order_by(FetchSchedule.slot_number).all()
        for slot in slots:
            job_id = f"news_fetch_slot_{slot.slot_number}"
            if slot.is_enabled:
                scheduler.add_job(
                    _run_news_fetch,
                    trigger=CronTrigger(hour=slot.hour, minute=0, timezone="Asia/Tokyo"),
                    id=job_id,
                    replace_existing=True,
                )
            else:
                try:
                    scheduler.remove_job(job_id)
                except Exception:
                    pass
    finally:
        db.close()


def reload_news_fetch_jobs():
    for job in scheduler.get_jobs():
        if job.id.startswith("news_fetch_slot_"):
            scheduler.remove_job(job.id)
    setup_news_fetch_jobs()
