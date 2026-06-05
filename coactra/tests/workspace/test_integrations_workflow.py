from pathlib import Path
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("pytest_asyncio")

from coactra.workspace.integrations.workflow import propose_candidate_workflow


@pytest.mark.asyncio
async def test_propose_writes_inert_yaml_candidate(tmp_path: Path):
    llm = AsyncMock()
    llm.ainvoke.return_value = type(
        "R", (), {"content": "name: cleanup_old_vms\nnodes: []\nedges: []\n"}
    )()

    path = await propose_candidate_workflow(
        work_order_summary="cleaned stale VMs",
        candidate_dir=tmp_path / "candidate",
        llm=llm,
    )

    assert path.name == "cleanup_old_vms.yaml"
    assert "NOT yet approved" in path.read_text()
