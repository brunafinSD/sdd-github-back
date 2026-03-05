# API Contracts: Fut Pay Manager

**Branch**: `001-api-core` | **Date**: 2026-03-04
**Source**: [spec.md](../spec.md) FRs + [data-model.md](../data-model.md)

---

## Base URL

```
http://localhost:8000
```

## Response Conventions

- **Success**: `{ "data": <payload> }` (single item) or `{ "data": [<items>], "meta": { ... } }` (paginated list)
- **Error**: `{ "detail": "<message>" }` (FastAPI default)
- **No Content**: Empty body (204)
- **Money**: All monetary values are integer centavos (1 R$ = 100)
- **Dates**: ISO 8601 UTC strings

## Authentication

All endpoints except `POST /auth/login` and `GET /docs` require:
```
Authorization: Bearer <jwt_token>
```

Unauthorized requests return `401 { "detail": "Token inválido ou expirado" }`.

---

## Endpoints

### 1. Authentication

#### POST /auth/login

Login and receive JWT token.

**Auth required**: No

**Request Body**:
```json
{
  "username": "parceriasdojoguinho",
  "password": "futdaquinta"
}
```

**Success Response** (200):
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 401 | Invalid credentials | `{ "detail": "Usuário ou senha inválidos" }` |
| 422 | Missing/empty fields | `{ "detail": [{ "msg": "...", ... }] }` |

**Business Rules**: FR-001, FR-002, FR-003
- Credentials are case-sensitive
- Input is trimmed before comparison
- Error message is generic (never reveals which field is wrong)

---

### 2. Games

#### POST /games

Create a new game.

**Auth required**: Yes

**Request Body**:
```json
{
  "date": "2026-03-10T20:00:00Z",
  "courtCost": 9000
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| date | datetime (ISO 8601) | yes | — | Valid datetime |
| courtCost | integer | no | 9000 | ≥ 0 |

**Success Response** (201):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "date": "2026-03-10T20:00:00Z",
    "status": "pending",
    "courtCost": 9000,
    "players": [],
    "cashImpact": null,
    "courtCredit": null,
    "createdAt": "2026-03-04T10:00:00Z",
    "updatedAt": "2026-03-04T10:00:00Z",
    "finishedAt": null
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 401 | Unauthorized | `{ "detail": "Token inválido ou expirado" }` |
| 422 | Validation error | `{ "detail": [...] }` |

---

#### GET /games

List games with optional filters and pagination.

**Auth required**: Yes

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| month | string (YYYY-MM) | — | Filter by month |
| status | enum | — | Filter by status: `pending`, `finished`, `cancelled` |
| page | integer | 1 | Page number (1-indexed) |
| limit | integer | 20 | Items per page (1–100) |

**Success Response** (200):
```json
{
  "data": [
    {
      "id": "65f1a2b3c4d5e6f7a8b9c0d1",
      "date": "2026-03-10T20:00:00Z",
      "status": "finished",
      "courtCost": 9000,
      "players": [
        {
          "id": "a1b2c3d4e5f6a7b8c9d0e1f2",
          "name": "Maria",
          "paymentMethod": "pix",
          "amountPaid": 1000
        }
      ],
      "cashImpact": 1000,
      "courtCredit": null,
      "createdAt": "2026-03-04T10:00:00Z",
      "updatedAt": "2026-03-10T22:00:00Z",
      "finishedAt": "2026-03-10T22:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "totalPages": 3
  }
}
```

---

#### GET /games/{id}

Get a single game with embedded players.

**Auth required**: Yes

**Path Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| id | string (ObjectId) | Game ID |

**Success Response** (200):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "date": "2026-03-10T20:00:00Z",
    "status": "pending",
    "courtCost": 9000,
    "players": [],
    "cashImpact": null,
    "courtCredit": null,
    "createdAt": "2026-03-04T10:00:00Z",
    "updatedAt": "2026-03-04T10:00:00Z",
    "finishedAt": null
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 404 | Game not found | `{ "detail": "Jogo não encontrado" }` |

---

#### PUT /games/{id}

Update a pending game (courtCost, date).

**Auth required**: Yes

**Request Body**:
```json
{
  "date": "2026-03-11T20:00:00Z",
  "courtCost": 12000
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| date | datetime | no | Valid datetime |
| courtCost | integer | no | ≥ 0 |

**Success Response** (200):
```json
{
  "data": { "...updated game object..." }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Jogo não pode ser editado após finalização ou cancelamento" }` |
| 404 | Not found | `{ "detail": "Jogo não encontrado" }` |

---

#### DELETE /games/{id}

Delete a pending game permanently.

**Auth required**: Yes

**Success Response** (204): No body

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Apenas jogos pendentes podem ser excluídos" }` |
| 404 | Not found | `{ "detail": "Jogo não encontrado" }` |

---

#### POST /games/{id}/finalize

Finalize a pending game — calculates cashImpact and creates transactions.

**Auth required**: Yes

**Request Body**: None

**Success Response** (200):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "status": "finished",
    "cashImpact": 1000,
    "finishedAt": "2026-03-10T22:00:00Z",
    "...rest of game fields..."
  }
}
```

**Side Effects**:
- Status changes to `finished`
- `cashImpact` = Σ(amountPaid) − courtCost + courtCredit
- `finishedAt` set to current time
- Transactions created:
  - 1 transaction `type=game`, `cashTarget=adm`, amount = Σ(amountPaid of pix players)
  - 1 transaction `type=game`, `cashTarget=court`, amount = Σ(amountPaid of on_court players)
  - Transactions with amount=0 are NOT created (skip if no players for that method)

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Jogo não pode ser finalizado" }` |
| 400 | No players | `{ "detail": "Jogo sem jogadoras não pode ser finalizado" }` |
| 404 | Not found | `{ "detail": "Jogo não encontrado" }` |

