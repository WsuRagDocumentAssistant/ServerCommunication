# AI RAG System

---

## 라우터 — 외부 통신 엔드포인트

### HealthRouter

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |

**예시**
```bash
curl -X GET https://<server>/health
```

### FileRouter

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| POST | `/file/upload` | `multipart/form-data` (`file`, `.hwpx`만 허용) | `{ filename, path, size }` |

**예시**
```bash
curl -X POST https://<server>/file/upload \
  -F "file=@문서.hwpx"
```

### AuthRouter (`prefix: /users`)

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| POST | `/users/login` | `{ email, password }` | `{ access_token, user }` |
| POST | `/users/create/user` | `{ email, password, name }` | `user` |
| POST | `/users/logout` | `Authorization: Bearer <token>` | 메시지만 |
| POST | `/users/sso/login` | `{ sso_token }` | `{ access_token, user }` |

**예시**
```bash
curl -X POST https://<server>/users/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@school.ac.kr", "password": "1234"}'

curl -X POST https://<server>/users/create/user \
  -H "Content-Type: application/json" \
  -d '{"email": "test@school.ac.kr", "password": "1234", "name": "테스터"}'

curl -X POST https://<server>/users/logout \
  -H "Authorization: Bearer eyJhbGciOi..."

curl -X POST https://<server>/users/sso/login \
  -H "Content-Type: application/json" \
  -d '{"sso_token": "eyJhbGciOi..."}'
```

---

## 서비스 — 내부 통신 메서드 파라미터

### LLMApiService (`services/llm_api_service.py`)

```python
BaseLLMApiInterface get_llm_api(AIProvider provider, str model, str api_key)
{
	...
}
```
```python
client = llm_api_service.get_llm_api(AIProvider.GPT, "gpt-5.5", None)
```

```python
ChatResponse chat(str prompt, str model, int max_tokens)
{
	...
}
```
```python
response = client.chat("프롬프트", "GPT-4.5", 10000)
```

```python
AsyncGenerator stream_chat(str prompt, str model, int max_tokens)
{
	...
}
```
```python
async for chunk in client.stream_chat("프롬프트", "GPT-4.5", 10000):
    print(chunk)
```

### LocalLLMService (`services/local_llm_service.py`)

```python
None connect()
{
	...
}
```
```python
await local_llm_service.connect()
```

```python
None disconnect()
{
	...
}
```
```python
await local_llm_service.disconnect()
```

```python
str send(dict payload)
{
	...
}
```
```python
result = await local_llm_service.send({"prompt": "프롬프트", "max_tokens": 512})
```

```python
AsyncGenerator stream_send(dict payload)
{
	...
}
```
```python
async for chunk in local_llm_service.stream_send({"prompt": "프롬프트", "max_tokens": 512}):
    print(chunk)
```

### SSOService (`services/sso_service.py`)

```python
None init()
{
	...
}
```
```python
await sso_service.init()
```

```python
bool validate_token(str token)
{
	...
}
```
```python
is_valid = await sso_service.validate_token("eyJhbGciOi...")
```

```python
dict get_user_info(str token)
{
	...
}
```
```python
info = await sso_service.get_user_info("eyJhbGciOi...")
```

```python
None close()
{
	...
}
```
```python
await sso_service.close()
```

### AuthService (`services/auth_service.py`)

```python
dict register(str email, str password, str name)
{
	...
}
```
```python
user = await auth_service.register("test@school.ac.kr", "1234", "테스터")
```

```python
tuple login(str email, str password)
{
	...
}
```
```python
access_token, user = await auth_service.login("test@school.ac.kr", "1234")
```

```python
tuple sso_login(str sso_token)
{
	...
}
```
```python
access_token, user = await auth_service.sso_login("eyJhbGciOi...")
```

```python
None logout(str token)
{
	...
}
```
```python
auth_service.logout("eyJhbGciOi...")
```

```python
dict decode_access_token(str token)
{
	...
}
```
```python
payload = auth_service.decode_access_token("eyJhbGciOi...")
```

### DatabaseService (`database/database_service.py`)

```python
list fetch(str query, *args)
{
	...
}
```
```python
rows = await database_service.fetch("SELECT * FROM users WHERE id = $1", 1)
```

```python
Record fetchrow(str query, *args)
{
	...
}
```
```python
row = await database_service.fetchrow("SELECT * FROM users WHERE email = $1", "test@school.ac.kr")
```

```python
Any fetchval(str query, *args)
{
	...
}
```
```python
count = await database_service.fetchval("SELECT COUNT(*) FROM users")
```

```python
str execute(str query, *args)
{
	...
}
```
```python
status = await database_service.execute("DELETE FROM users WHERE id = $1", 1)
```

```python
None executemany(str query, list args)
{
	...
}
```
```python
await database_service.executemany(
    "INSERT INTO users (email, name) VALUES ($1, $2)",
    [("a@school.ac.kr", "A"), ("b@school.ac.kr", "B")],
)
```
