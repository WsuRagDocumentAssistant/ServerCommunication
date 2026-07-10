# AI RAG System

멀티 AI 프로바이더 + 로컬 LLM + PostgreSQL 기반의 RAG 게이트웨이 서버

---

## 기술 스택

- **Runtime**: Python 3.11
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 17 + pgvector (asyncpg)
- **AI Providers**: Claude (Anthropic) / GPT (OpenAI) / Gemini (Google)
- **Local LLM**: TCP Socket 통신 (같은 K8s 네임스페이스 내 Pod)
- **Auth**: JWT (RS256 / HS256) - FastAPI Depends
- **Protocol**: HTTP REST

---

## 프로젝트 구조

```
ai_rag_system/
├── config.json              # 서버 설정 (비밀값 제외)
├── .env                     # API 키, DB 크레덴셜 (Git 제외)
├── requirements.txt
│
└── src/
    ├── server_starter.py    # 진입점
    ├── core/
    │   ├── app.py           # FastAPI 앱 초기화
    │   ├── controller.py    # 인프라 / 서비스 생명주기 관리
    │   └── routers/
    │       ├── health_router.py  # /health
    │       ├── file_router.py   # /file/*
    │       └── auth_router.py   # /users/*
    ├── services/
    │   ├── llm_api_service.py  # LLMApiService 오케스트레이터 (PROVIDER_REGISTRY + get_llm_api)
    │   ├── llm_api/
    │   │   ├── claude_service.py  # ClaudeService (Anthropic SDK)
    │   │   ├── openai_service.py  # OpenAIService (OpenAI SDK)
    │   │   └── gemini_service.py  # GeminiService (google-generativeai SDK)
    │   ├── local_llm_service.py  # 로컬 LLM TCP 소켓 통신 (내부 호출)
    │   ├── sso_service.py   # SSO 토큰 검증 (외부 SSO 발급 토큰)
    │   └── auth_service.py  # 로그인 / 회원가입 / 자체 JWT 발급·검증 (인메모리)
    ├── database/
    │   └── database_service.py  # PostgreSQL 커넥션 풀
    ├── interfaces/
    │   ├── base_llm_api_interface.py      # BaseLLMApiInterface
    │   ├── base_local_llm_interface.py    # BaseLocalLLMInterface
    │   ├── base_database_interface.py     # BaseDatabaseInterface (Postgres 전용)
    │   └── base_repository_interface.py   # BaseRepositoryInterface (저장소 순수 계약)
    ├── schemas/             # Pydantic 요청/응답 모델 (llm_api_schemas.py, local_llm_schemas.py 등)
    └── utils/
        ├── auth_helper.py   # verify_token Depends (자체 JWT 검증)
        ├── config_loader.py
        ├── log_helper.py
        └── response_helper.py
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/file/upload` | hwpx 파일 업로드 |
| POST | `/users/login` | 로컬 로그인 (이메일/비밀번호) |
| POST | `/users/create/user` | 회원가입 |
| POST | `/users/logout` | 로그아웃 (Bearer 토큰 필요) |
| POST | `/users/sso/login` | SSO 로그인 (SSO 토큰 → 자체 JWT 발급) |

> AI / LLM 호출은 클라이언트에 직접 노출하지 않고 서비스 레이어에서 내부적으로 처리
> `/users/*` 는 로그인/SSO 로그인 성공 시 자체 서명 JWT를 발급하며, 이후 인증이 필요한 요청은 `Authorization: Bearer <token>` 헤더 사용
> 사용자 정보 및 활성 토큰은 서버 메모리에 저장되며, 서버 재시작 시 초기화됨 (영구 저장소 미적용)

---

## LLMApiService — 외부 LLM 호출 (내부 전용)

`LLMApiService`(`services/llm_api_service.py`)는 프로바이더 조회/생성만 담당하는 오케스트레이터이며,
Claude/GPT/Gemini 공식 SDK(`anthropic`, `openai`, `google-generativeai`)를 사용하는 실제 구현체는
`services/llm_api/`(`ClaudeService`, `OpenAIService`, `GeminiService`)에 분리되어 있다.

