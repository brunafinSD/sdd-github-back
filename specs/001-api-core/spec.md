# Feature Specification: API REST — Fut Pay Manager

**Feature Branch**: `001-api-core`  
**Created**: 2026-03-04  
**Status**: Draft  
**Input**: Constitution v1.1.0 + frontend specs (001-futsal-cash-manager, 002-dual-cash-split, 003-fake-login-screen). API backend FastAPI + MongoDB para servir a PWA existente, substituindo a camada de dados local (IndexedDB/Dexie).

### Out-of-Scope

- Multi-user / roles / multi-tenancy (sistema é single-user)
- Notificações (push, email, SMS)
- Relatórios exportáveis (PDF, CSV, Excel)
- Migração de dados do IndexedDB para o backend
- Deploy, infraestrutura e CI/CD

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Autenticação JWT (Priority: P1)

O frontend envia credenciais (username + password) para a API e recebe um token JWT que deve ser incluído em todas as requisições subsequentes. Sem autenticação, nenhum endpoint é acessível.

**Why this priority**: Sem autenticação, nenhuma outra funcionalidade pode ser protegida. É prerequisito de todas as user stories.

**Independent Test**: Enviar `POST /auth/login` com credenciais corretas → receber token. Usar token em `GET /games` → 200. Enviar `GET /games` sem token → 401.

**Acceptance Scenarios**:

1. **Given** credenciais corretas (`parceriasdojoguinho` / `futdaquinta`), **When** `POST /auth/login` com body `{ "username": "parceriasdojoguinho", "password": "futdaquinta" }`, **Then** resposta 200 com `{ "access_token": "<jwt>", "token_type": "bearer" }`
2. **Given** credenciais incorretas, **When** `POST /auth/login`, **Then** resposta 401 com `{ "detail": "Usuário ou senha inválidos" }` — mensagem genérica sem revelar qual campo está errado
3. **Given** campos com espaços nas bordas, **When** `POST /auth/login` com `"  parceriasdojoguinho  "`, **Then** sistema aplica `trim()` e autentica normalmente
4. **Given** capitalização diferente (ex: `Parceriasdojoguinho`), **When** `POST /auth/login`, **Then** resposta 401 — comparação case-sensitive
5. **Given** campos vazios, **When** `POST /auth/login`, **Then** resposta 422 (validation error)
6. **Given** nenhum token no header, **When** qualquer requisição a endpoint protegido, **Then** resposta 401
7. **Given** token expirado, **When** qualquer requisição a endpoint protegido, **Then** resposta 401

---

### User Story 2 — CRUD de Jogos e Gestão de Presenças (Priority: P1)

A gerente cria um jogo, adiciona jogadoras (manualmente ou colando lista), define método de pagamento e valor de cada uma, e finaliza o jogo para que o caixa seja atualizado automaticamente.

**Why this priority**: É a operação principal do sistema. Sem jogos, o caixa não tem dados.

**Independent Test**: `POST /games` → criar jogo pendente. `POST /games/{id}/players` → adicionar jogadoras. `PUT /games/{id}/players/{pid}` → alterar pagamento. `POST /games/{id}/finalize` → verificar que transactions são criadas e CashSummary reflete o impacto.

**Acceptance Scenarios**:

1. **Given** usuário autenticado, **When** `POST /games` com `{ "date": "2026-03-10T20:00:00Z" }`, **Then** jogo criado com status `pending`, courtCost default 9000, players vazio, cashImpact null — resposta 201
2. **Given** jogo pendente, **When** `POST /games/{id}/players` com `{ "name": "Maria", "paymentMethod": "pix", "amountPaid": 1000 }`, **Then** jogadora adicionada ao jogo — resposta 201
3. **Given** jogo pendente, **When** `POST /games/{id}/players` com `{ "name": "A" }` (nome com menos de 2 chars), **Then** resposta 422
4. **Given** jogo pendente com jogadoras, **When** `PUT /games/{id}/players/{pid}` com `{ "paymentMethod": "on_court", "amountPaid": 1500 }`, **Then** jogadora atualizada
5. **Given** jogo pendente com jogadoras, **When** `DELETE /games/{id}/players/{pid}`, **Then** jogadora removida
6. **Given** jogo pendente com 10 jogadoras (R$ 10 cada, mistas pix/on_court), **When** `POST /games/{id}/finalize`, **Then** jogo muda para `finished`, `cashImpact` calculado como `Σ(amountPaid) - courtCost`, transactions criadas separadas por `cashTarget` (pix→adm, on_court→court), `finishedAt` definido
7. **Given** jogo pendente sem jogadoras, **When** `POST /games/{id}/finalize`, **Then** resposta 400 — não pode finalizar jogo sem jogadoras
8. **Given** jogo já finalizado, **When** `PUT /games/{id}` ou `POST /games/{id}/players`, **Then** resposta 400 — jogo imutável após finalização
9. **Given** jogo pendente, **When** `POST /games/{id}/cancel`, **Then** status muda para `cancelled`, nenhuma transaction criada, nenhum impacto no caixa
10. **Given** jogo pendente, **When** `PUT /games/{id}` com `{ "courtCost": 12000 }`, **Then** courtCost atualizado para R$ 120,00
11. **Given** jogo pendente, **When** `DELETE /games/{id}`, **Then** jogo excluído permanentemente — resposta 204
12. **Given** jogo finalizado ou cancelado, **When** `DELETE /games/{id}`, **Then** resposta 400 — apenas jogos pendentes podem ser excluídos

