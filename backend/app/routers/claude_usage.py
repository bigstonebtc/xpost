from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.claude_usage import get_claude_stats, get_pricing_config, update_pricing_config

router = APIRouter(prefix="/claude", tags=["claude"])


@router.get("/stats")
def stats(user: str = Depends(get_current_user)):
    return get_claude_stats(user)


@router.get("/pricing")
def get_pricing(user: str = Depends(get_current_user)):
    return get_pricing_config(user)


class PricingUpdate(BaseModel):
    claude_input_tokens_price: float
    claude_output_tokens_price: float


@router.put("/pricing")
def update_pricing(body: PricingUpdate, user: str = Depends(get_current_user)):
    if body.claude_input_tokens_price < 0 or body.claude_output_tokens_price < 0:
        raise HTTPException(status_code=400, detail="料金は0以上で指定してください")
    return update_pricing_config(user, body.claude_input_tokens_price, body.claude_output_tokens_price)
