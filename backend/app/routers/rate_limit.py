from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.utils.rate_limit import get_usage

router = APIRouter(prefix="/rate-limit", tags=["rate-limit"])


@router.get("/usage")
def usage(_=Depends(get_current_user)):
    return {
        "anthropic": get_usage("anthropic"),
        "x_api": get_usage("x_api"),
    }
