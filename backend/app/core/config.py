# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


    # Accounts (N5): minimum length for NEW passwords only (registration,
    # reset, change). Existing passwords are never re-checked at login.
    password_min_length: int = 8
    # Breached-password check (N5): Pwned Passwords k-anonymity lookup.
    # It fails open, so an outage never blocks registration.
    hibp_enabled: bool = True
    hibp_timeout_s: float = 3.0


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

    # Conversations (N4): semantic retrieval policy and request guardrails.
    # Cosine distance: 0 = identical, larger = less similar.
    chat_retrieval_max_distance: float = 0.65
    chat_max_chips: int = 2
    chat_max_partner_sentences: int = 3
    chat_max_history_messages: int = 20
    chat_max_message_chars: int = 500

    timeout: int = 15

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()