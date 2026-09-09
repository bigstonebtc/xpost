from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.env_file import upsert_env_values
from app.paths import env_conf_path
from app.user_registry import get_user_config, update_user_config_fields

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(user_id: str, secret_key: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, secret_key, algorithm=ALGORITHM)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    cfg = get_user_config(form_data.username)
    # 存在しないユーザー名でもパスワード不一致と同じエラーにする（ユーザー列挙対策）。
    # bcryptハッシュはダミー値を検証してタイミングをある程度均す。
    hash_to_check = cfg.admin_password_hash if cfg else pwd_context.hash("dummy-for-timing")
    password_ok = pwd_context.verify(form_data.password, hash_to_check)

    if cfg is None or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証失敗")

    token = create_access_token(cfg.user_id, cfg.secret_key)
    return {"access_token": token, "token_type": "bearer"}


class PasswordChange(BaseModel):
    new_password: str
    new_password_confirm: str


@router.put("/password")
def change_password(body: PasswordChange, user: str = Depends(get_current_user)):
    if body.new_password != body.new_password_confirm:
        raise HTTPException(status_code=400, detail="新しいパスワードが一致しません")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="パスワードは8文字以上にしてください")

    new_hash = pwd_context.hash(body.new_password)
    try:
        upsert_env_values(env_conf_path(user), {"ADMIN_PASSWORD_HASH": new_hash})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定ファイルの更新に失敗しました: {e}")

    # ファイルとメモリキャッシュを同時に更新し、backend再起動なしで即時反映する。
    # 発行済みJWTはsecret_keyを変えていないため引き続き有効（次回ログインから新パスワードが有効）。
    update_user_config_fields(user, admin_password_hash=new_hash)
    return {"ok": True}
