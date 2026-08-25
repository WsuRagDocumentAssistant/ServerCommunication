# ai_rag_comm — 내부 통신 라이브러리

RAG 시스템 전체 아키텍처 중 **내부 통신(LLM API / Local LLM / DB) 계층만** 구현된 pip 패키지입니다.
`RAG_Router`(Gateway)가 관리하는 별도 저장소이며, 이 프로젝트는 Gateway와 **같은 파이썬 프로세스**에
`import`되어 실제 작업(GPT 호출, 로컬 LLM 호출, DB 조회)을 처리하는 라이브러리입니다.
자체 HTTP 서버/엔드포인트는 없으며, Gateway와의 큐 연결은 이 프로젝트 담당자가 아닌 별도 담당자가 관리합니다.

* Python 3.11.5
* 순수 라이브러리 (FastAPI/uvicorn 없음) — `pip install -e .`로 설치해서 임포트해서 사용
* 커스텀 데코레이터/레지스트리 없음 — 각 통신은 인터페이스를 구현한 평범한 클래스로 직접 호출

---

## 지원하는 통신 3가지

1. **LLM API 호출** — GPT(OpenAI) / Claude(Anthropic) / Gemini(Google) 지원 (`RestChannel`)
2. **Local LLM 호출** — 사내 KServe로 서빙되는 OpenAI 호환 HTTP 엔드포인트 호출 (`LocalLLMChannel`)
3. **DB 호출** — PostgreSQL 조회/저장

1번과 2번은 겉보기엔 둘 다 OpenAI 호환 HTTP라 하나의 선택기로 묶을 수도 있어 보이지만, 인증 방식이
다르고(API 키 vs 커스텀 헤더) 클라이언트 캐싱/설정 스키마가 서로 다른 전제를 깔고 있어서 **의도적으로
분리된 채널**로 유지합니다. GPT를 고를 땐 `RestChannel`, 로컬 LLM을 부를 땐 `LocalLLMChannel`을 씁니다.

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
├── __init__.py                  # 공개 API 재노출 (Controller, RestChannel, LocalLLMChannel, ...)
├── core/
│   └── controller.py            # DB 초기화(선택) + LLM 설정 노출
│
├── services/                    # 실제로 일을 처리하는 코드
│   ├── llm_api/
│   │   ├── openai_service.py    #   OpenAI 호환 HTTP 클라이언트 (base_url/headers로 다른 엔드포인트도 가리킴)
│   │   ├── claude_service.py    #   Claude(Anthropic) 클라이언트
│   │   └── gemini_service.py    #   Gemini(Google, google-genai) 클라이언트
│   └── channels/
│       ├── rest_channel.py      #   LLM API(GPT) 호출
│       └── local_llm_channel.py #   로컬 LLM(KServe, OpenAI 호환) 호출
│
├── database/
│   └── database_service.py      # PostgreSQL 커넥션 풀 (asyncpg 미설치 시 생성 시점에 RuntimeError)
│
├── interface/                   # 각 통신이 반드시 지켜야 하는 추상 인터페이스
│   ├── base_channel_interface.py    #   BaseChannelInterface (call 계약)
│   ├── base_llm_api_interface.py    #   BaseLLMApiInterface
│   ├── base_database_interface.py   #   BaseDatabaseInterface
│   └── base_repository_interface.py #   BaseRepositoryInterface
│
├── schemas/                     # 데이터 객체(DTO) 정의
│   ├── llm_api_schemas.py       #   AIProvider(GPT/CLAUDE/GEMINI), ChatRequest, ChatResponse
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
pip install "git+https://github.com/<org>/ai_rag_system.git"
```

필요한 provider/기능만 extra로 골라 설치합니다. `RestChannel`/`LocalLLMChannel`(GPT, 로컬 LLM)은 기본
의존성만으로 동작하고, Claude/Gemini/DB는 실제로 그 클라이언트를 생성하는 순간에만 필요합니다 — extra
없이 설치해도 import 자체는 되고, 안 쓰는 provider의 SDK가 없어도 다른 provider 호출에는 영향 없음.

```bash
pip install -e "/path/to/ai_rag_system[claude,gemini,db]"
```

| extra | 설치되는 패키지 | 없으면 |
|---|---|---|
| `claude` | `anthropic` | `RestChannel(..., AIProvider.CLAUDE)` 생성 시 `RuntimeError` |
| `gemini` | `google-genai` | `RestChannel(..., AIProvider.GEMINI)` 생성 시 `RuntimeError` |
| `db` | `asyncpg` | `DatabaseService` 생성 시 `RuntimeError` (`Controller.init()`은 `db=None`으로 계속 진행) |

설치하면 `import ai_rag_comm`으로 바로 쓸 수 있습니다. `config.json`/`.env`는 이 저장소 루트에 있는 것을
그대로 쓰거나, 설치한 쪽 프로젝트 루트에 동일한 형식으로 준비해두면 됩니다 (아래 [환경 설정](#환경-설정) 참고).
`load_config()`는 기본적으로 현재 작업 디렉터리(`Path.cwd()`)에서 `config.json`/`.env`를 찾으며,
`load_config(root=...)`로 직접 지정하거나 `APP_ROOT` 환경변수로 지정할 수도 있습니다.

---

## 빠른 시작

설치 후 실제로 쓰는 흐름은 3단계입니다: **① 설정 로드 → ② Controller 초기화 → ③ 통신 채널 호출**.

```python
import asyncio
from ai_rag_comm import Controller, RestChannel, LocalLLMChannel, AIProvider, load_config, setup_logging

