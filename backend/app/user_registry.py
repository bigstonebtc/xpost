"""全ユーザーの設定（env.conf）をプロセス起動時にメモリへキャッシュする。

共有プログラムモードの前提：
- backend は単一プロセスで全ユーザーを処理する
- 各ユーザーの設定は /home/<user>/xpost/conf/env.conf にあり、起動時に一括読み込みする
- リクエスト時はこのメモリキャッシュから取得する（ファイルI/Oゼロ）
- 新規ユーザー追加は backend 再起動が必要（このモジュールの再読み込みが必要なため）
- パスワード変更・APIキー変更は、ファイル更新と同時に users_config のキャッシュも
  更新することで、再起動なしに即時反映する（update_user_config_fields）
"""
from typing import Optional

from pydantic import BaseModel

from app.env_file import read_env_file
from app.paths import HOME_ROOT, env_conf_path


class UserConfig(BaseModel):
    user_id: str

    x_consumer_key: str = ""
    x_consumer_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    x_bearer_token: str = ""

    anthropic_api_key: str = ""

    legacy_news_feature_enabled: bool = False

    posting_mode: str = "tor"
    tor_proxy: str = "socks5h://tor:9050"
    tor_timeout: int = 60

    # setup_user.sh が自動生成するフィールド
    admin_password_hash: str
    secret_key: str


# user_id -> UserConfig。プロセス起動時に load_all_users() で構築する。
users_config: dict[str, UserConfig] = {}


def _to_bool(value: str, default: bool) -> bool:
    if not value:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_user_config(user_id: str) -> UserConfig:
    path = env_conf_path(user_id)
    raw = read_env_file(path)

    admin_password_hash = raw.get("ADMIN_PASSWORD_HASH", "")
    secret_key = raw.get("SECRET_KEY", "")
    if not admin_password_hash or not secret_key:
        raise ValueError(
            "ADMIN_PASSWORD_HASH / SECRET_KEY が env.conf にありません"
            "（setup_user.sh の実行が必要です）"
        )

    return UserConfig(
        user_id=user_id,
        x_consumer_key=raw.get("X_CONSUMER_KEY", ""),
        x_consumer_secret=raw.get("X_CONSUMER_SECRET", ""),
        x_access_token=raw.get("X_ACCESS_TOKEN", ""),
        x_access_token_secret=raw.get("X_ACCESS_TOKEN_SECRET", ""),
        x_bearer_token=raw.get("X_BEARER_TOKEN", ""),
        anthropic_api_key=raw.get("ANTHROPIC_API_KEY", ""),
        legacy_news_feature_enabled=_to_bool(raw.get("LEGACY_NEWS_FEATURE_ENABLED", ""), False),
        posting_mode=raw.get("POSTING_MODE") or "tor",
        tor_proxy=raw.get("TOR_PROXY") or "socks5h://tor:9050",
        tor_timeout=_to_int(raw.get("TOR_TIMEOUT", ""), 60),
        admin_password_hash=admin_password_hash,
        secret_key=secret_key,
    )


def load_all_users() -> list[str]:
    """/home/*/xpost/conf/env.conf を全て読み込み、users_config を再構築する。
    個別ユーザーの読み込みに失敗しても他ユーザーの起動は止めない。
    戻り値：読み込みに成功したuser_idのリスト。"""
    users_config.clear()
    if not HOME_ROOT.exists():
        return []

    loaded = []
    for env_path in sorted(HOME_ROOT.glob("*/xpost/conf/env.conf")):
        user_id = env_path.parent.parent.parent.name
        try:
            users_config[user_id] = load_user_config(user_id)
            loaded.append(user_id)
        except Exception:
            # 個別ユーザーの設定不備で全体の起動を止めない。
            # 呼び出し元（main.py）でログ出力する。
            continue
    return loaded


def get_user_config(user_id: str) -> Optional[UserConfig]:
    return users_config.get(user_id)


def update_user_config_fields(user_id: str, **fields) -> None:
    """メモリキャッシュのみ更新する（env.confファイルへの反映は呼び出し元の責務）。
    パスワード変更・APIキー変更をbackend再起動なしで即時反映するために使う。"""
    cfg = users_config.get(user_id)
    if cfg is None:
        return
    users_config[user_id] = cfg.model_copy(update=fields)
