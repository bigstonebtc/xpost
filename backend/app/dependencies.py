from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.user_registry import get_user_config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ALGORITHM = "HS256"


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """JWTを検証してuser_id(username)を返す。

    ユーザーごとに署名鍵(secret_key)が異なるため、検証前にどのユーザーの鍵を
    試すべきか分からない。そこで以下の2段階で検証する：
      1. 署名検証なしでpayloadだけを覗き、sub(ユーザー名候補)を取り出す
         → これは「どの鍵を試すか」の索引としてのみ使い、認可判断には使わない
      2. 候補ユーザーのsecret_keyで、署名・有効期限を含めて改めて検証する
         → ここで検証に成功したpayloadのsubだけを信頼する
    偽トークンで他人のsubを名乗っても、正しいsecret_keyで署名されていない限り
    手順2で必ず失敗する。
    """
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        unverified = jwt.get_unverified_claims(token)
    except JWTError:
        raise unauthorized

    candidate_user = unverified.get("sub")
    if not candidate_user:
        raise unauthorized

    cfg = get_user_config(candidate_user)
    if cfg is None:
        raise unauthorized

    try:
        payload = jwt.decode(token, cfg.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise unauthorized

    verified_user = payload.get("sub")
    if verified_user != candidate_user:
        raise unauthorized

    return verified_user


def require_legacy_news_enabled(user: str = Depends(get_current_user)) -> None:
    cfg = get_user_config(user)
    if cfg is None or not cfg.legacy_news_feature_enabled:
        raise HTTPException(status_code=404, detail="旧ニュース機能は無効化されています")