async def main():
    # ① config.json + .env 로드
    config = load_config()
    setup_logging(config.server.log_level)

    # ② Controller 초기화 (DB 커넥션 풀 준비) — 프로세스 시작 시 한 번만
    #    asyncpg가 없거나 DB가 필요 없으면 services["db"]는 None이 됨
    controller = Controller(config=config)
    await controller.init()

    try:
        services = controller.get_services()  # {"db": ..., "llm_api_config": ..., "local_llm_config": ...}

        # ③ 필요한 통신을 그때그때 호출
        gpt = RestChannel(services["llm_api_config"], AIProvider.GPT)
        answer = await gpt.call({"prompt": "안녕", "max_tokens": 256}, stream=False)

        local_cfg = services["local_llm_config"]
        local = LocalLLMChannel(local_cfg.base_url, local_cfg.model, local_cfg.headers, local_cfg.timeout)
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
  `lifespan`)에서 한 번씩만 호출하고, `RestChannel`/`LocalLLMChannel`은 요청이 들어올 때마다 필요한 곳에서 바로
  인스턴스화해서 씁니다. Gateway와 이 라이브러리는 반드시 **같은 파이썬 프로세스**여야 동작합니다.

---

## 통신 사용법

### 1. LLM API 호출 (GPT / Claude / Gemini)

```python
from ai_rag_comm import RestChannel, AIProvider

channel = RestChannel(llm_api_config, AIProvider.GPT, "gpt-5.5")
response = await channel.call(
    {"prompt": "프롬프트", "max_tokens": 1024, "temperature": 0.0},
    stream=False,
)

# provider만 바꾸면 나머지 호출부는 동일
claude = RestChannel(llm_api_config, AIProvider.CLAUDE, "claude-sonnet-4-6")
gemini = RestChannel(llm_api_config, AIProvider.GEMINI, "gemini-3.5-flash")
```

- `ai_rag_comm/services/channels/rest_channel.py`의 `PROVIDER_REGISTRY`에 `AIProvider.GPT`/`CLAUDE`/`GEMINI`
  세 개가 등록되어 있고, 각각 `config.llm_api.default_models["gpt"|"claude"|"gemini"]`와
  `openai_api_key`/`anthropic_api_key`/`gemini_api_key`를 사용함
- 실제 SDK 호출은 `services/llm_api/`의 `OpenAIService`/`ClaudeService`/`GeminiService`가 각각 담당
- `temperature`는 생략 가능(`payload`에 안 넣으면 API에 아예 안 보냄). 일부 모델(`gpt-5.5`)은
  `temperature=0`을 거부하므로, 그런 모델을 쓸 때는 지정하지 않는 편이 안전함

#### 구조화 출력 (`response_format`)

