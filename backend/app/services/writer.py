import anthropic
import json
import random
from pathlib import Path
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

DATA_DIR = Path("/app/data")
TWEETSOURCE_DIR = Path("/app/tweetsource")
SYSTEM_PROMPT_FILE = DATA_DIR / "system_prompt.txt"

SYSTEM_PROMPT_FALLBACK = """必ずJSON配列で10件のツイートを返してください。
例: ["ツイート1", "ツイート2", ...]"""


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return SYSTEM_PROMPT_FALLBACK


def _load_source_material() -> str:
    texts = []
    for f in sorted(TWEETSOURCE_DIR.glob("*")):
        if f.is_file():
            try:
                texts.append(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return "\n\n---\n\n".join(texts) if texts else ""


def generate_tweets(past_tweets: list[str]) -> list[str]:
    system_prompt = _load_system_prompt()
    source = _load_source_material()

    past_section = ""
    if past_tweets:
        samples = random.sample(past_tweets, min(20, len(past_tweets)))
        past_section = "\n【過去の投稿（これらと表現が被らないようにすること）】\n" + "\n".join(f"- {t}" for t in samples)

    # システムプロンプトをキャッシュ（安定コンテンツ）
    system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

    # ユーザーメッセージ: 安定部分（参考資料）はキャッシュ、変動部分（過去ツイート＋指示）はキャッシュしない
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


def generate_tweet_from_news(title: str, summary: str, max_chars: int = 128) -> str:
    system_prompt = _load_system_prompt()
    system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

    user_content = (
        f"以下のニュース記事をもとに、アカウントの思想・論調に合わせたツイートを{max_chars}文字以内で1件生成してください。\n"
        "URLは別途末尾に付与するため本文に含めないこと。\n"
        f"必ず{max_chars}文字以内厳守。JSON配列で1件のみ返答。\n\n"
        f"タイトル：{title}\n"
        f"概要：{summary or '（概要なし）'}\n\n"
        '例: ["ツイート本文"]'
    )

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    tweets = json.loads(text)
    tweet = tweets[0] if tweets else ""
    return tweet[:max_chars]
