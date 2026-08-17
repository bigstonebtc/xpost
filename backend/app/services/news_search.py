import json
import time
from datetime import date

import anthropic

from app.config import settings
from app.logger import generation_logger as logger
from app.services.writer import PROMPTS_DIR, _load_documents, _parse_prompt_file
from app.utils.rate_limit import check_and_record

NEWS_SEARCH_PROMPT_FILE = "news_search.prompt"

# prompts/news_search.prompt が存在しない場合のフォールバック
_DEFAULT_SYSTEM_PROMPT = (
    "あなたはXアカウントの運用担当です。ユーザーから渡されたツイート本文に関連する報道記事を"
    " web_search ツールで1件探してください。"
    ' 見つかった場合は {"found": true, "title": "...", "media": "...", "published_date": "YYYY-MM-DD",'
    ' "url": "https://...", "content_summary": "...", "article_type": "news または column",'
    ' "comment_rating": 1-5, "comment_reason": "..."} の形式で、'
    ' 見つからない場合は {"found": false, "reason": "..."} の形式で、JSONのみを出力してください。'
)


def _load_system_prompt() -> str:
    path = PROMPTS_DIR / NEWS_SEARCH_PROMPT_FILE
    if not path.exists():
        return _DEFAULT_SYSTEM_PROMPT

    cfg = _parse_prompt_file(path)
    system_prompt = cfg["prompt"] or _DEFAULT_SYSTEM_PROMPT
    docs = _load_documents(cfg.get("documents", []))
    if docs:
        system_prompt += "\n\n【参考資料】\n" + docs
    return system_prompt


def search_news_for_tweet(
    tweet_text: str,
    search_pattern: int | None = None,
    exclude_urls: list[str] | None = None,
) -> dict:
    check_and_record("anthropic")

    exclude_urls = exclude_urls or []
    user_parts = [
        f"## ツイート本文\n{tweet_text}",
        f"## 本日の日付\n{date.today().isoformat()}",
    ]
    if search_pattern is not None:
        direction = "順方向（主張を支持・補強する記事）寄り" if search_pattern % 2 == 0 else "逆方向（問題の現実を報道する記事）寄り"
        user_parts.append(f"## 検索パターン指定\n今回は{direction}のキーワードを重点的に使用してください。")
    if exclude_urls:
        joined = "\n".join(f"- {u}" for u in exclude_urls)
        user_parts.append(f"## 除外URL（既に提示済み。これらとは異なる記事を選定すること）\n{joined}")

    user_content = "\n\n".join(user_parts)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    started_at = time.monotonic()
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=_load_system_prompt(),
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed = time.monotonic() - started_at

    # web_search使用時、Claudeは検索経過の説明文を複数のtextブロックに分けて出力し、
    # 最後のtextブロックが最終回答（JSON）になる。全ブロックを連結すると説明文が
    # 混入してJSONとして解析できなくなるため、最後のブロックのみを使用する。
    text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    raw_text = text_blocks[-1].strip() if text_blocks else ""

    text = raw_text
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(text)
    except Exception:
        # 前後に説明文が付いてしまった場合に備え、最初の{から最後の}までを抽出して再試行
        start, end = text.find("{"), text.rfind("}")
        try:
            if start == -1 or end == -1 or end <= start:
                raise ValueError("JSONブロックが見つかりません")
            result = json.loads(text[start:end + 1])
        except Exception as e:
            logger.error(f"news-search: JSON解析失敗: {e}, raw={raw_text[:500]!r}")
            return {"found": False, "reason": "記事情報の解析に失敗しました"}

    if result.get("found"):
        logger.info(
            f"news-search: found rating={result.get('comment_rating')} "
            f"media={result.get('media')} in {elapsed:.1f}s"
        )
    else:
        logger.info(f"news-search: not found in {elapsed:.1f}s reason={result.get('reason', '')}")

    return result
