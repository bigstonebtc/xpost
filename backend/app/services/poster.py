import time
from pathlib import Path

import tweepy

from app.config import settings
from app.logger import posting_logger as logger

client = tweepy.Client(
    consumer_key=settings.x_consumer_key,
    consumer_secret=settings.x_consumer_secret,
    access_token=settings.x_access_token,
    access_token_secret=settings.x_access_token_secret,
)

_auth_v1 = tweepy.OAuth1UserHandler(
    settings.x_consumer_key,
    settings.x_consumer_secret,
    settings.x_access_token,
    settings.x_access_token_secret,
)
api_v1 = tweepy.API(_auth_v1)


def post_tweet(content: str, image_path: str = None) -> str:
    t0 = time.monotonic()
    try:
        media_ids = None
        if image_path and Path(image_path).exists():
            media = api_v1.media_upload(filename=image_path)
            media_ids = [str(media.media_id)]
        response = client.create_tweet(text=content, media_ids=media_ids)
        x_id = str(response.data["id"])
        elapsed = time.monotonic() - t0
        logger.info(f"posted x_tweet_id={x_id} in {elapsed:.1f}s")
        return x_id
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error(f"X API post failed after {elapsed:.1f}s: {e}")
        raise
