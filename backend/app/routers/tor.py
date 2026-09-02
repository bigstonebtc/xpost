from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.logger import app_logger
from app.services import tor as tor_service

router = APIRouter(prefix="/tor", tags=["tor"])


@router.get("/status")
def get_tor_status(_=Depends(get_current_user)):
    return tor_service.check_status()


@router.post("/restart")
def restart_tor(_=Depends(get_current_user)):
    try:
        return tor_service.restart_tor_container()
    except Exception as e:
        app_logger.error(f"Tor再起動に失敗しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tor再起動に失敗しました: {e}")
