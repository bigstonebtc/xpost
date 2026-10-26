"""+R（レビューしてから予約）のレビュー処理。

有効なレビュー用プロンプト（通常の .prompt ファイル）内の {review_target} を
レビュー前のツイート本文に置き換え、1通のメッセージとして Claude に渡す。
返答はそのまま修正後の本文とする。
返答に本文以外を含めないよう指示するのはレビュー用プロンプト側の役割なので、
ここでは JSON 解析などの加工はせず、前後の空白除去だけを行う。
"""
import anthropic

from app.paths import prompts_dir
from app.services.claude_usage import log_claude_usage
from app.services.writer import GENERATION_MODEL, PromptError, _load_documents, _parse_prompt_file, load_prompt
from app.user_registry import get_user_config
from app.utils.rate_limit import check_and_record

# nginx の proxy_read_timeout（300s）より十分短くし、タイムアウトをエラーとして返せるようにする
_REVIEW_TIMEOUT_SECONDS = 120

# プロンプト内でレビュー前の本文に置き換えるプレースホルダ
REVIEW_TARGET_PLACEHOLDER = "{review_target}"


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


def review_tweet(user_id: str, text: str, prompt_file: str) -> dict:
    """レビューを1回実行し、{"text", "input_tokens", "output_tokens"} を返す。
    失敗時は ReviewError（レート制限超過時は RateLimitExceeded）を送出する。"""
    try:
        prompt_cfg = load_prompt(user_id, prompt_file)
    except PromptError as e:
        raise ReviewError(str(e)) from e
    prompt, documents = prompt_cfg["prompt"], prompt_cfg["documents"]
    if REVIEW_TARGET_PLACEHOLDER not in prompt:
        raise ReviewError(f"レビュー用プロンプトに {REVIEW_TARGET_PLACEHOLDER} がありません")

    cfg = get_user_config(user_id)
    api_key = cfg.anthropic_api_key if cfg else ""
    if not api_key:
        raise ReviewError("Anthropic APIキーが設定されていません")

    user_content = []
    source = _load_documents(user_id, documents)
    if source:
        user_content.append({"type": "text", "text": "【参考資料】\n" + source})
    # str.format() は本文やプロンプト中の { } で失敗するため replace を使う
    user_content.append({"type": "text", "text": prompt.replace(REVIEW_TARGET_PLACEHOLDER, text)})

    check_and_record(user_id, "anthropic")
    client = anthropic.Anthropic(api_key=api_key, timeout=_REVIEW_TIMEOUT_SECONDS)
    try:
        message = client.messages.create(
            model=GENERATION_MODEL,
            max_tokens=2048,
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
