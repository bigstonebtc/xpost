"""ユーザーごとに隔離されたファイル領域のパス解決。

共有プログラムモードでは backend は単一プロセスで全ユーザーを処理する。
ユーザーの隔離は「/home/<user>/xpost/ 以下だけを見る」という規約で実現しており、
本モジュールはその規約を1箇所にまとめる。
"""
import os
from pathlib import Path

# ホスト側の /home をコンテナにそのままマウントする前提（docker-compose.yml参照）。
# ローカル開発など /home 以外を使いたい場合は環境変数で上書きできる。
HOME_ROOT = Path(os.environ.get("XPOST_HOME_ROOT", "/home"))


def user_root(user_id: str) -> Path:
    return HOME_ROOT / user_id / "xpost"


def conf_dir(user_id: str) -> Path:
    return user_root(user_id) / "conf"


def env_conf_path(user_id: str) -> Path:
    return conf_dir(user_id) / "env.conf"


def relevance_prompt_path(user_id: str) -> Path:
    return conf_dir(user_id) / "prompts" / "relevance.conf"


def prompts_dir(user_id: str) -> Path:
    return user_root(user_id) / "prompts"


def documents_dir(user_id: str) -> Path:
    return user_root(user_id) / "documents"


def logs_dir(user_id: str) -> Path:
    return user_root(user_id) / "logs"


def db_path(user_id: str) -> Path:
    return user_root(user_id) / "db" / "queue.sqlite"


def all_user_ids() -> list[str]:
    """/home/<user>/xpost/conf/env.conf が存在するユーザー名の一覧を返す。"""
    if not HOME_ROOT.exists():
        return []
    return sorted(
        p.parent.parent.parent.name
        for p in HOME_ROOT.glob("*/xpost/conf/env.conf")
    )
