from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import app_logger
from app.models.posting import PostingSettings
from app.services import posting_mode

router = APIRouter(prefix="/settings/posting", tags=["posting"])

VALID_SCHEDULE_MODES = ("120min", "24h_daytime", "72h", "120h")


class PostingSettingsUpdate(BaseModel):
    daily_schedule_limit: int


class ScheduleModeUpdate(BaseModel):
    schedule_mode: str


def _mode_note() -> str:
    return f"Docker再起動で {posting_mode.get_default_mode()} に戻ります"


@router.get("/")
def get_posting_settings(db: Session = Depends(get_db), _=Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    return {
        "daily_schedule_limit": ps.daily_schedule_limit if ps else 10,
        "schedule_mode": ps.schedule_mode if ps else "120min",
        "posting_mode": posting_mode.get_mode(),
        "default_mode": posting_mode.get_default_mode(),
        "note": _mode_note(),
    }


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


@router.put("/schedule-mode")
def update_schedule_mode(body: ScheduleModeUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if body.schedule_mode not in VALID_SCHEDULE_MODES:
        raise HTTPException(status_code=400, detail="schedule_mode は '120min' / '24h_daytime' / '72h' / '120h' を指定してください")
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ps.schedule_mode = body.schedule_mode
    db.commit()
    return {"ok": True}


class PostingModeUpdate(BaseModel):
    posting_mode: str


@router.get("/mode")
def get_posting_mode(_=Depends(get_current_user)):
    return {
        "posting_mode": posting_mode.get_mode(),
        "default_mode": posting_mode.get_default_mode(),
        "note": _mode_note(),
    }


@router.put("/mode")
def update_posting_mode(body: PostingModeUpdate, _=Depends(get_current_user)):
    if body.posting_mode not in posting_mode.VALID_MODES:
        raise HTTPException(status_code=400, detail="posting_mode は tor または direct を指定してください")

    old_mode = posting_mode.get_mode()
    posting_mode.set_mode(body.posting_mode)
    app_logger.info(
        f"posting_mode changed via UI: from={old_mode} to={body.posting_mode} "
        f"default_mode={posting_mode.get_default_mode()}"
    )

    mode_label = "Tor Mode" if body.posting_mode == "tor" else "Direct Mode"
    return {
        "status": "success",
        "message": f"Posting mode changed to {mode_label}",
        "posting_mode": body.posting_mode,
        "default_mode": posting_mode.get_default_mode(),
        "note": _mode_note(),
    }
