from __future__ import annotations

import importlib.util
import sys
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_simulated_native_journal_is_explicit_and_rejects_stale_or_frozen_writes():
    """Execute the actual browser stub JS; this is fixture qualification only."""
    smoke = _load_smoke_module()
    node = shutil.which("node")
    assert node is not None, "declared Node runtime required for browser fixture validation"
    script = "import {webcrypto} from 'node:crypto'; import assert from 'node:assert/strict'; globalThis.window={}; if(!globalThis.crypto)Object.defineProperty(globalThis,'crypto',{value:webcrypto});\n"
    script += smoke.host_bridge_stub(stateful_documents=True)
    script += """
const command=(operation,body)=>window.__TAURI__.core.invoke('core_command',{request:{operation,payload:body?{body}:{}}});
const initial=await command('ui_state_read');
assert.equal(initial.status,200);assert.equal(initial.body.schema,'archeaxis.ui-working-state/v1');
assert.deepEqual(initial.body.state.drafts,{});
const {workspace_id,restore_epoch,state_revision}=initial.body;
const state={...initial.body.state,pending_original:{create_request_id:'fixed-request',title:'中文',editor_json:{type:'doc',content:[]}}};
const body={workspace_id,restore_epoch,state_revision,state};
const written=await command('ui_state_write',body);assert.equal(written.status,200);
assert.equal(written.body.state_revision,state_revision+1);assert.match(written.body.pending_document_id,/^doc_req_[a-f0-9]{64}$/);
assert.equal((await command('ui_state_write',body)).status,409);
const changed=structuredClone(body);changed.state_revision=written.body.state_revision;changed.state.pending_original.title='different';
assert.equal((await command('ui_state_write',changed)).status,422);
assert.deepEqual((await command('ui_state_read')).body,written.body);
assert.equal((await command('ui_state_recover',{workspace_id,restore_epoch,state_revision:written.body.state_revision,action:'discard'})).status,409);
const unsupported=await command('ui_state_clear_saved',{workspace_id,restore_epoch,state_revision:written.body.state_revision,document_id:'absent',base_version:1,saved_version:2,content_sha256:'b'.repeat(64)});
assert.equal(unsupported.status,409);console.log('SIMULATED_JOURNAL_FIXTURE_PASS');
"""
    result = subprocess.run([node, "--input-type=module"], input=script, text=True,
                            capture_output=True, timeout=20, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "SIMULATED_JOURNAL_FIXTURE_PASS"

def _load_smoke_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "a0_browser_smoke.py"
    spec = importlib.util.spec_from_file_location("a0_browser_smoke_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    # Match the direct script entry point without relying on another test to
    # have leaked scripts/ into the interpreter search path.
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


@pytest.mark.parametrize('inner_overflow,inner_height,unreachable', [
    ('auto', 'auto', False),
    ('hidden', '80px', True),
    ('clip', '80px', True),
])
def test_real_browser_reachability_skips_nonoverflowing_auto_but_keeps_clip_barriers(
    inner_overflow, inner_height, unreachable,
):
    """Real layout regression: an auto wrapper is not necessarily the scroller."""
    smoke = _load_smoke_module()
    with smoke.sync_playwright() as playwright:
        options = {'headless': True}
        if sys.platform == 'win32':
            executable = smoke._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
            assert executable, 'declared project Chromium required; do not install implicitly'
            options['executable_path'] = executable
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width': 800, 'height': 600})
            page.set_content(f'''<style>
                body {{margin:0}}
                .outer {{height:120px;width:300px;overflow:auto}}
                .inner {{overflow:{inner_overflow};height:{inner_height}}}
                #templates {{height:500px;display:flex;flex-direction:column;justify-content:flex-end}}
                button {{height:32px}}
                </style><div class="outer"><div class="inner"><section id="templates">
                <button>模板操作</button></section></div></div>''')
            measured = smoke.measure_geometry(page, {'templates': '#templates'})
            assert bool(measured['unreachableBands']) is unreachable, measured
            if not unreachable:
                button = page.get_by_role('button', name='模板操作')
                button.scroll_into_view_if_needed()
                assert button.evaluate('''e => {const r=e.getBoundingClientRect();
                    return r.y>=0 && r.bottom<=120 && e.contains(document.elementFromPoint(
                        r.x+r.width/2,r.y+r.height/2));}''')
                button.click(timeout=3000)
        finally:
            browser.close()


def _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path):
    """Provide the only local prerequisite that Windows start_vite validates."""
    vite = tmp_path / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    vite.parent.mkdir(parents=True)
    vite.write_text("// unit-test Vite entrypoint\n", encoding="utf-8")
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    return vite


def test_windows_starts_vite_with_the_direct_node_entrypoint(monkeypatch, tmp_path):
    """The tracked Node process must be Vite itself, not a transient cmd/npm wrapper."""
    smoke = _load_smoke_module()
    captured: dict[str, object] = {}

    class _Process:
        pid = 4242

        def poll(self):
            return None

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Process()

    vite = _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path)
    monkeypatch.setattr(smoke.os, "name", "nt")
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "C:/node.exe")
    monkeypatch.setattr(smoke.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: _Response())

    process, log = smoke.start_vite(tmp_path / "vite.log")
    log.close()

    assert process.pid == 4242
    command = captured["command"]
    assert command[0] == "C:/node.exe"
    assert str(vite) in command
    assert "cmd.exe" not in command
    assert "npm" not in command
    assert captured["kwargs"]["cwd"] == smoke.ROOT / "frontend"


