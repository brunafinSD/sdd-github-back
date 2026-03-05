# Fut Pay Manager — API

API REST para gerenciamento de caixa de futsal. Controla jogos, presenças de jogadoras, pagamentos, transferências entre caixas e resumo financeiro.

## Tech Stack

- **Python 3.12+** / **FastAPI 0.115+**
- **MongoDB 7.x** via Motor (driver async)
- **PyJWT** para autenticação JWT
- **Pydantic v2** + **Pydantic Settings** para validação e configuração
- **Ruff** para linting e formatação

## Pré-requisitos

- Python 3.12 ou superior
- MongoDB 7.x rodando localmente (porta padrão `27017`)

## Setup

```bash
# 1. Clone o repositório
git clone <url-do-repo>
cd api-fut-pay-manager

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate

# 3. Instale as dependências
pip install -e ".[dev]"

# 4. Configure as variáveis de ambiente (opcional — já tem defaults para dev)
cp .env.example .env
```

## Rodando

```bash
# Modo desenvolvimento (com reload automático)
fastapi dev app/main.py

# Modo produção
fastapi run app/main.py
```

A API estará disponível em `http://localhost:8000`.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Autenticação

A API usa JWT com credenciais fixas (single-user).

**Credenciais padrão** (configuráveis via `.env`):
- Usuário: `parceriasdojoguinho`
- Senha: `futdaquinta`

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "parceriasdojoguinho", "password": "futdaquinta"}'
```

Use o `access_token` retornado em todas as requisições:

```
Authorization: Bearer <token>
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/login` | Login (JWT) |
| POST | `/games` | Criar jogo |
| GET | `/games` | Listar jogos (paginado, filtrável) |
| GET | `/games/{id}` | Buscar jogo |
| PUT | `/games/{id}` | Editar jogo pendente |
| DELETE | `/games/{id}` | Excluir jogo pendente |
| POST | `/games/{id}/finalize` | Finalizar jogo (cria transações) |
| POST | `/games/{id}/cancel` | Cancelar jogo |
| POST | `/games/{id}/apply-credit` | Aplicar crédito de quadra |
| POST | `/games/{id}/players` | Adicionar jogadora |
| PUT | `/games/{id}/players/{pid}` | Editar jogadora |
| DELETE | `/games/{id}/players/{pid}` | Remover jogadora |
| GET | `/transactions` | Histórico de transações |
| POST | `/transactions` | Criar transação manual |
| POST | `/transactions/transfer` | Transferir quadra → ADM |
| GET | `/cash/summary` | Resumo financeiro |

## Variáveis de Ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `MONGODB_URL` | `mongodb://localhost:27017` | URL de conexão MongoDB |
| `MONGODB_DATABASE` | `fut_pay_manager` | Nome do banco de dados |
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production` | Chave secreta para JWT |
| `AUTH_USERNAME` | `parceriasdojoguinho` | Usuário para login |
| `AUTH_PASSWORD` | `futdaquinta` | Senha para login |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Origens permitidas (CORS) |

## Estrutura do Projeto

```
app/
├── main.py              # App factory, CORS, lifespan, routers
├── config.py            # Settings via env vars (Pydantic BaseSettings)
├── database.py          # Motor client, lifespan, indexes
├── auth/
│   ├── router.py        # POST /auth/login
│   ├── service.py       # Validação de credenciais, criação JWT
│   └── deps.py          # Dependência get_current_user
├── models/
│   ├── enums.py         # GameStatus, PaymentMethod, TransactionType, CashTarget
│   ├── common.py        # PyObjectId, DataEnvelope, PaginatedEnvelope
│   ├── auth.py          # LoginRequest, LoginResponse
│   ├── game.py          # Game, Player schemas
│   ├── transaction.py   # Transaction schemas
│   └── cash.py          # CashSummary schema
├── services/
│   ├── game_service.py  # CRUD jogos, jogadoras, finalizar, cancelar
│   ├── cash_service.py  # Resumo financeiro, transações manuais, histórico
│   └── transfer_service.py  # Transferência quadra→ADM, crédito de quadra
├── routes/
│   ├── games.py         # Endpoints de jogos e jogadoras
│   ├── transactions.py  # Endpoints de transações e transferências
│   └── cash.py          # Endpoint de resumo financeiro
└── utils/
    └── (reservado)
```

## Convenções

- **Valores monetários**: sempre em **centavos** (integer). R$ 10,00 = `1000`.
- **Respostas de sucesso**: `{ "data": ... }` ou `{ "data": [...], "meta": { ... } }`
- **Respostas de erro**: `{ "detail": "..." }`
- **Datas**: ISO 8601 UTC
- **Transações**: append-only, imutáveis — nunca editadas ou deletadas

## Linting

```bash
# Verificar
ruff check app/

# Corrigir automaticamente
ruff check app/ --fix

# Formatar
ruff format app/
```

## Documentação Técnica

Especificações completas em `specs/001-api-core/`:

- [spec.md](specs/001-api-core/spec.md) — Especificação funcional
- [plan.md](specs/001-api-core/plan.md) — Plano de implementação
- [data-model.md](specs/001-api-core/data-model.md) — Modelo de dados
- [contracts/api-endpoints.md](specs/001-api-core/contracts/api-endpoints.md) — Contratos da API
- [research.md](specs/001-api-core/research.md) — Decisões técnicas
