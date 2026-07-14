from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def test_architecture_guard_rejects_new_boundary_violations(tmp_path: Path):
    from scripts.check_architecture import scan_architecture

    _write(
        tmp_path,
        "app/new_bootstrap.py",
        "import sys\n"
        "sys.path.insert(0, 'vendor')\n"
        "sys.path.extend(['vendor2'])\n"
        "sys.path[:] = ['vendor3']\n"
        "sys.path += ['vendor4']\n"
        "alias = sys.path\n"
        "alias.append('vendor5')\n"
        "import sys as system\n"
        "system.path.append('vendor6')\n"
        "del sys.path[:]\n",
    )
    _write(tmp_path, "cli.py", "from sys import path as search_path\nsearch_path.append('vendor')\n")
    _write(tmp_path, "shared-contracts/schemas/leak.py", "from app.core import router\n")
    _write(
        tmp_path,
        "platform/leak.py",
        "import os, app\n"
        "import importlib as il\n"
        "from importlib import import_module\n"
        "import knowledge_base\n"
        "il.import_module('app.agent.executor')\n"
        "import_module('knowledge_base')\n",
    )
    _write(
        tmp_path,
        "app/core/reverse.py",
        "from app import facades, main\n"
        "import importlib\n"
        "import importlib as il\n"
        "from importlib import import_module as load_module\n"
        "importlib.import_module('app.facades.runtime')\n"
        "il.import_module('app.facades.runtime')\n"
        "load_module('app.main')\n"
        "__import__('app.main')\n",
    )
    _write(
        tmp_path,
        "shared/personal_path.py",
        "DATA_ROOT = 'load E:/private/vault'\n"
        "UNC_ROOT = r'\\\\server\\share\\vault'\n"
        "OPT_ROOT = '/opt/private/vault'\n"
        "VAR_ROOT = '/var/private/vault'\n"
        "TMP_ROOT = '/tmp/private/vault'\n"
        "WSL_ROOT = '/mnt/e/private/vault'\n"
        "FORWARD_UNC = '//server/share/vault'\n"
        "ETC_ROOT = '/etc/cognitive/config'\n"
        "SRV_ROOT = '/srv/cognitive/data'\n"
        "ROOT_HOME = '/root/cognitive'\n"
        "DATA_DIR = '/data/cognitive'\n"
        "WORKSPACE_DIR = '/workspace/cognitive'\n"
        "USR_DIR = '/usr/local/cognitive'\n",
    )

    issues = scan_architecture(tmp_path)

    assert Counter(issue.code for issue in issues) == Counter(
        {
            "forbidden-absolute-path": 13,
            "forbidden-sys-path-mutation": 8,
            "reverse-business-dependency": 5,
            "reverse-facade-dependency": 5,
        }
    )
    assert {issue.path for issue in issues} == {
        "app/core/reverse.py",
        "app/new_bootstrap.py",
        "cli.py",
        "platform/leak.py",
        "shared-contracts/schemas/leak.py",
        "shared/personal_path.py",
    }


def test_architecture_guard_does_not_transfer_grandfather_to_a_new_line(tmp_path: Path):
    from scripts.check_architecture import scan_architecture

    _write(
        tmp_path,
        "shared/backlinks.py",
        "import sys\n"
        "from pathlib import Path\n"
        "_PROJECT_ROOT = Path(__file__).resolve().parents[1]\n"
        "# the historical expression has moved to a different occurrence\n"
        "sys.path.insert(0, str(_PROJECT_ROOT))\n",
    )

    issues = scan_architecture(tmp_path)

    assert [issue.code for issue in issues] == ["forbidden-sys-path-mutation"]


def test_architecture_guard_consumes_grandfathered_occurrence_once(tmp_path: Path):
    from scripts.check_architecture import scan_architecture

    content = "\n" * 20 + (
        "sys.path.insert(0, str(_PROJECT_ROOT)); "
        "sys.path.insert(0, str(_PROJECT_ROOT))\n"
    )
    _write(tmp_path, "shared/backlinks.py", content)

    assert [issue.code for issue in scan_architecture(tmp_path)] == [
        "forbidden-sys-path-mutation"
    ]


def test_architecture_guard_ignores_documentation_and_error_examples(tmp_path: Path):
    from scripts.check_architecture import scan_architecture

    _write(
        tmp_path,
        "app/core/examples.py",
        '"""Documentation may mention E:/example and /tmp/example."""\n'
        "import sys\n"
        "alias = sys.path\n"
        "def explain():\n"
        '    """A function example may mention /opt/example."""\n'
        "    raise ValueError('do not use E:/example here')\n",
    )

    assert scan_architecture(tmp_path) == []


@pytest.mark.parametrize("lower_path", ["app/core", "app/agent", "shared", "knowledge_base"])
@pytest.mark.parametrize(
    "statement",
    [
        "from app import facades",
        "from app import main",
        "import importlib; importlib.import_module('app.facades.runtime')",
        "__import__('app.main')",
    ],
)
def test_architecture_guard_covers_each_lower_runtime_boundary(
    tmp_path: Path, lower_path: str, statement: str
):
    from scripts.check_architecture import scan_architecture

    _write(tmp_path, f"{lower_path}/leak.py", f"{statement}\n")

    assert [issue.code for issue in scan_architecture(tmp_path)] == [
        "reverse-facade-dependency"
    ]


def test_architecture_guard_accepts_current_grandfathered_tree():
    from scripts.check_architecture import scan_architecture

    root = Path(__file__).resolve().parents[1]
    assert scan_architecture(root) == []


def test_ci_runs_architecture_guard():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python scripts/check_architecture.py" in workflow
