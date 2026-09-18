from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEE_SERVICE_ACCOUNT_EMAIL: str
    GEE_PROJECT_ID: str
    GEE_KEY_PATH: str = "secrets/gee-key.json"

    DATABASE_URL: str = "postgresql+psycopg://deforcompliance:deforcompliance@localhost:5434/deforcompliance"
    CORS_ORIGINS: str = "http://localhost:5174"


settings = Settings()
