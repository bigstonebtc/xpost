from sqlalchemy import Column, Integer, Boolean
from sqlalchemy.sql import func
from app.database import Base
from app.db_types import TZDateTime


class PostingSettings(Base):
    __tablename__ = "posting_settings"

    id = Column(Integer, primary_key=True)
    daily_schedule_limit = Column(Integer, default=10, nullable=False)
    schedule_hours = Column(Integer, default=120, nullable=False)
    allow_over_140 = Column(Boolean, default=True, nullable=False)
    updated_at = Column(TZDateTime(), onupdate=func.now())
