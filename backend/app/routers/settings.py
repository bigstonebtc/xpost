from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_current_user
from app.models.news import NewsSource, FetchSchedule, NewsKeyword

router = APIRouter(prefix="/settings/news", tags=["settings"])


class SourceUpdate(BaseModel):
    is_enabled: bool


class ScheduleSlot(BaseModel):
    slot_number: int
    hour: int
    is_enabled: bool


class ScheduleUpdate(BaseModel):
    slots: list[ScheduleSlot]


class KeywordCreate(BaseModel):
    keyword: str
    type: str  # 'include' or 'exclude'


@router.get("/")
def get_news_settings(db: Session = Depends(get_db), _=Depends(get_current_user)):
    sources = db.query(NewsSource).order_by(NewsSource.id).all()
    schedules = db.query(FetchSchedule).order_by(FetchSchedule.slot_number).all()
    keywords = db.query(NewsKeyword).order_by(NewsKeyword.type, NewsKeyword.id).all()
    return {
        "sources": sources,
        "schedules": schedules,
        "keywords": keywords,
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


@router.post("/keywords")
def add_keyword(body: KeywordCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if body.type not in ("include", "exclude"):
        raise HTTPException(status_code=400, detail="type は include または exclude")
    kw = NewsKeyword(keyword=body.keyword.strip(), type=body.type)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    kw = db.query(NewsKeyword).filter(NewsKeyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="キーワードが見つかりません")
    db.delete(kw)
    db.commit()
    return {"ok": True}
