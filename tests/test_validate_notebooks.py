import json
import subprocess
from pathlib import Path

from scripts import validate_notebooks as validator
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


def write_notebook(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def initialize_git_repository(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True)


def test_validate_notebook_accepts_clean_notebook(tmp_path: Path) -> None:
    path = tmp_path / "clean.ipynb"
    write_notebook(path, notebook())
    assert validate_notebook(path) == []


def test_validate_notebook_rejects_execution_count(tmp_path: Path) -> None:
    path = tmp_path / "dirty.ipynb"
    write_notebook(path, notebook(execution_count=1))
    assert "code cell 3 has an execution count" in validate_notebook(path)


def test_validate_notebook_rejects_non_object_root(tmp_path: Path) -> None:
    path = tmp_path / "non-object.ipynb"
    write_notebook(path, [])

    assert validate_notebook(path) == ["notebook root must be a JSON object"]


def test_validate_notebook_rejects_non_list_cells(tmp_path: Path) -> None:
    path = tmp_path / "non-list-cells.ipynb"
    write_notebook(path, {"cells": {}})

    assert validate_notebook(path) == ["notebook cells must be a list"]


def test_validate_notebook_rejects_non_object_cell(tmp_path: Path) -> None:
    path = tmp_path / "non-object-cell.ipynb"
    write_notebook(path, {"cells": [42]})

    assert validate_notebook(path) == ["cell 0 must be a JSON object"]


def test_validate_notebook_rejects_non_string_source(tmp_path: Path) -> None:
    path = tmp_path / "non-string-source.ipynb"
    write_notebook(path, {"cells": [{"cell_type": "markdown", "source": 42}]})

    assert validate_notebook(path) == [
        "cell 0 source must be a string or a list of strings"
    ]


def test_validate_notebook_rejects_source_list_with_non_strings(tmp_path: Path) -> None:
    path = tmp_path / "mixed-source.ipynb"
    write_notebook(
        path,
        {"cells": [{"cell_type": "markdown", "source": ["# Title", 42]}]},
    )

    assert validate_notebook(path) == [
        "cell 0 source must be a string or a list of strings"
    ]


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


def test_run_validation_discovers_nested_notebooks(tmp_path: Path, capsys) -> None:
    path = tmp_path / "experiments" / "nested" / "clean.ipynb"
    write_notebook(path, notebook())

    assert run_validation(tmp_path, tmp_path) == 0
    output = capsys.readouterr().out
    assert "PASS experiments/nested/clean.ipynb" in output
    assert "Validated 1 notebooks; 0 failed." in output


def test_main_validates_only_git_tracked_notebooks(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    initialize_git_repository(tmp_path)
    tracked = tmp_path / "research" / "tracked.ipynb"
    untracked = tmp_path / "notebooks" / "untracked.ipynb"
    write_notebook(tracked, notebook())
    write_notebook(untracked, [])
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "research/tracked.ipynb"],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(validator, "PROJECT_ROOT", tmp_path)

    assert validator.main() == 0
    output = capsys.readouterr().out
    assert "PASS research/tracked.ipynb" in output
    assert "untracked.ipynb" not in output
    assert "Validated 1 notebooks; 0 failed." in output
