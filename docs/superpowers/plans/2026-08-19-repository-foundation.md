# Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a Git-backed, documented operating foundation for the recommendation-system project.

**Architecture:** Preserve the remote `main` history and LICENSE, establish development and staging branches, and add repository documentation that defines the SQL Server source-to-PostgreSQL target architecture. Environment templates document configuration without containing secrets.

**Tech Stack:** Git/GitHub, Python, SQL Server source warehouse, PostgreSQL application database, Markdown.

**Spec:** User-approved repository-foundation design in this task.

## Global Constraints

- Preserve existing remote `main` history and LICENSE.
- Use the `it20pepito` GitHub authorization for remote operations.
- SQL Server is read-only; PostgreSQL is the destination application database.
- Never commit secrets or production transaction data.

---

### Task 1: Preserve remote history and establish branches

**Files:**
- Create: Git metadata and `main`, `develop`, `staging` branch references

- [x] Initialize the existing workspace as a Git repository.
- [x] Add the remote as `origin` and fetch `origin/main`.
- [x] Check out local `main` tracking `origin/main`, preserving the LICENSE commit.
- [ ] Create `develop` and `staging` from the documented baseline on `main`.
- [ ] Verify each branch points at the same baseline commit.

### Task 2: Add repository documentation and safe configuration

**Files:**
- Create: `README.md`, `.gitignore`, `docs/AGENTS.md`, `docs/*.md`, environment example files

- [x] Add the requested governance documents with data, model, release, issue-lifecycle, and agent guidance.
- [x] Document the SQL Server source and PostgreSQL destination separation.
- [x] Add secret-free environment templates for development, staging, and production.
- [x] Add ignore rules for credentials, local environments, logs, caches, and generated artifacts.
- [x] Verify required files exist and no example contains a credential.

### Task 3: Validate and publish the baseline

**Files:**
- Modify: Git index and branch references

- [x] Inspect Markdown headings and environment-template keys.
- [x] Review the staged change set for accidental sensitive content.
- [ ] Commit the baseline on `main`.
- [ ] Push `main`, `develop`, and `staging` to `origin` using `it20pepito` authorization.
