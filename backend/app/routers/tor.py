from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.logger import system_logger
from app.services import tor as tor_service
from app.user_registry import get_user_config

router = APIRouter(prefix="/tor", tags=["tor"])


@router.get("/status")
def get_tor_status(user: str = Depends(get_current_user)):
    cfg = get_user_config(user)
    return tor_service.check_status(cfg.tor_proxy, cfg.tor_timeout)


@router.post("/restart")
def restart_tor(user: str = Depends(get_current_user)):
    cfg = get_user_config(user)
    try:
        tor_service.restart_tor_container()
        return tor_service.check_status(cfg.tor_proxy, cfg.tor_timeout)
    except Exception as e:
        system_logger.error(f"Tor再起動に失敗しました（要求者: user={user}）: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tor再起動に失敗しました: {e}")
