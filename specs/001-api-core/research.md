# Technical Research: API REST — Fut Pay Manager

**Branch**: `001-api-core` | **Date**: 2026-03-04  
**Context**: FastAPI 0.115+ · MongoDB 7.x · Motor 3.x · Pydantic v2 · Python 3.12+

---

## 1. FastAPI + Motor Integration Pattern

### Decision

Use the **lifespan context manager** to initialize and close the Motor `AsyncIOMotorClient`. Expose a module-level `get_database()` function that returns the database reference. No singleton class needed.

### Rationale

- **Lifespan is the canonical pattern** since FastAPI 0.93+. The older `@app.on_event("startup")` / `@app.on_event("shutdown")` decorators are **deprecated** in FastAPI 0.103+ and will be removed in a future version. For FastAPI 0.115+, lifespan is the only recommended approach.
- Motor's `AsyncIOMotorClient` manages its own **connection pool** internally (default `maxPoolSize=100`). No manual pool management is needed — just create one client at startup and reuse it.
- A module-level `database.py` file that holds a reference to the client/database is simpler than dependency injection of the database object. Routes call `get_database()` to get the `AsyncIOMotorDatabase` reference. This avoids passing the database through FastAPI's DI for every route, which adds boilerplate without benefit in a single-database project.
- The lifespan context manager naturally handles cleanup: the `yield` point separates startup from shutdown, and the client is closed after `yield`.

### Pattern Overview

```
# database.py — module-level references
client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None

def get_database() -> AsyncIOMotorDatabase:
    return db  # set during lifespan startup

# main.py — lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create client, assign db
    yield
    # shutdown: close client
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| `@app.on_event("startup/shutdown")` | Deprecated since FastAPI 0.103+. Will raise warnings and be removed. |
| Dependency injection of database via `Depends(get_db)` | Adds boilerplate to every route signature. Useful in multi-DB scenarios, unnecessary for single-database single-user projects. |
| ODM libraries (Beanie, ODMantic) | Adds abstraction layer over Motor. Constitution §IV (Simplicity & YAGNI) favors Motor directly. Beanie has its own initialization ceremony and magic that's overkill for ~4 entities. |
| MongoEngine / PyMongo (sync) | Sync drivers block the event loop in async FastAPI. Motor is the async driver for MongoDB; PyMongo should never be used directly in async routes. |

### Connection Pooling Notes

- Motor wraps PyMongo and uses its connection pool. Default `maxPoolSize=100` is more than sufficient for a single-user application.
- Set `MONGODB_URL` via env vars (Pydantic `BaseSettings`). For local dev: `mongodb://localhost:27017`.
- Database name should also be configurable: `MONGODB_DATABASE=fut_pay_manager`.

---

## 2. Pydantic v2 + MongoDB ObjectId Handling

### Decision

Use `Annotated[str, ...]` for the `id` field in Pydantic response models. MongoDB's `_id` (ObjectId) is **converted to string** at the service/repository layer before constructing the Pydantic model. Use `BeforeValidator` with a custom annotated type `PyObjectId` for input validation when receiving IDs in path parameters.

### Rationale

- **Pydantic v2 does not natively serialize `bson.ObjectId`**. Attempting to use `ObjectId` directly in a Pydantic model causes serialization errors because Pydantic doesn't know how to convert it to JSON.
- The cleanest pattern in Pydantic v2 is to define a custom annotated type using `BeforeValidator` that accepts both `str` and `ObjectId` and converts to `str`. This is idiomatic Pydantic v2 (replaces the v1 `__get_validators__` pattern).
- **Field aliasing** handles the `_id` → `id` rename: use `Field(alias="_id")` combined with `model_config = ConfigDict(populate_by_name=True)` so the model can be constructed from MongoDB documents (which have `_id`) but serialized with `id`.
- For **creating** documents, don't include `id` in the input model — let MongoDB generate `_id` automatically. After insertion, the `inserted_id` is converted to string for the response.

### Pattern Overview

