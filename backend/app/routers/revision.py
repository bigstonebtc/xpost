from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.writer import rewrite_tweet
from app.utils.rate_limit import RateLimitExceeded, format_message

router = APIRouter(prefix="/revision", tags=["revision"])


class RewriteRequest(BaseModel):
    text: str
    prompt_id: str


@router.post("/rewrite")
def rewrite(body: RewriteRequest, user: str = Depends(get_current_user)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="テキストを入力してください")

    try:
        rewritten = rewrite_tweet(user, body.text, prompt_file=body.prompt_id)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=format_message(e.api_type, e.reset_at))

    return {"original": body.text, "rewritten": rewritten, "status": "success"}
