from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "Attention Drift Agent"

    DATABASE_URL: str

    WINDOW_SIZE_SECONDS: int = 300

    SNAPSHOT_INTERVAL_SECONDS: int = 30

    class Config:
        env_file = ".env"


settings = Settings()