```
# Annotated type for ObjectId ↔ str conversion
PyObjectId = Annotated[str, BeforeValidator(str)]

# Response model
class GameResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = Field(alias="_id")
    date: datetime
    status: GameStatus
    ...
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Use string UUIDs instead of ObjectId | Loses MongoDB's built-in `_id` index and natural ObjectId benefits (timestamp encoding, sortability). Would require generating UUIDs before insert. Unnecessary complexity. |
| Use `bson.ObjectId` directly in Pydantic models with custom JSON encoder | Pydantic v2 removed `json_encoders` config. Would require a custom `__get_pydantic_core_schema__` implementation, which is verbose and fragile. |
| Use Beanie's `PydanticObjectId` | Pulls in Beanie as a dependency just for one type. Constitution §IV (YAGNI). The `Annotated[str, BeforeValidator(str)]` pattern is 2 lines. |
| Store `_id` as string in MongoDB | Anti-pattern. ObjectId is MongoDB's native, indexed, sortable ID type. Storing strings as `_id` loses these benefits and goes against MongoDB conventions. |

### Key Implementation Notes

- When querying by ID, convert the string back to `ObjectId` for the MongoDB query: `ObjectId(id_str)`.
- Validate that the string is a valid ObjectId format (24 hex chars) in path parameter validation. Return 400/404 for invalid IDs.
- The `_id` → `id` aliasing means MongoDB documents can be passed directly to the Pydantic model constructor without manual field renaming.

---

## 3. JWT Authentication in FastAPI

### Decision

Use **PyJWT** (`pyjwt` package) for token creation and validation. Implement a single `get_current_user` dependency using FastAPI's `HTTPBearer` security scheme. Hardcoded credentials are loaded from env vars via Pydantic `BaseSettings` (with defaults for dev).

### Rationale

- **PyJWT** is the most maintained, lightest JWT library for Python. It focuses exclusively on JWT encoding/decoding with a minimal API. For this project (single-user, HS256), it's the right choice.
- `python-jose` was the historically recommended library in FastAPI tutorials, but it is **unmaintained** (last PyPI release was 2021, and the project has been stale). FastAPI's own documentation now recommends PyJWT or has removed the python-jose dependency.
- Token flow: `POST /auth/login` validates credentials → creates JWT with `exp` (24h) and `sub` (username) → returns `{ "access_token": "<jwt>", "token_type": "bearer" }`.
- Protected routes use `Depends(get_current_user)` which extracts the token from `Authorization: Bearer <token>`, decodes it with PyJWT, and raises `HTTPException(401)` if invalid/expired.
- FastAPI's `HTTPBearer` security scheme auto-generates the lock icon in Swagger UI at `/docs`.

### Pattern Overview

```
# deps.py
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(401, "Token inválido ou expirado")

# router.py
@router.post("/auth/login")
async def login(body: LoginRequest):
    # validate credentials (trim + compare)
    # return { "access_token": jwt.encode(...), "token_type": "bearer" }
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| `python-jose` | Unmaintained since 2021. Multiple open CVEs and stale PRs. FastAPI community has migrated away from it. |
| `authlib` | Full-featured OAuth/OIDC library — massive overkill for single-user JWT with hardcoded credentials. |
| `fastapi-jwt-auth` | Third-party extension that couples auth to the framework. Adds dependency for something achievable in ~30 lines with PyJWT. Last release is old. |
| `OAuth2PasswordBearer` | FastAPI's built-in scheme, but it uses form-encoded `username`/`password` (OAuth2 spec). The frontend sends JSON body, so `HTTPBearer` + a custom login endpoint is cleaner. |
| RS256 (asymmetric keys) | Overkill for single-service single-user. HS256 with a secret key is simpler, faster, and sufficient when the same service creates and validates tokens. |

### Security Notes

- `SECRET_KEY` must be loaded from env var (`JWT_SECRET_KEY`), with a dev default.
- Token payload: `{ "sub": username, "exp": now + 24h, "iat": now }`. Minimal claims — no roles/permissions needed.
- Credentials comparison: `trim()` input, then compare literally (case-sensitive) per FR-002.
- Error messages: always generic "Usuário ou senha inválidos" per FR-003.

---

## 4. MongoDB Aggregation for CashSummary

### Decision

Use a **single Motor aggregation pipeline** on the `transactions` collection with `$group` to compute all CashSummary fields in one database round-trip. No materialized/cached summary — always compute on-demand.

### Rationale

- CashSummary is specified to be **computed dynamically, never persisted** (spec Key Entities). An aggregation pipeline is the natural MongoDB pattern for this.
- A single aggregation query replaces multiple `find()` + client-side computation. MongoDB's aggregation engine runs server-side, which is faster and avoids transferring all transactions to the application.
- For a single-user system with modest transaction volume (tens to low thousands), the aggregation will execute in < 50ms — well within the 200ms P95 target.
- The pipeline uses `$group` with `$sum` and conditional expressions (`$cond`) to split by `cashTarget` in one pass.