프로바이더별 클라이언트 클래스·설정 키는 `PROVIDER_REGISTRY`에 선언적으로 등록해두고
`get_llm_api(provider, model=None, api_key=None)`로 조회/생성한다. 새 프로바이더 추가 시
`services/llm_api/`에 클라이언트 클래스만 만들고 레지스트리에 한 줄만 등록하면 됨 (`if/elif` 분기 불필요).

```python
# 1. 프로바이더(+선택적 model/api_key 오버라이드)로 클라이언트 조회/생성
client = llm_api_service.get_llm_api(AIProvider.CLAUDE)                       # 기본 설정값 사용
client = llm_api_service.get_llm_api(AIProvider.CLAUDE, model="claude-opus-4-8")  # 모델 오버라이드
client = llm_api_service.get_llm_api(AIProvider.GPT, api_key="sk-user-own-key")   # API 키 오버라이드 (BYOK)

# 2. 실제 요청은 client에서 처리
response = await client.chat(prompt="...", model=None, max_tokens=1024)
```

동일한 `(provider, model, api_key)` 조합은 캐시된 클라이언트를 재사용한다.

개별 프로바이더 서비스가 필요하면 오케스트레이터를 거치지 않고 바로 가져다 쓸 수도 있음:

```python
from services import ClaudeService, OpenAIService, GeminiService
# 또는
from services.llm_api import ClaudeService
```

### config.json / .env 연결 구조

`get_llm_api()`가 `model`/`api_key`를 명시적으로 넘기지 않으면, `PROVIDER_REGISTRY`의
`api_key_field`/`model_key`로 `LLMApiConfig`(= `.env` + `config.json` 로드 결과)에서 기본값을 가져온다.

```
.env                              config_loader.py (LLMApiConfig)     config.json "llm_api.default_models"
─────────────────────             ──────────────────────────         ────────────────────────────────────
CLAUDE_API_KEY   ───────────────▶  claude_api_key                     "claude": "claude-sonnet-4-6" ──┐
OPENAI_API_KEY   ───────────────▶  openai_api_key                     "gpt": "gpt-5.5"                ├─▶ default_models
GEMINI_API_KEY   ───────────────▶  gemini_api_key                     "gemini": "gemini-3.5-flash" ───┘
```

즉 **`config.json`의 `llm_api.default_models` 값을 바꾸면 서버가 사용하는 기본 모델도 바뀐다**
(단, `load_config()`는 서버 시작 시 1회만 호출되므로 서버 재시작이 필요함 — 런타임 hot-reload는 지원하지 않음).

> `config.json`의 `local_llm` 섹션은 로컬 LLM Pod(TCP 소켓) 연결 설정(`LocalLLMConfig`)이며,
> `llm_api` 섹션은 외부 LLM API(Claude/GPT/Gemini) 설정(`LLMApiConfig`)이다.

---

## 환경 설정

### config.json

```json
{
  "server": { "host": "0.0.0.0", "port": 8000, "log_level": "INFO" },
  "local_llm": { "host": "127.0.0.1", "port": 11434, "timeout": 30.0, "auto_connect": false },
  "database": {
    "host": "/tmp",
    "port": 5432,
    "name": "ragdb",
    "pool_min": 2,
    "pool_max": 10,
    "auto_connect": true
  },
  "llm_api": {
    "default_models": {
      "claude": "claude-sonnet-4-6",
      "gpt": "gpt-5.5",
      "gemini": "gemini-3.5-flash"
    }
  }
}
```

### .env

```env
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

DB_USER=raguser
DB_PASSWORD=...

JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

---

## 실행 방법

```bash
pip install -r requirements.txt
python src/server_starter.py
```

---

## PostgreSQL 설정 (Kubeflow 환경)

PostgreSQL 17 + pgvector를 Kubeflow notebook 내부에서 운용.
데이터는 NFS PVC(`/home/jovyan/rag/postgresql/data`)에 영구 저장.
소켓 통신: `/tmp/.s.PGSQL.5432`

### 기동

```bash
pg_ctl -D /home/jovyan/rag/postgresql/data \
  -l /home/jovyan/rag/postgresql/logs/postgresql.log \
  start
