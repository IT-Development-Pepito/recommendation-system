# Agent Daily Operating Rules

These mandatory issue-lifecycle rules apply to every human or AI contributor. They supplement `AGENTS.md` and `docs/DEVELOPMENT_WORKFLOW.md`; the development workflow remains authoritative when a detail is not repeated here.

## Start of work

1. Work only from a clearly identified issue, or create one before material work begins.
2. Confirm owner, objective, acceptance criteria, priority, dependencies, data classification, and target environment.
3. Read the current issue history, `PROGRESS.md`, relevant architecture, and the latest operational context.
4. Declare scope before editing. Escalate if the requested work includes a production release, destructive action, database migration, credential change, or unclear data access.

## During work

1. Keep the issue status current: `Open` → `In Progress` → `In Review` → `Done`, or `Blocked` with the blocker and needed owner action.
2. Record decisions, assumptions, implementation links, validation evidence, and material risks in the issue.
3. Do not silently broaden scope. Create or link a follow-up issue for unrelated discoveries.
4. Do not use production credentials or data beyond approved, least-privilege access. Redact identifiers and secrets from logs, screenshots, notebooks, commits, and discussion.
5. Keep changes on a focused branch; rebase or merge according to team policy before review.

## End of work

1. Run the required checks and attach or link the results to the issue.
2. Update `PROGRESS.md` for every completed implementation, bug fix, documentation update, experiment, release, or operational change.
3. Request review with a concise summary, test evidence, data/ML impact, rollback plan, and known limitations.
4. Close an issue only after acceptance criteria, review, documentation, validation, and deployment status are recorded. Otherwise leave it `In Review` or `Blocked`.

## Daily hygiene

- Review assigned open and blocked issues at the beginning and end of each work period.
- Surface stale blockers, failed validations, source-data anomalies, drift, and unowned follow-ups promptly.
- Never mark work complete solely because code was written; completion requires evidence and traceability.