### Pipeline Overview

```
Pipeline: transactions.aggregate([
  {
    "$group": {
      "_id": None,
      "totalIn":  { "$sum": { "$cond": [{"$gt": ["$amount", 0]}, "$amount", 0] } },
      "totalOut": { "$sum": { "$cond": [{"$lt": ["$amount", 0]}, { "$abs": "$amount" }, 0] } },
      "courtBalance": { "$sum": { "$cond": [{"$eq": ["$cashTarget", "court"]}, "$amount", 0] } },
      "admBalance":   { "$sum": { "$cond": [{"$eq": ["$cashTarget", "adm"]}, "$amount", 0] } },
      "transactionCount": { "$sum": 1 },
      "lastUpdatedAt":    { "$max": "$createdAt" }
    }
  }
])
# totalBalance = courtBalance + admBalance (computed in application or added to pipeline)
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Persist CashSummary document + update on each transaction | Introduces data consistency risk (summary can drift from transactions). Violates the spec which states CashSummary is "calculado dinamicamente". Adds write complexity for no performance gain at this scale. |
| Multiple `find()` queries + client-side sum | Transfers all transaction documents over the wire. Slower, more memory, more code. Aggregation engine is purpose-built for this. |
| MongoDB View | A view is essentially a stored aggregation pipeline. Adds administrative complexity without benefit — the service can run the pipeline directly. |
| Redis/in-memory cache | Premature optimization. Transaction volume is low for single-user. Adds infrastructure dependency. If performance becomes an issue later, caching can be added non-intrusively. |

### Implementation Notes

- When no transactions exist (empty collection), the aggregation returns an empty cursor. The service should return zeroed CashSummary in that case.
- `totalOut` is stored as a positive number in the response (absolute value of negative amounts) per spec: "totalOut: N" (positive integer representing total outflow).
- `totalBalance` is computed as `courtBalance + admBalance` per FR-025. Can be computed in the pipeline with `$add` or in the application layer after the aggregation.

---

## 5. Testing Async FastAPI + MongoDB

### Decision

Use **pytest + pytest-asyncio + httpx.AsyncClient** with a **separate test database** (same MongoDB instance, different database name). Use `@pytest.fixture` with function/session scope for test setup and per-test cleanup via collection drops.

### Rationale

- `httpx.AsyncClient` with FastAPI's `ASGITransport` is the modern replacement for the old `TestClient` (which uses `requests` internally). It supports async and is the recommended approach for testing async FastAPI apps.
- Using a separate database (e.g., `fut_pay_manager_test`) avoids polluting development data. Same MongoDB instance, different database name — no extra infrastructure needed.
- `pytest-asyncio` provides the `@pytest.mark.asyncio` decorator and async fixture support needed for Motor-based tests.
- Per-test cleanup (dropping collections after each test) ensures test isolation. This is simpler than transactions/snapshots in MongoDB (which require replica sets).

### Fixture Pattern Overview

```
# conftest.py
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def app():
    # Override database to test DB
    # Return FastAPI app instance

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c
    # Cleanup: drop all collections in test DB

@pytest.fixture
async def auth_headers(client):
    # Login and return {"Authorization": "Bearer <token>"}
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| `TestClient` (sync, from Starlette) | Uses `requests` under the hood, creates its own event loop. Incompatible with testing truly async code. Legacy approach. |
| mongomock / mongomock-motor | Mocks MongoDB in memory. Doesn't support all aggregation operators (e.g., `$cond`, `$abs`). CashSummary aggregation would not be testable. Real MongoDB is more reliable for integration tests. |
| Docker-based test MongoDB | Adds infrastructure complexity. A real MongoDB instance is already needed for development. Using a separate database name on the same instance is sufficient. |
| Per-test transactions (rollback) | MongoDB transactions require a replica set. Overly complex for test isolation. Dropping collections is simpler and deterministic. |
| Factory Boy / model factories | Can be added later but isn't needed initially. Simple dict/model construction in test helpers is sufficient for ~4 entities. |

### Configuration Notes