---

#### POST /games/{id}/cancel

Cancel a pending game without financial impact.

**Auth required**: Yes

**Request Body**: None

**Success Response** (200):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "status": "cancelled",
    "...rest of game fields..."
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Apenas jogos pendentes podem ser cancelados" }` |
| 404 | Not found | `{ "detail": "Jogo não encontrado" }` |

---

#### POST /games/{id}/apply-credit

Apply court balance as credit to reduce a game's effective court cost.

**Auth required**: Yes

**Request Body**:
```json
{
  "amount": 6000
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | integer | yes | > 0, ≤ courtBalance |

**Success Response** (200):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "courtCredit": 6000,
    "...rest of game fields..."
  }
}
```

**Side Effects**:
- `courtCredit` set on the game
- Transaction `type=manual_out`, `cashTarget=court`, `amount=-{amount}` created
- courtBalance decreases

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Crédito só pode ser aplicado a jogos pendentes" }` |
| 400 | Insufficient balance | `{ "detail": "Saldo insuficiente no caixa quadra" }` |
| 404 | Not found | `{ "detail": "Jogo não encontrado" }` |
| 422 | amount ≤ 0 | `{ "detail": [...] }` |

---

### 3. Players (sub-resource of Game)

#### POST /games/{id}/players

Add a player to a pending game.

**Auth required**: Yes

