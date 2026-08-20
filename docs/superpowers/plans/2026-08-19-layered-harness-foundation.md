# Layered Harness Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, database-free development harness with `uv`, tested repository and notebook checks, authoritative Windows CI, and advisory Linux portability checks.

**Architecture:** Keep the existing recommendation code unchanged and place the harness around it. `pyproject.toml` and `uv.lock` define the environment, focused Python validators enforce repository invariants, pytest verifies validator behavior, and one GitHub Actions workflow runs the same commands used locally.

**Tech Stack:** Python 3.14.6, uv, pytest, pytest-cov, Ruff, GitHub Actions, PowerShell-compatible commands

**Spec:** `docs/superpowers/specs/2026-08-19-layered-harness-foundation-design.md`

## Global Constraints

- Pin the default interpreter to Python 3.14.6 and declare support for Python `>=3.14,<3.15`.
- Use compatible dependency ranges in `pyproject.toml` and exact resolutions in committed `uv.lock`.
- Do not require SQL Server, PostgreSQL, Spark, Java, or a working ODBC connection for tests.
- Do not change recommendation algorithms, production data contracts, or database behavior.
- Do not apply Ruff to `apriori.py`, `apriori_store.py`, or notebook cell source in Phase 1.
- Windows CI is authoritative and blocking; Linux portability CI is advisory.
- Keep SQL Server read-only and reserve application writes for PostgreSQL.
- Record material deferred work as issues linked to issue #4.

## File map

- Create `.python-version`: pin uv's default interpreter.
- Create `pyproject.toml`: define project metadata, dependency groups, and tool configuration.
- Create `uv.lock`: record the exact dependency resolution.
- Create `AGENTS.md`: provide a short root entry map to authoritative guidance.
- Create `scripts/__init__.py`: make harness utilities importable by tests.
- Create `scripts/validate_repository.py`: validate required files, tracked environment files, and obvious secret material.
- Modify `scripts/validate_notebooks.py`: expose an injectable validation runner while preserving CLI behavior.
- Create `tests/test_validate_repository.py`: test repository-invariant failures and success.
- Create `tests/test_validate_notebooks.py`: test notebook hygiene and CLI-level results.
- Modify `notebooks/pyspark_apriori.ipynb`: clear the one stored execution count; do not alter cell source.
- Create `.github/workflows/ci.yml`: run authoritative Windows and advisory Linux checks.
- Modify `README.md`: document uv setup and validation commands.
- Modify `docs/AGENTS.md`: document dependency and validation rules for agents.
- Modify `docs/DEVELOPMENT_WORKFLOW.md`: make harness commands part of authoritative validation.
- Modify `docs/SYSTEM_ARCHITECTURE.md`: add the development-harness and CI flow.
- Modify `docs/PROGRESS.md`: record the completed harness work and validation evidence.
- Create `docs/brainstorms/2026-08-19-layered-harness-foundation.md`: retain approved issue-writing context.

---

### Task 1: Reproducible Python environment

**Files:**
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Python 3.14.6 compatibility decisions in the approved spec.
- Produces: `uv sync --locked` environments with core dependencies plus optional `notebook`, `spark`, and `dev` groups.

- [ ] **Step 1: Verify or install uv**

Run:

```powershell
uv --version
```

Expected now: FAIL because `uv` is not installed. Install the official Windows package, restart the shell if PATH does not refresh, and rerun the version check:

```powershell
winget install --id astral-sh.uv --exact
uv --version
```

Expected after installation: PASS and print the installed uv version.

- [ ] **Step 2: Add the Python pin and dependency policy**

Create `.python-version`:

```text
3.14.6
```

Create `pyproject.toml`:

