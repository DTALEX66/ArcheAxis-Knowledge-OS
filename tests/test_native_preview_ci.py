"""CI必须把本job刚构建的Core交给真实native预览测试；不允许隐式跳过。"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def assert_owned_core_wiring(workflow):
    steps = workflow["jobs"]["desktop-fast"]["steps"]
    prepare_index, prepare = next(
        (index, step) for index, step in enumerate(steps)
        if step.get("id") == "desktop_runtime"
    )
    script = prepare["run"]
    build = "python -B scripts/runtime/dev.py -- cargo build -p archeaxis-api --bin archeaxis-api --release --locked"
    bind = "$previewCore = Join-Path $env:CARGO_TARGET_DIR 'release/archeaxis-api.exe'"
    verify = "if (-not (Test-Path -LiteralPath $previewCore -PathType Leaf)) { throw 'Owned preview Core build output missing' }"
    resolve = "$previewCore = (Resolve-Path -LiteralPath $previewCore).Path"
    export = '"BE10_PREVIEW_CORE=$previewCore" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append'
    positions = [script.index(line) for line in [build, bind, verify, resolve, export]]
    assert positions == sorted(positions)
    assert "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }" in script[positions[0]:positions[1]]
    assert prepare.get("working-directory") == "${{ github.workspace }}"
    assert "if" not in prepare
    consumers = [
        (index, step) for index, step in enumerate(steps)
        if step.get("working-directory") == "src-tauri" and "cargo test" in step.get("run", "")
    ]
    assert len(consumers) == 2
    for index, step in consumers:
        assert index > prepare_index
        assert "if" not in step
        assert "continue-on-error" not in step
        assert "BE10_PREVIEW_CORE" not in step.get("env", {})
        assert "--ignore" not in step["run"]
    return prepare_index


def test_real_ci_binds_successfully_built_core_before_both_native_suites():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert_owned_core_wiring(workflow)


@pytest.mark.parametrize("tamper", ["export", "guard", "build_failure", "path", "skip"])
def test_ci_wiring_negative_controls_reject_regressions(tamper):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    workflow = copy.deepcopy(workflow)
    steps = workflow["jobs"]["desktop-fast"]["steps"]
    index = next(i for i, step in enumerate(steps) if step.get("id") == "desktop_runtime")
    step = steps[index]
    if tamper == "skip":
        step["if"] = "false"
    else:
        replacements = {
            "export": ('"BE10_PREVIEW_CORE=$previewCore"', '"OTHER_CORE=$previewCore"'),
            "guard": ("if (-not (Test-Path -LiteralPath $previewCore -PathType Leaf))", "if ($false)"),
            "build_failure": ("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }", "Write-Host ignored"),
            "path": ("'release/archeaxis-api.exe'", "'debug/other-api.exe'"),
        }
        before, after = replacements[tamper]
        step["run"] = step["run"].replace(before, after, 1)
    with pytest.raises((AssertionError, ValueError)):
        assert_owned_core_wiring(workflow)
