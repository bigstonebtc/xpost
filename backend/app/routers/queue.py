import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import get_logger
from app.models.tweet import Tweet, TweetStatus
from app.models.posting import PostingSettings
from app.routers.tweets import _ATTACHED_URL_RE
from app.services.poster import post_tweet_with_retry
from app.services.review import ReviewError, get_review_prompt, review_tweet
from app.services.scheduler import schedule_tweet
from app.services.scheduling import DEFAULT_SCHEDULE_DAYS, pick_weighted_day, schedule_one
from app.utils.rate_limit import RateLimitExceeded, format_message

router = APIRouter(prefix="/queue", tags=["queue"])

JST = ZoneInfo("Asia/Tokyo")


class TweetUpdate(BaseModel):
    content: str


class TweetAdd(BaseModel):
    content: str


def _check_content_char_limit(content: str, db: Session) -> None:
    ps = db.query(PostingSettings).first()
    allow_over_140 = ps.allow_over_140 if ps else True
    if not allow_over_140 and len(content) > 140:
        raise HTTPException(status_code=400, detail="140文字を超えています")


def _check_char_limit(tweet: Tweet, db: Session) -> None:
    _check_content_char_limit(tweet.content, db)


@router.post("/reschedule-all")
def reschedule_all(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """今日に予約済みの投稿はそのまま残し、それ以外の予約済み投稿を対象に、
    予約をいったん解除した状態から空き枠による重み付きランダムロジックで
    1件ずつ割り当て直す（スケジュール平準化）。未スケジュール（queued）の
    投稿は対象に含めない。"""
    from app.services.scheduler import unschedule_tweet

    now_jst = datetime.now(JST)
    today = now_jst.date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=JST).astimezone(timezone.utc)
    today_end = today_start + timedelta(days=1)

    tweets = (
        db.query(Tweet)
        .filter(Tweet.status == TweetStatus.scheduled)
        .filter((Tweet.scheduled_at < today_start) | (Tweet.scheduled_at >= today_end))
        .order_by(Tweet.id.asc())
        .all()
    )
    if not tweets:
        return {"rescheduled": 0}

    for tweet in tweets:
        unschedule_tweet(user, tweet.id)
        tweet.status = TweetStatus.queued
        tweet.scheduled_at = None
    db.commit()

    ps = db.query(PostingSettings).first()
    schedule_days = ps.schedule_days if ps else DEFAULT_SCHEDULE_DAYS
    daily_limit = ps.daily_schedule_limit if ps else 10

    rescheduled = 0
    for tweet in tweets:
        scheduled_at = schedule_one(schedule_days, daily_limit, db)
        if scheduled_at is None:
            # これ以上空き枠がない。以降の投稿も結果は同じなので打ち切り、未スケジュールのまま残す
            break
        tweet.status = TweetStatus.scheduled
        tweet.scheduled_at = scheduled_at
        db.commit()
        schedule_tweet(user, tweet.id, scheduled_at)
        rescheduled += 1

    get_logger(user, "posting").info(f"reschedule_all: {rescheduled}/{len(tweets)}件を再スケジュールしました")
    return {"rescheduled": rescheduled}


@router.get("/")
def list_queue(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import asc, nulls_last
    tweets = (
        db.query(Tweet)
        .filter(Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled, TweetStatus.failed]))
        .order_by(
            case(
                (Tweet.status == TweetStatus.queued, 0),
                (Tweet.status == TweetStatus.failed, 1),
                else_=2,
            ),
            nulls_last(asc(Tweet.scheduled_at)),
            Tweet.id.desc()
        )
        .all()
    )
    return tweets


def _add_content_to_queue(db: Session, content: str) -> Tweet:
    if not content.strip():
        raise HTTPException(status_code=400, detail="内容を入力してください")
    if len(content) > 1024:
        raise HTTPException(status_code=400, detail="1024文字を超えています")

    queue_count = db.query(Tweet).filter(Tweet.status == TweetStatus.queued).count()
    if queue_count >= 100:
        raise HTTPException(status_code=400, detail="キューが上限（100件）に達しています")

    tweet = Tweet(content=content, status=TweetStatus.queued, source_type="manual")
    db.add(tweet)
    db.commit()
    db.refresh(tweet)
    return tweet


