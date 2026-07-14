# AI RAG System

코딩 막 시작한 사람도 읽을 수 있게 최대한 쉽게 쓴 문서입니다.
어려운 용어가 나오면 그 자리에서 바로 설명을 붙였습니다.

---

## 1. 이 프로젝트가 뭐 하는 앱인가요?

- 사용자가 로그인/회원가입을 하고
- 파일(hwpx)을 올리고
- Claude/GPT/Gemini 같은 AI나, 회사 안에 있는 로컬 LLM(사내에서 직접 돌리는 AI 모델)한테 질문을 보내는

**서버(Backend)** 코드입니다. "서버"란 사용자의 요청(질문, 로그인 시도 등)을 받아서 처리하고 결과를 돌려주는 프로그램이에요.

사용하는 도구:

- **Python** — 이 서버를 만든 프로그래밍 언어
- **FastAPI** — 파이썬으로 웹 서버를 쉽게 만들게 도와주는 도구(프레임워크)
- **PostgreSQL** — 데이터를 저장하는 데이터베이스(DB)

---

## 2. 실행하는 법

```bash
pip install -r requirements.txt   # 필요한 도구들 설치
python src/server_starter.py      # 서버 실행
```

`requirements.txt`는 "이 프로젝트를 돌리려면 이런 부품들이 필요해요"라고 적어둔 목록입니다.

---

## 3. 폴더가 왜 이렇게 나뉘어 있나요?

옷장 서랍처럼, 비슷한 역할을 하는 코드끼리 폴더로 묶어놓은 것뿐입니다.

```
src/
├── server_starter.py     # 제일 먼저 실행되는 파일 (전원 버튼)
├── core/                 # 서버의 뼈대
│   ├── app.py            # FastAPI 앱을 만드는 곳
│   ├── controller.py     # 서버 켜질 때/꺼질 때 준비물 챙기는 곳
│   └── routers/          # "외부에서 오는 요청을 받는 창구" 모음 (전부 @Route로 통일, 5장 참고)
├── services/             # "실제로 일을 처리하는" 코드 모음 (전부 @Channel/@Service로 통일, 6·7장 참고)
│   ├── llm_api/              # Claude/GPT/Gemini 실제 호출 코드 (프로바이더별로 하나씩)
│   ├── channels/             # 통신 방식(REST/소켓/SSE)을 갈아 끼울 수 있게 만든 코드
│   ├── auth/                 # 회원가입/로그인/로그아웃 명령들 + 공유 상태(AuthStore)
│   └── sso/                  # 학교/회사 로그인(SSO) 검증 명령들 + 공유 상태(SsoStore)
├── database/             # DB랑 연결하는 코드
├── interfaces/           # "이런 기능은 꼭 있어야 해"라고 정해둔 약속(설명은 6·7장 참고)
├── schemas/              # 요청/응답 데이터의 모양을 정의 (설명은 아래)
└── utils/                # 여기저기서 공용으로 쓰는 잡다한 도구 함수들
```

> **스키마(schema)가 뭔가요?** "이 데이터는 반드시 이런 필드를 가져야 한다"는 설계도입니다.
> 예를 들어 로그인 요청은 `{ email: 문자열, password: 문자열 }` 모양이어야 한다고 정해두는 것.

---

## 4. 요청이 들어오면 어떤 순서로 처리되나요?

사용자가 로그인 버튼을 눌렀다고 가정해봅시다.

```
1. 클라이언트(웹 화면)가 서버에 "로그인해줘" 요청을 보냄
        ↓
2. core/routers/auth_routes.py 의 LoginRoute 가 이 요청을 받음 (창구 역할)
        ↓
3. services/auth/login_service.py 의 LoginService 가 실제로 이메일/비밀번호를 확인함 (일꾼 역할)
        ↓
4. 맞으면 "출입증"(토큰)을 만들어서 돌려줌
```

**라우터(router)** = 손님을 맞이하는 창구 직원. "무슨 요청인지"만 확인하고 실제 일은 서비스에 넘김
**서비스(service)** = 뒤에서 실제 업무 처리하는 직원

---

## 5. 라우터 — 외부에서 호출할 수 있는 창구 목록