프롬프트로 "JSON으로 답해"라고만 요구하면 모델이 코드펜스나 설명을 앞뒤에 붙여서 파싱이 깨질 수 있습니다.
`response_format`에 순수 JSON Schema(object)를 넘기면 API가 스키마를 강제해서 응답이 항상 그 스키마를
따르는 JSON 텍스트가 됩니다 (GPT/로컬 LLM/Claude/Gemini 넷 다 지원 확인).

```python
schema = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
    "required": ["name", "email"],
    "additionalProperties": False,
}

response = await channel.call(
    {"prompt": "이름과 이메일을 추출해줘: ...", "response_format": schema},
    stream=False,
)
import json
data = json.loads(response)  # 스키마를 따르는 JSON이 보장됨
```

- `response_format`은 provider에 상관없이 **항상 순수 JSON Schema dict**로 넘김. 각 서비스가 내부에서
  provider별 파라미터로 감싸서 보냄 — GPT/로컬 LLM은 `response_format={"type": "json_schema", ...}`,
  Claude는 `output_config={"format": {"type": "json_schema", ...}}`, Gemini는
  `response_mime_type="application/json"` + `response_json_schema=...`
- 생략하면(`None`) 기존처럼 평문 응답. 스키마를 강제할 필요가 있는 추출/분류 작업에만 사용

### 2. Local LLM 호출

```python
from ai_rag_comm import LocalLLMChannel

channel = LocalLLMChannel(
    local_llm_config.base_url,   # 예: http://117.16.166.22/v1
    local_llm_config.model,      # 예: gemma-4-12B-it
    local_llm_config.headers,    # 예: {"x-user-id": "npark-01"}
    local_llm_config.timeout,
)
response = await channel.call({"prompt": "프롬프트", "temperature": 0.0}, stream=False)
```

- 사내 로컬 LLM은 KServe로 서빙되는 **OpenAI 호환 HTTP 엔드포인트**라 내부적으로 `OpenAIService`를 그대로
  재사용하지만, 인증이 API 키가 아니라 커스텀 헤더라서 `RestChannel`/`AIProvider`와는 **별개의 채널**로 분리함
- `temperature=0`처럼 GPT가 거부하는 옵션도 로컬 모델에서는 받아준다 (같은 입력에 같은 결과가 필요한
  추출 작업 등에 유용)
- `response_format`도 동일하게 지원 (내부적으로 `OpenAIService`를 그대로 씀)

### 3. DB 호출

```python
rows = await services["db"].fetch("SELECT * FROM table WHERE id = $1", 1)
```

- `ai_rag_comm/database/database_service.py` — `fetch`/`fetchrow`/`fetchval`/`execute`/`executemany`
- DB를 쓰지 않는다면 `pip install ai-rag-comm`(⁠`[db]` extra 없이)만으로도 LLM API/Local LLM 호출은 그대로 동작함

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
  "local_llm": {
    "base_url": "http://117.16.166.22/v1",
    "model": "gemma-4-12B-it",
    "timeout": 30.0,
    "headers": { "x-user-id": "npark-01" }
  },
  "database": { "host": "/tmp", "port": 5432, "name": "ragdb", "pool_min": 2, "pool_max": 10, "auto_connect": true },
  "llm_api": {
    "default_models": {
      "gpt": "gpt-5.5",
      "claude": "claude-sonnet-4-6",
      "gemini": "gemini-3.5-flash"
    }
  }
}
```

### .env

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
DB_USER=raguser
DB_PASSWORD=...
```

쓰지 않는 provider의 키는 빈 값으로 둬도 됩니다 — 그 provider를 실제로 호출하기 전까지는 참조되지 않습니다.

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

실제로 이 라이브러리를 가져다 쓰려던 쪽(`ragmodul`)에서 막혔던 지점들을 반영해서 추가로 정리함:

- **`OpenAIService`에 `base_url`/`default_headers`/`timeout` 추가**: `AsyncOpenAI`가 이미 지원하는 옵션을
  감싸는 쪽에서 막고 있었음. 이제 OpenAI 호환 HTTP 엔드포인트라면 어디든 가리킬 수 있음