- Test database name: `MONGODB_DATABASE_TEST=fut_pay_manager_test` or derived as `f"{MONGODB_DATABASE}_test"`.
- `pytest-asyncio` mode: set `asyncio_mode = "auto"` in `pyproject.toml` / `pytest.ini` to avoid decorating every test with `@pytest.mark.asyncio`.
- The `auth_headers` fixture performs an actual login and returns headers, so all protected-endpoint tests are realistic (full auth flow).
- Cleanup order: drop collections **after** each test function (in the `client` fixture teardown), not at session end, to ensure isolation.

---

## 6. Response Envelope Pattern

### Decision

Use a **generic wrapper response model** at the route level. Each route explicitly returns `{ "data": ... }` by wrapping its result in an envelope model. Errors remain in FastAPI's default `{ "detail": "..." }` format untouched.

### Rationale

- FR-039 requires success responses to use `{ "data": ... }` envelope. FR-041 requires errors to use FastAPI's default `{ "detail": "..." }` format.
- A **route-level wrapping** approach is the most explicit and type-safe: each route function constructs `{"data": result}` and declares the full envelope as its `response_model`. This keeps OpenAPI schemas accurate — Swagger UI shows the exact envelope structure.
- A generic `DataEnvelope[T]` model using Pydantic generics provides reusability without repetition.

### Pattern Overview

```
# Generic envelope
class DataEnvelope(BaseModel, Generic[T]):
    data: T

# Route usage
@router.get("/cash/summary", response_model=DataEnvelope[CashSummaryResponse])
async def get_cash_summary(...):
    summary = await cash_service.get_summary()
    return DataEnvelope(data=summary)

# Paginated envelope (extends with metadata)
class PaginatedEnvelope(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Custom middleware that wraps all 2xx responses | Would also wrap error responses or require fragile content-type / status-code inspection. Breaks FastAPI's `response_model` validation (middleware sees raw bytes, not models). OpenAPI schema wouldn't reflect the envelope. |
| Custom `JSONResponse` subclass | Similar to middleware — operates at the response level, after serialization. Doesn't integrate with `response_model` or OpenAPI schema generation. |
| Custom `APIRoute` class that wraps return values | Clever but magical. Harder to debug, harder for new contributors to understand. Breaks the principle of least surprise. |
| No envelope (return data directly) | Violates FR-039. Also, wrapping in `{ "data": ... }` makes it easier for the frontend to distinguish success payloads from error payloads structurally. |

### Implementation Notes

- For **single-item** responses: `DataEnvelope[GameResponse]` → `{ "data": { ... } }`.
- For **list** responses with pagination: `PaginatedEnvelope[GameResponse]` → `{ "data": [...], "meta": { "page": 1, "limit": 20, "total": 42, "totalPages": 3 } }`.
- For **201 Created** responses: same envelope, just different status code via `status_code=201` in the decorator.
- For **204 No Content** (e.g., DELETE): no body, no envelope.
- Errors (4xx, 5xx) pass through FastAPI's default exception handling → `{ "detail": "..." }`.

---

## 7. CORS Configuration

### Decision

Use FastAPI's built-in **`CORSMiddleware`** with explicit origin allowlist. In development, allow `http://localhost:5173` (Vite default) and `http://localhost:3000`. In production, configure via env var `CORS_ORIGINS`.

### Rationale

- `CORSMiddleware` is Starlette's built-in (FastAPI inherits it). No third-party dependency needed. It handles preflight `OPTIONS` requests, `Access-Control-Allow-*` headers, and credentialed requests.
- Explicit origin allowlist is more secure than `allow_origins=["*"]`. For a PWA that sends `Authorization` headers, `allow_credentials=True` is required — and it **cannot** be used with `allow_origins=["*"]` (browsers enforce this).
- The PWA frontend likely runs on `localhost:5173` (Vite) during development and on a deployed domain in production. Making origins configurable via env var covers both.

### Configuration Overview

