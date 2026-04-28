import tweepy
from app.config import settings

client = tweepy.Client(
    consumer_key=settings.x_consumer_key,
    consumer_secret=settings.x_consumer_secret,
    access_token=settings.x_access_token,
    access_token_secret=settings.x_access_token_secret,
)


def post_tweet(content: str) -> str:
    response = client.create_tweet(text=content)
    return str(response.data["id"])
