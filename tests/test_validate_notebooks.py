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
