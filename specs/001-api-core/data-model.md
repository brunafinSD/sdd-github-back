# Data Model: API REST — Fut Pay Manager

**Branch**: `001-api-core` | **Date**: 2026-03-04
**Source**: [spec.md](spec.md) Key Entities + Constitution §Data Model Canon

---

## Entity Overview

| Entity | Storage | Mutability | Notes |
|--------|---------|------------|-------|
| Game | MongoDB collection `games` | Mutable while `pending`, immutable after `finished`/`cancelled` | Players embedded as array |
| Player | Embedded in Game | Mutable while parent Game is `pending` | No standalone collection |
| Transaction | MongoDB collection `transactions` | Append-only, immutable | Never edited or deleted |
| CashSummary | Not persisted | N/A (computed) | Aggregated from transactions on-demand |

---

## Entities

### Game

Partida de futsal com jogadoras e controle financeiro.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| id | string (ObjectId) | auto | auto-generated | MongoDB `_id` | Identificador único |
| date | datetime (ISO 8601 UTC) | yes | — | Must be valid datetime | Data/hora da partida |
| status | enum: `pending` \| `finished` \| `cancelled` | auto | `pending` | — | Estado do jogo |
| courtCost | integer (centavos) | no | 9000 | ≥ 0 | Custo da quadra (R$ 90,00 = 9000) |
| players | Player[] | auto | `[]` | — | Jogadoras participantes |
| cashImpact | integer (centavos) \| null | auto | null | Set on finalize | Impacto financeiro = Σ(amountPaid) − courtCost + courtCredit |
| courtCredit | integer (centavos) \| null | auto | null | ≤ courtBalance when applied | Crédito de quadra aplicado |
| createdAt | datetime (ISO 8601 UTC) | auto | now | — | Data de criação |
| updatedAt | datetime (ISO 8601 UTC) | auto | now | Updated on any change | Última atualização |
| finishedAt | datetime (ISO 8601 UTC) \| null | auto | null | Set on finalize | Data de finalização |

**State Transitions**:

```
pending → finished    (POST /games/{id}/finalize)
pending → cancelled   (POST /games/{id}/cancel)
pending → [deleted]   (DELETE /games/{id})
```

No transitions from `finished` or `cancelled` to any other state.

**Validation Rules**:
- `courtCost` editable only while `status = pending`
- All mutations (PUT, add/edit/delete players) blocked when `status ≠ pending`
- Finalization blocked if `players` is empty
- DELETE only allowed when `status = pending` (hard delete)

---

### Player

Participação de uma jogadora em um jogo específico (embedded no Game).

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| id | string (ObjectId) | auto | auto-generated | Unique within game | Identificador dentro do jogo |
| name | string | yes | — | 2–100 chars, trim applied | Nome da jogadora |
| paymentMethod | enum: `pix` \| `on_court` | no | `pix` | — | Método de pagamento |
| amountPaid | integer (centavos) | no | 1000 | > 0 | Valor pago (R$ 10,00 = 1000) |

**Validation Rules**:
- Nome: trim → validate length 2–100
- Nomes duplicados são permitidos (pessoas diferentes podem ter o mesmo nome)
- `amountPaid` must be > 0 (positive integer)
- Operations blocked when parent game `status ≠ pending`

---

### Transaction

Movimentação financeira no caixa (append-only, imutável).

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| id | string (ObjectId) | auto | auto-generated | MongoDB `_id` | Identificador único |
| type | enum: `game` \| `manual_in` \| `manual_out` \| `transfer` | yes | — | — | Tipo de transação |
| amount | integer (centavos) | yes | — | Positive for in, negative for out | Valor da transação |
| description | string | no | — | — | Descrição livre |
| justification | string \| null | conditional | null | Required for `manual_in`/`manual_out`, 5–500 chars | Justificativa obrigatória para ajustes manuais |
| gameId | string (ObjectId) \| null | conditional | null | References Game.id | Referência ao jogo (para type=`game`) |
| cashTarget | enum: `court` \| `adm` | yes | `adm` | — | Caixa destino |
| createdAt | datetime (ISO 8601 UTC) | auto | now | — | Data de criação |

**Type-specific Rules**:

| Type | amount sign | justification | gameId | cashTarget | Creation trigger |
|------|-------------|---------------|--------|------------|-----------------|
| `game` | positive | null | required | From `paymentMethod` | Auto on game finalize |
| `manual_in` | positive | required (5-500 chars) | null | user choice (default `adm`) | Manual via POST /transactions |
| `manual_out` | negative | required (5-500 chars) | null | user choice (default `adm`) | Manual via POST /transactions |
| `transfer` | positive (out) / positive (in) | null | null | `court` (out), `adm` (in) | POST /transactions/transfer |

**Immutability**: No endpoint for edit or delete. To correct an error, create a reversing transaction.

**Game Finalization Transactions**: When a game is finalized, transactions are created grouped by `paymentMethod`:
- All `pix` players → 1 transaction with `cashTarget=adm`, amount = Σ(amountPaid of pix players)
- All `on_court` players → 1 transaction with `cashTarget=court`, amount = Σ(amountPaid of on_court players)

---

### CashSummary

Resumo financeiro calculado dinamicamente (nunca persistido).

| Field | Type | Description |
|-------|------|-------------|
| totalBalance | integer (centavos) | courtBalance + admBalance |
| courtBalance | integer (centavos) | Σ(amount) where cashTarget=court |
| admBalance | integer (centavos) | Σ(amount) where cashTarget=adm |
| totalIn | integer (centavos) | Σ(amount) where amount > 0 |
| totalOut | integer (centavos) | Σ(|amount|) where amount < 0 (positive number) |
| transactionCount | integer | Total number of transactions |
| lastUpdatedAt | datetime (ISO 8601 UTC) \| null | Max createdAt from transactions, null if no transactions |

**Invariant**: `totalBalance` MUST always equal `courtBalance + admBalance` (FR-025, SC-004).

**Computation**: Aggregation pipeline on `transactions` collection — single `$group` stage.

---

## Enums

| Enum | Values | Usage |
|------|--------|-------|
| GameStatus | `pending`, `finished`, `cancelled` | Game.status |
| PaymentMethod | `pix`, `on_court` | Player.paymentMethod |
| TransactionType | `game`, `manual_in`, `manual_out`, `transfer` | Transaction.type |
| CashTarget | `court`, `adm` | Transaction.cashTarget |

---

## Relationships

```
Game 1──* Player          (embedded array, lifecycle bound to Game)
Game 1──* Transaction     (via Transaction.gameId, only for type=game)
Transaction *──1 CashTarget  (determines which balance is affected)
CashSummary ←── aggregation of all Transactions
```

---

## MongoDB Collections

| Collection | Indexes | Notes |
|------------|---------|-------|
| `games` | `_id` (default), `status`, `date` | Players embedded — no separate collection |
| `transactions` | `_id` (default), `createdAt`, `type`, `cashTarget`, `gameId` | Append-only |

---

## Money Convention

All monetary values are stored and transmitted as **integer centavos** (1 R$ = 100 centavos).

| Display | Centavos | Field example |
|---------|----------|---------------|
| R$ 10,00 | 1000 | amountPaid default |
| R$ 90,00 | 9000 | courtCost default |
| R$ 0,01 | 1 | minimum amount |

Never use floating-point for money. Arithmetic on integers is exact.
