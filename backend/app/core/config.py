# app/core/config.py
from pydantic import Field
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
    # bcrypt only uses the first 72 BYTES of a password and bcrypt 4.0.1
    # truncates silently (verified here). You may set this LOWER in .env, but a
    # value above 72 fails at startup instead of silently weakening passwords.
    password_max_bytes: int = Field(default=72, ge=1, le=72)
    # Breached-password check (N5): Pwned Passwords k-anonymity lookup.
    # It fails open, so an outage never blocks registration.
    hibp_enabled: bool = True
    hibp_timeout_s: float = 3.0

    # Usernames (N5): length limits for NEW usernames. The migration keeps
    # its own frozen copy of these numbers on purpose.
    username_min_length: int = 3
    username_max_length: int = 20

    # Email (N5): which sender implementation to use. Only "console" exists
    # for now (it prints the message, links included, to the server's stdout).
    email_backend: str = "console"

    # Email tokens (N5): how long a single-use link stays valid, in minutes.
    # Verification is generous (the mail may be read tomorrow). Reset is short
    # because it is an account-takeover key, and OWASP says under 24 h, so a
    # value above 1440 fails at startup.
    verify_email_token_ttl_minutes: int = Field(default=1440, ge=1)
    reset_password_token_ttl_minutes: int = Field(default=30, ge=1, le=1440)

    # Forgot-password cooldown (N5): minimum seconds between reset emails for
    # the SAME account. Stops someone using our endpoint to flood a victim's
    # inbox (slowapi limits per IP, which an attacker can rotate). The floor
    # of 1 prevents 0, which would disable the protection silently.
    reset_password_cooldown_s: int = Field(default=60, ge=1)

    # Base URL for links inside emails. NEVER derived from the request's Host
    # header (host-header injection). Must be the real https origin in production.
    frontend_base_url: str = "http://localhost:5173"


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