from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(50))
    is_enabled = Column(Boolean, default=True)
    is_preset = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FetchSchedule(Base):
    __tablename__ = "fetch_schedules"

    id = Column(Integer, primary_key=True, index=True)
    slot_number = Column(Integer, nullable=False)
    hour = Column(Integer, nullable=False)
    is_enabled = Column(Boolean, default=True)


class NewsSettings(Base):
    __tablename__ = "news_settings"

    id = Column(Integer, primary_key=True, index=True)
    fetch_limit_per_run = Column(Integer, default=20)
    schedule_mode = Column(String(20), default="120min")
    news_prompt_file = Column(String(255), default="news_comment.prompt")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    summary = Column(Text)
    source_id = Column(Integer, ForeignKey("news_sources.id"))
    published_at = Column(DateTime(timezone=True))
    ai_relevant = Column(Boolean)
    tweet_text = Column(Text)
    status = Column(String(20), default="pending")  # pending / queued / skipped
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
