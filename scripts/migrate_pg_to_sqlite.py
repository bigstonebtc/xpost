#!/usr/bin/env python3
"""既存の単一ユーザー版（PostgreSQL）のデータを、共有プログラムモードの
ユーザー個別SQLiteファイルへ移行する。

前提: 実行前に必ず `pg_dump` 等でPostgreSQL側のバックアップを取得しておくこと。
本スクリプトはPostgreSQL側を読み取るのみで変更しない（非破壊）。

使い方:
  pip install psycopg2-binary   # このスクリプト専用。アプリ本体の依存には含めない
  python3 migrate_pg_to_sqlite.py \\
      --pg-url postgresql://xpost:changeme@localhost:5432/xpost \\
      --sqlite-path /home/claude/xpost/db/queue.sqlite

詳細はdocs/multi_user_design.md 12章参照。
"""
import argparse
import sys
from pathlib import Path

# backend/app のモデル定義を再利用する
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models.news import NewsSource, FetchSchedule, NewsSettings, NewsItem  # noqa: E402
from app.models.tweet import Tweet  # noqa: E402
from app.models.posting import PostingSettings  # noqa: E402

# FK依存関係を満たす順序（参照される側を先に移行する）
MODELS_IN_ORDER = [NewsSource, FetchSchedule, NewsSettings, PostingSettings, NewsItem, Tweet]


def migrate(pg_url: str, sqlite_path: str) -> None:
    sqlite_file = Path(sqlite_path)
    sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    pg_engine = create_engine(pg_url)
    sqlite_engine = create_engine(f"sqlite:///{sqlite_file}")
    Base.metadata.create_all(bind=sqlite_engine)

    PgSession = sessionmaker(bind=pg_engine)
    SqliteSession = sessionmaker(bind=sqlite_engine)

    with PgSession() as src, SqliteSession() as dst:
        for model in MODELS_IN_ORDER:
            rows = src.query(model).order_by(model.id).all()
            skipped = 0
            for row in rows:
                data = {c.name: getattr(row, c.name) for c in model.__table__.columns}
                try:
                    dst.merge(model(**data))
                except Exception as e:
                    skipped += 1
                    print(f"  警告: {model.__tablename__} id={data.get('id')} をスキップ: {e}")
            dst.commit()
            msg = f"{model.__tablename__}: {len(rows)}件移行"
            if skipped:
                msg += f"（{skipped}件スキップ）"
            print(msg)

    print("移行完了。SQLite経由でアプリを起動し、キュー・履歴が正しく表示されることを確認してください。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pg-url", required=True, help="移行元PostgreSQLのURL（例: postgresql://user:pass@host:5432/db）")
    parser.add_argument("--sqlite-path", required=True, help="移行先SQLiteファイルパス（例: /home/claude/xpost/db/queue.sqlite）")
    args = parser.parse_args()

    migrate(args.pg_url, args.sqlite_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
