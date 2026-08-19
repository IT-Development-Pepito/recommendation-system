# Repository Guidance

This file is the entry map for humans and AI agents. The authoritative development process is `docs/DEVELOPMENT_WORKFLOW.md`; when guidance differs or is not repeated elsewhere, that workflow wins.

Before changing the repository, read:

1. `docs/DEVELOPMENT_WORKFLOW.md`
2. `docs/AGENT_DAILY_OPERATING_RULES.md`
3. `docs/AGENTS.md`
4. `docs/SYSTEM_ARCHITECTURE.md`
5. `docs/SKILLS.md`
6. the relevant record under `docs/brainstorms/` or `docs/superpowers/specs/`

Use Python 3.14.6 and uv. Install the normal development environment with `uv sync --locked --group notebook --group dev --no-group spark`. Run repository validation, notebook validation, scoped Ruff checks, and pytest before requesting review.

Dependency changes must update both `pyproject.toml` and `uv.lock`. Ordinary unit tests must not require SQL Server, PostgreSQL, Spark, Java, or an ODBC connection. Treat SQL Server as read-only and direct future application writes only to PostgreSQL.

Keep changes issue-scoped. Record material blockers, drawbacks, risks, dependencies, and intentionally excluded work as linked follow-up issues under the required type and P0/P1/P2 conventions.
