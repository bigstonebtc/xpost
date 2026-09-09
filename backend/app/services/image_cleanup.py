"""どのツイートからも参照されていない添付画像ファイルを削除する。

通常のライフサイクル（投稿成功・破棄・差し替え・明示削除）では画像は
その場で即座に削除されるため、本来ここで拾うものはほぼ無いはずだが、
何らかの理由（処理中のクラッシュ等）で削除が漏れた孤児ファイルの
掃除用に、backend起動時に保険として実行する。
"""
from app.database import session_for
from app.logger import system_logger
from app.paths import images_dir
from app.user_registry import users_config


def cleanup_orphaned_images() -> None:
    from app.models.tweet import Tweet

    for user_id in users_config:
        user_dir = images_dir(user_id)
        if not user_dir.exists():
            continue
        db = session_for(user_id)
        try:
            referenced = {
                row[0] for row in db.query(Tweet.image_path).filter(Tweet.image_path.isnot(None)).all()
            }
        finally:
            db.close()
        for f in user_dir.iterdir():
            if f.is_file() and str(f) not in referenced:
                f.unlink(missing_ok=True)
                system_logger.info(f"user={user_id} 未参照の画像を削除: {f.name}")
