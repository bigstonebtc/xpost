import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.services.conf_parser import parse_conf, build_conf, PROMPTS_DIR

router = APIRouter(prefix="/prompts", tags=["prompts"])

_VALID_FILENAME = re.compile(r"^[a-z0-9_]+\.prompt$")


def _validate_filename(filename: str) -> str:
    if not _VALID_FILENAME.match(filename):
        raise HTTPException(400, "ファイル名は英数字・アンダースコアのみ使用可能です（例: my_prompt.prompt）")
    return filename


def _name_to_filename(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return (slug or "prompt") + ".prompt"


@router.get("/")
def list_prompts(_=Depends(get_current_user)):
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(PROMPTS_DIR.glob("*.prompt")):
        try:
            parsed = parse_conf(f.read_text(encoding="utf-8"))
        except Exception:
            parsed = {"name": f.stem, "documents": [], "prompt": ""}
        result.append({
            "filename": f.name,
            "name": parsed["name"] or f.stem,
            "documents": parsed["documents"],
        })
    return result


@router.get("/{filename}")
def get_prompt(filename: str, _=Depends(get_current_user)):
    filename = _validate_filename(filename)
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "プロンプトが見つかりません")
    parsed = parse_conf(path.read_text(encoding="utf-8"))
    return {"filename": filename, **parsed}


class PromptBody(BaseModel):
    name: str
    documents: list[str] = []
    prompt: str


@router.post("/")
def create_prompt(body: PromptBody, _=Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(400, "プロンプト名は必須です")
    if len(body.name) > 50:
        raise HTTPException(400, "プロンプト名は50文字以内にしてください")
    if not body.prompt.strip():
        raise HTTPException(400, "プロンプト本文は必須です")

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    base = _name_to_filename(body.name)
    path = PROMPTS_DIR / base
    # 衝突回避: 連番サフィックスを付ける
    counter = 1
    while path.exists():
        stem = base[: -len(".prompt")]
        path = PROMPTS_DIR / f"{stem}_{counter}.prompt"
        counter += 1

    path.write_text(build_conf(body.name, body.documents, body.prompt), encoding="utf-8")
    return {"filename": path.name}


@router.put("/{filename}")
def update_prompt(filename: str, body: PromptBody, _=Depends(get_current_user)):
    filename = _validate_filename(filename)
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "プロンプトが見つかりません")
    if not body.name.strip():
        raise HTTPException(400, "プロンプト名は必須です")
    if not body.prompt.strip():
        raise HTTPException(400, "プロンプト本文は必須です")

    path.write_text(build_conf(body.name, body.documents, body.prompt), encoding="utf-8")
    return {"ok": True}


@router.delete("/{filename}")
def delete_prompt(filename: str, _=Depends(get_current_user)):
    filename = _validate_filename(filename)
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "プロンプトが見つかりません")
    path.unlink()
    return {"ok": True}