```

### 접속

```bash
psql -h /tmp -U raguser -d ragdb
```

> Pod 재시작 후에는 위 `pg_ctl start` 명령을 다시 실행해야 함

---

## 인프라 설정 (현재 환경: Kubeflow on K8s)

### K8s Service

rag-0 Pod을 클러스터 내부에서 접근 가능하도록 Service 등록.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: rag-service
  namespace: ragsystem
spec:
  selector:
    app: rag
  ports:
    - port: 8000
      targetPort: 8000
EOF
```

- ClusterIP: `10.99.68.28`
- 네임스페이스 내 DNS: `rag-service.ragsystem.svc.cluster.local:8000`

### Cloudflare Tunnel (외부 접근)

cloudflared 바이너리는 NFS PVC에 저장하여 Pod 재시작 후에도 유지.

```bash
# 임시 터널 (테스트용 - 재실행 시 URL 변경됨)
/home/jovyan/rag/cloudflared tunnel --url http://localhost:8000

# 고정 도메인 터널 (Cloudflare 계정 + 도메인 필요)
/home/jovyan/rag/cloudflared tunnel run [터널이름]
```

> Pod 재시작 후 cloudflared 재실행 필요

### NFS PVC 마운트

| 경로 | 용도 |
|------|------|
| `/home/jovyan/rag/postgresql/data` | PostgreSQL 데이터 (영구 저장) |
| `/home/jovyan/rag/postgresql/logs` | PostgreSQL 로그 |
| `/home/jovyan/rag/uploads` | hwpx 파일 업로드 저장소 |
| `/home/jovyan/rag/cloudflared` | cloudflared 바이너리 |

---

## 새 서버 환경 마이그레이션 시 변경 필요 사항

현재는 Kubeflow notebook 내부에서 운용 중이며, 순수 K8s 환경으로 이전 시 아래 항목 변경 필요.

| 항목 | 현재 (Kubeflow) | 변경 후 (순수 K8s) |
|------|----------------|-------------------|
| PostgreSQL | notebook Pod 내부 설치 | 별도 StatefulSet으로 분리 |
| PostgreSQL 소켓 | Unix Socket `/tmp` | TCP `postgres-service:5432` |
| cloudflared | 수동 실행 | Deployment로 상시 운용 |
| 스토리지 | NFS PVC | K8s 네이티브 PVC |
| config.json `database.host` | `/tmp` | `postgres-service` |

---

## 아키텍처

```
Client (HTTP)
      │
 ┌────▼──────────────────────────────┐
 │  FastAPI (app.py)                 │
 │  CORS / Request Logging           │
 │  자체 JWT 검증 (verify_token)     │
 └────┬──────────────────────────────┘
      │
 ┌────▼──────────────────────────────┐
 │  Controller                       │
 │  인프라 / 서비스 생명주기 관리     │
 └────┬──────────────┬───────────────┘
      │              │
 ┌────▼─────────────┐  ┌─────▼──────────────┐
 │LLMApiService     │  │ LocalLLMService    │
 │(PROVIDER_REGISTRY│  │ 로컬 LLM Pod       │
 │ + get_llm_api)   │  │ TCP Socket         │
 └────┬─────────────┘  └────────────────────┘
      │
 ┌────▼──────────────────────┐
 │ services/llm_api/         │
 │ ClaudeService,            │
 │ OpenAIService,            │  
 │ GeminiService             │
 └────┬──────────────────────┘
      │
 ┌────▼──────────────┐
 │ External AI APIs  │
 └───────────────────┘

 ┌──────────────────────────┐
 │ DatabaseService          │
 │ PostgreSQL 17 + pgvector │
 │ Unix Socket /tmp         │
 └──────────────────────────┘
```
