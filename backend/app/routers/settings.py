from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_current_user
from app.models.news import NewsSource, FetchSchedule, NewsSettings

router = APIRouter(prefix="/settings/news", tags=["settings"])


class SourceUpdate(BaseModel):
    is_enabled: bool


class ScheduleSlot(BaseModel):
    slot_number: int
    hour: int
    is_enabled: bool


class ScheduleUpdate(BaseModel):
    slots: list[ScheduleSlot]


class GeneralUpdate(BaseModel):
    fetch_limit_per_run: int
    relevance_prompt: str
    news_prompt_file: str = "news_comment.prompt"


@router.get("/")
def get_news_settings(db: Session = Depends(get_db), _=Depends(get_current_user)):
    sources = db.query(NewsSource).order_by(NewsSource.id).all()
    schedules = db.query(FetchSchedule).order_by(FetchSchedule.slot_number).all()
    ns = db.query(NewsSettings).first()
    return {
        "sources": sources,
        "schedules": schedules,
        "general": ns,
    }


@router.put("/sources/{source_id}")
def update_source(source_id: int, body: SourceUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="ソースが見つかりません")
    source.is_enabled = body.is_enabled
    db.commit()
    return {"ok": True}


@router.put("/schedule")
def update_schedule(body: ScheduleUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.services.scheduler import reload_news_fetch_jobs

    for slot_data in body.slots:
        slot = db.query(FetchSchedule).filter(FetchSchedule.slot_number == slot_data.slot_number).first()
        if not slot:
            raise HTTPException(status_code=404, detail=f"スロット {slot_data.slot_number} が見つかりません")
        slot.hour = slot_data.hour
        slot.is_enabled = slot_data.is_enabled
    db.commit()
    reload_news_fetch_jobs()
    return {"ok": True}


@router.put("/general")
def update_general(body: GeneralUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if "{title}" not in body.relevance_prompt or "{summary}" not in body.relevance_prompt:
        raise HTTPException(status_code=400, detail="{title} と {summary} のプレースホルダーが必要です")
    if body.fetch_limit_per_run not in (20, 50, 100):
        raise HTTPException(status_code=400, detail="取得件数上限は 20 / 50 / 100 から選択してください")
    if not body.news_prompt_file.endswith(".prompt"):
        raise HTTPException(status_code=400, detail="news_prompt_file は .prompt 拡張子のファイル名を指定してください")

    ns = db.query(NewsSettings).first()
    if not ns:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ns.fetch_limit_per_run = body.fetch_limit_per_run
    ns.relevance_prompt = body.relevance_prompt
    ns.news_prompt_file = body.news_prompt_file
    db.commit()
    return {"ok": True}