라우터도 7번(통신 방식 통합 인터페이스)이랑 **똑같은 패턴**으로 만들었습니다.
예전에는 창구(엔드포인트)마다 클래스가 따로 있고 각자 FastAPI에 등록하는 코드가 있었는데,
지금은 전부 `@Route(method, path)` 스티커 하나 붙이고 `call(payload)` 함수 하나만 만들면
`build_router()`가 자동으로 찾아서 등록해줍니다. (기존 `HealthRouter`/`FileRouter`/`AuthRouter` 클래스는 삭제)

```python
@Route("POST", "/users/login", tags=["Auth"])
class LoginRoute(BaseRouteInterface):
    REQUEST_SCHEMA = LoginRequest   # ← 이 DTO 모양대로 요청을 검증(9번 참고)

    def __init__(self, **services):
        self._services = services  # 실제 처리는 7번 방식대로 서비스 명령에 위임

    async def call(self, payload: LoginRequest) -> dict:
        service = get_service_cls(ServiceOp.AUTH_LOGIN)(**self._services)
        result = await service.call(payload.model_dump())
        return ok(data=result)
```

`REQUEST_SCHEMA`를 선언한 라우트는 `payload`로 **검증이 끝난 DTO 객체**가 들어옵니다
(형식이 안 맞으면 `call()`이 실행되기도 전에 422 에러로 자동 차단 — 9번 참고).
안 쓰는 라우트(파일 업로드, 헤더만 쓰는 로그아웃 등)는 예전처럼 raw dict가 그대로 들어옵니다.
어떤 주소(`/health`든 `/users/login`이든)로 요청이 오든 서버 내부에서 실제로 실행되는 건 항상 `call(payload)` 하나입니다.

- `interfaces/base_route_interface.py` — `BaseRouteInterface.call(payload)` 계약 (`BaseChannelInterface`와 동일한 모양)
- `core/routers/route_registry.py` — `@Route(method, path)` 데코레이터 + 레지스트리
- `core/routers/route_dispatcher.py` — 레지스트리를 실제 FastAPI 라우터로 조립하는 `build_router()` (DTO 검증도 여기서 처리)
- `core/routers/health_route.py`, `file_upload_route.py`, `auth_routes.py` — 실제 창구들

### 창구 목록 (겉에서 호출하는 방식은 이전과 100% 동일합니다)

| Method | 주소(Path) | 보내는 것 | 받는 것 |
|--------|------|------|------|
| GET | `/health` | 없음 | 서버 정상 여부 |
| POST | `/file/upload` | 파일 (`.hwpx`만 가능) | `{ filename, path, size }` |
| POST | `/users/login` | `{ email, password }` | `{ access_token, user }` |
| POST | `/users/create/user` | `{ email, password, name }` | 가입된 사용자 정보 |
| POST | `/users/logout` | 로그인 토큰(`Authorization` 헤더) | 완료 메시지 |
| POST | `/users/sso/login` | `{ sso_token }` | `{ access_token, user }` |

```bash
curl -X GET https://<server>/health

curl -X POST https://<server>/file/upload \
  -F "file=@문서.hwpx"

curl -X POST https://<server>/users/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@school.ac.kr", "password": "1234"}'
```

`access_token`은 일종의 "출입증"입니다. 로그인에 성공하면 하나 발급받고,
그 다음부터는 다른 요청 보낼 때마다 `Authorization: Bearer <access_token>` 형태로 같이 보내서
"저 로그인한 사람 맞아요"라고 증명합니다.

---

## 6. 도메인 서비스 — Auth/SSO도 같은 패턴으로 통일 (`services/auth/`, `services/sso/`)

`AuthService`, `SSOService`처럼 "여러 가지 일을 하나의 큰 클래스가 다 하는" 방식은 없앴습니다.
대신 **동작 하나당 클래스 하나**를 만들고, `@Service(어떤 동작인지)` 스티커를 붙여서 등록해뒀습니다
(라우터의 `@Route`, 채널의 `@Channel`이랑 완전히 같은 방식).

```python
@Service(ServiceOp.AUTH_LOGIN)
class LoginService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]   # 회원 정보/토큰을 들고 있는 공유 저장소

    async def call(self, payload: dict) -> dict:
        ...
        return {"access_token": token, "user": user}
```

