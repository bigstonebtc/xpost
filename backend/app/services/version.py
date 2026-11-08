"""アプリのバージョンと更新履歴。

- バージョン番号はリポジトリ直下の VERSION ファイル（例: 2.1.10）
- 日付は VERSION を最後に変更したコミットの日付（JST）を git から取得する
- 更新履歴は git のコミットメッセージ

本番ではリポジトリ直下を backend コンテナの /app/repo に読み取り専用でマウントする
（docker-compose.yml 参照）。.git が無い（rsync でデプロイした等）場合は、
番号だけを返し、日付と履歴は取得できないものとして扱う。
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

_HISTORY_LIMIT = 200
# 履歴の本文から除く行（コミットの帰属表示）
_TRAILER_PREFIXES = ("Co-Authored-By:", "Claude-Session:")


def _repo_root() -> Path:
    env = os.environ.get("XPOST_REPO_DIR")
    if env:
        return Path(env)
    mounted = Path("/app/repo")
    if (mounted / "VERSION").is_file():
        return mounted
    # ローカル開発時: backend/app/services/version.py から見たリポジトリ直下
    return Path(__file__).resolve().parents[3]


def _git(*args: str) -> str | None:
    root = _repo_root()
    if not (root / ".git").exists():
        return None
    try:
        # コンテナ内の root とホスト側のリポジトリ所有者が異なっても読めるよう safe.directory を指定
        result = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(root), *args],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout


def _format_date(iso: str) -> str:
    """git の ISO8601 日時を JST の「2026.11.9」形式にする。"""
    d = datetime.fromisoformat(iso.strip()).astimezone(JST)
    return f"{d.year}.{d.month}.{d.day}"


def get_version() -> dict:
    """{"version": "2.1.10", "date": "2026.11.9" or None}"""
    try:
        version = (_repo_root() / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        version = None
    out = _git("log", "-1", "--format=%cI", "HEAD", "--", "VERSION")
    date = _format_date(out) if out and out.strip() else None
    return {"version": version, "date": date}


def version_label() -> str:
    v = get_version()
    label = v["version"] or "unknown"
    return f"{label} ({v['date']})" if v["date"] else label


def get_history(limit: int = _HISTORY_LIMIT) -> list[dict] | None:
    """コミット履歴（新しい順）。git が使えない場合は None。"""
    # 区切りに ASCII の US(0x1f) / RS(0x1e) を使い、本文中の改行や記号と衝突しないようにする
    out = _git("log", f"-{limit}", "--format=%h%x1f%cI%x1f%D%x1f%s%x1f%b%x1e", "HEAD")
    if out is None:
        return None
    history = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, iso, refs, subject, body = (record.split("\x1f") + [""] * 5)[:5]
        tags = [r.strip()[len("tag: "):] for r in refs.split(",") if r.strip().startswith("tag: ")]
        body_lines = [l for l in body.strip().splitlines() if not l.startswith(_TRAILER_PREFIXES)]
        history.append({
            "hash": sha,
            "date": _format_date(iso),
            "tags": tags,
            "subject": subject,
            "body": "\n".join(body_lines).strip(),
        })
    return history
