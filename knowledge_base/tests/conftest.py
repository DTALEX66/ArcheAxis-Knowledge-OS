"""KB 内部测试隔离：每个测试文件使用独立空库 + storage.init()。

tests/ 与 knowledge_base/tests 共享真实 data/cognitive_os.sqlite；
kb 测试假设 DB 干净（如 FTS candidate count 断言）。真实库可能被
其他测试留下历史数据 → 复制污染源无效。改为：每个测试重定向
shared.storage.DB_PATH 到全新空库，并用 storage.init() 创建
IR_KB_TABLES（含 FTS5 虚拟表，CREATE IF NOT EXISTS 幂等）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared import storage


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path) -> None:
    """Redirect storage.DB_PATH to a fresh empty DB with the KB schema."""
    real = Path(storage.DB_PATH)
    target = tmp_path / "cognitive_os_test.sqlite"
    storage.DB_PATH = target
    storage.init()
    yield
    storage.DB_PATH = real
