"""
config_helper.py
config.json + .env 를 읽어 Config 객체로 반환

- config.json : 비밀이 아닌 설정 (포트, 풀 크기, 모델명 등)
- .env        : 시크릿 (API 키, DB 비밀번호 등)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv


@dataclass
class ServerConfig:
    log_level: str


@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_min: int
    pool_max: int
    auto_connect: bool


@dataclass
class LocalLLMConfig:
    base_url: str
    model: str
    timeout: float
    headers: dict = field(default_factory=dict)


@dataclass
class LLMApiConfig:
    openai_api_key: str
    anthropic_api_key: str
    gemini_api_key: str
    default_models: dict
    timeout: float


@dataclass
class Config:
    server: ServerConfig
    database: DatabaseConfig
    local_llm: LocalLLMConfig
    llm_api: LLMApiConfig


def load_config(root: Optional[Union[str, Path]] = None) -> Config:
    root = Path(root or os.environ.get("APP_ROOT") or Path.cwd())

    load_dotenv(root / ".env")

    with open(root / "config.json", encoding="utf-8-sig") as f:
        raw = json.load(f)

    s = raw["server"]
    db = raw["database"]
    local_llm = raw["local_llm"]
    llm_api = raw["llm_api"]

    return Config(
        server=ServerConfig(
            log_level=s["log_level"],
        ),
        database=DatabaseConfig(
            host=db["host"],
            port=db["port"],
            name=db["name"],
            user=os.environ.get("DB_USER", ""),
            password=os.environ.get("DB_PASSWORD", ""),
            pool_min=db["pool_min"],
            pool_max=db["pool_max"],
            auto_connect=db["auto_connect"],
        ),
        local_llm=LocalLLMConfig(
            base_url=local_llm["base_url"],
            model=local_llm["model"],
            timeout=local_llm["timeout"],
            headers=local_llm.get("headers", {}),
        ),
        llm_api=LLMApiConfig(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            default_models=llm_api["default_models"],
            timeout=llm_api.get("timeout", 60.0),
        ),
    )
