from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
import enum


class TweetStatus(str, enum.Enum):
    queued = "queued"
    scheduled = "scheduled"
    posted = "posted"
    discarded = "discarded"


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(1024), nullable=False)
    status = Column(SAEnum(TweetStatus), default=TweetStatus.queued, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    x_tweet_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    source_type = Column(String(20), default="manual", nullable=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    image_path = Column(String(500), nullable=True)
