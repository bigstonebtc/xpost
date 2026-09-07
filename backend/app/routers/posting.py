from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import get_logger
from app.models.posting import PostingSettings
from app.services import posting_mode

router = APIRouter(prefix="/settings/posting", tags=["posting"])

SCHEDULE_HOURS_MIN = 24
SCHEDULE_HOURS_MAX = 720


class PostingSettingsUpdate(BaseModel):
    daily_schedule_limit: int


class ScheduleHoursUpdate(BaseModel):
    schedule_hours: int


class AllowOver140Update(BaseModel):
    allow_over_140: bool


def _mode_note(user_id: str) -> str:
    return f"Docker再起動で {posting_mode.get_default_mode(user_id)} に戻ります"


@router.get("/")
def get_posting_settings(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    return {
        "daily_schedule_limit": ps.daily_schedule_limit if ps else 10,
        "schedule_hours": ps.schedule_hours if ps else 24,
        "allow_over_140": ps.allow_over_140 if ps else True,
        "posting_mode": posting_mode.get_mode(user),
        "default_mode": posting_mode.get_default_mode(user),
        "note": _mode_note(user),
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


@router.put("/schedule-hours")
def update_schedule_hours(body: ScheduleHoursUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not (SCHEDULE_HOURS_MIN <= body.schedule_hours <= SCHEDULE_HOURS_MAX):
        raise HTTPException(status_code=400, detail=f"schedule_hours は{SCHEDULE_HOURS_MIN}〜{SCHEDULE_HOURS_MAX}の整数で指定してください")
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ps.schedule_hours = body.schedule_hours
    db.commit()
    return {"ok": True}


@router.put("/allow-over-140")
def update_allow_over_140(body: AllowOver140Update, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ps.allow_over_140 = body.allow_over_140
    db.commit()
    return {"ok": True}


class PostingModeUpdate(BaseModel):
    posting_mode: str


@router.get("/mode")
def get_posting_mode(user: str = Depends(get_current_user)):
    return {
        "posting_mode": posting_mode.get_mode(user),
        "default_mode": posting_mode.get_default_mode(user),
        "note": _mode_note(user),
    }


@router.put("/mode")
def update_posting_mode(body: PostingModeUpdate, user: str = Depends(get_current_user)):
    if body.posting_mode not in posting_mode.VALID_MODES:
        raise HTTPException(status_code=400, detail="posting_mode は tor または direct を指定してください")

    old_mode = posting_mode.get_mode(user)
    posting_mode.set_mode(user, body.posting_mode)
    get_logger(user, "app").info(
        f"posting_mode changed via UI: from={old_mode} to={body.posting_mode} "
        f"default_mode={posting_mode.get_default_mode(user)}"
    )

    mode_label = "Tor Mode" if body.posting_mode == "tor" else "Direct Mode"
    return {
        "status": "success",
        "message": f"Posting mode changed to {mode_label}",
        "posting_mode": body.posting_mode,
        "default_mode": posting_mode.get_default_mode(user),
        "note": _mode_note(user),
    }
