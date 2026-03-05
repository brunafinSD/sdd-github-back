<!--
Sync Impact Report
  Version change: 0.0.0 → 1.0.0 (MAJOR — first ratification)
  Modified principles: N/A (first version)
  Added sections:
    - Core Principles (4): Spec-Driven, Contract-First API,
      Type Safety & Validation, Simplicity
    - Technical Stack
    - Data Model Canon
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ compatible (no changes needed)
    - .specify/templates/spec-template.md ✅ compatible (no changes needed)
    - .specify/templates/tasks-template.md ✅ compatible (no changes needed)
    - .specify/templates/checklist-template.md ✅ compatible (no changes needed)
  Follow-up TODOs: none
-->

# Fut Pay Manager API — Constitution

## Core Principles

### I. Spec-Driven Development

Every feature MUST begin with a specification in `specs/` before any
code is written. The specification is the single source of truth for
requirements, acceptance scenarios and data contracts.

- Each feature lives in a numbered directory (`specs/NNN-feature-name/`)
  containing at minimum `spec.md` and `plan.md`.
- User stories MUST be prioritized (P1, P2, …) and independently
  testable — a single story MUST deliver a viable increment of value.
- Implementation MUST NOT diverge from the spec without an explicit
  amendment to the spec document first.
- Frontend specifications live under `specs/frontend/`; backend (API)
  specifications live under `specs/` at root level.

### II. Contract-First API

The REST API contract (endpoints, request/response shapes, status codes)
MUST be defined before implementation begins.

- Every endpoint MUST be documented in `contracts/` with request body,
  response body, error codes and example payloads.
- Responses MUST use consistent envelope: `{ "data": ... }` for success,
  `{ "detail": "..." }` for errors (FastAPI default).
- Monetary values MUST be transmitted as **integer cents** (`Money` type)
  — never floating-point — to guarantee precision.
- All date/time fields MUST be serialized as ISO 8601 strings in UTC.
- The API MUST return appropriate HTTP status codes: 200 (OK), 201
  (Created), 400 (Bad Request), 401 (Unauthorized), 404 (Not Found),
  422 (Validation Error), 500 (Internal Server Error).
- Breaking changes to existing endpoints MUST be versioned or
  documented as a spec amendment.

### III. Type Safety & Validation

All data entering and leaving the system MUST be validated at the
boundary.

- Pydantic v2 models MUST define every request and response schema.
- MongoDB documents MUST conform to the Pydantic model before
  persistence (no raw dict inserts).
- Domain rules (e.g., justification required for manual transactions,
  transfer amount ≤ court balance) MUST be enforced in the service
  layer, not only in the API layer.
- Enum values (`GameStatus`, `PaymentMethod`, `TransactionType`,
  `CashTarget`) MUST be defined as Python `StrEnum` and validated
  by Pydantic.

### IV. Simplicity & YAGNI

Start with the simplest implementation that satisfies the spec.
Complexity MUST be justified.

- No abstraction layer unless it is required by two or more consumers.
- Single-file-per-concern is preferred over deep folder nesting.
- Prefer Motor (async MongoDB driver) directly over heavy ODM
  frameworks unless proven necessary.
- Avoid premature optimization — measure first, optimize second.
- Each task in `tasks.md` MUST be small enough to implement and verify
  in a single session.

## Technical Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic v2 | 2.x |
| Database | MongoDB | 7.x |
| Async Driver | Motor | 3.x |
| Auth | JWT (PyJWT / python-jose) | — |
| Testing | pytest + pytest-asyncio + httpx | — |
| Linting | Ruff | — |
| Type Checking | pyright / mypy (optional) | — |

**Project layout** (single project):

```text
app/
├── main.py              # FastAPI application factory
├── config.py            # Settings (env-based)
├── auth/                # JWT helpers, login endpoint, deps
├── models/              # Pydantic schemas (request/response/DB)
├── services/            # Business logic (game, cash, transfer)
├── routes/              # FastAPI routers
├── database.py          # Motor client & collections
└── utils/               # Money helpers, parsers
tests/
├── conftest.py
├── test_games.py
├── test_cash.py
├── test_transfers.py
└── test_auth.py
```

## Data Model Canon

Canonical entities for the API, consolidating frontend specs
001-004 and resolving known inconsistencies:

| Entity | Key Fields | Notes |
|--------|-----------|-------|
| **Game** | id, date, status (`pending \| finished \| cancelled`), courtCost (Money), players (embedded Player[]), cashImpact (Money \| null), courtCredit (Money \| null), createdAt, updatedAt, finishedAt | `finishedAt` (not `finalishedAt`). `cashImpact` null until finalized. |
| **Player** | id, name, paymentMethod (`pix \| on_court`), amountPaid (Money, default 1000) | Embedded inside Game document. Duplicate names allowed. |
| **Transaction** | id, type (`game \| manual_in \| manual_out \| transfer`), amount (Money), description, justification (required for manual), gameId (nullable), cashTarget (`court \| adm`), createdAt | Append-only / immutable. Transferências court→adm usam `type='transfer'` (sem entidade separada). |
| **CashSummary** | totalBalance, courtBalance, admBalance, totalIn, totalOut, transactionCount, lastUpdatedAt | Computed on-demand, never persisted. |

**Cash calculation rule**: O caixa NÃO paga a quadra — quem paga são
as jogadoras. O caixa serve para gerenciar o excedente. Ao finalizar
um jogo, `cashImpact` = Σ(`amountPaid`) − `courtCost`. Se positivo,
o valor excedente entra no caixa; se negativo, indica déficit e o
caixa absorve a diferença. Pagamentos `on_court` geram transactions
com `cashTarget=court`; pagamentos `pix` geram com `cashTarget=adm`.
O `courtCost` é apenas referência de cálculo, NÃO gera transação
própria de saída.

**Transferências court → adm**: Registradas como
`Transaction(type='transfer')`. Não há entidade `Transfer` separada.
A transaction de transferência tem `amount > 0`, `cashTarget='court'`
(saída) e gera implicitamente entrada no ADM. `amount` ≤ `courtBalance`.

**GameStatus transitions**:

```
pending → finished    (finaliza e calcula cashImpact)
pending → cancelled   (cancela sem impacto no caixa)
```

**Authentication**: JWT simples. Credenciais hardcoded no backend
(configuráveis via variáveis de ambiente). Single-user. Token retornado
no login, verificado via dependency injection em todas as rotas
protegidas.

## Governance

- Esta constituição é a autoridade máxima do projeto. Em caso de
  conflito entre a constituição e qualquer outro documento, a
  constituição prevalece.
- Emendas à constituição DEVEM ser documentadas com justificativa,
  incremento de versão semântica e atualização da data `Last Amended`.
- Toda spec e plan DEVE incluir uma seção "Constitution Check"
  verificando conformidade com os princípios acima.
- Complexidade adicionada além do princípio de simplicidade (IV)
  DEVE ser justificada na seção "Complexity Tracking" do plan.

**Version**: 1.1.0 | **Ratified**: 2026-03-04 | **Last Amended**: 2026-03-04
