# API Boundary Security Checklist

Reference for securing API endpoints — input validation, rate limiting, error handling, and authentication token management.

## Purpose

Answer: "Are our API endpoints properly secured against malicious input, abuse, and information leakage?"

## Checklist

Before auditing, identify:

- [ ] Which API frameworks are in use (Django REST, Flask, FastAPI, Express, Gin, Actix)
- [ ] Whether an API gateway sits in front of the application
- [ ] Which authentication mechanism APIs use (JWT, session cookies, API keys, OAuth)
- [ ] Whether the API serves public consumers, internal services, or both
- [ ] Which data formats are accepted (JSON, XML, multipart, GraphQL)

## Input Validation

### Validation Strategy

All user input must be validated at the API boundary before any processing:

| Validation Type | What to check | Example |
|----------------|--------------|---------|
| Type coercion | Input matches expected type | `user_id` is an integer, not a string |
| Length limits | Strings have max length | Username <= 128 chars, bio <= 2000 chars |
| Format validation | Input matches expected pattern | Email matches RFC 5322, UUID matches format |
| Range validation | Numbers within expected range | `page` >= 1, `limit` <= 100 |
| Allowlist values | Enum inputs match known values | `sort_by` in `['name', 'date', 'score']` |
| Sanitization | HTML/script content stripped or escaped | User-generated content sanitized before storage |

### Framework Patterns

**Python (FastAPI/Pydantic):**
```python
# GOOD — Pydantic validates automatically
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=128, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    age: int = Field(ge=13, le=150)

# BAD — no validation
@app.post("/users")
async def create_user(request: Request):
    data = await request.json()  # unvalidated!
    username = data["username"]  # could be anything
```

**Python (Flask):**
```python
# GOOD — explicit validation
from marshmallow import Schema, fields, validate

class UserSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=128))
    email = fields.Email(required=True)

# BAD — direct access to request data
username = request.form['username']  # unvalidated!
```

**Node.js (Express + Joi/Zod):**
```javascript
// GOOD — Zod schema validation
const UserSchema = z.object({
  username: z.string().min(3).max(128).regex(/^[a-zA-Z0-9_]+$/),
  email: z.string().email(),
  age: z.number().int().min(13).max(150),
});

// BAD — no validation
app.post('/users', (req, res) => {
  const { username } = req.body;  // unvalidated!
});
```

## Parameterized Queries

**Never** interpolate user input into SQL queries:

```python
# GOOD — parameterized
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# BAD — SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

```javascript
// GOOD — parameterized
db.query('SELECT * FROM users WHERE id = $1', [userId]);

// BAD — SQL injection
db.query(`SELECT * FROM users WHERE id = ${userId}`);
```

## Rate Limiting

| Framework | Library | Example |
|-----------|---------|---------|
| FastAPI | `slowapi` | `limiter = Limiter(key_func=get_remote_address); @limiter.limit("10/minute")` |
| Flask | `flask-limiter` | `limiter = Limiter(app, default_limits=["100/hour"])` |
| Express | `express-rate-limit` | `rateLimit({ windowMs: 15*60*1000, max: 100 })` |
| Django | `django-ratelimit` | `@ratelimit(key='ip', rate='10/m')` |
| Go | `golang.org/x/time/rate` | `limiter := rate.NewLimiter(rate.Limit(10), 1)` |

**What to rate limit:**
- Login endpoints (prevent brute force): 5-10 attempts per minute per IP
- Registration endpoints (prevent spam): 3-5 per hour per IP
- Password reset (prevent abuse): 3 per hour per email
- API endpoints (prevent abuse): 100-1000 per minute per API key
- File upload (prevent resource exhaustion): 10 per hour per user

## Error Handling

**Production error responses must:**
- Return generic error messages (not stack traces, SQL errors, or file paths)
- Use consistent error format (e.g., `{"error": "message", "code": "ERROR_CODE"}`)
- Log detailed error information server-side only
- Never expose framework version, server software, or internal architecture

**Grep patterns for information leakage:**

| Pattern | Language | Issue |
|---------|----------|-------|
| `traceback.format_exc()` returned to client | Python | Stack trace leakage |
| `str(e)` in API response | Python | Internal error message leakage |
| `res.status(500).send(err.message)` | Node.js | Error message leakage |
| `DEBUG = True` in production settings | Django | Full debug page with secrets |
| `app.debug = True` | Flask | Debug mode with interactive console |

## JWT Security

| Check | Correct implementation |
|-------|----------------------|
| Signature verification | `jwt.decode(token, key, algorithms=['RS256'])` — never skip verification |
| Algorithm restriction | Explicit `algorithms` parameter — prevent `none` algorithm attack |
| Expiration check | Verify `exp` claim, reject expired tokens |
| Issuer validation | Verify `iss` claim matches expected issuer |
| Audience validation | Verify `aud` claim matches your service |
| Not-before check | Verify `nbf` claim if present |
| Token storage | `HttpOnly` cookie (preferred) or `Authorization` header — never `localStorage` |

## Request Size and Content-Type

| Framework | How to limit request size |
|-----------|--------------------------|
| FastAPI | `app.add_middleware(ContentSizeLimitMiddleware, max_content_size=10_000_000)` |
| Flask | `app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024` |
| Express | `express.json({ limit: '10mb' })` |
| Django | `DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760` |
| nginx | `client_max_body_size 10m;` |

## Best practices

- Validate input at the boundary, not deep in business logic
- Use schema validation libraries (Pydantic, Joi, Zod) — don't write custom validators
- Return 400 for validation errors with field-level details (but not internal state)
- Log all validation failures for security monitoring
- Use allowlists over denylists for input validation
- Set appropriate `Content-Type` on all responses

## Anti-patterns

- Trusting input because "the frontend validates it" — frontends can be bypassed
- Catching all exceptions and returning 500 with `str(e)` — leaks internals
- Using `*` for CORS `Access-Control-Allow-Origin` with credentials
- Rate limiting only on the frontend (easily bypassed)
- Validating input format but not input length (buffer overflow risk)
