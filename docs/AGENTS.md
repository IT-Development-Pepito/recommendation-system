# Repository Agent Instructions

All human and AI contributors must follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/AGENT_DAILY_OPERATING_RULES.md`. The development workflow is authoritative whenever the documents differ or a rule is not repeated.

Read this document, `docs/SKILLS.md`, and `docs/SYSTEM_ARCHITECTURE.md` before planning or implementing changes. Do not expose credentials, production data, or personally identifiable transaction data in code, logs, notebooks, commits, or pull requests.

## Agent guideline

Agents are contributors, not autonomous release authorities.

### Required behavior

1. Start from the tracked issue and restate scope, acceptance criteria, constraints, and affected data systems.
2. Inspect existing code and documentation before proposing changes. Preserve unrelated work.
3. Prefer small, reviewable changes with tests and explicit validation evidence.
4. Never invent credentials, access production systems without authorization, or expose secrets or sensitive transaction data.
5. Treat SQL Server as read-only and send application writes only to PostgreSQL.
6. Update the relevant documentation and `PROGRESS.md`; provide exact verification performed and remaining risks.
7. Escalate ambiguous requirements, schema changes, destructive actions, data-quality failures, security concerns, and release decisions to a human owner.

### Branch and release authority

Agents may work on a scoped branch and prepare a change for review. Humans approve merges into `staging` and `main`, production data access, schema migrations, credential changes, and incident actions unless explicit written delegation says otherwise.

## Harness rules

Use Python 3.14.6 and provision the locked environment before validation:

```powershell
uv sync --locked --group notebook --group dev --no-group spark
```

Run the required harness checks before requesting review:

```powershell
uv run python scripts/validate_repository.py
uv run python scripts/validate_notebooks.py
uv run ruff check scripts tests
uv run pytest --cov=scripts --cov-report=term-missing
```

Dependency changes must refresh `uv.lock` alongside `pyproject.toml`. Ordinary unit tests must remain database-free and must not require SQL Server, PostgreSQL, Spark, Java, or a live ODBC connection.
