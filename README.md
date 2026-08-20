# Recommendation System

This repository contains the foundation for Pepito's product recommendation system. It derives product associations from retail transactions and will evolve into a production pipeline that extracts sales data from the SQL Server data warehouse, transforms it, and stores recommendation-ready data and results in PostgreSQL.

## Environments

Copy the appropriate example file to a local, untracked `.env` file and fill in credentials outside version control:

- `.env.development.example` for local development
- `.env.staging.example` for staging
- `.env.production.example` for production

The SQL Server warehouse is a read-only source. PostgreSQL is the application database and destination for transformed data, model outputs, and operational metadata.

## Development setup

The supported interpreter is Python 3.14.6. Install [uv](https://docs.astral.sh/uv/), then create the locked core, notebook, and development environment without the optional Spark group:

```powershell
uv sync --locked --group notebook --group dev --no-group spark
```

Run the same checks used by the authoritative Windows CI job:

```powershell
uv run python scripts/validate_repository.py
uv run python scripts/validate_notebooks.py
uv run ruff check scripts tests
uv run pytest --cov=scripts --cov-report=term-missing
```

PySpark is isolated in the `spark` dependency group and is not required for the Phase 1 harness. These checks do not connect to SQL Server or PostgreSQL.

## Branches

- `main` — production-ready releases
- `staging` — release-candidate validation
- `develop` — integrated development work

Read [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) and [docs/AGENTS.md](docs/AGENTS.md) before changing the system. Architecture and agent operating rules are documented in `docs/`.

## Repository layout

- `notebooks/` — exploratory Jupyter notebooks
- `datasets/` — local reference and exploratory CSV datasets
- `executable/` — batch launchers
- `logs/` — local runtime logs (ignored by Git)
