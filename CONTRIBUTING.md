# Contributing to Spend Tracker API

Thank you for your interest in contributing to **Spend Tracker API**! I welcome contributions from everyone, especially developers working with East African and Kenyan fintech integrations.

---

## 🛠 Development Workflow

### 1. Prerequisites
- Python 3.11+
- Git
- Docker & Docker Compose (optional, for running PostgreSQL 16 & Redis 7 locally)

### 2. Fork and Clone
```bash
git clone https://github.com/crnjihia/spend-tracker-api.git
cd spend-tracker-api
```

### 3. Set Up Local Environment
```bash
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
cp .env.example .env
```

### 4. Database Setup
```bash
# Run migrations
alembic upgrade head

# Seed default Kenyan categories
python -m app.db.seed
```

---

## 🧪 Testing & Code Quality Guidelines

Before submitting a Pull Request, ensure all checks pass:

1. **Linting**:
   ```bash
   ruff check .
   ```
2. **Type Checking**:
   ```bash
   mypy app
   ```
3. **Tests & Coverage**:
   ```bash
   pytest --cov=app --cov-report=term-missing
   ```
   *Coverage must remain **≥85%**.*

---

## 📝 Commit Conventions

I follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new feature (e.g., new endpoint or payment provider)
- `fix:` A bug fix
- `docs:` Documentation updates
- `test:` Adding or updating tests
- `refactor:` Code refactoring without changing functionality
- `ci:` CI/CD pipeline or configuration changes

---

## 📬 Submitting a Pull Request

1. Create a descriptive branch: `git checkout -b feature/my-feature`
2. Commit your changes with conventional commit messages
3. Push to your fork: `git push origin feature/my-feature`
4. Open a Pull Request against `main`
5. Ensure all GitHub Actions CI checks pass!
