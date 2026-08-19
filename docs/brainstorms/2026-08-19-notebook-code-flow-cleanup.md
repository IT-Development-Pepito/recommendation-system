# Notebook Code-Flow Cleanup Brainstorm

**Date:** 2026-08-19
**Status:** Approved
**Target:** `notebooks/`

## Problem

The exploratory notebooks mix setup, data access, transformation, mining, validation, visualization, and export steps without a consistent narrative. Several notebooks retain execution counts and generated outputs, making reviews noisy and potentially exposing operational details.

## Intended outcome

Each notebook should read and execute from top to bottom with a consistent structure: purpose and prerequisites, imports and configuration, data loading, validation and preparation, analysis or mining, evaluation or visualization, and optional export.

## Decisions

- Preserve the existing notebook logic and the local environment/SQL Server connection improvements already present in the working tree.
- Add concise Markdown headings and explanations around logical stages.
- Consolidate or remove empty, duplicate, and stale setup cells where safe.
- Resolve repository-relative paths from the project root.
- Clear all saved outputs and reset execution counts before committing.
- Keep production architecture and business/data flows unchanged.

## Alternatives considered

- Convert notebooks into Python modules now: rejected because reusable production extraction and mining modules require a separate design and issue.
- Preserve generated outputs: rejected because outputs make diffs noisy and may include source-system details.

## Assumptions and constraints

- SQL Server remains a read-only source.
- Full execution requires approved warehouse access, credentials, ODBC drivers, and notebook dependencies.
- This issue improves notebook organization and reviewability; it does not certify analytical correctness or production readiness.

## Acceptance criteria

1. All notebooks are valid notebook JSON and retain at least one code cell.
2. Every notebook starts with a title/purpose section and uses Markdown sections for its major stages.
3. Code cells have no saved outputs and all execution counts are reset.
4. Repository-relative dataset paths work whether Jupyter starts from the repository root or `notebooks/`.
5. Existing user-authored environment and connection changes are preserved.
6. The implementation and validation results are recorded in `docs/PROGRESS.md`.

## Recommended issue breakdown

- One P1 task covering the five notebooks because the cleanup convention and validation are shared.
- Follow-up issues should capture any broken analytical logic, missing reusable modules, or environment/dependency blockers discovered during cleanup.