@router.post("/add", status_code=201)
def add_tweet(body: TweetAdd, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return _add_content_to_queue(db, body.content)


@router.post("/{tweet_id}/post")
def post_tweet_now(tweet_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    posting_logger = get_logger(user, "posting")
    tweet = db.query(Tweet).filter(
        Tweet.id == tweet_id,
        Tweet.status.in_([TweetStatus.queued, TweetStatus.failed]),
    ).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    _check_char_limit(tweet, db)

    image_path = tweet.image_path
    try:
        started_at = time.monotonic()
        result = post_tweet_with_retry(user, tweet.content, image_path, tweet_id=tweet_id)
        elapsed = time.monotonic() - started_at

        if result.ok:
            tweet.status = TweetStatus.posted
            tweet.posted_at = datetime.now(timezone.utc)
            tweet.x_tweet_id = result.x_tweet_id
            tweet.posted_via_tor = result.posted_via_tor
            tweet.image_path = None
            tweet.error_code = None
            tweet.error_message = None
            tweet.retry_attempt = result.retry_attempt
            db.commit()
            if image_path:
                Path(image_path).unlink(missing_ok=True)
            posting_logger.info(
                f"posted tweet_id={tweet_id} x_id={result.x_tweet_id} posted_via_tor={result.posted_via_tor} "
                f"in {elapsed:.1f}s"
            )
            return {"ok": True, "x_tweet_id": result.x_tweet_id}

        tweet.status = TweetStatus.failed
        tweet.error_code = result.error_code
        tweet.error_message = result.error_message
        tweet.retry_attempt = result.retry_attempt
        tweet.posted_via_tor = result.posted_via_tor
        tweet.failed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"{result.error_code}: {result.error_message}")

    except RateLimitExceeded as e:
        db.rollback()
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        posting_logger.error(f"posting failed tweet_id={tweet_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tweet_id}/reschedule")
def reschedule_tweet(tweet_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """failedのツイートを再びキュー(queued)に戻す。自動リトライは行わず、
    ユーザーが改めて[投稿]または[Schedule]を押す想定（仕様：自動リトライなし）。"""
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.failed).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    tweet.status = TweetStatus.queued
    tweet.error_code = None
    tweet.error_message = None
    tweet.retry_attempt = 0
    tweet.failed_at = None
    db.commit()
    get_logger(user, "posting").info(f"tweet_id={tweet_id} rescheduled: status=queued")
    return {"ok": True}


@router.post("/{tweet_id}/schedule")
def schedule_tweet_post(tweet_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """未予約の投稿を予約する。有効なレビュー用プロンプトが選ばれていれば（Review: なし 以外）
    レビューしてから予約し、「なし」ならそのまま予約する。"""
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    ps = db.query(PostingSettings).first()
    if get_review_prompt(user, ps.review_prompt_file if ps else None):
        return _review_and_schedule(tweet_id, db, user)

    _check_char_limit(tweet, db)

    schedule_days = ps.schedule_days if ps else DEFAULT_SCHEDULE_DAYS
    daily_limit = ps.daily_schedule_limit if ps else 10

    scheduled_at = schedule_one(schedule_days, daily_limit, db)
    if scheduled_at is None:
        raise HTTPException(status_code=400, detail="予約範囲内に空き枠がありません")

    tweet.status = TweetStatus.scheduled
    tweet.scheduled_at = scheduled_at
    # 以前レビュー付きで予約→unschedule された投稿の場合に、元のツイート欄・青字表示が残らないようにする
    tweet.original_content = None
    db.commit()
    schedule_tweet(user, tweet_id, scheduled_at)

    return {"scheduled_at": scheduled_at}


def _review_and_schedule(tweet_id: int, db: Session, user: str):
    """有効なレビュー用プロンプトで本文をレビューし、修正後の本文に置き換えて予約する。
    予約時刻の決め方は通常の Schedule と同じ。レビューに失敗した場合は予約せず、
    投稿は未予約のまま残す。本文末尾のニュースURLはレビュー対象外とし、そのまま引き継ぐ。"""
    logger = get_logger(user, "posting")

    def fail(status_code: int, detail: str):
        logger.warning(f"review failed tweet_id={tweet_id}: {detail}")
        raise HTTPException(status_code=status_code, detail=detail)

    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    ps = db.query(PostingSettings).first()
    prompt_file = ps.review_prompt_file if ps else None
    if not prompt_file:
        fail(400, "レビュー用プロンプトが設定されていません")
    schedule_days = ps.schedule_days if ps else DEFAULT_SCHEDULE_DAYS
    daily_limit = ps.daily_schedule_limit if ps else 10

    # 空き枠が無ければ、APIを呼ぶ前に打ち切る（結果を予約できず料金だけかかるのを防ぐ）
    if pick_weighted_day(schedule_days, daily_limit, db) is None:
        fail(400, "予約範囲内に空き枠がありません")

    original = tweet.content
    match = _ATTACHED_URL_RE.search(original)
    body = original[:match.start()].rstrip() if match else original
    url_suffix = "\n" + match.group(1) if match else ""
    if not body.strip():
        fail(400, "レビューする本文がありません")

    started_at = time.monotonic()
    try:
        result = review_tweet(user, body, prompt_file)
    except RateLimitExceeded as e:
        fail(429, format_message(e.api_type, e.reset_at))
    except ReviewError as e:
        fail(502, f"レビューに失敗しました: {e}")
    except Exception as e:
        logger.error(f"review error tweet_id={tweet_id}: {e}", exc_info=True)
        fail(502, f"レビューに失敗しました: {e}")
    elapsed = time.monotonic() - started_at

    new_content = result["text"] + url_suffix
    if len(new_content) > 1024:
        fail(400, "レビュー後の本文が1024文字を超えたため予約しませんでした")
    try:
        _check_content_char_limit(new_content, db)
    except HTTPException:
        fail(400, "レビュー後の本文が140文字を超えたため予約しませんでした")

    # レビュー中（数秒〜数十秒）に別画面で編集・削除・予約された場合は、その操作を優先する
    db.refresh(tweet)
    if tweet.status != TweetStatus.queued or tweet.content != original:
        fail(409, "レビュー中に投稿が変更されたため予約しませんでした")

    scheduled_at = schedule_one(schedule_days, daily_limit, db)
    if scheduled_at is None:
        fail(400, "予約範囲内に空き枠がありません")

    tweet.original_content = original
    tweet.content = new_content
    tweet.status = TweetStatus.scheduled
    tweet.scheduled_at = scheduled_at
    db.commit()
    schedule_tweet(user, tweet_id, scheduled_at)

    logger.info(
        f"review succeeded tweet_id={tweet_id} prompt={prompt_file} "
        f"tokens={result['input_tokens']}+{result['output_tokens']} in {elapsed:.1f}s scheduled_at={scheduled_at}"
    )
    return {"scheduled_at": scheduled_at}


@router.post("/{tweet_id}/unschedule")
def unschedule_tweet_post(tweet_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    from app.services.scheduler import unschedule_tweet

    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.scheduled).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    unschedule_tweet(user, tweet_id)
    tweet.status = TweetStatus.queued
    tweet.scheduled_at = None
    db.commit()
    return {"ok": True}


@router.post("/{tweet_id}/discard")
def discard_tweet(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(
        Tweet.id == tweet_id,
        Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled, TweetStatus.failed])
    ).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    image_path = tweet.image_path
    tweet.status = TweetStatus.discarded
    tweet.image_path = None
    db.commit()
    if image_path:
        Path(image_path).unlink(missing_ok=True)
    return {"ok": True}


@router.put("/{tweet_id}")
def edit_tweet(tweet_id: int, body: TweetUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.status == TweetStatus.queued).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    if len(body.content) > 1024:
        raise HTTPException(status_code=400, detail="1024文字を超えています")
    tweet.content = body.content
    db.commit()
    return tweet


@router.delete("/")
def clear_queue(db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Tweet).filter(Tweet.status == TweetStatus.queued).delete()
    db.commit()
    return {"ok": True}