```
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,    # ["http://localhost:5173"] or from env
    allow_credentials=True,                  # Required for Authorization header
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| `allow_origins=["*"]` | Incompatible with `allow_credentials=True`. Even if credentials weren't needed, wildcard origins are a security risk for APIs that handle financial data. |
| No CORS (reverse proxy handles it) | Adds infrastructure dependency. For local development, CORS must be handled by the API regardless. The middleware approach works in all environments. |
| Third-party CORS libraries | Unnecessary — Starlette's `CORSMiddleware` is mature, well-tested, and purpose-built for ASGI frameworks. |

### Configuration Notes

- `CORS_ORIGINS` env var: comma-separated list of allowed origins. Default: `http://localhost:5173,http://localhost:3000`.
- `allow_methods`: explicit list is preferred over `["*"]` for clarity. Include only the HTTP methods the API actually uses.
- `allow_headers`: include `Authorization` (for JWT) and `Content-Type` (for JSON bodies). `["*"]` works but explicit is clearer.
- `expose_headers`: not needed unless the frontend reads custom response headers (it doesn't in this project).

---

## 8. Pagination Pattern

### Decision

Use **offset-based pagination** with `page` (1-indexed) and `limit` query parameters. Return pagination metadata in the response envelope under a `meta` key. Use MongoDB `skip()` + `limit()` with a separate `count_documents()` for total count.

### Rationale

- Offset-based pagination is the simplest pattern and matches the frontend's expectations (spec defines `?page=2&limit=10`).
- 1-indexed `page` is more intuitive for end users and matches the spec's acceptance scenarios (FR-009, FR-026).
- `count_documents()` provides the `total` count needed to compute `totalPages`. For a single-user app with modest data volume, the overhead of a count query is negligible.
- Pagination metadata (`page`, `limit`, `total`, `totalPages`) is included in the response envelope under `meta`, keeping it separate from the `data` array.

### Pattern Overview

```
# Query parameters (reusable dependency or inline)
page: int = Query(1, ge=1)
limit: int = Query(20, ge=1, le=100)

# Service layer
skip = (page - 1) * limit
cursor = collection.find(filter).sort("createdAt", -1).skip(skip).limit(limit)
items = await cursor.to_list(length=limit)
total = await collection.count_documents(filter)
total_pages = ceil(total / limit)

# Response
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "totalPages": 3
  }
}
```

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Cursor-based pagination (keyset) | More efficient for large datasets but more complex. Requires stable sort field and opaque cursor tokens. Overkill for single-user app with low data volume. Frontend expects `page`/`limit` parameters. |
| `skip/offset` instead of `page` | Semantically equivalent but less intuitive. `page=2&limit=20` is clearer than `offset=20&limit=20`. The spec uses page-based language. |
| No pagination metadata | Frontend needs `total` and `totalPages` to render pagination controls. Without metadata, the frontend can't know how many pages exist. |
| `estimated_document_count()` for total | Returns an approximation (metadata-based). For accuracy in filtered queries, `count_documents(filter)` is required. The performance difference is negligible at this scale. |
| Link headers (RFC 5988) | REST standard for pagination links (`rel=next`, `rel=prev`). More complex to implement and consume. JSON metadata in the body is simpler and more common in modern APIs. |

### Implementation Notes

- **Default values**: `page=1`, `limit=20`. Max `limit=100` to prevent abuse.
- **Empty results**: Return `{ "data": [], "meta": { "page": 1, "limit": 20, "total": 0, "totalPages": 0 } }`.
- **Reusable**: Define a `PaginationParams` dependency or dataclass to avoid repeating `page`/`limit` in every route.
- **Sort order**: All paginated endpoints sort by `createdAt` desc (most recent first) per spec acceptance scenarios.
- **Performance**: For the anticipated scale (hundreds to low thousands of documents), `skip()` + `count_documents()` is perfectly adequate. If scale grows beyond 100k documents, migrate to cursor-based pagination.
- **Filter + pagination**: Both `GET /games` and `GET /transactions` combine filters (month, status, type, date range) with pagination. The same `count_documents(filter)` call must use the same filter as the `find(filter)` to ensure consistency.

---

## Summary of Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | FastAPI + Motor | Lifespan context manager, module-level `get_database()`, no ODM |
| 2 | Pydantic v2 + ObjectId | `Annotated[str, BeforeValidator(str)]` + `Field(alias="_id")` |
| 3 | JWT Auth | PyJWT + `HTTPBearer` + `get_current_user` dependency |
| 4 | CashSummary Aggregation | Single `$group` aggregation pipeline, computed on-demand |
| 5 | Testing | pytest-asyncio + httpx `AsyncClient` + separate test database + collection drop cleanup |
| 6 | Response Envelope | Generic `DataEnvelope[T]` model, route-level wrapping, errors untouched |
| 7 | CORS | `CORSMiddleware` with explicit origin allowlist from env var |
| 8 | Pagination | Offset-based `page`/`limit`, `meta` in response, `skip()`+`count_documents()` |