**Request Body**:
```json
{
  "name": "Maria",
  "paymentMethod": "pix",
  "amountPaid": 1000
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| name | string | yes | — | 2–100 chars (trimmed) |
| paymentMethod | enum | no | `pix` | `pix` or `on_court` |
| amountPaid | integer | no | 1000 | > 0 |

**Success Response** (201):
```json
{
  "data": {
    "id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "date": "2026-03-10T20:00:00Z",
    "status": "pending",
    "players": [
      {
        "id": "a1b2c3d4e5f6a7b8c9d0e1f2",
        "name": "Maria",
        "paymentMethod": "pix",
        "amountPaid": 1000
      }
    ],
    "...rest of game fields..."
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Jogadoras só podem ser adicionadas a jogos pendentes" }` |
| 404 | Game not found | `{ "detail": "Jogo não encontrado" }` |
| 422 | Validation error | `{ "detail": [...] }` |

---

#### PUT /games/{id}/players/{playerId}

Update a player in a pending game.

**Auth required**: Yes

**Request Body**:
```json
{
  "name": "Maria Silva",
  "paymentMethod": "on_court",
  "amountPaid": 1500
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | no | 2–100 chars (trimmed) |
| paymentMethod | enum | no | `pix` or `on_court` |
| amountPaid | integer | no | > 0 |

**Success Response** (200):
```json
{
  "data": { "...updated game with updated player..." }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Jogadoras não podem ser editadas em jogos finalizados ou cancelados" }` |
| 404 | Game or player not found | `{ "detail": "Jogo não encontrado" }` or `{ "detail": "Jogadora não encontrada" }` |
| 422 | Validation error | `{ "detail": [...] }` |

---

#### DELETE /games/{id}/players/{playerId}

Remove a player from a pending game.

**Auth required**: Yes

**Success Response** (200):
```json
{
  "data": { "...updated game without the removed player..." }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Game not pending | `{ "detail": "Jogadoras não podem ser removidas de jogos finalizados ou cancelados" }` |
| 404 | Game or player not found | `{ "detail": "..." }` |

---

### 4. Transactions

#### GET /transactions

List transactions with optional filters and pagination.

**Auth required**: Yes

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| from | date (YYYY-MM-DD) | — | Start date (inclusive) |
| to | date (YYYY-MM-DD) | — | End date (inclusive) |
| type | enum | — | Filter: `game`, `manual_in`, `manual_out`, `transfer` |
| cashTarget | enum | — | Filter: `court`, `adm` |
| page | integer | 1 | Page number (1-indexed) |
| limit | integer | 20 | Items per page (1–100) |

**Success Response** (200):
```json
{
  "data": [
    {
      "id": "b2c3d4e5f6a7b8c9d0e1f2a3",
      "type": "game",
      "amount": 5000,
      "description": "Jogo 10/03/2026 — pagamentos pix",
      "justification": null,
      "gameId": "65f1a2b3c4d5e6f7a8b9c0d1",
      "cashTarget": "adm",
      "createdAt": "2026-03-10T22:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 15,
    "totalPages": 1
  }
}
```

---

#### POST /transactions

Create a manual transaction (manual_in or manual_out).

**Auth required**: Yes

**Request Body**:
```json
{
  "type": "manual_in",
  "amount": 5000,
  "description": "Doação de João",
  "justification": "Contribuição mensal",
  "cashTarget": "adm"
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| type | enum | yes | — | `manual_in` or `manual_out` only |
| amount | integer | yes | — | > 0 |
| description | string | no | — | — |
| justification | string | yes | — | 5–500 chars |
| cashTarget | enum | no | `adm` | `court` or `adm` |

**Business Rules**:
- Only `manual_in` and `manual_out` types accepted (not `game` or `transfer`)
- For `manual_out`: amount is accepted as positive but stored as negative
- `justification` is mandatory for manual types

**Success Response** (201):
```json
{
  "data": {
    "id": "c3d4e5f6a7b8c9d0e1f2a3b4",
    "type": "manual_in",
    "amount": 5000,
    "description": "Doação de João",
    "justification": "Contribuição mensal",
    "gameId": null,
    "cashTarget": "adm",
    "createdAt": "2026-03-04T15:00:00Z"
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 422 | Validation (justification < 5 chars, invalid type, etc.) | `{ "detail": [...] }` |

---

#### POST /transactions/transfer

Transfer money from court balance to ADM balance.

**Auth required**: Yes

**Request Body**:
```json
{
  "amount": 6000
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | integer | yes | > 0, ≤ courtBalance |

**Success Response** (201):
```json
{
  "data": {
    "transferredAmount": 6000,
    "courtTransaction": {
      "id": "d4e5f6a7b8c9d0e1f2a3b4c5",
      "type": "transfer",
      "amount": -6000,
      "cashTarget": "court",
      "description": "Transferência Quadra → ADM",
      "createdAt": "2026-03-04T16:00:00Z"
    },
    "admTransaction": {
      "id": "e5f6a7b8c9d0e1f2a3b4c5d6",
      "type": "transfer",
      "amount": 6000,
      "cashTarget": "adm",
      "description": "Transferência Quadra → ADM",
      "createdAt": "2026-03-04T16:00:00Z"
    }
  }
}
```

**Error Responses**:
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Insufficient court balance | `{ "detail": "Saldo insuficiente no caixa quadra" }` |
| 422 | amount ≤ 0 | `{ "detail": [...] }` |

---

### 5. Cash Summary

#### GET /cash/summary

Get the current financial summary computed from all transactions.

**Auth required**: Yes

**Success Response** (200):
```json
{
  "data": {
    "totalBalance": 15000,
    "courtBalance": 5000,
    "admBalance": 10000,
    "totalIn": 25000,
    "totalOut": 10000,
    "transactionCount": 8,
    "lastUpdatedAt": "2026-03-10T22:00:00Z"
  }
}
```

**Empty state** (no transactions):
```json
{
  "data": {
    "totalBalance": 0,
    "courtBalance": 0,
    "admBalance": 0,
    "totalIn": 0,
    "totalOut": 0,
    "transactionCount": 0,
    "lastUpdatedAt": null
  }
}
```

---

## Endpoint Summary Table

| Method | Path | Auth | Description | FR |
|--------|------|------|-------------|-----|
| POST | /auth/login | No | Login, get JWT | FR-001–005 |
| POST | /games | Yes | Create game | FR-006–007 |
| GET | /games | Yes | List games (paginated, filterable) | FR-006,008–010 |
| GET | /games/{id} | Yes | Get single game | FR-006,010 |
| PUT | /games/{id} | Yes | Update pending game | FR-006,011 |
| DELETE | /games/{id} | Yes | Delete pending game | FR-006,011a |
| POST | /games/{id}/finalize | Yes | Finalize game | FR-018–021 |
| POST | /games/{id}/cancel | Yes | Cancel game | FR-022–023 |
| POST | /games/{id}/apply-credit | Yes | Apply court credit | FR-034–036 |
| POST | /games/{id}/players | Yes | Add player | FR-012–017 |
| PUT | /games/{id}/players/{pid} | Yes | Update player | FR-012–017 |
| DELETE | /games/{id}/players/{pid} | Yes | Remove player | FR-012,017 |
| GET | /transactions | Yes | List transactions (paginated, filterable) | FR-026 |
| POST | /transactions | Yes | Manual transaction | FR-027–030 |
| POST | /transactions/transfer | Yes | Transfer court→adm | FR-031–033 |
| GET | /cash/summary | Yes | Financial summary | FR-024–025 |

**Total**: 16 endpoints (1 public + 15 protected)
