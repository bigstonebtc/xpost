import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user

router = APIRouter(prefix="/prompts", tags=["prompts"])

PROMPTS_DIR = Path("/app/prompts")
DOCUMENTS_DIR = Path("/app/documents")

_VALID_FILENAME = re.compile(r"^[a-zA-Z0-9_]+\.prompt$")


def _ensure_dirs():
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _parse_multiline_field(lines: list[str]) -> str:
    """インデントされた続き行を結合して返す（空行・#コメントはスキップ）"""
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            result.append(stripped)
    return "\n".join(result)


def _parse_prompt_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    documents = []
    topics_lines = []
    types_lines = []
    body_lines = []

    # パース状態: header / topics / types / prompt
    state = "header"

    for line in text.splitlines():
        if state == "prompt":
            body_lines.append(line)
            continue

        stripped = line.strip()

        if stripped.startswith("[prompt]"):
            state = "prompt"
            continue

        # 継続行（インデントあり）は現在のマルチライン状態に追加
        if line.startswith(" ") or line.startswith("\t"):
            if state == "topics":
                if stripped and not stripped.startswith("#"):
                    topics_lines.append(stripped)
            elif state == "types":
                if stripped and not stripped.startswith("#"):
                    types_lines.append(stripped)
            continue

        # 空行はヘッダー継続行の区切りとして扱うがstateは維持
        if not stripped:
            continue

        if stripped.startswith("#"):
            continue

        if "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            if key == "name":
                name = val
                state = "header"
            elif key == "documents":
                documents = [d.strip() for d in val.split(",") if d.strip()]
                state = "header"
            elif key == "topics":
                state = "topics"
                if val:
                    topics_lines.append(val)
            elif key == "types":
                state = "types"
                if val:
                    types_lines.append(val)

    return {
        "filename": path.name,
        "name": name,
        "documents": documents,
        "topics": "\n".join(topics_lines),
        "types": "\n".join(types_lines),
        "prompt": "\n".join(body_lines).strip(),
    }


def _write_prompt_file(
    path: Path,
    name: str,
    documents: list[str],
    prompt: str,
    topics: str = "",
    types: str = "",
):
    docs_str = ", ".join(documents)
    lines = ["# プロンプト設定ファイル", f"name = {name}", f"documents = {docs_str}"]

    if topics.strip():
        lines.append("topics =")
        for line in topics.strip().splitlines():
            if line.strip():
                lines.append(f"  {line.strip()}")

    if types.strip():
        lines.append("types =")
        for line in types.strip().splitlines():
            if line.strip():
                lines.append(f"  {line.strip()}")

    lines.append("")
    lines.append("[prompt]")
    lines.append(prompt)
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


class PromptCreate(BaseModel):
    name: str
    documents: list[str] = []
    topics: Optional[str] = ""
    types: Optional[str] = ""
    prompt: str


class PromptUpdate(BaseModel):
    name: str
    documents: list[str] = []
    topics: Optional[str] = ""
    types: Optional[str] = ""
    prompt: str


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
def create_prompt(body: PromptCreate, _=Depends(get_current_user)):
    _ensure_dirs()
    if not body.name or len(body.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not body.prompt:
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    filename = re.sub(r"[^a-zA-Z0-9_]", "_", body.name.lower().replace(" ", "_")) + ".prompt"
    path = PROMPTS_DIR / filename
    if path.exists():
        raise HTTPException(status_code=409, detail=f"{filename} は既に存在します")

    _write_prompt_file(path, body.name, body.documents, body.prompt, body.topics or "", body.types or "")
    return _parse_prompt_file(path)


@router.put("/{filename}")
def update_prompt(filename: str, body: PromptUpdate, _=Depends(get_current_user)):
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    if not body.name or len(body.name) > 50:
        raise HTTPException(status_code=400, detail="プロンプト名は1〜50文字で入力してください")
    if not body.prompt:
        raise HTTPException(status_code=400, detail="プロンプト本文は必須です")

    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="プロンプトが見つかりません")

    _write_prompt_file(path, body.name, body.documents, body.prompt, body.topics or "", body.types or "")
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
