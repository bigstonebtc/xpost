"""SQLiteでもタイムゾーン付き日時を正しく往復させるためのカスタム型。

SQLiteには本来のタイムゾーン付き日時型が無く、SQLAlchemyの
DateTime(timezone=True) は実質何もしない（保存時にtzinfoを捨て、
読み出し時はナイーブなdatetimeを返す）。これをそのままFastAPIで
JSONにすると、UTCであることを示す "Z"/"+00:00" が付かない文字列
（例: "2026-09-10T05:00:00"）になり、ブラウザ側の new Date(...) が
ローカルタイムと誤解釈して表示時刻がずれる（JSTなら9時間ずれる）。

このTZDateTimeは、書き込み時に必ずUTCへ正規化してから保存し、
読み出し時に明示的にtzinfo=UTCを付与することで、アプリ側からは
常にawareなUTC datetimeとして扱えるようにする。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class TZDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            # 呼び出し側の実装ミスで素通ししてしまわないよう明示的に弾く。
            raise ValueError("naive datetime は保存できません（tzinfo付きにしてください）")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)
