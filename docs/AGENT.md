# Agent Guideline

Agents are contributors, not autonomous release authorities. Read `AGENTS.md`, this file, `DEVELOPMENT_WORKFLOW.md`, `SYSTEM_ARCHITECTURE.md`, and `AGENT_DAILY_OPERATING_RULES.md` before changing repository state.

## Required behavior

1. Start from the tracked issue and restate scope, acceptance criteria, constraints, and affected data systems.
2. Inspect existing code and documentation before proposing changes. Preserve unrelated work.
3. Prefer small, reviewable changes with tests and explicit validation evidence.
4. Never invent credentials, access production systems without authorization, or expose secrets or sensitive transaction data.
5. Treat SQL Server as read-only and send application writes only to PostgreSQL.
6. Update the relevant documentation and `PROGRESS.md`; provide exact verification performed and remaining risks.
7. Escalate ambiguous requirements, schema changes, destructive actions, data-quality failures, security concerns, and release decisions to a human owner.

## Branch and release authority

Agents may work on a scoped branch and prepare a change for review. Humans approve merges into `staging` and `main`, production data access, schema migrations, credential changes, and incident actions unless explicit written delegation says otherwise.
