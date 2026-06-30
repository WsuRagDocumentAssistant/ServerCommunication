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
    │       └── file_router.py   # /file/*
    ├── services/
    │   ├── ai_service.py    # Claude / GPT / Gemini 클라이언트 (내부 호출)
    │   ├── llm_service.py   # 로컬 LLM TCP 소켓 통신 (내부 호출)
    │   └── user_service.py  # SSO 토큰 검증
    ├── database/
    │   └── database_service.py  # PostgreSQL 커넥션 풀
    ├── interfaces/          # 추상 인터페이스
    ├── schemas/             # Pydantic 요청/응답 모델
    └── utils/
        ├── auth_helper.py   # verify_token Depends
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

> AI / LLM 호출은 클라이언트에 직접 노출하지 않고 서비스 레이어에서 내부적으로 처리

---

## 환경 설정

### config.json

```json
{
  "server": { "host": "0.0.0.0", "port": 8000, "log_level": "INFO" },
  "llm": { "host": "127.0.0.1", "port": 11434, "timeout": 30.0, "auto_connect": false },
  "database": {
    "host": "/tmp",
    "port": 5432,
    "name": "ragdb",
    "pool_min": 2,
    "pool_max": 10,
    "auto_connect": true
  },
  "ai": {
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

## 아키텍처

```
Client (HTTP)
      │
 ┌────▼──────────────────────────────┐
 │  FastAPI (app.py)                 │
 │  CORS / Request Logging           │
 │  SSO 토큰 검증 (verify_token)     │
 └────┬──────────────────────────────┘
      │
 ┌────▼──────────────────────────────┐
 │  Controller                       │
 │  인프라 / 서비스 생명주기 관리     │
 └────┬──────────────┬───────────────┘
      │              │
 ┌────▼────┐   ┌─────▼──────────────┐
 │AIService│   │ LLMService         │
 │Claude   │   │ 로컬 LLM Pod       │
 │GPT      │   │ TCP Socket         │
 │Gemini   │   └────────────────────┘
 └────┬────┘
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