```toml
[project]
name = "recommendation-system"
version = "0.1.0"
description = "Product-association recommendation pipeline"
readme = "README.md"
requires-python = ">=3.14,<3.15"
dependencies = [
    "fpgrowth-py==1.0.0",
    "mlxtend>=0.25,<0.26",
    "numpy>=2.5,<3",
    "pandas>=3.0,<4",
    "pyodbc>=5.3,<6",
    "python-dotenv>=1.2,<2",
    "sqlalchemy>=2.0,<3",
]

[dependency-groups]
dev = [
    "pytest>=9,<10",
    "pytest-cov>=7,<8",
    "ruff>=0.14,<1",
]
notebook = [
    "ipykernel>=7.3,<8",
    "matplotlib>=3.11,<4",
    "scikit-learn>=1.9,<2",
]
spark = [
    "pyspark>=4.2,<5",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
target-version = "py314"
line-length = 100
extend-exclude = [
    "apriori.py",
    "apriori_store.py",
    "notebooks",
]

[tool.coverage.run]
source = ["scripts"]

[tool.coverage.report]
show_missing = true
```

Add uv's cache directory to `.gitignore`:

```gitignore
.uv-cache/
```

- [ ] **Step 3: Resolve and lock the environment**

Run:

```powershell
uv lock
uv lock --check
```

Expected: both commands exit 0 and `uv.lock` records a Python 3.14-compatible resolution using the approved ranges.

- [ ] **Step 4: Synchronize without Spark and smoke-test imports**

Run:

```powershell
uv sync --locked --group notebook --group dev --no-group spark
uv run python -c "import dotenv, fpgrowth_py, matplotlib, mlxtend, numpy, pandas, pyodbc, sklearn, sqlalchemy; print('dependency imports passed')"
```

Expected: synchronization and imports pass without opening a database connection. Confirm that neither deprecated `dotenv` nor unused `schedule` is directly declared:

```powershell
uv tree
Select-String -Path pyproject.toml -Pattern '"dotenv|"schedule'
```

Expected: `dotenv` may appear only as the import supplied by `python-dotenv`; the `Select-String` command returns no direct declaration.

- [ ] **Step 5: Commit the environment contract**

```powershell
git add .python-version pyproject.toml uv.lock .gitignore
git commit -m "build: establish uv dependency environment"
```

---

### Task 2: Tested repository-invariant validator

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/validate_repository.py`
- Create: `tests/test_validate_repository.py`

**Interfaces:**
- Consumes: repository root and paths returned by `git ls-files -z`.
- Produces: `validate_repository(project_root: Path, tracked_paths: Sequence[Path]) -> list[str]` and `main() -> int`.

- [ ] **Step 1: Write failing repository-validation tests**

Create an empty `scripts/__init__.py`, then create `tests/test_validate_repository.py` with tests built around this fixture and assertions:

```python
from pathlib import Path

from scripts.validate_repository import REQUIRED_PATHS, validate_repository


def valid_repository(tmp_path: Path) -> list[Path]:
    tracked: list[Path] = []
    for relative in REQUIRED_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
        tracked.append(relative)
    return tracked


def test_reports_missing_required_file(tmp_path: Path) -> None:
    errors = validate_repository(tmp_path, [])
    assert "missing required path: AGENTS.md" in errors


