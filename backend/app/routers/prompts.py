import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user

router = APIRouter(prefix="/prompts", tags=["prompts"])

PROMPTS_DIR = Path("/app/prompts")
DOCUMENTS_DIR = Path("/app/documents")

_VALID_FILENAME = re.compile(r"^[^\\/\x00-\x1f]+\.prompt$")
_UNSAFE_FILENAME_CHARS = re.compile(r"[\\/\x00-\x1f]")
_NAME_LINE = re.compile(r"^name\s*=\s*(.*)$")
_DOCUMENTS_LINE = re.compile(r"^documents\s*=\s*(.*)$")


def _ensure_dirs():
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(name: str) -> str:
    """プロンプト名からファイル名を作る。日本語などはそのまま残し、
    パス区切り文字や制御文字だけを置換する"""
    slug = _UNSAFE_FILENAME_CHARS.sub("_", name.strip())
    slug = slug.strip(" .")
    return slug or "prompt"


def _parse_prompt_file(path: Path) -> dict:
    """name / documents だけを抽出し、それ以外（コメント・topics/types/[prompt]・
    本文）は一切解釈せず生テキスト（body）としてそのまま返す"""
    lines = path.read_text(encoding="utf-8").splitlines()
    name = path.stem
    documents: list[str] = []
    name_idx = None
    documents_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if name_idx is None and (m := _NAME_LINE.match(stripped)):
            name = m.group(1).strip()
            name_idx = i
        elif documents_idx is None and (m := _DOCUMENTS_LINE.match(stripped)):
            documents = [d.strip() for d in m.group(1).split(",") if d.strip()]
            documents_idx = i

    body_lines = [l for i, l in enumerate(lines) if i not in (name_idx, documents_idx)]

    return {
        "filename": path.name,
        "name": name,
        "documents": documents,
        "body": "\n".join(body_lines).strip("\n"),
    }


def _write_prompt_file(path: Path, name: str, documents: list[str], body: str):
    docs_str = ", ".join(documents)
    header = f"name = {name}\ndocuments = {docs_str}\n"
    path.write_text(header + "\n" + body.strip("\n") + "\n", encoding="utf-8")


class PromptCreate(BaseModel):
    name: str
    documents: list[str] = []
    body: str


class PromptUpdate(BaseModel):
    name: str
    documents: list[str] = []
    body: str


@router.get("/")
def list_prompts(_=Depends(get_current_user)):
    _ensure_dirs()
    result = []
    for p in sorted(PROMPTS_DIR.glob("*.prompt")):
        try:
            result.append(_parse_prompt_file(p))
        except Exception:
            pass
    return result


@router.get("/{filename}")
def get_prompt(filename: str, _=Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")
    return _parse_prompt_file(path)


@router.post("/", status_code=201)
def create_prompt(payload: PromptCreate, _=Depends(get_current_user)):
    _ensure_dirs()
    if not payload.name or len(payload.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    filename = _slugify(payload.name) + ".prompt"
    path = PROMPTS_DIR / filename
    if path.exists():
        raise HTTPException(status_code=409, detail=f"{filename} は既に存在します")

    _write_prompt_file(path, payload.name, payload.documents, payload.body)
    return _parse_prompt_file(path)


@router.put("/{filename}")
def update_prompt(filename: str, payload: PromptUpdate, _=Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    if not payload.name or len(payload.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")

    _write_prompt_file(path, payload.name, payload.documents, payload.body)
    return _parse_prompt_file(path)


@router.delete("/{filename}", status_code=204)
def delete_prompt(filename: str, _=Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")
    path.unlink()


@router.get("/documents/list")
def list_documents(_=Depends(get_current_user)):
    _ensure_dirs()
    files = [f.name for f in sorted(DOCUMENTS_DIR.iterdir()) if f.is_file()]
    return {"documents": files}
