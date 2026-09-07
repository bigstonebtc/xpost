import os
import threading
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.env_file import read_env_file, upsert_env_values
from app.paths import env_conf_path
from app.services.poster import invalidate_client
from app.user_registry import update_user_config_fields

router = APIRouter(prefix="/settings", tags=["apikeys"])

TARGET_KEYS = [
    "X_CONSUMER_KEY",
    "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "ANTHROPIC_API_KEY",
]

_CONFIG_FIELD_MAP = {
    "X_CONSUMER_KEY": "x_consumer_key",
    "X_CONSUMER_SECRET": "x_consumer_secret",
    "X_ACCESS_TOKEN": "x_access_token",
    "X_ACCESS_TOKEN_SECRET": "x_access_token_secret",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
}


def _mask(value: str) -> str:
    return "●" * min(len(value), 12) if value else ""


@router.get("/apikeys")
def get_apikeys(user: str = Depends(get_current_user)):
    env = read_env_file(env_conf_path(user))
    return {k: _mask(env.get(k, "")) for k in TARGET_KEYS}


@router.get("/apikeys/raw")
def get_apikeys_raw(user: str = Depends(get_current_user)):
    env = read_env_file(env_conf_path(user))
    return {k: env.get(k, "") for k in TARGET_KEYS}


class ApiKeyUpdate(BaseModel):
    X_CONSUMER_KEY: Optional[str] = None
    X_CONSUMER_SECRET: Optional[str] = None
    X_ACCESS_TOKEN: Optional[str] = None
    X_ACCESS_TOKEN_SECRET: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None


@router.put("/apikeys")
def update_apikeys(body: ApiKeyUpdate, user: str = Depends(get_current_user)):
    path = env_conf_path(user)
    if not path.exists():
        raise HTTPException(status_code=500, detail="設定ファイルが見つかりません")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"ok": True}

    try:
        upsert_env_values(path, updates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルの書き込みに失敗しました: {e}")

    # ファイルとメモリキャッシュを同時に更新し、backend再起動なしで即時反映する。
    config_updates = {_CONFIG_FIELD_MAP[k]: v for k, v in updates.items()}
    update_user_config_fields(user, **config_updates)
    if any(k != "ANTHROPIC_API_KEY" for k in updates):
        # X APIキーが変わった場合は、古いキーで作られたtweepyクライアントを破棄する
        invalidate_client(user)
    return {"ok": True}


@router.post("/restart")
def restart_app(_=Depends(get_current_user)):
    # backendは全ユーザー共有の単一プロセスのため、この操作は他ユーザーにも影響する
    # （数秒程度の再接続待ちが発生する）。APIキー変更自体はupdate_apikeysで既に
    # 再起動なしで反映されるため、通常はこのエンドポイントを呼ぶ必要はない。
    def _kill():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return {"message": "再起動を開始しました"}
