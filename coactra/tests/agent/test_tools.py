import pytest
from pydantic import ValidationError

from coactra.agent import ToolSpec


def test_toolspec_minimal():
    t = ToolSpec(name="read_file", mount_id="fs")
    assert t.name == "read_file"
    assert t.mount_id == "fs"


def test_qualified_name_namespaces_by_mount_id():
    t = ToolSpec(name="read_file", mount_id="fs")
    assert t.qualified_name == "fs.read_file"


def test_toolspec_rejects_empty_name():
    with pytest.raises(ValidationError):
        ToolSpec(name="", mount_id="fs")
