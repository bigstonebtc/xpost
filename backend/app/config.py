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

    class Config:
        env_file = ".env"


settings = Settings()
