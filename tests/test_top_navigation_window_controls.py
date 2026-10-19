"""SYNTHETIC action contracts; actual pointer qualification remains the browser gate."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def check_actions():
    path = ROOT / "scripts/a0_browser_smoke.py"
    node = next(node for node in ast.parse(path.read_text(encoding="utf-8")).body
                if isinstance(node, ast.FunctionDef) and node.name == "check_top_navigation_actions")
    namespace = {"visible_control_box": lambda node: node.box}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["check_top_navigation_actions"]


class Node:
    def __init__(self, name, *, disabled=False, visible=True):
        self.name, self.disabled, self.visible = name, disabled, visible
        self.box = {"width": 32, "height": 32, "rawWidth": 32, "rawHeight": 32, "reachable": True}

    def count(self):
        return 1

    def is_visible(self):
        return self.visible

    def is_disabled(self):
        return self.disabled

    def is_enabled(self):
        return not self.disabled


def fixture(mode, suspended):
    toggle = "铺满主控台" if mode == "floating" else "还原主控台"
    nodes = {name: Node(name, disabled=(name == "运行诊断" and suspended)
                       or (name == toggle and mode == "compact"))
             for name in ("通知", "设置", "运行诊断", "avatar", toggle, "复位主控台")}
    if suspended:
        nodes["重新检查诊断连接"] = Node("重新检查诊断连接")
    missing = SimpleNamespace(count=lambda: 0)
    actions = SimpleNamespace(
        get_by_role=lambda role, *, name, exact: nodes.get(name, missing),
        locator=lambda selector: nodes["avatar"] if selector == "button.top-nav-user"
        else SimpleNamespace(count=lambda: len(nodes)))
    page = SimpleNamespace(locator=lambda selector: actions if selector == ".top-nav-right"
                           else SimpleNamespace(get_attribute=lambda name: mode))
    return page, nodes, toggle


@pytest.mark.parametrize("mode", ["floating", "full", "compact"])
@pytest.mark.parametrize("suspended", [False, True])
def test_exact_window_actions_and_old_actions_in_each_mode(mode, suspended):
    page, _nodes, _toggle = fixture(mode, suspended)
    check_actions()(page, diagnostics_suspended=suspended)


@pytest.mark.parametrize("tamper", ["missing_toggle", "hidden_reset", "disabled_reset",
    "disabled_full_toggle", "enabled_compact_toggle", "diagnostics_enabled", "missing_recheck",
    "hidden_recheck", "extra_action", "small_target", "clipped_target", "covered_target"])
def test_window_controls_do_not_weaken_existing_or_pointer_contracts(tamper):
    mode = "compact" if tamper == "enabled_compact_toggle" else "full"
    page, nodes, toggle = fixture(mode, True)
    if tamper == "missing_toggle":
        nodes.pop(toggle)
    elif tamper == "hidden_reset":
        nodes["复位主控台"].visible = False
    elif tamper == "disabled_reset":
        nodes["复位主控台"].disabled = True
    elif tamper == "disabled_full_toggle":
        nodes[toggle].disabled = True
    elif tamper == "enabled_compact_toggle":
        nodes[toggle].disabled = False
    elif tamper == "diagnostics_enabled":
        nodes["运行诊断"].disabled = False
    elif tamper == "missing_recheck":
        nodes.pop("重新检查诊断连接")
    elif tamper == "hidden_recheck":
        nodes["重新检查诊断连接"].visible = False
    elif tamper == "extra_action":
        nodes["unexpected"] = Node("unexpected")
    elif tamper == "small_target":
        nodes[toggle].box["width"] = 23
    elif tamper == "clipped_target":
        nodes[toggle].box["rawHeight"] = 50
    elif tamper == "covered_target":
        nodes[toggle].box["reachable"] = False
    with pytest.raises(AssertionError):
        check_actions()(page, diagnostics_suspended=True)
