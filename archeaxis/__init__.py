"""archeaxis — 星环知识平台根包（新规划 §一：Python 根包目标）。

当前实现为转发层：把既有的 app 包通过 sys.modules 别名挂到 archeaxis.* 命名空间，
使新根包名可用（from archeaxis.app.main import app）而无需一次性高风险重命名。
完整迁移（app/ -> archeaxis/ 目录重命名 + 全量 import 更新）记录为 G7 续项。
"""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.6.6"
__product__ = "ArcheAxis Knowledge / 星环知识平台"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# alias the legacy app package under the archeaxis namespace
import app as _app_pkg  # noqa: E402

_self = sys.modules[__name__]
sys.modules.setdefault("archeaxis.app", _app_pkg)
setattr(_self, "app", _app_pkg)
for _sub in ("main", "contracts", "federation", "ingestion", "knowledge", "setup", "workspace"):
    try:
        _mod = __import__(f"app.{_sub}", fromlist=["*"])
        sys.modules.setdefault(f"archeaxis.{_sub}", _mod)
        setattr(_self, _sub, _mod)
    except Exception:  # noqa: BLE001 - optional submodule aliases
        pass


def app_module():
    """Return the FastAPI application (aliased root package entry)."""
    from archeaxis.app.main import app
    return app
