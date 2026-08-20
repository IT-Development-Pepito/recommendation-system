import json
from pathlib import Path

import pytest

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


def test_requires_repository_specific_agent_guidance(tmp_path: Path) -> None:
    errors = validate_repository(tmp_path, [])
    assert "missing required path: docs/AGENTS.md" in errors


def test_rejects_tracked_nonexample_environment_file(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    secret_env = Path(".env.production")
    (tmp_path / secret_env).write_text("PASSWORD=replace_me\n", encoding="utf-8")
    errors = validate_repository(tmp_path, [*tracked, secret_env])
    assert "tracked environment file is not an approved example: .env.production" in errors


def test_rejects_uppercase_tracked_environment_file(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    secret_env = Path(".ENV")
    (tmp_path / secret_env).write_text("PASSWORD=replace_me\n", encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, secret_env])

    assert "tracked environment file is not an approved example: .ENV" in errors


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


@pytest.mark.parametrize("key_file", [Path("certificates/server.pem"), Path("id_ed25519")])
def test_rejects_private_key_marker_in_any_utf8_tracked_file(
    tmp_path: Path, key_file: Path
) -> None:
    tracked = valid_repository(tmp_path)
    (tmp_path / key_file).parent.mkdir(parents=True, exist_ok=True)
    key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    (tmp_path / key_file).write_text(key_marker, encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, key_file])

    assert f"obvious private-key material: {key_file.as_posix()}" in errors


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


def test_rejects_literal_credential_in_notebook_code_cell(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    notebook_path = Path("notebooks/credential.ipynb")
    (tmp_path / notebook_path).parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "source": ['api_token = "live-value-123"\n'],
            }
        ]
    }
    (tmp_path / notebook_path).write_text(json.dumps(notebook), encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, notebook_path])

    assert (
        "possible literal credential: notebooks/credential.ipynb:code cell 0 line 1"
        in errors
    )


def test_ignores_credential_named_variable_assigned_an_expression(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    source = Path("scripts/paths.py")
    (tmp_path / source).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / source).write_text(
        'secret_env = Path(".env.production")\n', encoding="utf-8"
    )

    errors = validate_repository(tmp_path, [*tracked, source])

    assert all("possible literal credential" not in error for error in errors)


def test_ignores_credential_assigned_a_bare_python_identifier(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    source = Path("scripts/settings.py")
    (tmp_path / source).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / source).write_text("secret = credential_value\n", encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, source])

    assert all("possible literal credential" not in error for error in errors)


def test_ignores_credential_assigned_python_attribute_access(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    source = Path("scripts/settings.py")
    (tmp_path / source).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / source).write_text("api_token = settings.api_token\n", encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, source])

    assert all("possible literal credential" not in error for error in errors)


def test_rejects_bare_environment_style_credential(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    settings = Path("settings.yaml")
    (tmp_path / settings).write_text("API_TOKEN: live-value-123\n", encoding="utf-8")

    errors = validate_repository(tmp_path, [*tracked, settings])

    assert "possible literal credential: settings.yaml:1" in errors


def test_accepts_clean_repository(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    assert validate_repository(tmp_path, tracked) == []