---

### User Story 3 — Dashboard e Resumo do Caixa (Priority: P1)

A gerente abre o app e vê o saldo total do caixa, o breakdown (Quadra / ADM) e os jogos do mês corrente.

**Why this priority**: É a primeira tela do app e funcionalidade de maior uso diário.

**Independent Test**: `GET /cash/summary` → retorna saldos corretos. `GET /games?month=2026-03` → retorna jogos do mês.

**Acceptance Scenarios**:

1. **Given** transactions existem no banco, **When** `GET /cash/summary`, **Then** resposta 200 com `{ "totalBalance": N, "courtBalance": N, "admBalance": N, "totalIn": N, "totalOut": N, "transactionCount": N, "lastUpdatedAt": "..." }` — todos os valores em centavos (integer)
2. **Given** `totalBalance` negativo, **When** `GET /cash/summary`, **Then** valor negativo retornado normalmente (sistema suporta débito)
3. **Given** jogos existem em março/2026, **When** `GET /games?month=2026-03`, **Then** retorna apenas jogos daquele mês, ordenados por data desc
4. **Given** nenhum jogo no mês, **When** `GET /games?month=2026-03`, **Then** resposta 200 com array vazio
5. **Given** não informado filtro de mês, **When** `GET /games`, **Then** retorna todos os jogos paginados

---

### User Story 4 — Ajustes Manuais do Caixa (Priority: P2)

A gerente adiciona entradas (doações, patrocínio) ou saídas (compra de material) manualmente ao caixa, sempre com justificativa obrigatória e seleção de caixa destino (Quadra ou ADM).

**Why this priority**: Permite manter o caixa preciso com movimentações que não são jogos.

**Independent Test**: `POST /transactions` com tipo `manual_in` e justificativa → saldo atualizado. Repetir com `manual_out`. Tentar sem justificativa → 422.

**Acceptance Scenarios**:

1. **Given** usuário autenticado, **When** `POST /transactions` com `{ "type": "manual_in", "amount": 5000, "description": "Doação de João", "justification": "Contribuição mensal", "cashTarget": "adm" }`, **Then** transaction criada, resposta 201, caixa ADM aumenta R$ 50
2. **Given** tipo `manual_out`, **When** `POST /transactions` com `{ "type": "manual_out", "amount": 8000, "description": "Compra de bolas", "justification": "Material esportivo", "cashTarget": "adm" }`, **Then** transaction criada com amount negativo (-8000), caixa ADM diminui R$ 80
3. **Given** justificativa vazia ou com menos de 5 caracteres, **When** `POST /transactions` com tipo manual, **Then** resposta 422
4. **Given** `cashTarget` não informado, **When** `POST /transactions`, **Then** assume `"adm"` como default
5. **Given** ajuste manual, **When** transação criada, **Then** `gameId` é null, `justification` é obrigatória

---

### User Story 5 — Histórico de Movimentações e Partidas (Priority: P2)

A gerente visualiza o histórico completo de transações com filtros por período e tipo, e uma listagem de todas as partidas finalizadas.

**Why this priority**: Importante para auditoria e transparência, mas não crítica para operação do dia a dia.

**Independent Test**: `GET /transactions` → listar todas. `GET /transactions?from=2026-03-01&to=2026-03-31` → filtragem por período. `GET /games?status=finished` → histórico de partidas.

**Acceptance Scenarios**:

