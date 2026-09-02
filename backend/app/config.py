from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    admin_password: str

    x_consumer_key: str
    x_consumer_secret: str
    x_access_token: str
    x_access_token_secret: str
    x_bearer_token: str

    anthropic_api_key: str

    legacy_news_feature_enabled: bool = False

    # --- Tor 経由投稿 ---
    posting_mode: str = "tor"  # tor / direct（Docker起動時のデフォルト値）
    tor_proxy: str = "socks5h://tor:9050"
    tor_timeout: int = 60
    tor_compose_service: str = "tor"  # docker restart 対象（com.docker.compose.serviceラベルで検索）

    class Config:
        env_file = "/app/conf/env.conf"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
