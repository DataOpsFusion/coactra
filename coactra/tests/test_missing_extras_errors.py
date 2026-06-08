"""Optional extras must raise MissingExtraError with install guidance."""

from __future__ import annotations

import pytest

from coactra.errors import MissingExtraError


def test_ai_missing_wrap_shelf_raises_missing_extra():
    from coactra.ai import _missing_wrap_shelf

    with pytest.raises(MissingExtraError) as exc:
        _missing_wrap_shelf()
    assert exc.value.extra == "ai"
    assert "coactra[ai]" in str(exc.value)