def test_rejects_tracked_nonexample_environment_file(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    secret_env = Path(".env.production")
    (tmp_path / secret_env).write_text("PASSWORD=replace_me\n", encoding="utf-8")
    errors = validate_repository(tmp_path, [*tracked, secret_env])
    assert "tracked environment file is not an approved example: .env.production" in errors


def test_rejects_private_key_marker(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    key_file = Path("scripts/key.py")
    (tmp_path / key_file).parent.mkdir(parents=True, exist_ok=True)
    key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    (tmp_path / key_file).write_text(
        f'KEY = "{key_marker}"\n', encoding="utf-8"
    )
    errors = validate_repository(tmp_path, [*tracked, key_file])
    assert "obvious private-key material: scripts/key.py" in errors


def test_rejects_literal_credential_but_allows_example_value(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    unsafe = Path("scripts/settings.py")
    safe = Path(".env.development.example")
    (tmp_path / unsafe).parent.mkdir(parents=True, exist_ok=True)
    credential_name = "API_" + "TOKEN"
    (tmp_path / unsafe).write_text(
        f'{credential_name} = "live-value-123"\n', encoding="utf-8"
    )
    (tmp_path / safe).write_text("PASSWORD=replace_me\n", encoding="utf-8")
    errors = validate_repository(tmp_path, [*tracked, unsafe, safe])
    assert "possible literal credential: scripts/settings.py:1" in errors
    assert all(".env.development.example" not in error for error in errors)


def test_accepts_clean_repository(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    assert validate_repository(tmp_path, tracked) == []
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run:

```powershell
uv run pytest tests/test_validate_repository.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'scripts.validate_repository'`.

- [ ] **Step 3: Implement the minimal validator**

Create `scripts/validate_repository.py` with these required elements:

```python
"""Validate repository-level harness and secret-safety invariants."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path(".python-version"),
    Path(".env.development.example"),
    Path(".env.staging.example"),
    Path(".env.production.example"),
    Path("docs/DEVELOPMENT_WORKFLOW.md"),
    Path("docs/AGENT_DAILY_OPERATING_RULES.md"),
    Path("docs/SYSTEM_ARCHITECTURE.md"),
    Path("docs/PROGRESS.md"),
    Path("docs/SKILLS.md"),
    Path(".github/workflows/ci.yml"),
)
TEXT_SUFFIXES = {
    ".bat",
    ".example",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
}
PRIVATE_KEY_MARKER = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
CREDENTIAL_ASSIGNMENT = re.compile(
    r"^\s*(?:export\s+|set\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY)"
    r"[A-Z0-9_]*\s*[:=]\s*[\"']?([^\"'\s#]+)",
    re.IGNORECASE | re.MULTILINE,
)
PLACEHOLDER_MARKERS = ("replace_me", "example", "changeme", "placeholder", "dummy", "your_")


def is_environment_file(path: Path) -> bool:
    return path.name == ".env" or path.name.startswith(".env.")


def is_approved_example(path: Path) -> bool:
    return path.name.startswith(".env.") and path.name.endswith(".example")


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        not lowered
        or lowered.startswith(("$", "{{", "<"))
        or any(marker in lowered for marker in PLACEHOLDER_MARKERS)
    )


def validate_repository(project_root: Path, tracked_paths: Sequence[Path]) -> list[str]:
    errors = [
        f"missing required path: {relative.as_posix()}"
        for relative in REQUIRED_PATHS
        if not (project_root / relative).exists()
    ]
    for relative in tracked_paths:
        if is_environment_file(relative) and not is_approved_example(relative):
            errors.append(
                f"tracked environment file is not an approved example: {relative.as_posix()}"
            )
        path = project_root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PRIVATE_KEY_MARKER.search(text):
            errors.append(f"obvious private-key material: {relative.as_posix()}")
        for match in CREDENTIAL_ASSIGNMENT.finditer(text):
            if not is_placeholder(match.group(1)):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"possible literal credential: {relative.as_posix()}:{line}")
    return errors


def tracked_paths(project_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(value) for value in result.stdout.split("\0") if value]


def main() -> int:
    try:
        tracked = tracked_paths(PROJECT_ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL cannot enumerate tracked files: {exc}", file=sys.stderr)
        return 1
    errors = validate_repository(PROJECT_ROOT, tracked)
    for error in errors:
        print(f"FAIL {error}")
    if errors:
        print(f"Repository validation failed with {len(errors)} error(s).")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused tests and static analysis**

Run:

```powershell
uv run pytest tests/test_validate_repository.py -v
uv run ruff check scripts/__init__.py scripts/validate_repository.py tests/test_validate_repository.py
```

Expected: all five tests pass and Ruff reports no errors. Do not run the validator against the actual repository until the CI workflow and root `AGENTS.md` exist.

- [ ] **Step 5: Commit the repository validator**

```powershell
git add scripts/__init__.py scripts/validate_repository.py tests/test_validate_repository.py
git commit -m "test: enforce repository harness invariants"
```

---

### Task 3: Testable notebook validation and clean notebook state

**Files:**
- Modify: `scripts/validate_notebooks.py`
- Create: `tests/test_validate_notebooks.py`
- Modify: `notebooks/pyspark_apriori.ipynb:23`

**Interfaces:**
- Consumes: notebook JSON files in a supplied directory.
- Produces: existing `validate_notebook(path: Path) -> list[str]` plus `run_validation(notebook_dir: Path, project_root: Path) -> int`.

- [ ] **Step 1: Write failing runner and hygiene tests**

Create `tests/test_validate_notebooks.py`:

```python
import json
from pathlib import Path

from scripts.validate_notebooks import run_validation, validate_notebook


def notebook(execution_count: int | None = None) -> dict:
    return {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# Title"]},
            {"cell_type": "markdown", "metadata": {}, "source": ["## Purpose"]},
            {"cell_type": "markdown", "metadata": {}, "source": ["## Result"]},
            {
                "cell_type": "code",
                "execution_count": execution_count,
                "metadata": {},
                "outputs": [],
                "source": ["value = 1"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_validate_notebook_accepts_clean_notebook(tmp_path: Path) -> None:
    path = tmp_path / "clean.ipynb"
    write_notebook(path, notebook())
    assert validate_notebook(path) == []


def test_validate_notebook_rejects_execution_count(tmp_path: Path) -> None:
    path = tmp_path / "dirty.ipynb"
    write_notebook(path, notebook(execution_count=1))
    assert "code cell 3 has an execution count" in validate_notebook(path)


def test_run_validation_fails_when_directory_has_no_notebooks(
    tmp_path: Path, capsys
) -> None:
    assert run_validation(tmp_path, tmp_path) == 1
    assert "No notebooks found." in capsys.readouterr().err


def test_run_validation_reports_all_clean_notebooks(tmp_path: Path, capsys) -> None:
    path = tmp_path / "clean.ipynb"
    write_notebook(path, notebook())
    assert run_validation(tmp_path, tmp_path) == 0
    assert "Validated 1 notebooks; 0 failed." in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests and verify the missing-runner failure**

Run:

```powershell
uv run pytest tests/test_validate_notebooks.py -v
```

Expected: collection fails because `run_validation` does not yet exist.

- [ ] **Step 3: Extract the injectable runner**

Move the body of the existing `main()` into this function without changing validation rules:

```python
def run_validation(notebook_dir: Path, project_root: Path) -> int:
    notebook_paths = sorted(notebook_dir.glob("*.ipynb"))
    if not notebook_paths:
        print("No notebooks found.", file=sys.stderr)
        return 1

    failures = 0
    for path in notebook_paths:
        errors = validate_notebook(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(project_root)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path.relative_to(project_root)}")

    print(f"Validated {len(notebook_paths)} notebooks; {failures} failed.")
    return 1 if failures else 0


def main() -> int:
    return run_validation(NOTEBOOK_DIR, PROJECT_ROOT)
```

- [ ] **Step 4: Run tests, then expose the real regression**

Run:

```powershell
uv run pytest tests/test_validate_notebooks.py -v
uv run python scripts/validate_notebooks.py
```

Expected: the four unit tests pass; repository validation fails only for `notebooks/pyspark_apriori.ipynb` because code cell 1 has an execution count.

- [ ] **Step 5: Clear the stored execution count without changing source**

At line 23 of `notebooks/pyspark_apriori.ipynb`, make this mechanical JSON change:

```diff
-   "execution_count": 1,
+   "execution_count": null,
```

Run:

```powershell
uv run python scripts/validate_notebooks.py
uv run pytest tests/test_validate_notebooks.py -v
uv run ruff check scripts/validate_notebooks.py tests/test_validate_notebooks.py
```

Expected: five tracked notebooks pass with zero failures, four focused tests pass, and Ruff reports no errors.

- [ ] **Step 6: Commit notebook harness coverage**

```powershell
git add scripts/validate_notebooks.py tests/test_validate_notebooks.py notebooks/pyspark_apriori.ipynb
git commit -m "test: cover notebook hygiene validation"
```

---

### Task 4: Authoritative Windows and advisory Linux CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `uv.lock`, dependency groups, both validator CLIs, Ruff configuration, and pytest tests.
- Produces: blocking `windows-harness` and non-blocking `linux-portability` GitHub Actions jobs.

- [ ] **Step 1: Add the workflow with least-privilege permissions**

Create `.github/workflows/ci.yml`:

```yaml
name: Harness validation

on:
  pull_request:
    branches: [develop, staging, main]
  push:
    branches: [develop]

permissions:
  contents: read

jobs:
  windows-harness:
    name: Windows harness
    runs-on: windows-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v5
      - name: Install uv and Python
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1
        with:
          python-version: 3.14.6
          enable-cache: true
      - name: Synchronize locked environment
        run: uv sync --locked --group notebook --group dev --no-group spark
      - name: Validate repository
        run: uv run python scripts/validate_repository.py
      - name: Validate notebooks
        run: uv run python scripts/validate_notebooks.py
      - name: Run scoped Ruff checks
        run: uv run ruff check scripts tests
      - name: Run harness tests with coverage
        run: uv run pytest --cov=scripts --cov-report=term-missing

  linux-portability:
    name: Linux portability (advisory)
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - name: Check out repository
        uses: actions/checkout@v5
      - name: Install uv and Python
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1
        with:
          python-version: 3.14.6
          enable-cache: true
      - name: Synchronize locked core and development environment
        run: uv sync --locked --group dev --no-group notebook --no-group spark
      - name: Validate repository
        run: uv run python scripts/validate_repository.py
      - name: Run scoped Ruff checks
        run: uv run ruff check scripts tests
      - name: Run database-free harness tests
        run: uv run pytest --cov=scripts --cov-report=term-missing
```

The exact setup-uv commit is the official v10.0.1 release shown in the upstream README during planning. Do not add database credentials or `pull_request_target`.

- [ ] **Step 2: Verify workflow invariants locally**

Run:

```powershell
Select-String -Path .github/workflows/ci.yml -Pattern 'windows-latest','continue-on-error: true','uv sync --locked','python-version: 3.14.6'
uv run ruff check scripts tests
uv run pytest --cov=scripts --cov-report=term-missing
```

Expected: each workflow invariant is found, Ruff passes, and all harness tests pass.

- [ ] **Step 3: Commit CI**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: enforce layered harness checks"
```

---

### Task 5: Root guidance, architecture, and operating documentation

**Files:**
- Create: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/AGENTS.md`
- Modify: `docs/DEVELOPMENT_WORKFLOW.md`
- Modify: `docs/SYSTEM_ARCHITECTURE.md`
- Modify: `docs/PROGRESS.md`
- Create: `docs/brainstorms/2026-08-19-layered-harness-foundation.md`

**Interfaces:**
- Consumes: the implemented uv commands, validator paths, CI behavior, and issue #4.
- Produces: one root entry map and synchronized human/agent operating documentation.

- [ ] **Step 1: Create the concise root guidance map**

Create `AGENTS.md` with this content:

```markdown
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
```

- [ ] **Step 2: Document local setup in README**

Add a `Development setup` section after `Environments` containing these exact commands and explanations:

````markdown
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
````

- [ ] **Step 3: Record the approved brainstorm**

Create `docs/brainstorms/2026-08-19-layered-harness-foundation.md`:

```markdown
# Layered Harness Foundation Brainstorm

**Date:** 2026-08-19<br>
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
```

- [ ] **Step 4: Synchronize detailed agent, workflow, and architecture guidance**

Append a `Harness rules` section to `docs/AGENTS.md` that requires the same four commands, a refreshed `uv.lock` for dependency changes, and database-free ordinary unit tests.

Add this paragraph to `docs/DEVELOPMENT_WORKFLOW.md` under `## 4. Validation and review`:

```markdown
For Python changes, provision the locked environment with uv and run `scripts/validate_repository.py`, `scripts/validate_notebooks.py`, scoped Ruff checks over `scripts` and `tests`, and pytest with coverage. Dependency changes must update both `pyproject.toml` and `uv.lock`. Ordinary unit tests must remain independent of SQL Server, PostgreSQL, Spark, Java, and live ODBC connections.
```

Add this row to the technology table in `docs/SYSTEM_ARCHITECTURE.md`:

```markdown
| Development harness | uv lockfile, pytest, Ruff, repository/notebook validators, GitHub Actions |
```

Add this section after `Current repository components`:

````markdown
## Development harness flow

```text
Issue branch and local change
           |
           v
uv locked environment -> repository checks -> notebook checks -> scoped Ruff -> pytest
           |
           v
GitHub Actions: blocking Windows harness + advisory Linux portability
           |
           v
Reviewed pull request to develop -> staging -> main
```

Harness tests use repository fixtures and notebook JSON only. They do not connect to SQL Server or PostgreSQL and do not execute Spark.
````

- [ ] **Step 5: Record progress**

Add the newest entry to `docs/PROGRESS.md`:

```markdown
- 2026-08-19 — infrastructure / harness engineering — established the Python 3.14.6 uv environment, tested repository and notebook validators, blocking Windows CI, advisory Linux portability checks, and concise root agent guidance without changing recommendation behavior — issue #4 — uv lock check, dependency import smoke test, repository validation, five-notebook validation, scoped Ruff, and pytest with coverage passed locally.
```

- [ ] **Step 6: Run the actual repository checks**

Run:

```powershell
uv run python scripts/validate_repository.py
uv run python scripts/validate_notebooks.py
uv run ruff check scripts tests
uv run pytest --cov=scripts --cov-report=term-missing
```

Expected: repository validation passes, all five notebooks pass, Ruff passes, and all harness tests pass.

- [ ] **Step 7: Commit synchronized guidance**

```powershell
git add AGENTS.md README.md docs/AGENTS.md docs/DEVELOPMENT_WORKFLOW.md docs/SYSTEM_ARCHITECTURE.md docs/PROGRESS.md docs/brainstorms/2026-08-19-layered-harness-foundation.md
git commit -m "docs: document layered harness workflow"
```

---

### Task 6: Record deferred harness work as linked issues

**Files:**
- No repository files.

**Interfaces:**
- Consumes: GitHub issue #4 and the approved out-of-scope list.
- Produces: six backlog issues whose bodies reference `Parent: #4`.

- [ ] **Step 1: Create missing classification labels**

Run idempotent label commands:

```powershell
gh label create P2 --description "Lower-priority improvement" --color 0E8A16 --force
gh label create security --description "Security controls and risk reduction" --color B60205 --force
gh label create component:application --description "Recommendation application code" --color 5319E7 --force
gh label create component:spark --description "PySpark runtime and workloads" --color 5319E7 --force
gh label create component:database --description "Database integration and persistence" --color 5319E7 --force
gh label create component:governance --description "Repository governance and branch policy" --color 5319E7 --force
gh label create status:backlog --description "Accepted work awaiting implementation" --color C2E0C6 --force
```

Expected: every command exits 0 and labels are visible in `gh label list`.

- [ ] **Step 2: Create the six follow-up issues**

Create each issue with the listed title, labels, and body:

```powershell
gh issue create --title "[task][P1] Bring legacy recommendation scripts under automated quality checks" --label task --label P1 --label component:application --label status:backlog --body "Parent: #4`n`nRefactor apriori.py and apriori_store.py into testable boundaries, add behavior-preserving regression tests, and extend Ruff only after the baseline is proven."
gh issue create --title "[infrastructure][P2] Add isolated Spark validation harness" --label infrastructure --label P2 --label component:spark --label environment:ci --label status:backlog --body "Parent: #4`n`nValidate the optional PySpark dependency and a minimal Spark execution path in an isolated job with an explicit Java runtime."
gh issue create --title "[infrastructure][P1] Add ephemeral PostgreSQL integration test environment" --label infrastructure --label P1 --label component:database --label environment:ci --label status:backlog --body "Parent: #4`n`nProvision disposable PostgreSQL in CI and validate migrations and persistence without requiring a developer-owned database. SQL Server remains read-only."
gh issue create --title "[infrastructure][P1] Enforce protected branches and required checks" --label infrastructure --label P1 --label component:governance --label environment:ci --label status:backlog --body "Parent: #4`n`nConfigure develop, staging, and main protections and required checks when the repository plan supports those controls."
gh issue create --title "[infrastructure][P2] Promote Linux portability CI to blocking" --label infrastructure --label P2 --label component:harness --label environment:ci --label status:backlog --body "Parent: #4`n`nResolve portability failures and make the Linux harness job required after its baseline is stable."
gh issue create --title "[security][P1] Add comprehensive secret scanning" --label security --label P1 --label component:harness --label environment:ci --label status:backlog --body "Parent: #4`n`nReplace or supplement the narrow literal-credential guard with maintained full-history and pull-request secret scanning while preserving useful environment examples."
```

Expected: six distinct issue URLs are returned. If an issue with the exact title already exists, reuse it instead of creating a duplicate.

- [ ] **Step 3: Link the issue numbers from parent #4**

Query the six issues and add a generated Markdown checklist to #4:

```powershell
$harnessFollowups = gh issue list --state open --search '"Parent: #4" in:body' --json number,title,url | ConvertFrom-Json
$harnessLines = $harnessFollowups | ForEach-Object { "- [ ] #$($_.number) $($_.title) — $($_.url)" }
$harnessBody = "Deferred work from #4:`n`n" + ($harnessLines -join "`n")
gh issue comment 4 --body $harnessBody
```

Expected: exactly six results are returned, issue #4 contains their numbers, titles, and URLs, and each follow-up body points back to #4.

---

### Task 7: End-to-end verification and review handoff

**Files:**
- Modify only if a validation command exposes a defect in a Phase 1 harness file.

**Interfaces:**
- Consumes: all Phase 1 deliverables.
- Produces: clean local evidence and a reviewable branch ready for push and pull request creation.

- [ ] **Step 1: Verify dependency reproducibility and imports**

Run:

```powershell
uv lock --check
uv sync --locked --group notebook --group dev --no-group spark
uv run python -c "import dotenv, fpgrowth_py, matplotlib, mlxtend, numpy, pandas, pyodbc, sklearn, sqlalchemy; print('dependency imports passed')"
```

Expected: all commands exit 0 and print the import success line.

- [ ] **Step 2: Run the complete harness suite**

Run:

```powershell
uv run python scripts/validate_repository.py
uv run python scripts/validate_notebooks.py
uv run ruff check scripts tests
uv run pytest --cov=scripts --cov-report=term-missing
```

Expected: repository validation passes; five notebooks pass with zero failures; Ruff reports no errors; pytest passes with a coverage table.

- [ ] **Step 3: Inspect scope and commit hygiene**

Run:

```powershell
git diff develop...HEAD --check
git status --short --branch
git log --oneline develop..HEAD
git diff --stat develop...HEAD
```

Expected: no whitespace errors, no uncommitted changes, focused commits only, and no modifications to `apriori.py` or `apriori_store.py`.

- [ ] **Step 4: Request code review before integration**

Use `superpowers:requesting-code-review` to compare the branch against issue #4 and the approved design. Address only verified Phase 1 defects and rerun the full suite after changes. The pull-request description must state that rollback is a revert of the harness pull request and requires no database migration or data repair. Then use `superpowers:finishing-a-development-branch` to present the integration choice and prepare the pull request to `develop`.
