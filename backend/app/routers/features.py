from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/")
def get_features(_=Depends(get_current_user)):
    return {"legacy_news_enabled": settings.legacy_news_feature_enabled}
