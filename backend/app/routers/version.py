from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.version import get_history, get_version

router = APIRouter(prefix="/version", tags=["version"])


@router.get("/")
def version(_=Depends(get_current_user)):
    return get_version()


@router.get("/history")
def history(_=Depends(get_current_user)):
    items = get_history()
    return {"available": items is not None, "items": items or []}
