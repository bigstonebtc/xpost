from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import get_logger
from app.models.posting import PostingSettings
from app.services import posting_mode
from app.services.review import get_review_prompt
from app.services.scheduling import DEFAULT_SCHEDULE_DAYS_AHEAD, SCHEDULE_DAYS_AHEAD_MAX, SCHEDULE_DAYS_AHEAD_MIN

router = APIRouter(prefix="/settings/posting", tags=["posting"])


class PostingSettingsUpdate(BaseModel):
    daily_schedule_limit: int


class ScheduleDaysAheadUpdate(BaseModel):
    # 明日から何日間か（今日は含まない）
    schedule_days_ahead: int


class AllowOver140Update(BaseModel):
    allow_over_140: bool


def _mode_note(user_id: str) -> str:
    return f"Docker再起動で {posting_mode.get_default_mode(user_id)} に戻ります"


@router.get("/")
def get_posting_settings(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    return {
        "daily_schedule_limit": ps.daily_schedule_limit if ps else 10,
        "schedule_days_ahead": ps.schedule_days_ahead if ps else DEFAULT_SCHEDULE_DAYS_AHEAD,
        "allow_over_140": ps.allow_over_140 if ps else True,
        # 有効なレビュー用プロンプト（Schedule 時のレビュー用）。未設定・ファイル削除済みなら None（=「なし」）
        "review_prompt": get_review_prompt(user, ps.review_prompt_file if ps else None),
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


@router.put("/schedule-days-ahead")
def update_schedule_days_ahead(body: ScheduleDaysAheadUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not (SCHEDULE_DAYS_AHEAD_MIN <= body.schedule_days_ahead <= SCHEDULE_DAYS_AHEAD_MAX):
        raise HTTPException(
            status_code=400,
            detail=f"予約範囲は明日から{SCHEDULE_DAYS_AHEAD_MIN}〜{SCHEDULE_DAYS_AHEAD_MAX}日間で指定してください",
        )
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    ps.schedule_days_ahead = body.schedule_days_ahead
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


class ReviewPromptUpdate(BaseModel):
    # None で「なし」
    review_prompt_file: str | None = None


@router.put("/review-prompt")
def update_review_prompt(body: ReviewPromptUpdate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    ps = db.query(PostingSettings).first()
    if not ps:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    review_prompt = None
    if body.review_prompt_file:
        review_prompt = get_review_prompt(user, body.review_prompt_file)
        if not review_prompt:
            raise HTTPException(status_code=404, detail="プロンプトが見つかりません")
    ps.review_prompt_file = review_prompt["filename"] if review_prompt else None
    db.commit()
    get_logger(user, "app").info(f"review_prompt changed via UI: {ps.review_prompt_file}")
    return {"review_prompt": review_prompt}


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