1. **Given** transactions existem, **When** `GET /transactions`, **Then** resposta 200 com lista paginada (default 20 por página), ordenada por `createdAt` desc
2. **Given** parâmetros de data, **When** `GET /transactions?from=2026-03-01&to=2026-03-31`, **Then** retorna apenas transações do período
3. **Given** filtro por tipo, **When** `GET /transactions?type=game`, **Then** retorna apenas transações de jogos
4. **Given** paginação, **When** `GET /transactions?page=2&limit=10`, **Then** retorna segunda página com 10 itens e metadata de paginação
5. **Given** jogos finalizados existem, **When** `GET /games?status=finished`, **Then** retorna histórico de partidas com data, número de jogadoras e cashImpact
6. **Given** transação de tipo `game`, **When** visualizar detalhes, **Then** `gameId` referencia o jogo correspondente

---

### User Story 6 — Transferências entre Caixas (Priority: P3)

A gerente transfere dinheiro acumulado no caixa Quadra (dinheiro físico recolhido na quadra) para o caixa ADM, registrando a operação como uma transação do tipo `transfer`.

**Why this priority**: Funcionalidade de suporte financeiro. O sistema funciona sem ela (o dinheiro fica no caixa quadra até ser transferido).

**Independent Test**: `POST /transactions/transfer` com amount válido → courtBalance diminui, admBalance aumenta, totalBalance não muda. Tentar com amount > courtBalance → 400.

**Acceptance Scenarios**:

1. **Given** courtBalance = R$ 60 (6000 centavos), **When** `POST /transactions/transfer` com `{ "amount": 6000 }`, **Then** duas transactions criadas (uma saída court, uma entrada adm), courtBalance = 0, admBalance += 6000, totalBalance inalterado — resposta 201
2. **Given** courtBalance = R$ 60, **When** `POST /transactions/transfer` com `{ "amount": 10000 }`, **Then** resposta 400 — saldo insuficiente no caixa quadra
3. **Given** amount = 0, **When** `POST /transactions/transfer`, **Then** resposta 422 — transferência de valor zero bloqueada
4. **Given** amount negativo, **When** `POST /transactions/transfer`, **Then** resposta 422
5. **Given** transferência realizada, **When** `GET /transactions`, **Then** operação aparece no histórico com tipo `transfer` e descrição "Transferência Quadra → ADM"

---

### User Story 7 — Crédito de Quadra em Jogo (Priority: P3)

A gerente pode usar o saldo do caixa Quadra para abater no custo de um jogo pendente (courtCredit), reduzindo o impacto financeiro que as jogadoras precisam cobrir.

**Why this priority**: Funcionalidade avançada de otimização. O fluxo básico funciona sem ela.

**Independent Test**: `POST /games/{id}/apply-credit` com amount ≤ courtBalance → courtCredit registrado no jogo, courtBalance reduzido.

**Acceptance Scenarios**:

1. **Given** courtBalance = R$ 60 e jogo pendente com courtCost R$ 90, **When** `POST /games/{id}/apply-credit` com `{ "amount": 6000 }`, **Then** jogo.courtCredit = 6000, transaction `manual_out` no court, courtBalance -= 6000
2. **Given** courtBalance = R$ 30, **When** `POST /games/{id}/apply-credit` com `{ "amount": 6000 }`, **Then** resposta 400 — saldo insuficiente
3. **Given** jogo com courtCredit já aplicado, **When** jogo é finalizado, **Then** `cashImpact` = Σ(amountPaid) − (courtCost − courtCredit)
4. **Given** jogo finalizado, **When** `POST /games/{id}/apply-credit`, **Then** resposta 400 — jogo imutável

---

### Edge Cases

- **Nomes duplicados**: Jogadoras com mesmo nome são permitidas (podem ser pessoas diferentes).
- **Jogo sem jogadoras**: Não pode ser finalizado, mas pode ser cancelado ou excluído.
- **Exclusão de jogo**: Apenas jogos `pending` podem ser excluídos (hard delete). Jogos `finished`/`cancelled` permanecem no histórico permanentemente.
- **Caixa negativo**: Sistema suporta valores negativos — não bloqueia operações.
- **Jogadora adicionada tardiamente**: Permitido adicionar jogadoras a jogo pendente a qualquer momento antes de finalizar.
- **courtCost editável**: Pode ser alterado por jogo (default R$ 90,00 = 9000 centavos), mas somente enquanto jogo está `pending`.
- **Transações imutáveis**: Nenhuma transação pode ser editada ou excluída. Para corrigir, criar transação reversa.
- **Estorno de jogo cancelado**: Se um jogo finalizado precisa ser desfeito, deve-se criar transações manuais reversas (não há endpoint de "desfinalizar").
- **Token expirado**: Todas as rotas protegidas retornam 401 quando token está expirado ou inválido.
- **Datas UTC**: Todas as datas retornadas pela API são UTC ISO 8601. A conversão para fuso local é responsabilidade do frontend.
- **Transferência parcial**: Transferir valor menor que o saldo do caixa quadra é permitido.
- **amountPaid editável**: Default R$ 10,00 (1000 centavos) mas pode ser alterado por jogadora enquanto jogo está pendente.

