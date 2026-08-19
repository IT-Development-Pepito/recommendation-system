from pathlib import Path

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


def test_rejects_tracked_nonexample_environment_file(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    secret_env = Path(".env.production")
    (tmp_path / secret_env).write_text("PASSWORD=replace_me\n", encoding="utf-8")
    errors = validate_repository(tmp_path, [*tracked, secret_env])
    assert "tracked environment file is not an approved example: .env.production" in errors


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


def test_accepts_clean_repository(tmp_path: Path) -> None:
    tracked = valid_repository(tmp_path)
    assert validate_repository(tmp_path, tracked) == []
