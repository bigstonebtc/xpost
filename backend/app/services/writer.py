import anthropic
import json
import random
from pathlib import Path
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

PROMPTS_DIR = Path("/app/prompt")
DOCUMENTS_DIR = Path("/app/documents")

_FALLBACK_PROMPT = """必ずJSON配列で10件のツイートを返してください。
例: ["ツイート1", "ツイート2", ...]"""

_FALLBACK_NEWS_PROMPT = """あなたはXアカウントの運用担当です。
提供されたニュース記事をもとに、140文字以内のツイートを1件生成してください。
URLは別途末尾に付与するため本文に含めないこと。
必ずJSON配列で1件のみ返答してください。
例: ["ツイート本文"]"""


def _parse_prompt_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    documents = []
    body_lines = []
    in_prompt_section = False

    for line in text.splitlines():
        if in_prompt_section:
            body_lines.append(line)
            continue
        stripped = line.strip()
        if stripped.startswith("[prompt]"):
            in_prompt_section = True
            continue
        if stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            if key == "name":
                name = val
            elif key == "documents":
                documents = [d.strip() for d in val.split(",") if d.strip()]

    return {
        "name": name,
        "documents": documents,
        "prompt": "\n".join(body_lines).strip(),
    }


def _load_documents(doc_names: list[str]) -> str:
    texts = []
    for name in doc_names:
        path = DOCUMENTS_DIR / name
        if path.is_file():
            try:
                texts.append(f"【資料: {name}】\n{path.read_text(encoding='utf-8', errors='ignore')}")
            except Exception:
                pass
    return "\n\n---\n\n".join(texts)


def _resolve_prompt(prompt_file: str | None) -> dict:
    if prompt_file:
        path = PROMPTS_DIR / prompt_file
        if path.exists():
            return _parse_prompt_file(path)
    return {"name": "default", "documents": [], "prompt": _FALLBACK_PROMPT}


def generate_tweets(past_tweets: list[str], prompt_file: str | None = None) -> list[str]:
    cfg = _resolve_prompt(prompt_file)
    system_prompt = cfg["prompt"] or _FALLBACK_PROMPT
    source = _load_documents(cfg["documents"])

    past_section = ""
    if past_tweets:
        samples = random.sample(past_tweets, min(20, len(past_tweets)))
        past_section = "\n【過去の投稿（これらと表現が被らないようにすること）】\n" + "\n".join(f"- {t}" for t in samples)

    system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

    content = []
    if source:
        content.append({
            "type": "text",
            "text": f"【参考資料】\n{source}",
            "cache_control": {"type": "ephemeral"},
        })

    content.append({
        "type": "text",
        "text": past_section if past_section else "ツイートを生成してください。",
    })

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": content}],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    tweets = json.loads(text)
    return [t[:140] for t in tweets[:10]]


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

    content = []
    if source:
        content.append({
            "type": "text",
            "text": f"【参考資料】\n{source}",
            "cache_control": {"type": "ephemeral"},
        })

    content.append({
        "type": "text",
        "text": (
            f"以下のニュース記事をもとに、アカウントの思想・論調に合わせたツイートを{max_chars}文字以内で1件生成してください。\n"
            "URLは別途末尾に付与するため本文に含めないこと。\n"
            f"必ず{max_chars}文字以内厳守。JSON配列で1件のみ返答。\n\n"
            f"タイトル：{title}\n"
            f"概要：{summary or '（概要なし）'}\n\n"
            '例: ["ツイート本文"]'
        ),
    })

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": content}],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    tweets = json.loads(text)
    tweet = tweets[0] if tweets else ""
    return tweet[:max_chars]
