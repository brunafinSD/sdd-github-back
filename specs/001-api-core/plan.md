# Implementation Plan: API REST — Fut Pay Manager

**Branch**: `001-api-core` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-api-core/spec.md`

## Summary

Implementar a API REST backend (FastAPI + MongoDB) para o sistema Fut Pay Manager, substituindo a camada local de dados (IndexedDB/Dexie) do frontend PWA existente. A API expõe 15+ endpoints cobrindo autenticação JWT, CRUD de jogos com gestão de jogadoras, transações financeiras (manuais e de jogo), transferências entre caixas (court→adm), crédito de quadra e resumo do caixa — tudo com valores monetários em centavos (integer) e validação rigorosa via Pydantic v2.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, Motor 3.x (async MongoDB driver), PyJWT / python-jose
**Storage**: MongoDB 7.x (players embedded em Game, transactions em collection separada, CashSummary computado on-demand)
**Testing**: pytest + pytest-asyncio + httpx (async test client)
**Target Platform**: Linux/Windows server (desenvolvimento local, sem deploy nesta feature)
**Project Type**: web-service (REST API)
**Performance Goals**: < 200ms P95 por endpoint em condições normais de uso
**Constraints**: Single-user, sem multi-tenancy, valores monetários em centavos (integer), append-only transactions
**Scale/Scope**: ~15 endpoints, 4 entidades, 41 FRs, 7 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 (initial)

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Spec-Driven Development | ✅ PASS | spec.md completo com 7 user stories, 41 FRs, 8 SCs, checklist validado, 5 clarifications resolvidas |
| II | Contract-First API | ⏳ PENDING | Contracts serão gerados na Phase 1 deste plan |
| III | Type Safety & Validation | ✅ PASS | Spec define enums, validações de boundary, Money como integer |
| IV | Simplicity & YAGNI | ✅ PASS | Single project, Motor direto, sem abstraction layers, out-of-scope declarado |

### Post-Phase 1 (re-evaluation)

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Spec-Driven Development | ✅ PASS | spec.md → plan.md → research.md → data-model.md → contracts/ → quickstart.md. Full spec-to-design pipeline complete |
| II | Contract-First API | ✅ PASS | `contracts/api-endpoints.md` defines all 16 endpoints with request/response schemas, status codes, error messages, and FR traceability |
| III | Type Safety & Validation | ✅ PASS | data-model.md defines 4 enums (StrEnum), all field constraints, type-specific validation rules. Research confirms Pydantic v2 + BeforeValidator for ObjectId |
| IV | Simplicity & YAGNI | ✅ PASS | Single project, Motor direct (no ODM), DataEnvelope[T] generic (no middleware magic), PyJWT (not authlib), offset pagination (not cursor). No complexity violations |

**Gate result**: ALL PASS — ready for Phase 2 (task generation via `/speckit.tasks`).

## Project Structure

### Documentation (this feature)

```text
specs/001-api-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-endpoints.md # REST API contract definitions
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
app/
├── main.py              # FastAPI application factory, CORS, lifespan
├── config.py            # Settings via env vars (Pydantic BaseSettings)
├── database.py          # Motor client, get_database(), collection refs
├── auth/
│   ├── router.py        # POST /auth/login
│   ├── service.py       # Credential validation, JWT creation
│   └── deps.py          # get_current_user dependency
├── models/
│   ├── game.py          # Game, Player Pydantic models
│   ├── transaction.py   # Transaction Pydantic models
│   ├── cash.py          # CashSummary Pydantic model
│   ├── enums.py         # GameStatus, PaymentMethod, TransactionType, CashTarget
│   └── common.py        # Pagination, envelope, shared schemas
├── services/
│   ├── game_service.py  # Game CRUD, finalize, cancel, player mgmt
│   ├── cash_service.py  # CashSummary aggregation, manual transactions
│   └── transfer_service.py  # Court→ADM transfer, apply-credit
├── routes/
│   ├── games.py         # /games endpoints + /games/{id}/players sub-resource
│   ├── transactions.py  # /transactions + /transactions/transfer
│   └── cash.py          # /cash/summary
└── utils/
    └── money.py         # Money helpers (if needed)

tests/
├── conftest.py          # Fixtures: async client, test DB, auth token
├── test_auth.py         # Login, token validation, expiry
├── test_games.py        # CRUD, players, finalize, cancel, delete
├── test_transactions.py # Manual in/out, listing, filters
├── test_transfers.py    # Court→ADM transfer
├── test_cash.py         # CashSummary, balances
└── test_credit.py       # Apply court credit
```

**Structure Decision**: Single project layout conforme Constitution §Technical Stack. Sem separação frontend/backend (frontend é projeto separado em `fut-pay-manager-2`). Routes, services e models seguem separation of concerns por domínio (game, cash, transfer, auth).

## Complexity Tracking

> Nenhuma violação de simplicidade identificada — tabela não aplicável.
