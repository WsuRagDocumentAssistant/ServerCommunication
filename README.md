# ai_rag_comm — 내부 통신 라이브러리

RAG 시스템 전체 아키텍처 중 **내부 통신(LLM API / Local LLM / DB) 계층만** 구현된 pip 패키지입니다.
`RAG_Router`(Gateway)가 관리하는 별도 저장소이며, 이 프로젝트는 Gateway와 **같은 파이썬 프로세스**에
`import`되어 실제 작업(GPT 호출, 로컬 LLM 소켓 호출, DB 조회)을 처리하는 라이브러리입니다.
자체 HTTP 서버/엔드포인트는 없으며, Gateway와의 큐 연결은 이 프로젝트 담당자가 아닌 별도 담당자가 관리합니다.

* Python 3.11.5
* 순수 라이브러리 (FastAPI/uvicorn 없음) — `pip install -e .`로 설치해서 임포트해서 사용
* 커스텀 데코레이터/레지스트리 없음 — 각 통신은 인터페이스를 구현한 평범한 클래스로 직접 호출

---

## 지원하는 통신 3가지

1. **LLM API 호출** — GPT(OpenAI)만 지원
2. **Local LLM 호출** — 같은 K8s 네임스페이스 내 로컬 LLM Pod와 TCP 소켓 통신
3. **DB 호출** — PostgreSQL 조회/저장

그 외(Auth, SSO, 파일 업로드, Health 체크, SSE/WebSocket, 커스텀 라우팅 데코레이터)는 전부 삭제되어 있습니다.
HTTP로 노출된 엔드포인트는 없으며, 3가지 통신은 라이브러리 코드로 직접 호출하는 형태로만 존재합니다.

---

## 폴더 구조

```
pyproject.toml                   # pip 패키징 설정 (패키지명: ai-rag-comm)
requirements.txt                 # 로컬 개발용 의존성 목록
examples/
└── basic_usage.py               # Controller/Channel 직접 사용 예시 (서버 아님)

src/ai_rag_comm/                 # import 대상 패키지 (import ai_rag_comm)
├── __init__.py                  # 공개 API 재노출 (Controller, RestChannel, SocketChannel, ...)
├── core/
│   └── controller.py            # DB 초기화 + LLM 설정 노출
│
├── services/                    # 실제로 일을 처리하는 코드
│   ├── llm_api/
│   │   └── openai_service.py    #   GPT(OpenAI) 클라이언트
│   └── channels/
│       ├── transport.py         #   Transport (REST, SOCKET)
│       ├── rest_channel.py      #   LLM API(GPT) 호출
│       └── socket_channel.py    #   로컬 LLM 소켓 호출
│
├── database/
│   └── database_service.py      # PostgreSQL 커넥션 풀
│
├── interface/                   # 각 통신이 반드시 지켜야 하는 추상 인터페이스
│   ├── base_channel_interface.py    #   BaseChannelInterface (call 계약)
│   ├── base_llm_api_interface.py    #   BaseLLMApiInterface
│   ├── base_database_interface.py   #   BaseDatabaseInterface
│   └── base_repository_interface.py #   BaseRepositoryInterface
│
├── schemas/                     # 데이터 객체(DTO) 정의
│   ├── llm_api_schemas.py       #   AIProvider(GPT만), ChatRequest, ChatResponse
│   └── db_schemas.py            #   DB 데이터 객체 정의 자리 (스키마 미확정, 비어 있음)
│
└── helpers/
    ├── config_helper.py         # config.json + .env 로딩
    ├── log_helper.py            # 로깅 설정 (KST 타임존 포맷)
    └── response_helper.py       # 공통 응답 포맷 헬퍼
```

> 모든 서브 패키지(`core`, `services`, `database`, `interface`, `schemas`, `helpers`)는
> `ai_rag_comm` 하나의 최상위 네임스페이스 아래에 있습니다. 최상위에 `core`/`services` 같은
> 흔한 이름을 그대로 노출하면 pip으로 다른 프로젝트에 설치했을 때 이름이 충돌할 수 있기 때문입니다.

