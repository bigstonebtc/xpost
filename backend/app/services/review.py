"""+R（レビューしてから予約）のレビュー処理。

有効なレビュー用プロンプト（通常の .prompt ファイル）をシステムプロンプトにして
ツイート本文を Claude に渡し、返答をそのまま修正後の本文とする。
返答に本文以外を含めないよう指示するのはレビュー用プロンプト側の役割なので、
ここでは JSON 解析などの加工はせず、前後の空白除去だけを行う。
"""
import anthropic

from app.paths import prompts_dir
from app.services.claude_usage import log_claude_usage
from app.services.writer import GENERATION_MODEL, _load_documents, _parse_prompt_file
from app.user_registry import get_user_config
from app.utils.rate_limit import check_and_record

# nginx の proxy_read_timeout（300s）より十分短くし、タイムアウトをエラーとして返せるようにする
_REVIEW_TIMEOUT_SECONDS = 120

_HEADER_KEYS = ("name", "documents", "visible", "topics", "types")


class ReviewError(Exception):
    pass


def _prompt_path(user_id: str, filename: str):
    if not filename or "/" in filename or "\\" in filename or not filename.endswith(".prompt"):
        return None
    path = prompts_dir(user_id) / filename
    return path if path.is_file() else None


def get_review_prompt(user_id: str, filename: str | None) -> dict | None:
    """有効なレビュー用プロンプトの {filename, name} を返す。未設定・ファイルが無い場合は None（=「なし」）。"""
    path = _prompt_path(user_id, filename) if filename else None
    if not path:
        return None
    try:
        name = _parse_prompt_file(path)["name"]
    except Exception:
        name = path.stem
    return {"filename": path.name, "name": name}


def _system_prompt_from_file(path) -> tuple[str, list[str]]:
    """[prompt] セクションがあればその本文を、無ければヘッダー行と # コメントを除いた
    全文をシステムプロンプトにする（管理画面では [prompt] を書かずに本文だけ保存できるため）。"""
    parsed = _parse_prompt_file(path)
    prompt = parsed["prompt"]
    if not prompt:
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            key, sep, _ = stripped.partition("=")
            if sep and key.strip() in _HEADER_KEYS:
                continue
            lines.append(line)
        prompt = "\n".join(lines).strip()
    return prompt, parsed["documents"]


def review_tweet(user_id: str, text: str, prompt_file: str) -> dict:
    """レビューを1回実行し、{"text", "input_tokens", "output_tokens"} を返す。
    失敗時は ReviewError（レート制限超過時は RateLimitExceeded）を送出する。"""
    path = _prompt_path(user_id, prompt_file)
    if not path:
        raise ReviewError("レビュー用プロンプトが見つかりません")
    system_prompt, documents = _system_prompt_from_file(path)
    if not system_prompt:
        raise ReviewError("レビュー用プロンプトの本文が空です")

    cfg = get_user_config(user_id)
    api_key = cfg.anthropic_api_key if cfg else ""
    if not api_key:
        raise ReviewError("Anthropic APIキーが設定されていません")

    user_content = []
    source = _load_documents(user_id, documents)
    if source:
        user_content.append({"type": "text", "text": "【参考資料】\n" + source})
    user_content.append({"type": "text", "text": text})

    check_and_record(user_id, "anthropic")
    client = anthropic.Anthropic(api_key=api_key, timeout=_REVIEW_TIMEOUT_SECONDS)
    try:
        message = client.messages.create(
            model=GENERATION_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APITimeoutError as e:
        raise ReviewError("Claude APIがタイムアウトしました") from e
    except anthropic.APIError as e:
        raise ReviewError(f"Claude APIエラー: {e}") from e

    log_claude_usage(user_id, "review", message.usage.input_tokens, message.usage.output_tokens)

    if message.stop_reason == "max_tokens":
        raise ReviewError("レビュー結果が長すぎて途中で打ち切られました")
    reviewed = "".join(b.text for b in message.content if b.type == "text").strip()
    if not reviewed:
        raise ReviewError("レビュー結果が空でした")

    return {
        "text": reviewed,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
