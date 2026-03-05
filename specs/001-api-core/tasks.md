# Tasks: API REST — Fut Pay Manager

**Input**: Design documents from `/specs/001-api-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: Not explicitly requested in the feature specification — test tasks are NOT included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and basic structure

- [x] T001 Create project directory structure per plan.md (`app/`, `app/auth/`, `app/models/`, `app/services/`, `app/routes/`, `app/utils/`, `tests/`)
- [x] T002 Initialize Python project with `pyproject.toml` — dependencies: fastapi[standard], motor, pyjwt, pydantic-settings, ruff; dev: pytest, pytest-asyncio, httpx
- [x] T003 [P] Configure Ruff linting and formatting in `pyproject.toml` (rules, line-length, target Python 3.12)
- [x] T004 [P] Create `.env.example` with all environment variables: MONGODB_URL, MONGODB_DATABASE, JWT_SECRET_KEY, AUTH_USERNAME, AUTH_PASSWORD, CORS_ORIGINS

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can begin

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement settings via Pydantic BaseSettings in `app/config.py` — MONGODB_URL, MONGODB_DATABASE, JWT_SECRET_KEY, AUTH_USERNAME, AUTH_PASSWORD, CORS_ORIGINS with dev defaults
- [x] T006 Implement Motor client with lifespan context manager in `app/database.py` — `get_database()` module-level function, client init on startup, close on shutdown
- [x] T007 [P] Define enum types as StrEnum in `app/models/enums.py` — GameStatus (pending|finished|cancelled), PaymentMethod (pix|on_court), TransactionType (game|manual_in|manual_out|transfer), CashTarget (court|adm)
- [x] T008 [P] Create shared schemas in `app/models/common.py` — PyObjectId annotated type, DataEnvelope[T] generic model, PaginatedEnvelope[T] with PaginationMeta (page, limit, total, totalPages)
- [x] T009 Create FastAPI application factory in `app/main.py` — lifespan from database.py, CORSMiddleware with settings.cors_origins, include all routers with prefixes
- [x] T010 Implement `__init__.py` files for all packages: `app/__init__.py`, `app/auth/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/routes/__init__.py`, `app/utils/__init__.py`

**Checkpoint**: `fastapi dev app/main.py` starts without errors, `/docs` is accessible

---

## Phase 3: User Story 1 — Autenticação JWT (Priority: P1) 🎯 MVP

**Goal**: Frontend can login with credentials and receive a JWT token. All protected endpoints reject unauthorized requests.

**Independent Test**: `POST /auth/login` → get token. Use token on any endpoint → 200. No token → 401.

### Implementation for User Story 1

- [x] T011 [P] [US1] Create login request/response models in `app/models/auth.py` — LoginRequest (username: str, password: str), LoginResponse (access_token: str, token_type: str = "bearer")
- [x] T012 [US1] Implement auth service in `app/auth/service.py` — validate_credentials (trim, case-sensitive compare vs settings), create_access_token (PyJWT, HS256, 24h exp, sub=username)
- [x] T013 [US1] Implement auth dependency in `app/auth/deps.py` — get_current_user with HTTPBearer, decode JWT, raise HTTPException(401) on invalid/expired
- [x] T014 [US1] Implement login router in `app/auth/router.py` — `POST /auth/login`, validate credentials, return DataEnvelope[LoginResponse], error 401 with generic message per FR-003
- [x] T015 [US1] Register auth router in `app/main.py` and verify `/docs` shows the login endpoint with lock icon

**Checkpoint**: Login works end-to-end. Token accepted on protected routes, rejected without token or with expired token.

---

## Phase 4: User Story 2 — CRUD de Jogos e Gestão de Presenças (Priority: P1) 🎯 MVP

**Goal**: Create games, manage players, finalize/cancel games with automatic transaction creation.

**Independent Test**: Create game → add players → finalize → verify transactions created and cashImpact calculated.

### Implementation for User Story 2

- [x] T016 [P] [US2] Create Game and Player Pydantic models in `app/models/game.py` — GameCreate (date, courtCost?), GameUpdate (date?, courtCost?), PlayerCreate (name, paymentMethod?, amountPaid?), PlayerUpdate (name?, paymentMethod?, amountPaid?), GameResponse (all fields with PyObjectId), PlayerResponse
- [x] T017 [P] [US2] Create Transaction Pydantic models in `app/models/transaction.py` — TransactionResponse (all fields with PyObjectId), TransactionInDB (for service layer)
- [x] T018 [US2] Implement game_service.py core CRUD in `app/services/game_service.py` — create_game (defaults: status=pending, courtCost=9000, players=[], cashImpact=null), get_game, list_games (with month/status filters + pagination), update_game (block if not pending), delete_game (block if not pending, hard delete)
- [x] T019 [US2] Implement player management in `app/services/game_service.py` — add_player (generate ObjectId, trim name, validate 2-100 chars, block if not pending), update_player, remove_player
- [x] T020 [US2] Implement finalize_game in `app/services/game_service.py` — validate has players, validate pending, calculate cashImpact = Σ(amountPaid) − courtCost + courtCredit, group players by paymentMethod, create game transactions (pix→cashTarget=adm, on_court→cashTarget=court, skip if amount=0), set status=finished, set finishedAt
- [x] T021 [US2] Implement cancel_game in `app/services/game_service.py` — validate pending, set status=cancelled, no transactions created
- [x] T022 [US2] Implement games router in `app/routes/games.py` — POST /games (201), GET /games (200, paginated), GET /games/{id} (200), PUT /games/{id} (200), DELETE /games/{id} (204), all with Depends(get_current_user) and DataEnvelope wrapping
- [x] T023 [US2] Implement player sub-routes in `app/routes/games.py` — POST /games/{id}/players (201), PUT /games/{id}/players/{pid} (200), DELETE /games/{id}/players/{pid} (200), return updated game in DataEnvelope
- [x] T024 [US2] Implement finalize and cancel routes in `app/routes/games.py` — POST /games/{id}/finalize (200), POST /games/{id}/cancel (200), return updated game in DataEnvelope
- [x] T025 [US2] Register games router in `app/main.py` with prefix `/games`

**Checkpoint**: Full game lifecycle works: create → add players → edit players → finalize (transactions created) or cancel. Delete works for pending games only.

---

## Phase 5: User Story 3 — Dashboard e Resumo do Caixa (Priority: P1) 🎯 MVP

**Goal**: API returns the current cash summary (totalBalance, courtBalance, admBalance) computed from all transactions.

**Independent Test**: After finalizing a game (US2), `GET /cash/summary` returns correct balances.

### Implementation for User Story 3

- [x] T026 [P] [US3] Create CashSummary Pydantic model in `app/models/cash.py` — CashSummaryResponse (totalBalance, courtBalance, admBalance, totalIn, totalOut, transactionCount, lastUpdatedAt nullable)
- [x] T027 [US3] Implement cash_service get_summary in `app/services/cash_service.py` — MongoDB aggregation pipeline with $group: split by cashTarget using $cond, compute totalIn/totalOut, handle empty collection (return zeroed summary)
- [x] T028 [US3] Implement cash router in `app/routes/cash.py` — GET /cash/summary (200), Depends(get_current_user), return DataEnvelope[CashSummaryResponse]
- [x] T029 [US3] Register cash router in `app/main.py` with prefix `/cash`

**Checkpoint**: `GET /cash/summary` returns correct balances. After game finalize, balances reflect the transactions. `totalBalance == courtBalance + admBalance` always holds.

---

## Phase 6: User Story 4 — Ajustes Manuais do Caixa (Priority: P2)

**Goal**: Create manual transactions (manual_in, manual_out) with required justification.

**Independent Test**: `POST /transactions` with type=manual_in → balance increases. With type=manual_out → balance decreases. Without justification → 422.

### Implementation for User Story 4

- [x] T030 [P] [US4] Create manual transaction request model in `app/models/transaction.py` — ManualTransactionCreate (type: manual_in|manual_out only, amount: int > 0, description?, justification: str 5-500 chars required, cashTarget: CashTarget default adm)
- [x] T031 [US4] Implement create_manual_transaction in `app/services/cash_service.py` — validate justification length, negate amount for manual_out, set gameId=null, insert into transactions collection
- [x] T032 [US4] Implement transactions router POST in `app/routes/transactions.py` — POST /transactions (201), Depends(get_current_user), validate only manual_in/manual_out types allowed, return DataEnvelope[TransactionResponse]
- [x] T033 [US4] Register transactions router in `app/main.py` with prefix `/transactions`

**Checkpoint**: Manual in/out transactions created successfully. Justification validated. Cash summary reflects changes.

---

## Phase 7: User Story 5 — Histórico de Movimentações (Priority: P2)

**Goal**: List transactions with filters by period, type, cashTarget, and pagination.

**Independent Test**: `GET /transactions` → paginated list. `GET /transactions?from=2026-03-01&to=2026-03-31` → filtered by period.

### Implementation for User Story 5

- [x] T034 [US5] Implement list_transactions in `app/services/cash_service.py` — filters: from/to (date range on createdAt), type, cashTarget; sort by createdAt desc; offset-based pagination (page/limit); count_documents for total
- [x] T035 [US5] Implement transactions router GET in `app/routes/transactions.py` — GET /transactions (200), query params: from, to, type, cashTarget, page, limit; return PaginatedEnvelope[TransactionResponse]

**Checkpoint**: Transaction history shows all types (game, manual, transfer). Filters and pagination work correctly.

---

## Phase 8: User Story 6 — Transferências entre Caixas (Priority: P3)

**Goal**: Transfer money from court balance to ADM balance.

**Independent Test**: `POST /transactions/transfer` → courtBalance decreases, admBalance increases, totalBalance unchanged.

### Implementation for User Story 6

- [x] T036 [P] [US6] Create transfer request model in `app/models/transaction.py` — TransferRequest (amount: int > 0)
- [x] T037 [US6] Implement transfer_service create_transfer in `app/services/transfer_service.py` — compute current courtBalance (reuse cash_service aggregation or targeted query), validate amount ≤ courtBalance, create 2 transactions: (1) type=transfer cashTarget=court amount=-N, (2) type=transfer cashTarget=adm amount=+N, description="Transferência Quadra → ADM"
- [x] T038 [US6] Implement transfer route in `app/routes/transactions.py` — POST /transactions/transfer (201), Depends(get_current_user), return DataEnvelope with both transaction details

**Checkpoint**: Transfer moves money from court to adm. Insufficient balance returns 400. Total balance unchanged after transfer.

---

## Phase 9: User Story 7 — Crédito de Quadra em Jogo (Priority: P3)

**Goal**: Apply court balance as credit to reduce a game's effective court cost.

**Independent Test**: `POST /games/{id}/apply-credit` → courtCredit set on game, courtBalance decreases. On finalize, cashImpact accounts for courtCredit.

### Implementation for User Story 7

- [x] T039 [P] [US7] Create apply-credit request model in `app/models/game.py` — ApplyCreditRequest (amount: int > 0)
- [x] T040 [US7] Implement apply_credit in `app/services/transfer_service.py` — validate game is pending, compute courtBalance, validate amount ≤ courtBalance, set game.courtCredit = amount, create transaction type=manual_out cashTarget=court amount=-N
- [x] T041 [US7] Implement apply-credit route in `app/routes/games.py` — POST /games/{id}/apply-credit (200), Depends(get_current_user), return DataEnvelope[GameResponse]

**Checkpoint**: Court credit applied to game. On finalize, cashImpact = Σ(amountPaid) − (courtCost − courtCredit). Insufficient court balance returns 400.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T042 [P] Create MongoDB indexes in `app/database.py` — games: (status, date), transactions: (createdAt, type, cashTarget, gameId) — created during lifespan startup
- [x] T043 [P] Add input validation edge cases across all routes — invalid ObjectId format returns 400/404 (not 500), consistent error messages in Portuguese
- [x] T044 Validate quickstart.md end-to-end — follow all steps from `specs/001-api-core/quickstart.md`, verify smoke test commands work
- [x] T045 Run Ruff lint and format on entire codebase (`ruff check app/ tests/ --fix; ruff format app/ tests/`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 Auth (Phase 3)**: Depends on Phase 2 — BLOCKS US2–US7 (auth dependency needed)
- **US2 Games (Phase 4)**: Depends on Phase 3 (auth) — can proceed independently
- **US3 Dashboard (Phase 5)**: Depends on Phase 4 (needs transactions from game finalize to show meaningful data)
- **US4 Manual Txns (Phase 6)**: Depends on Phase 3 (auth) — independent of US2/US3
- **US5 History (Phase 7)**: Depends on Phase 6 (transaction models/service shared)
- **US6 Transfers (Phase 8)**: Depends on Phase 3 (auth) — independent of US2–US5
- **US7 Court Credit (Phase 9)**: Depends on Phase 4 (games) + Phase 8 (transfer service)
- **Polish (Phase 10)**: Depends on all desired stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
  └─→ Phase 2 (Foundational)
        └─→ Phase 3 (US1: Auth) ←── BLOCKS ALL
              ├─→ Phase 4 (US2: Games)
              │     ├─→ Phase 5 (US3: Dashboard)
              │     └─→ Phase 9 (US7: Court Credit) ← also needs Phase 8
              ├─→ Phase 6 (US4: Manual Txns)
              │     └─→ Phase 7 (US5: History)
              └─→ Phase 8 (US6: Transfers)
                    └─→ Phase 9 (US7: Court Credit) ← also needs Phase 4
```

