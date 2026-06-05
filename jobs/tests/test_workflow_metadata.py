import json
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_adapter_maturity_manifest_has_runtime_resume_semantics():
    manifest = json.loads((repo_root() / "docs" / "adapter_maturity.json").read_text())
    semantics = set(manifest["resume_semantics_values"])

    assert {"same-thread", "new-run-with-prior-state", "unsupported", "host-owned"} <= semantics
    by_name = {item["name"]: item for item in manifest["adapters"]}
    assert by_name["TemporalEngine"]["resume_semantics"] == "same-thread"
    assert by_name["PrefectEngine"]["resume_semantics"] == "new-run-with-prior-state"
    assert by_name["DurableLangGraphEngine"]["resume_semantics"] == "same-thread"
