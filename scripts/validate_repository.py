"""Validate repository-level harness and secret-safety invariants."""


from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

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
    Path("docs/AGENTS.md"),
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
BARE_CREDENTIAL_SUFFIXES = {".bat", ".example", ".yaml", ".yml"}
PRIVATE_KEY_MARKER = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
CREDENTIAL_ASSIGNMENT = re.compile(
    r"^\s*(?:export\s+|set\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY)"
    r"[A-Z0-9_]*\s*[:=]\s*(?:"
    r"(?P<quote>[\"'])(?P<quoted>[^\"'\r\n]*)(?P=quote)"
    r"|(?P<bare>[^\"'()\[\]{},\s#]+)"
    r")\s*(?:#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)
PLACEHOLDER_MARKERS = ("replace_me", "example", "changeme", "placeholder", "dummy", "your_")


def is_environment_file(path: Path) -> bool:
    name = path.name.casefold()
    return name == ".env" or name.startswith(".env.")


def is_approved_example(path: Path) -> bool:
    name = path.name.casefold()
    return name.startswith(".env.") and name.endswith(".example")


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        not lowered
        or lowered.startswith(("$", "{{", "<"))
        or any(marker in lowered for marker in PLACEHOLDER_MARKERS)
    )


def credential_errors(
    relative: Path,
    text: str,
    *,
    location: str = "",
    allow_bare: bool = False,
) -> list[str]:
    errors: list[str] = []
    for match in CREDENTIAL_ASSIGNMENT.finditer(text):
        value = match.group("quoted")
        if value is None:
            if not allow_bare:
                continue
            value = match.group("bare")
        if not is_placeholder(value):
            line = text.count("\n", 0, match.start()) + 1
            position = f"{location}line {line}" if location else str(line)
            errors.append(f"possible literal credential: {relative.as_posix()}:{position}")
    return errors


def notebook_credential_errors(relative: Path, text: str) -> list[str]:
    try:
        notebook = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(notebook, dict):
        return []
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        return []

    errors: list[str] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list) and all(isinstance(part, str) for part in source):
            source = "".join(source)
        if not isinstance(source, str):
            continue
        errors.extend(
            credential_errors(relative, source, location=f"code cell {index} ")
        )
    return errors


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
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PRIVATE_KEY_MARKER.search(text):
            errors.append(f"obvious private-key material: {relative.as_posix()}")
        suffix = path.suffix.lower()
        if suffix == ".ipynb":
            errors.extend(notebook_credential_errors(relative, text))
        elif suffix in TEXT_SUFFIXES:
            errors.extend(
                credential_errors(
                    relative,
                    text,
                    allow_bare=suffix in BARE_CREDENTIAL_SUFFIXES,
                )
            )
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
