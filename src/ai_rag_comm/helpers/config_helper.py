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
class SchoolOracleConfig:
    enabled: bool
    host: str
    port: int
    service_name: str
    user: str
    password: str
    owner: str
    pool_min: int
    pool_max: int


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
    school_oracle: SchoolOracleConfig
    local_llm: LocalLLMConfig
    llm_api: LLMApiConfig


def _env(name: str, default: str = "") -> str:
    """환경변수 값. 앞뒤 공백과 감싼 따옴표를 벗긴다.

    .env 는 python-dotenv 가 SCHOOL_SYNC_ENABLED="true" 의 따옴표를 벗겨 주지만, 같은 줄을 k8s secret 에
    옮기면 따옴표까지 값이 된다("\"true\""). 그러면 켜짐 판정도, 호스트·계정 접속도 실패한다.
    """
    value = os.environ.get(name, default).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def _flag(name: str) -> bool:
    """켜짐/꺼짐 환경변수. true / 1 / yes / on (대소문자 무시)이면 켜짐."""
    return _env(name, "false").lower() in ("true", "1", "yes", "on")


def _local_llm_headers(local_llm: dict) -> dict:
    """로컬 LLM 요청 헤더. 인증 헤더(x-user-id 등)라 config.json 이 아니라 환경변수로 받는다.

    LOCAL_LLM_HEADERS 에 JSON 객체로 넣는다(예: {"x-user-id": "..."}, k8s secret).
    예전에는 config.json 에 값이 들어 있어 저장소를 본 사람이면 누구나 그 값을 알 수 있었다.
    환경변수가 없으면 config.json 의 headers 를 쓴다(로컬 개발용 — 저장소에는 비워 둔다).
    """
    raw = _env("LOCAL_LLM_HEADERS")
    if raw:
        try:
            value = json.loads(raw)
        except ValueError as e:
            raise ValueError("LOCAL_LLM_HEADERS 는 JSON 객체여야 합니다") from e
        if not isinstance(value, dict):
            raise ValueError("LOCAL_LLM_HEADERS 는 JSON 객체여야 합니다")
        return {str(k): str(v) for k, v in value.items()}
    return local_llm.get("headers") or {}


def load_config(root: Optional[Union[str, Path]] = None) -> Config:
    root = Path(root or os.environ.get("APP_ROOT") or Path.cwd())

    load_dotenv(root / ".env")

    with open(root / "config.json", encoding="utf-8-sig") as f:
        raw = json.load(f)

    s = raw["server"]
    db = raw["database"]
    oracle = raw.get("school_oracle", {})
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
            user=_env("DB_USER"),
            password=_env("DB_PASSWORD"),
            pool_min=db["pool_min"],
            pool_max=db["pool_max"],
            auto_connect=db["auto_connect"],
        ),
        school_oracle=SchoolOracleConfig(
            enabled=_flag("SCHOOL_SYNC_ENABLED"),
            host=_env("SCHOOL_ORACLE_HOST"),
            port=int(_env("SCHOOL_ORACLE_PORT", "1521") or "1521"),
            service_name=_env("SCHOOL_ORACLE_SERVICE_NAME"),
            user=_env("SCHOOL_ORACLE_USER"),
            password=_env("SCHOOL_ORACLE_PASSWORD"),
            owner=_env("SCHOOL_ORACLE_OWNER"),
            pool_min=oracle.get("pool_min", 1),
            pool_max=oracle.get("pool_max", 4),
        ),
        local_llm=LocalLLMConfig(
            base_url=local_llm["base_url"],
            model=local_llm["model"],
            timeout=local_llm["timeout"],
            headers=_local_llm_headers(local_llm),
        ),
        llm_api=LLMApiConfig(
            openai_api_key=_env("OPENAI_API_KEY"),
            anthropic_api_key=_env("ANTHROPIC_API_KEY"),
            gemini_api_key=_env("GEMINI_API_KEY"),
            default_models=llm_api["default_models"],
            timeout=llm_api.get("timeout", 60.0),
        ),
    )
