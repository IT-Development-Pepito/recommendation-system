# Recommendation System

This repository contains the foundation for Pepito's product recommendation system. It derives product associations from retail transactions and will evolve into a production pipeline that extracts sales data from the SQL Server data warehouse, transforms it, and stores recommendation-ready data and results in PostgreSQL.

## Environments

Copy the appropriate example file to a local, untracked `.env` file and fill in credentials outside version control:

- `.env.development.example` for local development
- `env.staging.example` for staging
- `.env.production.example` for production

The SQL Server warehouse is a read-only source. PostgreSQL is the application database and destination for transformed data, model outputs, and operational metadata.

## Branches

- `main` — production-ready releases
- `staging` — release-candidate validation
- `develop` — integrated development work

Read [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) before changing the system. Architecture and agent operating rules are documented in `docs/`.
