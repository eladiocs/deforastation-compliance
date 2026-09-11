from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEE_SERVICE_ACCOUNT_EMAIL: str
    GEE_PROJECT_ID: str
    GEE_KEY_PATH: str = "secrets/gee-key.json"

    DATABASE_URL: str = "postgresql+psycopg://deforcompliance:deforcompliance@localhost:5434/deforcompliance"
    REPORTS_DIR: str = "reports"
    REPORT_SIGNING_KEY_PATH: str = "secrets/report-signing-key.pem"


settings = Settings()
