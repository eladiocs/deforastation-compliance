from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+psycopg://deforcompliance:deforcompliance@localhost:5434/deforcompliance"
    CORS_ORIGINS: str = "http://localhost:5174"
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    WORLDCOVER_BASE_URL: str = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
    WORLDCOVER_ENABLED: bool = True


settings = Settings()
