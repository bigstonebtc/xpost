"""env.conf（KEY=VALUE形式）の読み書きヘルパー。

routers/apikeys.py（X/Anthropic APIキー更新）と routers/auth.py
（パスワード変更）の両方から使う共通処理。
"""
from pathlib import Path


def read_env_file(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def upsert_env_values(path: Path, updates: dict[str, str]) -> None:
    """既存キーは値を置き換え、存在しないキーは末尾に追記する。"""
    if not updates:
        return

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    remaining = dict(updates)
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in remaining:
            new_lines.append(f"{key}={remaining.pop(key)}\n")
        else:
            new_lines.append(line)

    if remaining:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        for key, value in remaining.items():
            new_lines.append(f"{key}={value}\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(new_lines), encoding="utf-8")
