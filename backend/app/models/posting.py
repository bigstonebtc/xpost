from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base


class PostingSettings(Base):
    __tablename__ = "posting_settings"

    id = Column(Integer, primary_key=True)
    daily_schedule_limit = Column(Integer, default=10, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
