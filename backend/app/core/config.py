# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/core/config.py
class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    groq_api_key: str

    scene_max_targets: int = 8
    scene_max_padding: int = 4
    scene_max_reviews_before_regen: int = 5

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()