---

## 설치 방법

Gateway(RAG_Router) 등 이 라이브러리를 쓰는 프로세스에서 pip으로 설치합니다. (아직 PyPI에는 올리지 않았고,
로컬 경로 또는 git 저장소를 직접 가리켜서 설치하는 방식)

```bash
# 로컬 경로에서 설치 (개발 중 수정사항이 바로 반영되는 editable 모드)
pip install -e /path/to/ai_rag_system

# 또는 git 저장소를 직접 가리켜서 설치
pip install git+https://github.com/<org>/ai_rag_system.git
```

설치하면 `import ai_rag_comm`으로 바로 쓸 수 있습니다. `config.json`/`.env`는 이 저장소 루트에 있는 것을
그대로 쓰거나, 설치한 쪽 프로젝트 루트에 동일한 형식으로 준비해두면 됩니다 (아래 [환경 설정](#환경-설정) 참고).

---

## 빠른 시작

설치 후 실제로 쓰는 흐름은 3단계입니다: **① 설정 로드 → ② Controller 초기화 → ③ 통신 채널 호출**.

```python
import asyncio
from ai_rag_comm import Controller, RestChannel, SocketChannel, AIProvider, load_config, setup_logging

async def main():
    # ① config.json + .env 로드
    config = load_config()
    setup_logging(config.server.log_level)

    # ② Controller 초기화 (DB 커넥션 풀 준비) — 프로세스 시작 시 한 번만
    controller = Controller(config=config)
    await controller.init()

    try:
        services = controller.get_services()  # {"db": ..., "llm_api_config": ..., "local_llm_config": ...}

        # ③ 필요한 통신을 그때그때 호출
        gpt = RestChannel(services["llm_api_config"], AIProvider.GPT)
        answer = await gpt.call({"prompt": "안녕", "max_tokens": 256}, stream=False)

        local = SocketChannel(
            services["local_llm_config"].host,
            services["local_llm_config"].port,
            services["local_llm_config"].timeout,
        )
        local_answer = await local.call({"prompt": "안녕"}, stream=False)

        rows = await services["db"].fetch("SELECT 1")

        print(answer, local_answer, rows)
    finally:
        # 프로세스 종료 시 한 번만 (DB 커넥션 풀 정리)
        await controller.close()

asyncio.run(main())
```

- 그대로 실행해보고 싶으면 저장소 안의 [`examples/basic_usage.py`](examples/basic_usage.py)를 실행하면 됩니다.
  ```bash
  pip install -r requirements.txt
  python examples/basic_usage.py
  ```
- **Gateway(RAG_Router)에서 쓸 때**: `Controller.init()`/`.close()`는 Gateway 프로세스의 시작/종료 시점(예: FastAPI
  `lifespan`)에서 한 번씩만 호출하고, `RestChannel`/`SocketChannel`은 요청이 들어올 때마다 필요한 곳에서 바로
  인스턴스화해서 씁니다. Gateway와 이 라이브러리는 반드시 **같은 파이썬 프로세스**여야 동작합니다.

---

## 통신 사용법

### 1. LLM API 호출 (GPT만)

```python
from ai_rag_comm import RestChannel, AIProvider

channel = RestChannel(llm_api_config, AIProvider.GPT, "gpt-5.5")
response = await channel.call({"prompt": "프롬프트", "max_tokens": 1024}, stream=False)
```

- `ai_rag_comm/services/channels/rest_channel.py`의 `PROVIDER_REGISTRY`에는 `AIProvider.GPT` 하나만 등록되어 있음
- 실제 OpenAI SDK 호출은 `ai_rag_comm/services/llm_api/openai_service.py`의 `OpenAIService`가 담당

### 2. Local LLM 호출

```python
from ai_rag_comm import SocketChannel

channel = SocketChannel(local_llm_config.host, local_llm_config.port, local_llm_config.timeout)
response = await channel.call({"prompt": "프롬프트"}, stream=False)
```

- 요청마다 TCP 연결을 열고 닫는 무상태 방식 (연결 생명주기 관리 없음)

### 3. DB 호출

```python
rows = await services["db"].fetch("SELECT * FROM table WHERE id = $1", 1)
```

- `ai_rag_comm/database/database_service.py` — `fetch`/`fetchrow`/`fetchval`/`execute`/`executemany`

두 채널 모두 커스텀 데코레이터/레지스트리 없이 **평범한 클래스를 직접 인스턴스화**해서 씁니다
(예전 `@Channel(Transport.REST)` 같은 데코레이터 방식은 제거됨).

---

## 환경 설정

값 하나당 아래 순서로 결정됩니다: **환경변수(.env) > config.json**

- `config.json`: 비밀값이 아닌 구조적 기본값 (서버 host/port, LLM 기본 모델명 등). git에 커밋됨.
- `.env`: 비밀값 (API 키, DB 비밀번호 등). git에 커밋하지 않음.

### config.json

```json
{
  "server": { "log_level": "INFO" },
  "local_llm": { "host": "10.101.96.71", "port": 8001, "timeout": 30.0 },
  "database": { "host": "/tmp", "port": 5432, "name": "ragdb", "pool_min": 2, "pool_max": 10, "auto_connect": true },
  "llm_api": { "default_models": { "gpt": "gpt-5.5" } }
}
```

### .env

```env
OPENAI_API_KEY=sk-...
DB_USER=raguser
DB_PASSWORD=...
```

---

## 변경 이력

이번 작업에서 `RAG_Router`(Gateway) 저장소와 네이밍/폴더 스타일을 맞추고, 3가지 통신(LLM API-GPT / Local LLM / DB)만 남도록 정리함:

- **폴더/파일명 스타일 통일**
  - `interfaces/` → `interface/`
  - `utils/` → `helpers/`, `config_loader.py` → `config_helper.py`
  - `schemas/`는 유지하되 DB 데이터 객체를 정의할 수 있도록 `db_schemas.py` 자리 추가 (현재는 비어 있음)
- **커스텀 어노테이션/레지스트리 제거**
  - `services/channels/channel_registry.py`(`@Channel`), `core/routers/`(`@Route`, `route_registry.py`, `route_dispatcher.py`) 전부 삭제
  - `RestChannel`/`SocketChannel`은 이제 데코레이터 없이 직접 인스턴스화해서 사용
- **그 외 정리**: Auth/SSO/파일 업로드/Health 라우트, SSE/WebSocket, Claude/Gemini 지원 삭제 (이전 변경 이력에서 이미 정리됨)

이후 작업에서 HTTP 라우트가 0개인 상태(FastAPI 앱을 유지할 이유가 없음)를 확인하고, 이 저장소 자체를
pip 패키지(`ai-rag-comm`)로 배포 가능하도록 전환함:

- **FastAPI/uvicorn 제거**: `core/app.py`(FastAPI `App`) 삭제, `requirements.txt`에서 `fastapi`/`uvicorn` 제거
- **`server_starter.py` → `examples/basic_usage.py`**: 서버 구동 대신 `Controller`를 직접 `init()`/`close()`하는 사용 예시로 전환
- **단일 패키지 네임스페이스로 재구성**: `src/{core,services,database,interface,schemas,helpers}` → `src/ai_rag_comm/{...}` 하나로 통합
  (흔한 이름의 최상위 모듈이 pip 설치 시 다른 패키지와 충돌하는 것을 방지)
- **`pyproject.toml` 추가**: `pip install -e .`로 로컬/다른 저장소에서 설치 가능하도록 패키징 (패키지명 `ai-rag-comm`, import명 `ai_rag_comm`)
- **`ServerConfig`에서 미사용 `host`/`port` 제거**: 자체 HTTP 서버가 없으므로 `log_level`만 유지
