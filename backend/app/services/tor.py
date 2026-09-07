import time
from datetime import datetime, timezone

import requests

from app.config import settings
from app.logger import app_logger

# Tor Project公式のチェックAPI。Tor経由かどうか(IsTor)と出口IPを同時に確認できる
_CHECK_URL = "https://check.torproject.org/api/ip"

_last_status = {
    "status": "error",
    "tor_connected": False,
    "exit_ip": None,
    "error": "起動後まだ確認していません",
    "last_verified_at": None,
}


def check_status() -> dict:
    """Tor SOCKS5プロキシ経由で外部サービスに接続し、実際にTor経由になっているか、
    出口IPが何かを確認する。"""
    proxies = {"http": settings.tor_proxy, "https": settings.tor_proxy}
    now = datetime.now(timezone.utc).isoformat()

    try:
        resp = requests.get(_CHECK_URL, proxies=proxies, timeout=settings.tor_timeout)
        resp.raise_for_status()
        data = resp.json()
        exit_ip = data.get("IP")
        is_tor = bool(data.get("IsTor"))

        if not is_tor:
            result = {
                "status": "error",
                "tor_connected": False,
                "exit_ip": exit_ip,
                "error": "Tor経由での接続を確認できませんでした（IsTor=false）",
                "last_verified_at": now,
            }
        else:
            result = {
                "status": "ok",
                "tor_connected": True,
                "exit_ip": exit_ip,
                "error": None,
                "last_verified_at": now,
            }
    except Exception as e:
        result = {
            "status": "error",
            "tor_connected": False,
            "exit_ip": None,
            "error": f"Cannot connect to Tor proxy at {settings.tor_proxy}: {e}",
            "last_verified_at": now,
        }

    global _last_status
    _last_status = result
    return result


def get_cached_status() -> dict:
    return _last_status


def restart_tor_container(wait_healthy_seconds: int = 30) -> dict:
    """docker socket経由でtorコンテナを再起動し、healthyに戻るまで待ってからステータス確認する。"""
    import docker

    client = docker.from_env()
    containers = client.containers.list(
        all=True,
        filters={"label": f"com.docker.compose.service={settings.tor_compose_service}"},
    )
    if not containers:
        raise RuntimeError(
            f"torコンテナが見つかりません（label com.docker.compose.service={settings.tor_compose_service}）"
        )
    container = containers[0]
    app_logger.info(f"torコンテナを再起動します: {container.name} ({container.id[:12]})")
    container.restart(timeout=10)

    deadline = time.monotonic() + wait_healthy_seconds
    while time.monotonic() < deadline:
        container.reload()
        health = container.attrs.get("State", {}).get("Health", {}).get("Status")
        if health == "healthy":
            break
        time.sleep(2)
    else:
        app_logger.warning(f"torコンテナがhealthyになる前にタイムアウトしました: {container.name}")

    return check_status()
