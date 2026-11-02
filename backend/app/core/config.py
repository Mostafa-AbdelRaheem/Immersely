# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-20b"

    scene_max_targets: int = 8
    scene_max_padding: int = 4
    scene_max_reviews_before_regen: int = 5

    flip_session_max_cards: int = 500

    # Read articles (N3): how many of the user's sentences feed one article,
    # and the length window (in characters of German text) the verifier enforces.
    read_max_sentences: int = 12
    read_min_chars: int = 1000
    read_max_chars: int = 1500

    timeout: int = 15

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()