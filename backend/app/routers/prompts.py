import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.paths import documents_dir, prompts_dir

router = APIRouter(prefix="/prompts", tags=["prompts"])

_VALID_FILENAME = re.compile(r"^[^\\/\x00-\x1f]+\.prompt$")
_UNSAFE_FILENAME_CHARS = re.compile(r"[\\/\x00-\x1f]")
_NAME_LINE = re.compile(r"^name\s*=\s*(.*)$")
_DOCUMENTS_LINE = re.compile(r"^documents\s*=\s*(.*)$")
_VISIBLE_LINE = re.compile(r"^visible\s*=\s*(.*)$")


def _ensure_dirs(user_id: str):
    prompts_dir(user_id).mkdir(parents=True, exist_ok=True)
    documents_dir(user_id).mkdir(parents=True, exist_ok=True)


def _slugify(name: str) -> str:
    """プロンプト名からファイル名を作る。日本語などはそのまま残し、
    パス区切り文字や制御文字だけを置換する"""
    slug = _UNSAFE_FILENAME_CHARS.sub("_", name.strip())
    slug = slug.strip(" .")
    return slug or "prompt"


def _parse_prompt_file(path: Path) -> dict:
    """name / documents / visible だけを抽出し、それ以外（コメント・topics/types/
    [prompt]・本文）は一切解釈せず生テキスト（body）としてそのまま返す"""
    lines = path.read_text(encoding="utf-8").splitlines()
    name = path.stem
    documents: list[str] = []
    visible = True
    name_idx = None
    documents_idx = None
    visible_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if name_idx is None and (m := _NAME_LINE.match(stripped)):
            name = m.group(1).strip()
            name_idx = i
        elif documents_idx is None and (m := _DOCUMENTS_LINE.match(stripped)):
            documents = [d.strip() for d in m.group(1).split(",") if d.strip()]
            documents_idx = i
        elif visible_idx is None and (m := _VISIBLE_LINE.match(stripped)):
            visible = m.group(1).strip().lower() != "false"
            visible_idx = i

    body_lines = [l for i, l in enumerate(lines) if i not in (name_idx, documents_idx, visible_idx)]

    return {
        "filename": path.name,
        "name": name,
        "documents": documents,
        "visible": visible,
        "body": "\n".join(body_lines).strip("\n"),
    }


def _write_prompt_file(path: Path, name: str, documents: list[str], visible: bool, body: str):
    docs_str = ", ".join(documents)
    header = f"name = {name}\ndocuments = {docs_str}\nvisible = {'true' if visible else 'false'}\n"
    path.write_text(header + "\n" + body.strip("\n") + "\n", encoding="utf-8")


class PromptCreate(BaseModel):
    name: str
    documents: list[str] = []
    visible: bool = True
    body: str


class PromptUpdate(BaseModel):
    name: str
    documents: list[str] = []
    visible: bool = True
    body: str


@router.get("/")
def list_prompts(visible_only: bool = False, user: str = Depends(get_current_user)):
    _ensure_dirs(user)
    result = []
    for p in sorted(prompts_dir(user).glob("*.prompt")):
        try:
            result.append(_parse_prompt_file(p))
        except Exception:
            pass
    if visible_only:
        result = [p for p in result if p["visible"]]
    return result


@router.get("/{filename}")
def get_prompt(filename: str, user: str = Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    path = prompts_dir(user) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")
    return _parse_prompt_file(path)


@router.post("/", status_code=201)
def create_prompt(payload: PromptCreate, user: str = Depends(get_current_user)):
    _ensure_dirs(user)
    if not payload.name or len(payload.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    filename = _slugify(payload.name) + ".prompt"
    path = prompts_dir(user) / filename
    if path.exists():
        raise HTTPException(status_code=409, detail=f"{filename} は既に存在します")

    _write_prompt_file(path, payload.name, payload.documents, payload.visible, payload.body)
    return _parse_prompt_file(path)


@router.put("/{filename}")
def update_prompt(filename: str, payload: PromptUpdate, user: str = Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    if not payload.name or len(payload.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    path = prompts_dir(user) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")

    _write_prompt_file(path, payload.name, payload.documents, payload.visible, payload.body)
    return _parse_prompt_file(path)


@router.delete("/{filename}", status_code=204)
def delete_prompt(filename: str, user: str = Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    path = prompts_dir(user) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")
    path.unlink()


@router.get("/documents/list")
def list_documents(user: str = Depends(get_current_user)):
    _ensure_dirs(user)
    files = [f.name for f in sorted(documents_dir(user).iterdir()) if f.is_file()]
    return {"documents": files}
