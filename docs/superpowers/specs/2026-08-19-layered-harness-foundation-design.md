# Layered Harness Foundation Design

**Status:** Approved in design review<br>
**Date:** 2026-08-19<br>
**Issue:** [#4 — `[infrastructure][P1] Establish layered harness foundation`](https://github.com/IT-Development-Pepito/recommendation-system/issues/4)

## Context

The repository documents its development and issue lifecycle well, but most rules are not mechanically enforced. It has no authoritative dependency manifest, reproducible lockfile, automated test suite, or continuous-integration workflow. The existing notebook validator can detect notebook hygiene regressions, but nothing requires contributors to run it before changes reach `develop`.

This phase establishes a dependable harness for humans and agents without changing the recommendation algorithms, data contracts, or database behavior. A live PostgreSQL instance is not required because this phase validates only repository structure and code that can run without external services.

## Goals

- Reproduce the supported Python environment with `uv` and a committed lockfile.
- Make one short root document the entry point to detailed repository guidance.
- Run the same explicit validation commands locally and in CI.
- Make Windows the authoritative CI environment while exposing Linux portability problems.
- Test harness behavior without SQL Server, PostgreSQL, Spark, or ODBC connections.
- Record deliberately deferred work as linked, classified GitHub issues.

## Non-goals

- Refactoring `apriori.py`, `apriori_store.py`, or recommendation logic.
- Creating the PostgreSQL database or implementing ETL integration.
- Executing Spark jobs in CI.
- Applying Ruff to all legacy Python and notebook code.
- Solving GitHub branch-protection limitations in the current repository plan.

## Runtime and dependency model

The repository will pin the developer and CI interpreter in `.python-version` to Python 3.14.6. `pyproject.toml` will declare support for Python `>=3.14,<3.15`, allowing compatible 3.14 patch releases while `uv` continues to provision the approved patch version by default.

`pyproject.toml` is the human-maintained dependency policy. The current repository will be configured as a non-packaged application, so `uv` manages its environment without expecting a distributable Python package. `uv.lock` is the exact, committed resolution used by local development and CI. A dependency change is incomplete unless both files are updated and validation passes with `uv sync --locked`.

Dependencies are separated by purpose:

- **Core project dependencies:** Pandas, NumPy, SQLAlchemy, PyODBC, mlxtend, python-dotenv, and the temporarily retained `fpgrowth-py`.
- **Notebook group:** ipykernel, Matplotlib, and scikit-learn.
- **Spark group:** PySpark. It remains separate because it is large and also depends on a suitable Java runtime for execution.
- **Development group:** pytest, pytest-cov, and Ruff.

Compatible release ranges will be used for actively maintained packages. `fpgrowth-py` will be pinned to version 1.0.0 and covered by future algorithm regression tests because its maintenance and Python 3.14 certification are weaker than the rest of the stack. The deprecated `dotenv` wrapper and currently unused `schedule` package will not be declared.

## Guidance structure

A concise root `AGENTS.md` will become the repository entry map. It will identify the authoritative workflow and point to:

- `docs/DEVELOPMENT_WORKFLOW.md`
- `docs/AGENT_DAILY_OPERATING_RULES.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/PROGRESS.md`
- `docs/SKILLS.md`
- relevant brainstorms and design specifications

Detailed rules remain in `docs/`; the root file will not duplicate them. It will state the supported `uv` setup and validation commands, the requirement to update the lockfile with dependency changes, the prohibition on live database requirements in ordinary unit tests, and the need to record material deferred work as linked issues.

## Validation components

### Repository validator

A small Python utility under `scripts/` will validate repository invariants and return a nonzero exit code on failure. It will:

- verify required guidance, environment-example, and project-configuration files exist;
- reject tracked environment files other than the approved `*.example` templates;
- reject obvious secret material in tracked text, limited to private-key block markers and non-placeholder literal assignments to names such as `password`, `secret`, `token`, and `api_key`; and
- report each violation with the affected path and a concise remediation message.

The validator will avoid network access and external services. Approved environment examples containing clearly marked placeholder values will not fail the credential check. Its behavior will be covered by focused pytest tests using temporary directory fixtures. This narrow guard is not a replacement for a comprehensive secret-scanning service; expanding secret detection will be recorded as deferred security work if implementation confirms it is warranted.

### Notebook validator

The existing `scripts/validate_notebooks.py` remains the notebook hygiene boundary. All tracked notebooks must be structurally valid and have cleared outputs and execution counts. The validator may be minimally refactored to make its behavior directly testable, but notebook computations and algorithms will not be changed.

### Static analysis

Ruff will initially cover new harness utilities and tests only. Existing production scripts and notebook cells remain outside its Phase 1 scope. Ruff configuration will be centralized in `pyproject.toml`, and exclusions will be explicit so that the boundary cannot be mistaken for full-repository compliance.

### Unit tests and coverage

pytest will test repository validation and notebook validation behavior, including successful input and representative failure cases. Coverage will be reported for tested harness modules. Phase 1 will report coverage rather than impose a broad application threshold because the legacy application is not yet structured for unit testing.

Tests must not open database connections, execute Spark, require Java, or depend on machine-specific paths.

## Continuous integration

One GitHub Actions workflow will run for pull requests targeting `develop`, `staging`, or `main`, and for pushes to `develop`.

### Authoritative Windows job

The Windows job is blocking and will:

1. check out the repository;
2. install `uv` and provision Python 3.14.6;
3. run `uv sync --locked` with the notebook and development groups, excluding Spark;
4. run the repository validator and secret check;
5. run the notebook validator;
6. run Ruff over harness utilities and tests; and
7. run pytest with terminal coverage output.

This job represents the current supported development and execution platform. No database credentials will be configured.

### Advisory Linux job

The Linux job will be marked non-blocking initially. It will provision the locked core and development environment, then run repository checks, scoped Ruff checks, and database-free harness tests. It will not install notebook or Spark groups unless a test demonstrably requires them.

Keeping this job advisory exposes portability problems without preventing Phase 1 delivery for Windows-specific issues such as ODBC packaging. A future issue may promote it to blocking after the portability baseline is stable.

## Developer and agent flow

The expected flow is:

`checkout → uv sync --locked → repository checks → notebook validation → Ruff → pytest with coverage`

CI will call the same underlying commands documented for local use. Validation utilities will print actionable failures and terminate nonzero; they must not silently skip missing inputs. Successful commands should remain concise.

Dependency updates will use `uv` to change `pyproject.toml` and refresh `uv.lock`, followed by the full local validation sequence. Automated dependency upgrades, when introduced, must arrive through reviewed pull requests rather than mutating the lockfile on protected branches.

## Documentation and issue lifecycle

The implementation will update `docs/SYSTEM_ARCHITECTURE.md` with the development-harness and CI flow, and will add an entry to `docs/PROGRESS.md`. Any commands added by the harness will also be documented in the root `README.md` and agent guidance.

The following deferred items will become issues linked to #4, with the repository's required type, priority, component, environment, and status labels:

- bring legacy Python scripts under Ruff and unit-testable boundaries;
- add isolated Spark installation and execution validation;
- add an ephemeral PostgreSQL integration-test environment;
- enforce protected-branch and required-check policies when repository capabilities allow it; and
- decide whether Linux CI is stable enough to become blocking.

## Failure handling and observability

Each validation layer is independent and identifies its failing command in GitHub Actions. Repository and notebook validators list affected paths. pytest emits failure details and a coverage summary. Dependency synchronization uses `--locked`, so lockfile drift fails instead of silently resolving a different environment.

CI logs are the Phase 1 operational record; no external monitoring service is introduced. If the harness produces excessive false positives, the responsible check may be reverted independently without changing application behavior.

## Rollout and rollback

The change will be delivered from the issue branch through a pull request to `develop`. CI is introduced on the pull request so its behavior is visible before merge. Existing code paths remain untouched except for clearing notebook execution artifacts if required by the already-approved validator.

Rollback consists of reverting the harness pull request. Because Phase 1 introduces development configuration, tests, documentation, and CI only, rollback requires no database migration or data repair.

## Acceptance criteria

- A fresh checkout provisions the approved Python 3.14.6 environment with `uv`.
- `uv sync --locked` reproduces the committed dependency resolution.
- The authoritative Windows job blocks on repository checks, notebook validation, scoped Ruff, and database-free tests.
- Linux portability results are visible but do not block Phase 1 delivery.
- All tracked notebooks pass structural and output-cleanliness checks.
- Harness tests pass without SQL Server, PostgreSQL, Spark, Java, or ODBC connections.
- Existing recommendation behavior and data contracts are unchanged.
- `dotenv` and `schedule` are absent from declared dependencies.
- Root guidance and detailed documentation accurately describe the harness.
- Material deferred work is recorded as linked GitHub issues.
