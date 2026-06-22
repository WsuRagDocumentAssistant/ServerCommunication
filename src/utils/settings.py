"""
settings.py
환경 설정 - .env 파일 기반
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 서버 ──────────────────────────────────
    host: str
    port: int
    log_level: str

    # ── 외부 AI API 키 ─────────────────────────
    claude_api_key: str
    openai_api_key: str
    gemini_api_key: str

    # ── 로컬 LLM 소켓 ──────────────────────────
    llm_host: str
    llm_port: int
    llm_timeout: float
    llm_auto_connect: bool

    # ── PostgreSQL ─────────────────────────────
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    db_pool_min: int
    db_pool_max: int
    db_auto_connect: bool

    # ── SSO ────────────────────────────────────
    sso_issuer_url: str = ""
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_algorithm: str = "RS256"