"""Hermetic repository-wide pytest environment."""

from __future__ import annotations

import atexit
import os
from tempfile import TemporaryDirectory

_RUNTIME = TemporaryDirectory(prefix="cognitive-pytest-")
os.environ["COGNITIVE_DATA_DIR"] = _RUNTIME.name
atexit.register(_RUNTIME.cleanup)
