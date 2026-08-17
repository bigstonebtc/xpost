import json
import time
from datetime import date

import anthropic

from app.config import settings
from app.logger import generation_logger as logger
from app.utils.rate_limit import check_and_record

SYSTEM_PROMPT = """あなたは @NakamuraMilei （自由主義・相続税廃止・私有財産権・規制緩和を訴えるXアカウント）の運用担当です。
ユーザーから渡されたツイート本文に関連する報道記事を web_search ツールで1件探し、構造化データで返してください。

## ステップ1: キーワード抽出と検索戦略
ツイート本文から3〜5個の基本キーワードを抽出したうえで、以下の2方向でそれぞれ2〜3パターン、
合計4〜6パターンのキーワードを生成し、web_search で検索してください。

1. 順方向: ツイートの主張を支持・補強する記事を探すキーワード
2. 逆方向: ツイートが指摘している問題の現実を報道している記事を探すキーワード

例（相続税・税制批判ツイートの場合）:
- 順方向: 「相続税廃止 経済効果」「相続税廃止 廃業減」
- 逆方向: 「相続税 廃業」「相続税 雇用喪失」

## ステップ2: 記事の選定基準
以下は除外する:
- Wikipedia・百科事典
- 研究所・シンクタンク・大学・学術機関の公式発表
- 政府公式統計・法律文書
- 個人ブログ・Note
- 士業向け専門解説サイト

優先するメディア（ニュース記事は発行日1年以内を優先）:
朝日新聞、日本経済新聞、読売新聞、東京新聞、NHK News Web、Yahoo!ニュース、Google News、
時事通信、共同通信、東洋経済オンライン、現代ビジネス、ダイヤモンド・オンライン、
Forbes Japan、週刊エコノミスト

コラム・解説記事は発行日の制限なし（優先度はニュース記事より低い）。

## ステップ3: 「ツイートへのコメントとして機能するか」の確認
記事は以下のいずれかを満たす場合のみ採用する:
1. 順方向: ツイートの主張を支持・補強する内容
2. 逆方向: ツイートが指摘している問題の現実を報道している内容

例:
- ツイート「減税すべき」+ 記事「政府が最大増税実施」→ 採用（「見ろ、逆をやっている」という批評が成立）
- ツイート「廃業が増えている」+ 記事「相続税で廃業増加」→ 採用（問題の現実を立証）
- ツイート「減税すべき」+ 記事「スイスの観光地が美しい」→ 不採用（無関係）

## ステップ4: コメント性評価（1〜5）
5: ツイートが指摘している問題の現実を直接報道
4: ツイートの主張の背景・文脈を補強・対比
3以下: 不採用（他の候補を探す。全候補が3以下なら見つからなかったものとして扱う）

## ステップ5: 出力
複数の候補がある場合は、最新日付のものを優先。同日付なら信頼度の高いメディアを優先。
最終的に1件を選び、以下のJSON形式のみで出力してください（説明文やコードフェンスは不要。JSON以外の文字を含めないこと）。

見つかった場合:
{"found": true, "title": "記事タイトル", "media": "媒体名", "published_date": "YYYY-MM-DD", "url": "https://...", "content_summary": "内容の要約（30〜50字程度）", "article_type": "news または column", "comment_rating": 4または5, "comment_reason": "採用理由"}

キーワード戦略を変えて探しても（最大2回まで）条件を満たす記事が見つからない場合:
{"found": false, "reason": "見つからなかった理由の簡潔な説明"}
"""


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
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed = time.monotonic() - started_at

    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        result = json.loads(text)
    except Exception as e:
        logger.error(f"news-search: JSON解析失敗: {e}, raw={text[:300]!r}")
        return {"found": False, "reason": "記事情報の解析に失敗しました"}

    if result.get("found"):
        logger.info(
            f"news-search: found rating={result.get('comment_rating')} "
            f"media={result.get('media')} in {elapsed:.1f}s"
        )
    else:
        logger.info(f"news-search: not found in {elapsed:.1f}s reason={result.get('reason', '')}")

    return result