## Requirements *(mandatory)*

### Functional Requirements

**Autenticação**
- **FR-001**: API DEVE expor `POST /auth/login` que valida credenciais (hardcoded, configuráveis via env vars) e retorna JWT
- **FR-002**: Validação de credenciais DEVE ser case-sensitive e aplicar trim() nos inputs
- **FR-003**: Mensagem de erro de login DEVE ser genérica, sem indicar qual campo está incorreto
- **FR-004**: Todas as rotas (exceto `/auth/login` e `/docs`) DEVEM exigir JWT válido no header `Authorization: Bearer <token>`
- **FR-005**: Token JWT DEVE expirar em 24 horas

**Jogos**
- **FR-006**: API DEVE expor CRUD de jogos: `POST /games`, `GET /games`, `GET /games/{id}`, `PUT /games/{id}`, `DELETE /games/{id}`
- **FR-007**: Jogo criado DEVE ter status `pending`, courtCost default 9000, players vazio, cashImpact null
- **FR-008**: API DEVE permitir filtrar jogos por mês (`?month=YYYY-MM`) e status (`?status=pending|finished|cancelled`)
- **FR-009**: GET /games DEVE suportar paginação (`?page=1&limit=20`)
- **FR-010**: Jogos DEVEM ser retornados com lista de jogadoras embedded
- **FR-011**: Edição de jogo (PUT) DEVE ser bloqueada se status ≠ `pending`
- **FR-011a**: Exclusão de jogo (DELETE) DEVE ser permitida apenas se status = `pending`. Jogos `finished` ou `cancelled` não podem ser excluídos

**Jogadoras**
- **FR-012**: API DEVE expor gerenciamento de jogadoras como sub-recurso: `POST /games/{id}/players`, `PUT /games/{id}/players/{pid}`, `DELETE /games/{id}/players/{pid}`
- **FR-013**: Nome de jogadora DEVE ter entre 2 e 100 caracteres, com trim aplicado
- **FR-014**: Nomes duplicados DEVEM ser permitidos
- **FR-015**: `amountPaid` default é 1000 (R$ 10,00), DEVE ser > 0 e editável
- **FR-016**: `paymentMethod` DEVE ser `pix` ou `on_court`
- **FR-017**: Operações em jogadoras DEVEM ser bloqueadas se jogo não está `pending`

**Finalização e Cancelamento**
- **FR-018**: `POST /games/{id}/finalize` DEVE mudar status para `finished`, calcular `cashImpact`, criar transactions separadas por `cashTarget`, definir `finishedAt`
- **FR-019**: `cashImpact` = Σ(amountPaid de todas jogadoras) − courtCost + courtCredit (se houver)
- **FR-020**: Transactions de jogo DEVEM ser separadas por método de pagamento: jogadoras `pix` → transaction com `cashTarget=adm`; jogadoras `on_court` → transaction com `cashTarget=court`
- **FR-021**: Finalização DEVE ser bloqueada se jogo não tem jogadoras
- **FR-022**: `POST /games/{id}/cancel` DEVE mudar status para `cancelled` sem criar transactions
- **FR-023**: Cancelamento DEVE ser bloqueado se status ≠ `pending`

**Caixa e Transações**
- **FR-024**: API DEVE expor `GET /cash/summary` retornando CashSummary calculado dinamicamente
- **FR-025**: `totalBalance` DEVE ser sempre igual a `courtBalance + admBalance`
- **FR-026**: API DEVE expor `GET /transactions` com filtros por período (`?from=&to=`), tipo (`?type=`), cashTarget (`?cashTarget=`) e paginação
- **FR-027**: API DEVE expor `POST /transactions` para ajustes manuais (manual_in, manual_out) com justificativa obrigatória (5-500 chars)
- **FR-028**: Ajustes manuais DEVEM aceitar `cashTarget` (default `adm`)
- **FR-029**: Para `manual_in`, `amount` DEVE ser positivo; para `manual_out`, API DEVE aceitar amount positivo e armazenar como negativo
- **FR-030**: Transações são append-only — nenhum endpoint de edição ou exclusão

**Transferências**
- **FR-031**: API DEVE expor `POST /transactions/transfer` para mover dinheiro de court → adm
- **FR-032**: Transferência DEVE ser bloqueada se `amount` > `courtBalance` ou `amount` ≤ 0
- **FR-033**: Transferência DEVE gerar transaction(s) com `type=transfer` registrando saída do court e entrada no adm

