# Spend Tracker API

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF.svg?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](#-testing--quality-assurance)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Production-grade personal finance & M-Pesa transaction tracking REST API built for East African spending habits.**  
> Features real-time M-Pesa C2B & SMS ingestion, rule-based categorisation with extensible Protocol architecture, automated budget threshold alerts, and spend analytics.

---

## 📸 Interactive API Documentation

![Spend Tracker API Swagger Documentation](docs/images/swagger_ui.png)

Explore interactive API schemas, request validation, and live execution at `/docs` (Swagger UI) or `/redoc` (ReDoc).

---

## ✨ Features

- 🇰🇪 **Kenyan FinTech Native**: Seamless ingestion and normalization of M-Pesa C2B and SMS transaction payloads, SACCO investments, utilities (KPLC, Nairobi Water), and grocery chains (Naivas, Carrefour, Quickmart).
- 🔐 **Rotating JWT Authentication**: Strict RFC 6749 refresh token rotation. Issues 15-minute access tokens and 7-day single-use refresh tokens stored as SHA-256 hashes in PostgreSQL to thwart replay attacks.
- ⚡ **Extensible Categorisation Engine**: Protocol-driven architecture (`CategoriserProtocol`) paired with a high-throughput `RuleBasedCategoriser` that classifies transactions by merchant name, paybill number, and bill reference. Designed for seamless drop-in of LLM backends without route alterations.
- 🚨 **Idempotent Budget Alerts**: Monitors month-to-date category totals against limits. Emits outbound webhook notifications deduplicated per period via atomic Redis locks.
- 📊 **Spending Analytics & Reports**: Generates category distributions, top 10 merchant expenses, month-over-month deltas, and daily expenditure time-series.
- 🛡️ **Role-Based Access Control (RBAC)**: Enforces complete multi-tenant tenant isolation for users and accounts, with administrative inspection routes (`GET /admin/users`).
- 📈 **Production Observability**: Structured JSON logging (`structlog`), automated `X-Request-ID` request tracking middleware, rate limiting (`slowapi`), and database health probes (`GET /health`).
- 🧪 **Zero-Dependency Test Suite**: 100% self-contained testing utilizing in-memory `aiosqlite` and `fakeredis` achieving **92% statement coverage**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    Client["Client / M-Pesa Webhook"] -->|HTTPS + JSON| API["FastAPI Application"]
    API --> Middleware["Request ID & SlowAPI Middleware"]
    Middleware --> Auth["JWT Security & RBAC Guard"]
    
    subgraph Services["Core Domain Services"]
        Auth --> TxnService["Transaction Service"]
        TxnService --> CatEngine["CategoriserProtocol\n(Rule-Based / LLM Fallback)"]
        TxnService --> AlertEngine["Budget Alert Engine"]
        Auth --> ReportEngine["Report Analytics Service"]
    end
    
    subgraph Storage["Persistence & Caching"]
        TxnService -->|Async SQLAlchemy 2.0| Postgres[("PostgreSQL 16\n(Transactions, Ledgers, Budgets)")]
        AlertEngine -->|Idempotency Locks| Redis[("Redis 7\n(Alert Flags & Rate Limits)")]
        ReportEngine --> Postgres
    end
    
    AlertEngine -->|HTTP POST Webhook| External["Budget Webhook Receiver"]
```

---

## 🚀 Quickstart

### Option 1: Docker Compose (Recommended)

Start the API, PostgreSQL 16, and Redis 7 in detached mode:

```bash
# 1. Clone & copy environment settings
git clone https://github.com/crnjihia/spend-tracker-api.git
cd spend-tracker-api
cp .env.example .env

# 2. Build and launch services
docker compose up -d --build

# 3. Apply database migrations and seed system categories
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```

Open your browser to:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option 2: Local Development (Poetry or Virtualenv)

```bash
# 1. Install dependencies
poetry install

# 2. Apply migrations & seed initial categories
poetry run alembic upgrade head
poetry run python -m app.db.seed

# 3. Launch local development server
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📡 API Reference

All functional routes are accessible both at root and prefixed under `/api/v1`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | Public | System liveness probe and database ping |
| `POST` | `/api/v1/auth/register` | Public | Register new user with email & password |
| `POST` | `/api/v1/auth/login` | Public | Authenticate; returns `{access_token, refresh_token}` |
| `POST` | `/api/v1/auth/refresh` | Public | Rotate refresh token (revokes previous token) |
| `POST` | `/api/v1/auth/logout` | Public | Revoke active refresh token |
| `POST` | `/api/v1/transactions/mpesa` | User | Ingest & auto-categorise M-Pesa C2B / SMS payload |
| `GET` | `/api/v1/transactions` | User | List transactions for the authenticated user |
| `GET` | `/api/v1/transactions/{id}` | User | Retrieve specific transaction details |
| `POST` | `/api/v1/budgets` | User | Create monthly category budget limit |
| `GET` | `/api/v1/budgets` | User | List user's category budgets |
| `GET` | `/api/v1/budgets/{id}` | User | Retrieve specific budget details |
| `PATCH` | `/api/v1/budgets/{id}` | User | Update budget limit or webhook URL |
| `DELETE` | `/api/v1/budgets/{id}` | User | Remove budget |
| `GET` | `/api/v1/reports/summary` | User | Generate spending summary, merchant rank & daily series |
| `GET` | `/api/v1/admin/users` | Admin | Administrative listing of registered users |

---

## 💡 Usage Example: M-Pesa Ingestion

### 1. Ingest Transaction
```bash
curl -X POST http://127.0.0.1:8000/api/v1/transactions/mpesa \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "TransID": "QGH7XYZ123",
    "TransAmount": "1500.00",
    "BusinessShortCode": "247247",
    "BillRefNumber": "Naivas Supermarket",
    "MSISDN": "254712345678",
    "TransTime": "20261008143022",
    "FirstName": "John"
  }'
```

### 2. Auto-Categorised Response (`201 Created`)
```json
{
  "id": "e6c2eeda-016a-46c4-b58a-6e8ad3279d88",
  "account_id": "43fea7b4-3407-4de9-975c-82a0e9975bbc",
  "amount": 1500.0,
  "category_id": "90e204cb-a88f-4a3c-ac3d-3a230e7f5d32",
  "merchant": "Naivas Supermarket",
  "ref_code": "QGH7XYZ123",
  "occurred_at": "2026-10-08T14:30:22",
  "direction": "out",
  "needs_review": false,
  "created_at": "2026-10-08T14:30:23.120Z",
  "raw_payload": { ... }
}
```

> **Idempotency Guarantee**: If the exact same `TransID` is ingested a second time, the API intercepts it before any balance or state changes and responds with `409 Conflict: {"detail": "Duplicate transaction"}`.

### 3. Budget Exceeded Webhook Payload
When a recorded expenditure pushes the month-to-date category total beyond its limit, the configured `alert_webhook_url` receives:

```json
{
  "event": "budget_exceeded",
  "category": "groceries",
  "limit": 10000.0,
  "spent": 11500.0,
  "period": "2026-10"
}
```

---

## 🔧 Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/matumizi` | Asynchronous SQLAlchemy connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis client URL for rate-limiting and webhook locks |
| `JWT_SECRET_KEY` | *(dev default)* | Cryptographic signing secret for JWT access tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Expiration window for access tokens |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Expiration window for refresh tokens |
| `RATE_LIMIT` | `100/minute` | Default SlowAPI rate limit |
| `LOG_LEVEL` | `INFO` | Logging threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DEBUG` | `False` | SQL echo and verbose exception reporting |
| `PROJECT_NAME` | `Spend Tracker API` | API metadata title |

---

## 🧪 Testing & Quality Assurance

The automated test suite uses in-memory `aiosqlite` and `fakeredis`, requiring **no running PostgreSQL or Redis instance**:

```bash
# Run pytest with missing line coverage reporting
pytest -v --cov=app --cov-report=term-missing

# Run code style & formatting checks
ruff check .
ruff format --check .

# Run static type validation
mypy .
```

### Coverage Report
```text
TOTAL: 1066 statements, 92% coverage
================ 18 passed in ~10s ================
```

---

## 📐 Design Decisions

1. **Single-Use Refresh Token Rotation**:
   - Refresh tokens are cryptographically signed JWTs, but persisted in the database solely as **SHA-256 hashes**.
   - Upon calling `/api/v1/auth/refresh`, the presented token is verified, marked `revoked = True`, and replaced with a newly minted token pair in an atomic transaction.
   - Any replayed presentation of an invalidated refresh token triggers an immediate `401 Unauthorized`.

2. **Idempotency & Ledger Integrity**:
   - M-Pesa `TransID` is enforced as unique on the database level via `Transaction.ref_code`.
   - Budget alert dispatch employs Redis key `budget_alert:{user_id}:{category_id}:{YYYY-MM}`. The flag is only persisted upon successful `200` response from the recipient webhook, guaranteeing automatic retry on transient downstream failures.

3. **Decoupled Categorisation Protocol**:
   - `CategoriserProtocol` specifies `async def categorise(transaction: Transaction) -> Optional[Category]`.
   - The default `RuleBasedCategoriser` scans merchant metadata, bill references, and short codes. Unmatched or ambiguous results yield `None`, flagging the transaction with `needs_review = True`.
   - Drop-in ML or LLM classifiers can implement `CategoriserProtocol` with zero changes to ingest routes.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