def test_windows_readiness_timeout_reclaims_the_started_vite_process(monkeypatch, tmp_path):
    smoke = _load_smoke_module()
    calls: list[tuple[object, object]] = []

    class _Process:
        pid = 4242
        waited = False
        terminated = False

        def poll(self):
            return None

        def wait(self, timeout):
            self.waited = True
            return 0

        def terminate(self):
            self.terminated = True

    process = _Process()
    clocks = iter((0.0, 31.0))

    _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path)
    monkeypatch.setattr(smoke.os, "name", "nt")
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "C:/node.exe")
    monkeypatch.setattr(smoke.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(clocks))

    with pytest.raises(RuntimeError, match="readiness timed out"):
        smoke.start_vite(tmp_path / "vite.log")

    assert process.waited
    assert process.terminated
    assert calls == []


def test_browser_smoke_records_the_dirty_candidate_without_writing_the_worktree_index(monkeypatch, tmp_path):
    smoke = _load_smoke_module()
    captured: list[object] = []
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    source = tmp_path / "frontend/src"
    source.mkdir(parents=True)
    (source / "tracked.ts").write_text("staged candidate", encoding="utf-8")
    untracked = source / "new.ts"
    untracked.write_text("new candidate", encoding="utf-8")

    def fake_check_output(command, **kwargs):
        captured.append(command)
        if command == ["git", "rev-parse", "HEAD"]:
            return "abc123\n"
        if command == ["git", "diff", "HEAD", "--no-ext-diff", "--binary"]:
            return b"diff --git a/a b/a\n"
        if command[:4] == ["git", "ls-files", "-z", "--cached"]:
            return b"frontend/src/tracked.ts\0frontend/src/new.ts\0frontend/src/deleted.ts\0"
        raise AssertionError(command)

    monkeypatch.setattr(smoke.subprocess, "check_output", fake_check_output)
    before = smoke.source_revision()
    assert before["base_commit"] == "abc123"
    assert before["worktree_dirty"] is True
    assert before["worktree_diff_sha256"] == "9e3e63fac9c92100f0f15e616e1abf395028edc8912bebfc42044c65eb17e114"
    assert set(before["files"]) == {"frontend/src/tracked.ts", "frontend/src/new.ts", "frontend/src/deleted.ts"}
    assert before["files"]["frontend/src/deleted.ts"] is None
    untracked.write_text("changed during run", encoding="utf-8")
    assert smoke.source_revision()["source_tree_sha256"] != before["source_tree_sha256"]
    assert all(command[1] in {"rev-parse", "diff", "ls-files"} for command in captured)



