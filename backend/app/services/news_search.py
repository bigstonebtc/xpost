import json
import time
from datetime import date

import anthropic

from app.logger import get_logger
from app.paths import prompts_dir
from app.services.claude_usage import estimate_cost, log_claude_usage
from app.services.writer import _load_documents, _parse_prompt_file
from app.user_registry import get_user_config
from app.utils.rate_limit import check_and_record

NEWS_SEARCH_PROMPT_FILE = "news_search.prompt"
MAX_ARTICLES = 5

# prompts/news_search.prompt が存在しない場合のフォールバック
_DEFAULT_SYSTEM_PROMPT = (
    "あなたはXアカウントの運用担当です。ユーザーから渡されたツイート本文に関連する報道記事を"
    " web_search ツールで探し、ツイートとの適合度を1〜5で評価してください。説明文や経過報告は出力しないこと。"
    " 評価4以上の記事を最大5件まで、JSON配列で返してください"
    ' （例: [{"title": "...", "media": "...", "published_date": "YYYY-MM-DD",'
    ' "url": "https://...", "snippet": "検索で得たスニペット（30-100字、要約の生成はしない）", "rating": 5}]）。'
    ' 1件も見つからない場合は {"found": false, "reason": "..."} の形式で、JSONのみを出力してください。'
)


def _extract_json(text: str):
    """前後に説明文が付いてしまった場合に備え、配列([...])／オブジェクト({...})の
    いずれかを抽出して再パースする。"""
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                continue
    raise ValueError("JSONブロックが見つかりません")


def _normalize_result(parsed) -> dict:
    """Claudeの応答（配列 or 単一オブジェクト）を {"found": bool, "articles": [...]}
    または {"found": False, "reason": ...} の形に正規化する。"""
    if isinstance(parsed, dict) and parsed.get("found") is False:
        return {"found": False, "reason": parsed.get("reason", "")}

    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        items = [parsed]
    else:
        items = []

    articles = []
    for item in items:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        articles.append({
            "title": item.get("title", ""),
            "media": item.get("media", ""),
            "published_date": item.get("published_date", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "rating": item.get("rating"),
        })

    # プロンプト側で評価・日付順に整列されている想定だが、念のためここでも保証する
    articles.sort(key=lambda a: (a.get("rating") or 0, a.get("published_date") or ""), reverse=True)
    articles = articles[:MAX_ARTICLES]

    if not articles:
        return {"found": False, "reason": "条件を満たす記事が見つかりませんでした"}
    return {"found": True, "articles": articles}


def _load_system_prompt(user_id: str) -> str:
    path = prompts_dir(user_id) / NEWS_SEARCH_PROMPT_FILE
    if not path.exists():
        return _DEFAULT_SYSTEM_PROMPT

    cfg = _parse_prompt_file(path)
    system_prompt = cfg["prompt"] or _DEFAULT_SYSTEM_PROMPT
    docs = _load_documents(user_id, cfg.get("documents", []))
    if docs:
        system_prompt += "\n\n【参考資料】\n" + docs
    return system_prompt


def search_news_for_tweet(
    user_id: str,
    tweet_text: str,
    search_pattern: int | None = None,
    exclude_urls: list[str] | None = None,
) -> dict:
    logger = get_logger(user_id, "generation")
    check_and_record(user_id, "anthropic")

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

    cfg = get_user_config(user_id)
    api_key = cfg.anthropic_api_key if cfg else ""
    client = anthropic.Anthropic(api_key=api_key)
    started_at = time.monotonic()
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=_load_system_prompt(user_id),
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed = time.monotonic() - started_at
    log_claude_usage(user_id, "news_search", message.usage.input_tokens, message.usage.output_tokens)
    total_tokens = message.usage.input_tokens + message.usage.output_tokens
    cost_usd = estimate_cost(user_id, message.usage.input_tokens, message.usage.output_tokens)

    if message.stop_reason == "max_tokens":
        logger.error(f"news-search: max_tokensに到達し最終回答を得られませんでした ({elapsed:.1f}s)")
        return {"found": False, "reason": "応答が長くなりすぎたため記事を特定できませんでした", "tokens": total_tokens, "cost_usd": cost_usd}

    # web_search使用時、Claudeは検索経過の説明文を複数のtextブロックに分けて出力することがあり、
    # 最後のtextブロックが最終回答（JSON）になる。全ブロックを連結すると説明文が
    # 混入してJSONとして解析できなくなるため、最後のブロックのみを使用する。
    text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    raw_text = text_blocks[-1].strip() if text_blocks else ""

    text = raw_text
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(text)
    except Exception:
        try:
            parsed = _extract_json(text)
        except Exception as e:
            logger.error(f"news-search: JSON解析失敗: {e}, raw={raw_text[:500]!r}")
            return {"found": False, "reason": "記事情報の解析に失敗しました", "tokens": total_tokens, "cost_usd": cost_usd}

    result = _normalize_result(parsed)

    if result["found"]:
        ratings = ", ".join(str(a.get("rating")) for a in result["articles"])
        logger.info(f"news-search: found {len(result['articles'])}件 ratings=[{ratings}] in {elapsed:.1f}s")
    else:
        logger.info(f"news-search: not found in {elapsed:.1f}s reason={result.get('reason', '')}")

    result["tokens"] = total_tokens
    result["cost_usd"] = cost_usd
    return result
