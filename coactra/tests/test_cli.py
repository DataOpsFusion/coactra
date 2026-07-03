from __future__ import annotations

import json
import subprocess
import sys


def test_cli_doctor(capsys):
    from coactra.cli import main

    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "coactra doctor" in out
    assert "python=" in out


def test_cli_init_creates_minimal_project(tmp_path, capsys):
    from coactra.cli import main

    target = tmp_path / "triage-bot"

    assert main(["init", str(target)]) == 0

    assert (target / "app.py").exists()
    assert (target / ".env.example").exists()
    assert (target / "README.md").exists()
    assert "Team.local" in (target / "app.py").read_text()
    assert "created" in capsys.readouterr().out


def test_cli_validate_json_team_spec(tmp_path, capsys):
    from coactra.cli import main

    spec = tmp_path / "team.json"
    spec.write_text(json.dumps({"agents": [{"name": "triage"}]}))

    assert main(["validate", str(spec)]) == 0
    assert "valid" in capsys.readouterr().out


def test_cli_validate_rejects_missing_file(tmp_path, capsys):
    from coactra.cli import main

    assert main(["validate", str(tmp_path / "missing.json")]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_package_is_module_executable():
    result = subprocess.run(
        [sys.executable, "-m", "coactra", "doctor"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "coactra doctor" in result.stdout
