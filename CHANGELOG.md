# Changelog

All notable changes to the **Spend Tracker API** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-17

Initial production release of **Spend Tracker API**, a personal finance and M-Pesa transaction tracking REST API built for Kenyan and East African spending habits.

### ✨ Added
- **M-Pesa Ingestion Engine**:
  - Real-time ingestion endpoint (`POST /api/v1/transactions/mpesa`) supporting C2B Paybill, Till Numbers, and SMS confirmation payloads.
  - Idempotent transaction processing with duplicate detection based on unique `TransID` (`409 Conflict`).
  - Automatic balance deductions on linked user accounts.
- **Extensible Categorisation System**:
  - `CategoriserProtocol` architecture supporting swappable classification backends (rules, ML, LLMs).
  - High-throughput `RuleBasedCategoriser` matching keywords across merchants, reference codes, and bill reference numbers.
  - Default seeds for Kenyan spend categories: Groceries (Naivas, Carrefour, Quickmart), Utilities (KPLC, Nairobi Water), SACCOs, Transport (Uber, Bolt, fuel stations), and Entertainment.
  - `needs_review` flag automatically assigned to transactions with ambiguous or missing category matches.
- **Idempotent Budget Alert Engine**:
  - Monthly category budget limits (`POST /api/v1/budgets`) with period tracking (`YYYY-MM`).
  - Automated threshold monitoring on new outflow transactions.
  - Webhook notifications dispatched once per period utilizing atomic Redis locks.
- **Rotating JWT Authentication**:
  - 15-minute access tokens and 7-day single-use refresh tokens.
  - Refresh tokens stored as SHA-256 hashes in PostgreSQL to thwart replay attacks.
  - Instant token revocation on rotation and logout.
- **Spend Analytics & Reports**:
  - Comprehensive analytical summary endpoint (`GET /api/v1/reports/summary`).
  - Category spending breakdown, top 10 merchants by spend, daily spending time-series, and month-over-month expenditure deltas.
- **Multi-Tenant RBAC & Admin Auditing**:
  - Role-based access control distinguishing `USER` and `ADMIN` roles.
  - User and account isolation across all endpoints.
  - Administrative user inspection route (`GET /api/v1/admin/users`).
- **Production Observability & Reliability**:
  - Structured JSON logging via `structlog` with automated `X-Request-ID` propagation.
  - Rate limiting via `slowapi` (`100/minute`).
  - Health check endpoint (`GET /health`) with live database reachability probe.
- **CI/CD & Cloud Infrastructure**:
  - GitHub Actions CI workflow for linting, type-checking, and pytest test execution.
  - GitHub Container Registry (GHCR) automated package workflow (`ghcr.io/crnjihia/spend-tracker-api`).
  - Automated GitHub Pages documentation deployment hosting interactive Swagger UI, ReDoc, and 92% statement coverage reports.
  - Automated OpenAPI 3.1 specification release workflow attaching versioned JSON, YAML, and zip archives to GitHub Releases.

### 🧪 Test Coverage
- Comprehensive test harness using `pytest-asyncio`, `aiosqlite`, and `fakeredis`.
- 18 unit and integration tests passing with 92% statement coverage.
