# API Versioning & Release Strategy

This document outlines the API versioning strategy, endpoint lifecycle, breaking change policies, and OpenAPI release distributions for **Spend Tracker API**.

---

## 📌 Current API Versions

| API Version | Route Prefix | Status | OpenAPI Spec | Supported Since | End of Life (EOL) |
|---|---|---|---|---|---|
| **v1** (Current) | `/api/v1` | **Active / Stable** | [openapi.json](openapi.json) / [openapi.yaml](openapi.yaml) | 2026-10-15 | TBD |
| **Root Alias** | `/` | **Convenience Alias** | Linked to `/api/v1` | 2026-10-15 | Maintained |

---

## 🏛️ Versioning Rules & Semantic Principles

Spend Tracker API follows **Semantic Versioning (SemVer 2.0.0)** for both code releases and API specifications:
- **MAJOR (`v1.0.0` -> `v2.0.0`)**: Incompatible API schema changes, removal of existing endpoints or fields, alteration of validation rules, or fundamental authentication changes.
- **MINOR (`v1.0.0` -> `v1.1.0`)**: Backward-compatible new endpoints, optional query parameters, or non-breaking field additions to response models.
- **PATCH (`v1.0.0` -> `v1.0.1`)**: Backward-compatible internal bug fixes, performance improvements, rate limiting adjustments, and documentation updates.

### URI Versioning Convention
All production client integrations MUST target the explicit version prefix `/api/v1/...` to ensure resilience against future major version increments.

```
https://api.spendtracker.ke/api/v1/transactions/mpesa
https://api.spendtracker.ke/api/v1/budgets
https://api.spendtracker.ke/api/v1/reports/summary
```

---

## 📋 v1 API Endpoint Catalog

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/register`: Register new user account.
- `POST /api/v1/auth/login`: Authenticate with email/password; returns 15-minute access token and 7-day refresh token.
- `POST /api/v1/auth/refresh`: Single-use RFC 6749 refresh token rotation.
- `POST /api/v1/auth/logout`: Revoke active refresh token.

### Transactions (`/api/v1/transactions`)
- `POST /api/v1/transactions/mpesa`: Ingest and auto-categorise M-Pesa C2B Paybill/Till confirmation payload.
- `GET /api/v1/transactions`: Retrieve paginated transaction history for authenticated user.
- `GET /api/v1/transactions/{id}`: Retrieve single transaction detail.

### Budgets (`/api/v1/budgets`)
- `POST /api/v1/budgets`: Create monthly category spending budget limit (`YYYY-MM`).
- `GET /api/v1/budgets`: List user's active budgets.
- `GET /api/v1/budgets/{id}`: Inspect specific budget details.
- `PATCH /api/v1/budgets/{id}`: Update budget limit or webhook alert URL.
- `DELETE /api/v1/budgets/{id}`: Remove budget.

### Reports & Analytics (`/api/v1/reports`)
- `GET /api/v1/reports/summary`: Category distributions, top 10 merchants, daily expenditure time-series, and month-over-month spending deltas.

### Administration (`/api/v1/admin`)
- `GET /api/v1/admin/users`: Administrative listing of registered tenant accounts (requires `role: admin`).

---

## 📦 Automated Release Assets

Every tagged release (`vX.Y.Z`) on GitHub automatically compiles and attaches:
1. **`openapi.json`**: Official OpenAPI 3.1 specification.
2. **`openapi.yaml`**: YAML representation of the OpenAPI 3.1 specification.
3. **`spend-tracker-api-openapi-vX.Y.Z.zip`**: Complete distribution bundle with specs, licenses, and documentation.
4. **`checksums-vX.Y.Z.txt`**: Cryptographic SHA-256 verification hashes.
5. **GHCR Docker Package**: Published to `ghcr.io/crnjihia/spend-tracker-api:vX.Y.Z`.