def test_the_viewport_matrix_covers_the_stylesheets_own_breakpoints():
    """The matrix must render both sides of every width the shell actually branches on.

    The phone end was retired by owner decision on 2026-10-07, so this no longer asks for a
    sub-600 viewport. It asks for the stronger thing instead: that no phone block survived the
    retirement, and that each remaining breakpoint has a matrix entry on both sides of it.
    """
    import re

    root = Path(__file__).resolve().parents[1]
    smoke = (root / "scripts" / "a0_browser_smoke.py").read_text(encoding="utf-8")
    styles = "".join((root / "frontend" / "src" / "design-system" / name).read_text(encoding="utf-8")
                     for name in ("tokens.css", "themes.css"))

    entries = re.findall(r"\(\"[^\"]+\", (\d+), \d+, [\d.]+\)", smoke)
    assert entries, "the desktop viewport matrix could not be read"
    widths = [int(value) for value in entries]

    # Only what a @media condition branches on; a plain `max-width: 120px` declaration on an
    # element is a size, not a breakpoint, and the first draft of this check confused the two.
    breakpoints = sorted({int(value) for value in re.findall(r"@media[^{]*max-width: (\d+)px", styles)})
    assert breakpoints, "the stylesheet declares no width breakpoint at all"
    for limit in breakpoints:
        assert any(width <= limit for width in widths), (limit, widths)
        assert any(width > limit for width in widths), (limit, widths)

    assert not re.search(r"@media \(max-width: \d+px\) \{[^@]*?\.context-subnav \{\s*display: none;", styles, re.S), \
        "a phone block that hides the context strip came back after the owner retired that end"
    # A conditional branch is legitimate (the reading-column floor uses one); a branch at phone
    # width is not, because that end was retired.
    branches = [int(value) for value in re.findall(r"if width <= (\d+):", smoke)]
    assert all(branch > 600 for branch in branches), branches

    # Exercise the actual gate, including the independent short-window branch.
    # Every declaration retains a 280px reading floor, including short and wide views.
    gate = _load_smoke_module()
    bands = {"navigation_trigger": 'button[aria-label="打开产品导航"]'}
    for width, height, _historical_compact in ((1200, 761, True), (1201, 760, True),
                                    (640, 480, True), (1201, 761, False)):
        geometry = {
            "scrollWidth": width, "clientWidth": width,
            "dock": {"y": 120, "bottom": 140}, "rail": None,
            "main": {"x": 0, "right": 280, "bottom": 120, "width": 280, "height": 120},
            "body": {"x": 0, "right": 280, "width": 280}, "inspector": 0,
            "bodyPadding": {"left": 0, "right": 0, "top": 0, "bottom": 0, "gap": 0},
            "applicationMenu": {"y": 0, "bottom": 42},
            "applicationDock": {"y": 150, "bottom": 200},
            "devicePixelRatio": 1, "statusBarOverlaps": [], "missingBands": [],
            "landmarkCount": len(bands), "expectedBands": sorted(bands),
            "landmarkOverlaps": [], "clippedBands": [], "unreachableBands": [],
            "unscrollableBands": [], "escapedChildren": [], "motionFast": "0ms",
        }
        assert gate.check_geometry(geometry, width=width, height=height, scale=1, bands=bands) is geometry
        geometry["main"]["width"] = geometry["body"]["width"] = 279
        geometry["main"]["right"] = geometry["body"]["right"] = 279
        with pytest.raises(AssertionError):
            gate.check_geometry(geometry, width=width, height=height, scale=1, bands=bands)


@pytest.mark.parametrize("containing_block", [False, True])
def test_visible_fixed_menu_escapes_only_ordinary_clip_ancestors(containing_block):
    smoke = _load_smoke_module()
    with smoke.sync_playwright() as playwright:
        options = {"headless": True}
        if sys.platform == 'win32':
            options['executable_path'] = smoke._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
            assert options['executable_path']
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": 800, "height": 600})
            transform = "transform:translateZ(0);" if containing_block else ""
            page.set_content(f"""<style>body{{margin:0}} nav{{height:42px;width:250px;overflow:auto;{transform}}}
                .popup{{position:fixed;top:60px;left:20px}}button{{height:38px;width:180px}}</style>
                <nav><section class="popup"><button>固定菜单操作</button></section></nav>""")
            box = smoke.visible_control_box(page.get_by_role('button'))
            assert box['reachable'] is not containing_block, box
            assert (box['height'] >= 24) is not containing_block, box
        finally:
            browser.close()


def test_visible_control_box_counts_paint_containment_even_with_visible_overflow():
    smoke = _load_smoke_module()
    with smoke.sync_playwright() as playwright:
        options = {"headless": True}
        if sys.platform == 'win32':
            options['executable_path'] = smoke._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
            assert options['executable_path']
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": 800, "height": 600})
            page.set_content("""<style>body{margin:0}nav{height:42px;width:250px;contain:paint;overflow:visible}
              .popup{position:fixed;top:20px;left:20px}button{height:38px;width:180px}</style>
              <nav><section class="popup"><button>部分裁剪菜单</button></section></nav>""")
            box = smoke.visible_control_box(page.get_by_role('button'))
            assert box['rawHeight'] == 38 and box['height'] == 22, box
            assert box['reachable'] is True, box  # Center hit alone must not qualify a 24px target.
        finally:
            browser.close()
