from sqlalchemy import Column, Integer, Text
from sqlalchemy.sql import func
from app.database import Base
from app.db_types import TZDateTime


class FixedTweet(Base):
    __tablename__ = "fixed_tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    last_used_at = Column(TZDateTime(), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    created_at = Column(TZDateTime(), server_default=func.now())
    updated_at = Column(TZDateTime(), onupdate=func.now())
