import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import tweepy

from app.logger import get_logger
from app.services import posting_mode
from app.user_registry import UserConfig, get_user_config
from app.utils.rate_limit import RateLimitExceeded, check_and_record

# ユーザーごとにtweepyクライアントをキャッシュする（APIキーがユーザーごとに異なるため）。
_clients: dict[str, tweepy.Client] = {}
_clients_v1: dict[str, tweepy.API] = {}


def invalidate_client(user_id: str) -> None:
    """APIキー変更時に呼び出し、古いキーで作られたクライアントを破棄する。"""
    _clients.pop(user_id, None)
    _clients_v1.pop(user_id, None)


def _get_clients(user_id: str, cfg: UserConfig) -> tuple[tweepy.Client, tweepy.API]:
    client = _clients.get(user_id)
    api_v1 = _clients_v1.get(user_id)
    if client is not None and api_v1 is not None:
        return client, api_v1

    client = tweepy.Client(
        consumer_key=cfg.x_consumer_key,
        consumer_secret=cfg.x_consumer_secret,
        access_token=cfg.x_access_token,
        access_token_secret=cfg.x_access_token_secret,
    )
    auth_v1 = tweepy.OAuth1UserHandler(
        cfg.x_consumer_key,
        cfg.x_consumer_secret,
        cfg.x_access_token,
        cfg.x_access_token_secret,
    )
    api_v1 = tweepy.API(auth_v1)

    _clients[user_id] = client
    _clients_v1[user_id] = api_v1
    return client, api_v1


def _apply_proxy(client: tweepy.Client, api_v1: tweepy.API, mode: str, tor_proxy: str) -> None:
    """現在の投稿モードに応じてtweepyのHTTPプロキシ設定を切り替える。
    tor以外の経路が存在しないよう、呼び出しの直前に毎回設定し直す。"""
    if mode == "tor":
        proxies = {"http": tor_proxy, "https": tor_proxy}
    else:
        proxies = {}
    client.session.proxies = proxies
    api_v1.proxy = dict(proxies)


def post_tweet(user_id: str, content: str, image_path: str = None) -> str:
    """X APIへ1件投稿する。現在の posting_mode（tor/direct）に従ってプロキシを設定する。
    Torが起動していない場合、tor経路の接続自体が失敗するため、tor以外の経路で
    投稿が成立することはない（direct modeを明示的に選択した場合を除く）。"""
    cfg = get_user_config(user_id)
    if cfg is None:
        raise RuntimeError(f"user={user_id} の設定が見つかりません")

    client, api_v1 = _get_clients(user_id, cfg)
    mode = posting_mode.get_mode(user_id)
    _apply_proxy(client, api_v1, mode, cfg.tor_proxy)

    check_and_record(user_id, "x_api")
    media_ids = None
    if image_path and Path(image_path).exists():
        media = api_v1.media_upload(filename=image_path)
        media_ids = [str(media.media_id)]
    response = client.create_tweet(text=content, media_ids=media_ids)
    return str(response.data["id"])


@dataclass
class PostResult:
    ok: bool
    x_tweet_id: Optional[str] = None
    posted_via_tor: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_attempt: int = 0


_MAX_RETRIES = 3


def post_tweet_with_retry(user_id: str, content: str, image_path: str = None, tweet_id: int = None) -> PostResult:
    """Tor経由投稿のリトライ・エラー分類ロジック。

    - Tor接続エラー（プロキシに繋がらない等）: 最大3回リトライ（30秒→60秒待機）
    - X APIエラー（4xx/5xx）: リトライせず即座に失敗として返す
    - RateLimitExceeded（アプリ内レート制限）: リトライ・分類の対象外。呼び出し元にそのまま送出する
    """
    posting_logger = get_logger(user_id, "posting")
    mode = posting_mode.get_mode(user_id)
    retry_attempt = 0

    while True:
        try:
            x_id = post_tweet(user_id, content, image_path)
            if retry_attempt:
                posting_logger.info(f"tweet_id={tweet_id} retry succeeded after {retry_attempt} attempt(s)")
            return PostResult(ok=True, x_tweet_id=x_id, posted_via_tor=(mode == "tor"), retry_attempt=retry_attempt)

        except RateLimitExceeded:
            raise

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if mode != "tor":
                # direct modeでの接続失敗はTorと無関係。リトライせず即座に失敗させる
                posting_logger.error(f"tweet_id={tweet_id} status=failed error_code=CONNECTION_ERROR error_message=\"{e}\"")
                return PostResult(
                    ok=False, posted_via_tor=False,
                    error_code="CONNECTION_ERROR", error_message=str(e),
                    retry_attempt=retry_attempt,
                )

            retry_attempt += 1
            if retry_attempt >= _MAX_RETRIES:
                posting_logger.error(
                    f"tweet_id={tweet_id} status=failed error_code=TOR_CONNECTION_TIMEOUT "
                    f"error_message=\"{e}\" retry_attempts={retry_attempt}"
                )
                return PostResult(
                    ok=False, posted_via_tor=False,
                    error_code="TOR_CONNECTION_TIMEOUT", error_message=str(e),
                    retry_attempt=retry_attempt,
                )

            wait_seconds = 30 * retry_attempt
            posting_logger.warning(
                f"tweet_id={tweet_id} retry_attempt={retry_attempt} error_code=TOR_CONNECTION_TIMEOUT "
                f"error_message=\"{e}\" next_retry_in={wait_seconds}s"
            )
            time.sleep(wait_seconds)

        except tweepy.errors.HTTPException as e:
            status_code = getattr(e.response, "status_code", "UNKNOWN")
            posting_logger.error(
                f"tweet_id={tweet_id} status=failed error_code=X_API_{status_code} "
                f"error_message=\"{e}\" posted_via_tor={mode == 'tor'}"
            )
            return PostResult(
                ok=False, posted_via_tor=(mode == "tor"),
                error_code=f"X_API_{status_code}", error_message=str(e),
                retry_attempt=retry_attempt,
            )

        except Exception as e:
            posting_logger.error(f"tweet_id={tweet_id} status=failed error_code=UNKNOWN_ERROR error_message=\"{e}\"", exc_info=True)
            return PostResult(
                ok=False, posted_via_tor=(mode == "tor"),
                error_code="UNKNOWN_ERROR", error_message=str(e),
                retry_attempt=retry_attempt,
            )
