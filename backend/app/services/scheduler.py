import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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
        if not tweet:
            print(f"[scheduler] tweet_id={tweet_id} が見つかりません")
            return
        if tweet.status != TweetStatus.scheduled:
            print(f"[scheduler] tweet_id={tweet_id} のステータスが scheduled ではありません: {tweet.status}")
            return
        print(f"[scheduler] tweet_id={tweet_id} を投稿中...")
        x_id = post_tweet(tweet.content)
        tweet.status = TweetStatus.posted
        tweet.posted_at = datetime.now(timezone.utc)
        tweet.x_tweet_id = x_id
        db.commit()
        print(f"[scheduler] tweet_id={tweet_id} 投稿完了 x_id={x_id}")
    except Exception as e:
        print(f"[scheduler] 投稿エラー tweet_id={tweet_id}: {e}")
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
    print("[scheduler] ニュース自動取得開始")
    try:
        stats = fetch_and_process()
        print(f"[scheduler] ニュース自動取得完了: {stats}")
    except Exception as e:
        print(f"[scheduler] ニュース取得エラー: {e}")
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
                print(f"[scheduler] ニュース取得ジョブ登録: slot={slot.slot_number} hour={slot.hour}JST")
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
