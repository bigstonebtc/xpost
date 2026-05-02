from pathlib import Path

PROMPTS_DIR = Path("/app/prompts")
DOCUMENTS_DIR = Path("/app/documents")


def parse_conf(content: str) -> dict:
    """Parse .conf file content. Returns dict with keys: name, documents, prompt."""
    name = ""
    documents = []
    prompt_lines = []
    in_prompt = False

    for line in content.splitlines():
        if in_prompt:
            prompt_lines.append(line)
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "[prompt]":
            in_prompt = True
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key == "name":
                name = val
            elif key == "documents":
                documents = [d.strip() for d in val.split(",") if d.strip()]

    return {
        "name": name,
        "documents": documents,
        "prompt": "\n".join(prompt_lines).strip(),
    }


def build_conf(name: str, documents: list, prompt: str) -> str:
    """Build .conf file content from fields."""
    docs_str = ", ".join(documents)
    return f"name = {name}\ndocuments = {docs_str}\n\n[prompt]\n{prompt}\n"


def load_conf(filename: str) -> dict:
    """Load and parse a .prompt file by filename. Raises FileNotFoundError if missing."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"プロンプトファイルが見つかりません: {filename}")
    return parse_conf(path.read_text(encoding="utf-8"))


def load_documents(filenames: list) -> str:
    """Load document files and return concatenated text. Skips unreadable files."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    parts = []
    for fname in filenames:
        path = DOCUMENTS_DIR / fname
        if not path.exists():
            print(f"[conf_parser] 資料ファイルが見つかりません: {fname}")
            continue
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[conf_parser] 資料ファイル読み込みエラー {fname}: {e}")
    return "\n\n---\n\n".join(parts)