**Crédito de Quadra**
- **FR-034**: API DEVE expor `POST /games/{id}/apply-credit` para aplicar saldo do caixa quadra como abatimento no custo de um jogo pendente
- **FR-035**: Crédito DEVE ser bloqueado se `amount` > `courtBalance` ou jogo não está `pending`
- **FR-036**: `courtCredit` DEVE ser considerado no cálculo de `cashImpact` na finalização

**Gerais**
- **FR-037**: Todos os valores monetários DEVEM ser integer (centavos) — nunca floating-point
- **FR-038**: Todas as datas DEVEM ser retornadas como ISO 8601 UTC
- **FR-039**: Respostas de sucesso DEVEM usar envelope `{ "data": ... }` para consistência
- **FR-040**: API DEVE suportar CORS para permitir requisições do frontend PWA
- **FR-041**: Respostas de erro DEVEM usar o formato padrão do framework (`{ "detail": "..." }`) — sem envelope customizado de erro

### Key Entities

Conforme Data Model Canon da Constitution v1.1.0:

- **Game**: Partida de futsal — id, date, status (pending|finished|cancelled), courtCost, players[], cashImpact, courtCredit, createdAt, updatedAt, finishedAt. Players são parte integrante do Game (não existem independentemente).

- **Player**: Participação de uma jogadora em um jogo — id, name, paymentMethod (pix|on_court), amountPaid. Vinculado diretamente ao Game.

- **Transaction**: Movimentação financeira no caixa — id, type (game|manual_in|manual_out|transfer), amount, description, justification, gameId, cashTarget (court|adm), createdAt. Append-only, imutável.

- **CashSummary**: Resumo financeiro agregado — totalBalance, courtBalance, admBalance, totalIn, totalOut, transactionCount, lastUpdatedAt. Calculado dinamicamente a partir das transações existentes, nunca persistido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todos os endpoints retornam resposta em < 200ms (P95) em condições normais de uso
- **SC-002**: Token JWT gerado e validado corretamente — 100% de bloqueio sem token, 100% de acesso com token válido
- **SC-003**: Cálculo de `cashImpact` e `CashSummary` é 100% preciso em todos os cenários (valores inteiros, sem erros de arredondamento)
- **SC-004**: Cálculo de `courtBalance + admBalance` é sempre igual a `totalBalance` — zero discrepância
- **SC-005**: Nenhuma transação pode ser editada ou excluída via API — 100% append-only
- **SC-006**: Todas as validações de negócio (jogo imutável após finalização, justificativa obrigatória, saldo insuficiente em transferência) retornam erro HTTP adequado com mensagem clara
- **SC-007**: API suporta o fluxo completo do frontend sem alteração nos contratos de dados existentes (Money em centavos, enums, IDs)
- **SC-008**: Documentação interativa da API é acessível via navegador em `/docs`, cobrindo todos os endpoints com schemas de request/response

## Assumptions

- Sistema é single-user (uma gerente) — não há necessidade de multi-tenancy ou roles
- Credenciais de autenticação são configuráveis via variáveis de ambiente (defaults fornecidos para desenvolvimento)
- Todos os valores monetários são representados em centavos (integer) para eliminar erros de arredondamento
- O frontend PWA existente já implementa a lógica de exibição — a API foca exclusivamente em persistência e regras de negócio
- Transferências são sempre unidirecionais: Quadra → ADM
- O campo `courtCredit` é um abatimento no custo do jogo usando saldo do caixa Quadra, não um pagamento de jogadora
- Datas são armazenadas e retornadas em UTC ISO 8601 — conversão de fuso é responsabilidade do frontend
- Não há migração de dados do IndexedDB — quando o frontend integrar com a API, o banco começa do zero. Dados locais existentes são de desenvolvimento/teste
- Observabilidade/logging: sem configuração customizada — logs padrão do framework são suficientes para esta fase

## Clarifications

### Session 2026-03-04

- Q: O que acontece com os dados existentes no IndexedDB quando a API entrar no ar? → A: Começar do zero — sem migração. Dados locais são de teste.
- Q: A gerente pode excluir um jogo? → A: Apenas jogos `pending` podem ser excluídos. Jogos `finished`/`cancelled` permanecem no histórico.
- Q: Qual nível de observabilidade/logging é necessário? → A: Nenhum customizado — confiar nos logs padrão do framework.
- Q: Qual formato padrão para respostas de erro? → A: Formato padrão do framework (`{ "detail": "..." }`), sem envelope customizado.
- Q: O que está fora do escopo desta feature? → A: Multi-user, notificações, relatórios, migração IndexedDB, deploy/infra.
