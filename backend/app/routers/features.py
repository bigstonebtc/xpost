from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.user_registry import get_user_config

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/")
def get_features(user: str = Depends(get_current_user)):
    cfg = get_user_config(user)
    return {"legacy_news_enabled": bool(cfg and cfg.legacy_news_feature_enabled)}
