# Layered Harness Foundation Brainstorm

**Date:** 2026-08-19  
**Issue:** #4

## Problem and intended outcome

Repository rules are mostly prose and the Python environment is not reproducible. Establish a database-free harness that gives humans and agents fast, consistent feedback without changing recommendation behavior.

## Decisions

- Use uv with Python 3.14.6, compatible ranges in `pyproject.toml`, and exact versions in `uv.lock`.
- Make Windows CI blocking and Linux portability CI advisory.
- Enforce repository structure, notebook hygiene, scoped Ruff, and harness tests.
- Keep Spark, PostgreSQL integration, and broad legacy cleanup outside Phase 1.

## Alternatives considered

- A minimal uv-and-CI setup was rejected because too many repository rules would remain unenforced.
- Full application modernization was deferred because it would mix harness work with behavioral and database changes.

## Assumptions and constraints

- SQL Server remains read-only and PostgreSQL remains the future application destination.
- No live database, Spark, Java, or ODBC connection is required.
- The current GitHub plan does not support the desired protected-branch controls.

## Open questions

There are no open questions for Phase 1. Follow-up issues will decide the Spark harness, PostgreSQL integration environment, legacy-code migration, comprehensive secret scanning, Linux blocking status, and branch protection.

## Acceptance criteria and issue breakdown

Issue #4 owns the uv environment, validators, tests, CI, and guidance. Completion requires a reproducible fresh setup, passing Windows checks, visible Linux results, clean notebooks, unchanged recommendation behavior, synchronized documentation, and linked issues for every deferred item.
