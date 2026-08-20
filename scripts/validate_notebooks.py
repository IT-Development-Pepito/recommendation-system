"""Validate repository conventions for committed Jupyter notebooks."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
RELATIVE_CSV_EXPORT = re.compile(r"\.to_csv\(\s*['\"][^'\"]+\.csv['\"]")


def source_text(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


def validate_notebook(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read valid notebook JSON: {exc}"]

    if not isinstance(notebook, dict):
        return ["notebook root must be a JSON object"]
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        return ["notebook cells must be a list"]
    if not cells:
        return ["contains no cells"]

    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            errors.append(f"cell {index} must be a JSON object")
            continue
        source = cell.get("source", "")
        if not isinstance(source, str) and not (
            isinstance(source, list)
            and all(isinstance(part, str) for part in source)
        ):
            errors.append(f"cell {index} source must be a string or a list of strings")
    if errors:
        return errors

    first_cell = cells[0]
    if first_cell.get("cell_type") != "markdown" or not source_text(first_cell).lstrip().startswith("# "):
        errors.append("must start with a Markdown title")

    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
    if not code_cells:
        errors.append("must contain at least one code cell")
    if len(markdown_cells) < 3:
        errors.append("must contain at least three Markdown structure cells")

    for index, cell in enumerate(cells):
        text = source_text(cell)
        if not text.strip():
            errors.append(f"cell {index} is empty")
        if cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None:
            errors.append(f"code cell {index} has an execution count")
        if cell.get("outputs"):
            errors.append(f"code cell {index} has saved outputs")
        if RELATIVE_CSV_EXPORT.search(text):
            errors.append(f"code cell {index} exports CSV using a working-directory-relative path")
        try:
            ast.parse(text, filename=f"{path.name}:cell-{index}")
        except SyntaxError as exc:
            errors.append(f"code cell {index} has invalid Python syntax: {exc.msg}")

    return errors


def validate_paths(notebook_paths: Sequence[Path], project_root: Path) -> int:
    if not notebook_paths:
        print("No notebooks found.", file=sys.stderr)
        return 1

    failures = 0
    for path in notebook_paths:
        errors = validate_notebook(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(project_root).as_posix()}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path.relative_to(project_root).as_posix()}")

    print(f"Validated {len(notebook_paths)} notebooks; {failures} failed.")
    return 1 if failures else 0


def run_validation(notebook_dir: Path, project_root: Path) -> int:
    return validate_paths(sorted(notebook_dir.rglob("*.ipynb")), project_root)


def tracked_notebook_paths(project_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "-z", "--", "*.ipynb"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [project_root / value for value in result.stdout.split("\0") if value]


def main() -> int:
    try:
        notebook_paths = tracked_notebook_paths(PROJECT_ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL cannot enumerate tracked notebooks: {exc}", file=sys.stderr)
        return 1
    return validate_paths(notebook_paths, PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
