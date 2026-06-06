"""Deprecated compatibility path for work-order adapters.

Import from ``coactra.jobs.work.adapters`` instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "coactra.jobs.adapters is deprecated; import from coactra.jobs.work.adapters instead.",
    DeprecationWarning,
    stacklevel=2,
)

from coactra.jobs.work.adapters import *  # noqa: F403
