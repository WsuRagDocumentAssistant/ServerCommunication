"""
config_helper.py
config.json + .env 를 읽어 Config 객체로 반환

- config.json : 비밀이 아닌 설정 (포트, 풀 크기, 모델명 등)
- .env        : 시크릿 (API 키, DB 비밀번호 등)
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[3]


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
    host: str
    port: int
    timeout: float


@dataclass
class LLMApiConfig:
    openai_api_key: str
    default_models: dict


@dataclass
class Config:
    server: ServerConfig
    database: DatabaseConfig
    local_llm: LocalLLMConfig
    llm_api: LLMApiConfig


def load_config() -> Config:
    load_dotenv(_ROOT / ".env")

    with open(_ROOT / "config.json", encoding="utf-8-sig") as f:
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
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            pool_min=db["pool_min"],
            pool_max=db["pool_max"],
            auto_connect=db["auto_connect"],
        ),
        local_llm=LocalLLMConfig(
            host=local_llm["host"],
            port=local_llm["port"],
            timeout=local_llm["timeout"],
        ),
        llm_api=LLMApiConfig(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            default_models=llm_api["default_models"],
        ),
    )
