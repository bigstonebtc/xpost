from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.services.conf_parser import DOCUMENTS_DIR

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
def list_documents(_=Depends(get_current_user)):
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return [f.name for f in sorted(DOCUMENTS_DIR.iterdir()) if f.is_file()]
