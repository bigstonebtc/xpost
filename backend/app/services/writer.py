import anthropic
import json
import random
from app.config import settings
from app.services.conf_parser import load_conf, load_documents

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

DEFAULT_PROMPT_FILE = "souzokuzei_ronten.prompt"
DEFAULT_NEWS_PROMPT_FILE = "news_comment.prompt"


def generate_tweets(past_tweets: list[str], prompt_file: str = DEFAULT_PROMPT_FILE) -> list[str]:
    try:
        conf = load_conf(prompt_file)
    except FileNotFoundError as e:
        raise ValueError(str(e))

    system_prompt = conf["prompt"]
    source = load_documents(conf["documents"])

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
    prompt_file: str = DEFAULT_NEWS_PROMPT_FILE,
    max_chars: int = 128,
) -> str:
    try:
        conf = load_conf(prompt_file)
    except FileNotFoundError as e:
        raise ValueError(str(e))

    system_prompt = conf["prompt"]
    source = load_documents(conf["documents"])

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
