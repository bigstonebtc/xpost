import anthropic
import json
import random
from pathlib import Path
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

DATA_DIR = Path("/app/data")
SYSTEM_PROMPT_FILE = DATA_DIR / "system_prompt.txt"

SYSTEM_PROMPT_FALLBACK = """必ずJSON配列で10件のツイートを返してください。
例: ["ツイート1", "ツイート2", ...]"""


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return SYSTEM_PROMPT_FALLBACK


def _load_source_material() -> str:
    texts = []
    for f in DATA_DIR.glob("*.txt"):
        if f.name != "system_prompt.txt":
            texts.append(f.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(texts) if texts else ""


def generate_tweets(past_tweets: list[str]) -> list[str]:
    system_prompt = _load_system_prompt()
    source = _load_source_material()

    past_section = ""
    if past_tweets:
        samples = random.sample(past_tweets, min(20, len(past_tweets)))
        past_section = "\n【過去の投稿（これらと表現が被らないようにすること）】\n" + "\n".join(f"- {t}" for t in samples)

    source_section = f"\n【参考資料】\n{source}" if source else ""

    user_message = f"以下の条件でツイートを10件生成してください。{past_section}{source_section}"

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    tweets = json.loads(text)
    return [t[:140] for t in tweets[:10]]
