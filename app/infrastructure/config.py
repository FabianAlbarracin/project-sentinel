from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )

    postgres_host: str = "postgres_central"
    postgres_port: int = 5432
    postgres_db: str = "sentinel"
    postgres_user: str = "sentinel_user"
    postgres_password: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    woot_api_key: str = ""
    woot_interval_seconds: int = 900

    reddit_interval_seconds: int = 600

    telegram_channels: str = ""
    telegram_interval_seconds: int = 300

    max_observations_per_cycle: int = 500

    heartbeat_hour_utc: int = 14
    summary_hour_utc: int = 3

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
