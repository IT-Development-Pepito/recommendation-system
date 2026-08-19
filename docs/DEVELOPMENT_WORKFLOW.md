# Development Workflow

This is the authoritative workflow for people and AI agents contributing to the recommendation system.

## 1. Intake and planning

1. Create or select a tracked issue with a problem statement, owner, priority, acceptance criteria, risk, and affected environment.
2. Classify the work as data, model/algorithm, ETL, application, infrastructure, security, defect, or documentation.
3. Inspect the current architecture, contracts, data classification, and relevant progress entries before proposing a change.
4. For material changes, write a design that states interfaces, rollback plan, observability, and validation. Obtain review before implementation.

## 2. Data and AI/ML controls

- Treat SQL Server as a read-only source warehouse and PostgreSQL as the application-system destination. Never write back to the warehouse from this project.
- Use least-privilege credentials, parameterized queries, secret-managed environment variables, and encrypted connections where available.
- Do not commit raw production transactions, credentials, customer data, or notebook outputs containing sensitive data.
- Version extraction logic, transformation assumptions, feature definitions, algorithm parameters, schemas, and output contracts.
- Validate source freshness, row counts, duplicates, null rates, schema drift, and business invariants before publishing ETL output.
- Evaluate recommendation changes against defined offline metrics and business guardrails. Record data window, parameters, comparison baseline, and results before promotion.

## 3. Implementation

1. Branch from `develop` using a focused name such as `feat/etl-postgres-load` or `fix/duplicate-bills`.
2. Make the smallest safe change. Keep source extraction, transformations, mining, persistence, and orchestration separately testable.
3. Add or update automated tests before relying on implementation behavior. Include negative and data-quality cases for ETL/ML changes.
4. Update architecture, runbook, environment examples, and `PROGRESS.md` when the public behavior, operations, or data contract changes.

## 4. Validation and review

Before review, run applicable formatting, static analysis, unit tests, integration tests, and a safe data-quality check. Reviewers verify acceptance criteria, data safety, security, reproducibility, migration safety, observability, and rollback readiness.

Changes flow as `develop` → `staging` → `main`. Staging validates release candidates with representative non-production data and operational checks. Only reviewed, validated releases reach `main`.

## 5. Release and operations

- Use versioned, reversible database migrations; back up or snapshot before destructive changes.
- Monitor ETL completion, source freshness, row counts, error rates, recommendation volume, distribution drift, and database write failures.
- Stop publication and roll back to the last known-good release when validation or guardrails fail.
- Log the release, validation evidence, incidents, and follow-up actions in `PROGRESS.md` and the associated issue.

## Definition of done

An issue is done only when acceptance criteria pass, validation evidence is recorded, documentation is updated, the change is reviewed, and the issue lifecycle is closed under `docs/AGENT_DAILY_OPERATING_RULES.md`.
