from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.utils.rate_limit import get_usage

router = APIRouter(prefix="/rate-limit", tags=["rate-limit"])


@router.get("/usage")
def usage(user: str = Depends(get_current_user)):
    return {
        "anthropic": get_usage(user, "anthropic"),
        "x_api": get_usage(user, "x_api"),
    }
