# Quickstart: API REST — Fut Pay Manager

**Branch**: `001-api-core` | **Date**: 2026-03-04

---

## Prerequisites

- Python 3.12+
- MongoDB 7.x running locally on `localhost:27017`
- Git (for branch management)

## Setup

```bash
# 1. Checkout the feature branch
git checkout 001-api-core

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# 3. Install dependencies
pip install fastapi[standard] motor pyjwt pydantic-settings ruff
pip install pytest pytest-asyncio httpx  # dev/test deps

# 4. Set environment variables (or use defaults for dev)
# Optional — defaults work out of the box for development
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_DATABASE="fut_pay_manager"
export JWT_SECRET_KEY="dev-secret-key-change-in-production"
export AUTH_USERNAME="parceriasdojoguinho"
export AUTH_PASSWORD="futdaquinta"
export CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
```

## Run

```bash
# Start the API server (dev mode with auto-reload)
fastapi dev app/main.py

# Or with uvicorn directly
uvicorn app.main:app --reload --port 8000
```

API available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

## Quick Smoke Test

```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "parceriasdojoguinho", "password": "futdaquinta"}'
# → {"data": {"access_token": "eyJ...", "token_type": "bearer"}}

# 2. Save the token
TOKEN="eyJ..."  # paste from response

# 3. Create a game
curl -X POST http://localhost:8000/games \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-03-10T20:00:00Z"}'
# → {"data": {"id": "...", "status": "pending", ...}}

# 4. Check cash summary (should be empty)
curl http://localhost:8000/cash/summary \
  -H "Authorization: Bearer $TOKEN"
# → {"data": {"totalBalance": 0, ...}}
```

## Run Tests

```bash
# Make sure MongoDB is running, then:
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with async debug
pytest tests/ -v --tb=short
```

## Project Structure

```
app/
├── main.py           # FastAPI app factory, lifespan, CORS
├── config.py         # Pydantic BaseSettings (env vars)
├── database.py       # Motor client, get_database()
├── auth/             # JWT login, deps
├── models/           # Pydantic schemas + enums
├── services/         # Business logic
├── routes/           # API routers
└── utils/            # Helpers

tests/
├── conftest.py       # Async fixtures, test DB
└── test_*.py         # Test modules
```

## Key Files to Implement First

1. `app/config.py` — Settings from env vars
2. `app/database.py` — Motor client + lifespan
3. `app/models/enums.py` — GameStatus, PaymentMethod, TransactionType, CashTarget
4. `app/models/` — Pydantic schemas
5. `app/auth/` — Login + JWT dependency
6. `app/main.py` — App factory with routers and middleware

## Useful Commands

```bash
# Lint
ruff check app/ tests/
ruff format app/ tests/

# MongoDB shell (check data)
mongosh fut_pay_manager
db.games.find().pretty()
db.transactions.find().pretty()
```