- **로컬 LLM을 소켓 → HTTP로 전환**: 실제 로컬 LLM이 KServe로 서빙되는 OpenAI 호환 HTTP 엔드포인트로
  바뀌어서, `SocketChannel`/`Transport` enum(둘 다 소켓 전제)을 삭제하고 `LocalLLMChannel`을 새로 추가함.
  `LLM API(GPT) 선택기(RestChannel/AIProvider)와는 의도적으로 분리` — 인증 방식(API 키 vs 커스텀 헤더)이
  다르고, 같은 레지스트리/캐시에 묶으면 헤더가 캐시에 안 반영되는 문제가 생기기 때문
- **`temperature` 파라미터 추가**: `payload`/`chat()`/`stream_chat()` 세 층 모두에서 빠져 있던 걸 추가.
  `None`이면 API에 안 보냄 (일부 모델은 `temperature` 인자 자체를 거부함)
- **`load_config(root=...)` 도입**: 기존엔 파일 내 상대 경로로 저장소 루트를 추정해서, `pip install`로
  설치하면 엉뚱한 경로(`site-packages` 하위)를 가리켰음. 이제 `Path.cwd()`가 기본값이고, `root` 인자나
  `APP_ROOT` 환경변수로 직접 지정 가능. `DB_USER`/`DB_PASSWORD`도 없으면 빈 문자열로 처리해서 LLM만 쓰는
  경우에 `KeyError`로 죽지 않게 함
- **버전 핀 완화**: `pydantic`/`openai`/`python-dotenv`를 `==`에서 `>=`로 풀어서, 이 라이브러리를 가져다
  쓰는 프로젝트의 다른 의존성과 충돌할 여지를 줄임
- **`asyncpg`를 `[db]` extra로 분리**: `DatabaseService`의 `import asyncpg`를 지연 임포트로 바꿔서,
  LLM API/Local LLM 호출만 쓰는 경우 `asyncpg` 없이도 `import ai_rag_comm`과 `Controller.init()`이 동작함
  (DB가 필요 없으면 `services["db"]`가 `None`)

**Claude/Gemini 재추가**: `AIProvider`에 `CLAUDE`/`GEMINI`를 다시 추가하고, `PROVIDER_REGISTRY`에
`ClaudeService`/`GeminiService`를 등록함 (이전 "GPT만 남도록 대폭 축소" 단계에서 삭제됐던 걸 복원).

- `ClaudeService`는 `anthropic.AsyncAnthropic` 사용, 응답에서 `type == "text"`인 블록만 이어붙여 파싱
  (thinking 등 다른 타입 블록이 섞여도 안전하게 텍스트만 추출)
- `GeminiService`는 `google-generativeai`가 아니라 후속 통합 SDK `google-genai`(`google.genai.Client`) 사용 —
  `google-generativeai`는 지원 종료(EOL)되어 실제로 `FutureWarning`이 뜨는 걸 확인하고 교체함. 네이티브
  비동기 API(`client.aio.models.generate_content[_stream]`)를 그대로 씀 (기존처럼 스레드풀로 감싸지 않음)
- `LLMApiConfig`에 `anthropic_api_key`/`gemini_api_key` 추가, `config.json`의 `default_models`에
  `claude`/`gemini` 항목 추가
- `anthropic`/`google-genai`도 `[claude]`/`[gemini]` extra로 분리 — 안 쓰는 provider의 SDK를 강제로
  설치하지 않아도 됨 (openai_service.py와 동일한 지연 임포트 + `RuntimeError` 패턴)

**`response_format`(구조화 출력) 추가**: `chat()`/`stream_chat()`/`RestChannel`/`LocalLLMChannel`이
`response_format`(순수 JSON Schema dict)을 받아서 각 provider의 구조화 출력 파라미터로 감싸 전달함
(GPT/로컬 LLM `response_format={"type": "json_schema", ...}`, Claude
`output_config={"format": {"type": "json_schema", ...}}`, Gemini `response_mime_type` +
`response_json_schema`). 전엔 프롬프트로 JSON을 요구하고 평문에서 파싱해야 해서 코드펜스나 설명이
섞이면 깨졌는데, 이제 API가 스키마를 보장함. `None`이면 기존처럼 평문 응답.