```python
# 어떤 동작(ServiceOp.AUTH_LOGIN)을 할지 고르고 호출
service = get_service_cls(ServiceOp.AUTH_LOGIN)(**services)
result = await service.call({"email": "test@school.ac.kr", "password": "1234"})
```

- `services/auth/auth_store.py` — 회원 정보/활성 토큰을 들고 있는 공유 저장소 (`AuthStore`). 여러 명령 클래스가 이걸 같이 씀
- `services/auth/register_service.py`, `login_service.py`, `logout_service.py`, `sso_login_service.py`, `decode_token_service.py` — 각각 하나의 동작만 담당
- `services/sso/sso_store.py`(`SsoStore`), `validate_token_service.py`, `get_user_info_service.py` — SSO 쪽도 동일 패턴

> 지금은 가입한 사용자 정보를 서버의 메모리(RAM, `AuthStore`)에만 저장합니다.
> 즉 **서버를 껐다 켜면 가입 정보가 전부 사라집니다.** 진짜 서비스로 쓰려면 DB에 저장하도록 바꿔야 함.

`DatabaseService`(DB에 데이터 저장/조회)는 이 패턴으로 안 바꿨습니다. `fetch`/`execute`처럼 하는 일이
명확히 다른 여러 함수를 그냥 그대로 두는 게 자연스러워서 그대로 남겨뒀습니다.

```python
rows = await database_service.fetch("SELECT * FROM users WHERE id = $1", 1)
```

`$1`은 SQL(데이터베이스에 질문하는 언어)에서 "여기에 1번째로 넘긴 값을 넣어라"는 뜻입니다.
문자열을 직접 이어붙이지 않고 이렇게 넘기면, 해킹(SQL Injection)에 안전합니다.

---

## 7. 통신 방식을 갈아 끼울 수 있는 구조 (`services/channels/`)

조금 어려운 내용이라 비유로 설명합니다.

- **인터페이스(interface)** = "이 기능을 쓰려면 반드시 이 이름의 함수를 만들어야 해"라는 계약서
- **데코레이터(decorator, `@무언가`)** = 함수나 클래스 위에 붙이는 스티커. "이건 이런 용도예요"라고 표시해두는 것

이 프로젝트에는 AI랑 대화하는 방법이 여러 가지 있습니다 (인터넷 API로 REST 방식, 회사 내부망 소켓 방식, 실시간 스트리밍 SSE 방식). 방식은 다른데 "질문 보내고 답 받기"라는 목적은 똑같아서, **같은 이름의 함수(`call`)로 통일**해뒀습니다.
예전에 있던 `LLMApiService`/`LocalLLMService`라는 별도 클래스는 없애고, 그 로직을 채널 클래스 안으로 합쳤습니다.

```python
# 어떤 방식(REST)을 쓸지 고르고
RestChannelCls = get_channel_cls(Transport.REST)
rest_channel = RestChannelCls(llm_api_config, AIProvider.GPT, "gpt-5.5")
response = await rest_channel.call({"prompt": "프롬프트"}, stream=False)

# 방식만 SOCKET으로 바꿔도 호출하는 코드는 똑같음
SocketChannelCls = get_channel_cls(Transport.SOCKET)
socket_channel = SocketChannelCls(local_llm_config.host, local_llm_config.port, local_llm_config.timeout)
response = await socket_channel.call({"prompt": "프롬프트"}, stream=False)
```

`stream=False`면 답을 한 번에 다 받고, `stream=True`면 답이 만들어지는 대로 조금씩 받습니다
(ChatGPT 화면에서 글자가 하나씩 나오는 것처럼).

---

## 9. schemas — Spring Boot의 DTO처럼 쓰기

**DTO(Data Transfer Object)** = "이 데이터를 주고받을 땐 반드시 이런 모양이어야 한다"고 정해둔 상자.
`schemas/` 폴더 안의 클래스들이 전부 이 DTO 역할입니다 (`LoginRequest`, `UserResponse` 등).

Spring Boot에서 `@RequestBody @Valid LoginDto dto`라고 쓰면 요청이 그 모양과 안 맞을 때
컨트롤러 코드가 실행되기도 전에 자동으로 에러를 돌려주는데, 이 프로젝트에서도 똑같이 동작합니다.
방법은 라우트 클래스에 `REQUEST_SCHEMA`를 선언하는 것뿐입니다.

