from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.posting import PostingSettings

router = APIRouter(prefix="/settings/posting", tags=["posting"])


class PostingSettingsUpdate(BaseModel):
    daily_schedule_limit: int


@router.get("/")
def get_posting_settings(db: Session = Depends(get_db), _=Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    if not ps:
        return {"daily_schedule_limit": 10}
    return {"daily_schedule_limit": ps.daily_schedule_limit}


@router.put("/")
def update_posting_settings(body: PostingSettingsUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if body.daily_schedule_limit < 1:
        raise HTTPException(status_code=400, detail="1以上の整数を入力してください")
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ps.daily_schedule_limit = body.daily_schedule_limit
    db.commit()
    return {"ok": True}
