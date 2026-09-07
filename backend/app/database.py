from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from fastapi import Depends

from app.dependencies import get_current_user
from app.paths import db_path


class Base(DeclarativeBase):
    pass


# user_id ごとに独立したSQLiteファイル・engine・sessionmakerを持つ（完全隔離）。
# 1ユーザーにつき1回だけ生成し、以降はプロセス内でキャッシュする。
_engines: dict[str, Engine] = {}
_sessionmakers: dict[str, sessionmaker] = {}


def get_engine(user_id: str) -> Engine:
    engine = _engines.get(user_id)
    if engine is not None:
        return engine

    path = db_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as conn:
        # 読み取りと書き込みの同時実行性を上げる（ユーザーごとに別ファイルなので
        # 他ユーザーへの影響はない）。
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    _engines[user_id] = engine
    _sessionmakers[user_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


def get_sessionmaker(user_id: str) -> sessionmaker:
    if user_id not in _sessionmakers:
        get_engine(user_id)
    return _sessionmakers[user_id]


def session_for(user_id: str) -> Session:
    """FastAPIのDependsを経由しない場所（スケジューラのバックグラウンドジョブ等）
    から、そのユーザーのDBセッションを直接取得する。呼び出し元でclose()すること。"""
    return get_sessionmaker(user_id)()


def get_db(user_id: str = Depends(get_current_user)):
    db = get_sessionmaker(user_id)()
    try:
        yield db
    finally:
        db.close()