```python
class LoginRequest(BaseModel):   # DTO
    email: str
    password: str


@Route("POST", "/users/login", tags=["Auth"])
class LoginRoute(BaseRouteInterface):
    REQUEST_SCHEMA = LoginRequest   # 이 한 줄이 Spring의 @Valid에 해당
    ...
```

- `email`, `password`를 안 보내거나 타입이 다르면(숫자를 보낸다든지) → **422 에러**가 자동으로 나가고 `call()`은 아예 실행되지 않습니다.
- 검증을 통과하면 `call(payload)`의 `payload`는 이미 `LoginRequest` 타입 객체라서 `payload.email`, `payload.password`처럼 바로 꺼내 쓸 수 있습니다.

```bash
# password를 빼먹고 보내면
curl -X POST https://<server>/users/login -d '{"email": "a@b.com"}'
# → 422 { "detail": [{ "loc": ["password"], "msg": "Field required", ... }] }
```

응답 쪽도 마찬가지로 DTO(`UserResponse`, `TokenResponse`)로 모양을 정해두고,
라우트가 그 모양대로 채워서 돌려줍니다 — 내부 값을 아무거나 그대로 흘려보내지 않고,
"밖으로 나가는 데이터는 이 모양이어야 한다"를 강제하는 것도 DTO의 역할입니다.

> 파일 업로드처럼 원래 JSON이 아닌 요청(멀티파트 파일)이나, 헤더만 보고 처리하는 로그아웃 같은 라우트는
> `REQUEST_SCHEMA`를 선언하지 않습니다. Spring에서도 `MultipartFile` 파라미터에 DTO를 강제하지 않는 것과 같은 이유입니다.

---

## 10. 이번에 정리한 내용 (변경 이력)

- 안 쓰는 코드 삭제
  - `schemas/db_schemas.py` (아무도 안 쓰던 파일) 삭제
  - `requirements.txt`에서 중복 기록된 `httpx`, 이제 안 쓰는 `websockets` 제거
  - 예전 WebSocket 관련 설명 문구 정리
- `LocalLLMService` 구조 단순화
  - 예전: 서버 켤 때 미리 연결해두고, 끊기면 자동으로 재연결 감시하는 코드가 따로 있었음
  - 지금: 요청 하나 올 때마다 연결 → 전송 → 종료. 관리할 상태가 없어져서 코드가 훨씬 단순해짐
- 통신 방식 통합 인터페이스(`services/channels/`) 추가
  - REST(외부 AI), Socket(내부 AI), SSE(실시간 스트리밍)를 같은 방식으로 호출할 수 있게 정리
- 라우터도 같은 패턴(`@Route` + `call()`)으로 통일
  - `HealthRouter`/`FileRouter`/`AuthRouter` 클래스 전부 삭제
  - `core/routers/route_registry.py`(`@Route` 데코레이터), `route_dispatcher.py`(`build_router()`)로 교체
  - 외부에서 호출하는 주소/방식(Method, Path, 요청/응답 값)은 이전과 동일 — 내부 구현만 통일됨
- `services/` 폴더 전체를 `@Channel`/`@Service` 패턴으로 통일
  - `LLMApiService`, `LocalLLMService` 삭제 → 로직을 `RestChannel`/`SocketChannel`에 흡수
  - `AuthService`, `SSOService` 삭제 → `services/auth/`, `services/sso/`의 동작 하나당 클래스 하나(`@Service`)로 분리
  - `Controller`는 이제 개별 서비스 인스턴스 대신 공유 상태(`AuthStore`, `SsoStore`)와 설정만 들고 있음
- `schemas`를 Spring Boot의 DTO처럼 사용하도록 정리
  - 라우트에 `REQUEST_SCHEMA` 선언 시 요청 본문을 자동 검증(형식 안 맞으면 422, `call()` 실행 전 차단)
  - `LoginRoute`/`RegisterRoute`/`SsoLoginRoute`에 각각 `LoginRequest`/`RegisterRequest`/`SSOLoginRequest` 적용
