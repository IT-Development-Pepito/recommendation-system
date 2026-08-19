"""Validate repository conventions for committed Jupyter notebooks."""

from __future__ import annotations

import ast
import json
import re
import sys
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

    cells = notebook.get("cells", [])
    if not cells:
        return ["contains no cells"]

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


if __name__ == "__main__":
    raise SystemExit(main())
