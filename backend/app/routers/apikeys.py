import os
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["apikeys"])

ENV_PATH = Path("/app/conf/env.conf")
TARGET_KEYS = [
    "X_CONSUMER_KEY",
    "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "ANTHROPIC_API_KEY",
]


def _read_env() -> dict:
    result = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _mask(value: str) -> str:
    return "●" * min(len(value), 12) if value else ""


@router.get("/apikeys")
def get_apikeys(_=Depends(get_current_user)):
    env = _read_env()
    return {k: _mask(env.get(k, "")) for k in TARGET_KEYS}


@router.get("/apikeys/raw")
def get_apikeys_raw(_=Depends(get_current_user)):
    env = _read_env()
    return {k: env.get(k, "") for k in TARGET_KEYS}


class ApiKeyUpdate(BaseModel):
    X_CONSUMER_KEY: Optional[str] = None
    X_CONSUMER_SECRET: Optional[str] = None
    X_ACCESS_TOKEN: Optional[str] = None
    X_ACCESS_TOKEN_SECRET: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None


@router.put("/apikeys")
def update_apikeys(body: ApiKeyUpdate, _=Depends(get_current_user)):
    if not ENV_PATH.exists():
        raise HTTPException(status_code=500, detail="設定ファイルが見つかりません")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"ok": True}

    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = []
        for line in lines:
            key = line.split("=")[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
            else:
                new_lines.append(line)
        ENV_PATH.write_text("".join(new_lines), encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルの書き込みに失敗しました: {e}")


@router.post("/restart")
def restart_app(_=Depends(get_current_user)):
    def _kill():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return {"message": "再起動を開始しました"}
