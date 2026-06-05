import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic

from app.config import settings


PROMPTS_DIR = Path("/app/prompts")
DOCUMENTS_DIR = Path("/app/documents")

_FALLBACK_PROMPT = "あなたはXアカウントの運用担当です。140文字以内のツイートを1件生成してください。JSON配列で返答。例: [\"ツイート本文\"]"
_FALLBACK_NEWS_PROMPT = "あなたはXアカウントの運用担当です。提供されたニュース記事をもとに140文字以内のツイートを1件生成してください。URLは別途付与するため本文に含めないこと。JSON配列で1件のみ返答。例: [\"ツイート本文\"]"


def _parse_prompt_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    documents = []
    topics_lines = []
    types_lines = []
    body_lines = []
    state = "header"

    for line in text.splitlines():
        if state == "prompt":
            body_lines.append(line)
            continue

        stripped = line.strip()

        if stripped.startswith("[prompt]"):
            state = "prompt"
            continue

        if line.startswith(" ") or line.startswith("\t"):
            if state == "topics" and stripped and not stripped.startswith("#"):
                topics_lines.append(stripped)
            elif state == "types" and stripped and not stripped.startswith("#"):
                types_lines.append(stripped)
            continue

        if not stripped or stripped.startswith("#"):
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
        "name": name,
        "documents": documents,
        "topics": [l for l in topics_lines if l.strip()],
        "types": [l for l in types_lines if l.strip()],
        "prompt": "\n".join(body_lines).strip(),
    }


def _load_documents(doc_names: list[str]) -> str:
    texts = []
    for name in doc_names:
        path = DOCUMENTS_DIR / name
        if path.is_file():
            try:
                texts.append("【資料: " + name + "】\n" + path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return "\n\n---\n\n".join(texts)


def _resolve_prompt(prompt_file: str | None) -> dict:
    if prompt_file:
        path = PROMPTS_DIR / prompt_file
        if path.exists():
            return _parse_prompt_file(path)
    return {"name": "default", "documents": [], "topics": [], "types": [], "prompt": _FALLBACK_PROMPT}


def _pick(lst: list, n: int) -> list[str]:
    """n件選ぶ。lst < n の場合はランダム循環で補充。lst が空なら空文字リスト。"""
    if not lst:
        return [""] * n
    pool = random.sample(lst, min(n, len(lst)))
    while len(pool) < n:
        pool += random.sample(lst, min(n - len(pool), len(lst)))
    return pool[:n]


def _call_claude_once(system_prompt: str, user_content: list[dict]) -> str:
    """同期で Claude API を1回呼び、ツイート1件を返す。
    スレッドセーフのためクライアントをスレッドごとに生成する。"""
    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = _client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        items = json.loads(text)
        return (items[0] if items else "")[:140]
    except Exception:
        # JSONパース失敗時はテキストをそのまま使う
        return text[:140]


def generate_tweets(past_tweets: list[str], prompt_file: str | None = None, count: int = 10) -> list[str]:
    cfg = _resolve_prompt(prompt_file)
    source = _load_documents(cfg["documents"])
    prompt_template = cfg["prompt"] or _FALLBACK_PROMPT

    use_topic = "{topic}" in prompt_template
    use_type = "{type}" in prompt_template

    selected_topics = _pick(cfg.get("topics", []), count) if use_topic else []
    shuffled_types = _pick(cfg.get("types", []), count) if use_type else []

    past_section = ""
    if past_tweets:
        samples = random.sample(past_tweets, min(20, len(past_tweets)))
        past_section = "\n【過去の投稿（これらと表現が被らないようにすること）】\n" + "\n".join("- " + t for t in samples)

    instruction = "140文字以内のツイートを1件生成してください。JSON配列で1件のみ返答。例: [\"ツイート本文\"]"

    def build_call(i: int):
        # str.replace() を使用（str.format() は {topic}/{type} でKeyErrorになるため不可）
        prompt = prompt_template
        if use_topic:
            prompt = prompt.replace("{topic}", selected_topics[i])
        if use_type:
            prompt = prompt.replace("{type}", shuffled_types[i])

        user_content = []
        if source:
            user_content.append({
                "type": "text",
                "text": "【参考資料】\n" + source,
                "cache_control": {"type": "ephemeral"},
            })
        user_content.append({
            "type": "text",
            "text": past_section + "\n\n" + instruction if past_section else instruction,
        })
        return prompt, user_content

    calls = [build_call(i) for i in range(count)]

    results = [""] * count
    with ThreadPoolExecutor(max_workers=count) as executor:
        future_to_idx = {executor.submit(_call_claude_once, p, uc): i for i, (p, uc) in enumerate(calls)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                print(f"[writer] generate_tweets [{idx}] エラー: {e}")

    return [t for t in results if t]


def generate_tweet_from_news(
    title: str,
    summary: str,
    max_chars: int = 128,
    prompt_file: str | None = None,
) -> str:
    cfg = _resolve_prompt(prompt_file)
    system_prompt = cfg["prompt"] or _FALLBACK_NEWS_PROMPT
    source = _load_documents(cfg["documents"])

    system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    user_content = []
    if source:
        user_content.append({
            "type": "text",
            "text": "【参考資料】\n" + source,
            "cache_control": {"type": "ephemeral"},
        })
    user_content.append({
        "type": "text",
        "text": (
            "以下のニュース記事をもとに、アカウントの思想・論調に合わせたツイートを" + str(max_chars) + "文字以内で1件生成してください。\n"
            "URLは別途末尾に付与するため本文に含めないこと。\n"
            "必ず" + str(max_chars) + "文字以内厳守。JSON配列で1件のみ返答。\n\n"
            "タイトル：" + title + "\n"
            "概要：" + (summary or "（概要なし）") + "\n\n"
            '例: ["ツイート本文"]'
        ),
    })

    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = _client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        tweets = json.loads(text)
        tweet = tweets[0] if tweets else ""
    except Exception:
        tweet = text
    return tweet[:max_chars]