### Within Each User Story

- Models before services
- Services before routes
- Routes registered in main.py last
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004 can run in parallel (Phase 1)
- T007, T008 can run in parallel (Phase 2 — different model files)
- T011 can run in parallel with Phase 2 tasks (different file)
- T016, T017 can run in parallel (different model files)
- T026 can run in parallel with US2 implementation (different file)
- T030 can run in parallel with other story models (different file)
- T036 can run in parallel with other story models (different file)
- T039 can run in parallel with other story models (different file)
- T042, T043 can run in parallel (Phase 10 — different concerns)

---

## Parallel Example: User Story 2

```bash
# Step 1: Launch models in parallel (different files)
Task T016: "Create Game/Player models in app/models/game.py"
Task T017: "Create Transaction models in app/models/transaction.py"

# Step 2: Service layer (depends on T016 + T017)
Task T018: "Game CRUD in app/services/game_service.py"
Task T019: "Player management in app/services/game_service.py"  # same file as T018

# Step 3: Finalize logic (depends on T018)
Task T020: "Finalize game in app/services/game_service.py"
Task T021: "Cancel game in app/services/game_service.py"

# Step 4: Routes (depends on T018-T021)
Task T022: "Games router in app/routes/games.py"
Task T023: "Player sub-routes in app/routes/games.py"  # same file as T022
Task T024: "Finalize/cancel routes in app/routes/games.py"  # same file
Task T025: "Register in app/main.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1 Auth
4. Complete Phase 4: US2 Games (core functionality)
5. Complete Phase 5: US3 Dashboard
6. **STOP and VALIDATE**: Auth + Games + Dashboard = functional MVP
7. The gerente can: login, create games, manage players, finalize, see cash summary

### Incremental Delivery

1. Setup + Foundational + Auth → Foundation ready
2. Add Games (US2) → Core operations available
3. Add Dashboard (US3) → MVP! Cash visibility
4. Add Manual Transactions (US4) → Financial flexibility
5. Add History (US5) → Audit trail
6. Add Transfers (US6) → Cash management
7. Add Court Credit (US7) → Advanced feature
8. Polish → Production-ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its phase completes
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
- All monetary values in centavos (integer) — never floating-point
- Total tasks: 45 (T001–T045)
