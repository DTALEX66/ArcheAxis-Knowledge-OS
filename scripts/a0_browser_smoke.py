#!/usr/bin/env python3
"""Real-browser geometry and theme gate for the formal Tauri/React desktop UI (SUP-022).

This proves the rendered shell in Chromium at desktop viewports; it does not prove the
installed WebView2 host, physical IME, or Owner acceptance, which stay separate Q14 tiers.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import Route, sync_playwright

from browser_color import composite

ROOT = Path(__file__).resolve().parents[1]


def _recorded(path: Path) -> str:
    """A printable location for an artefact, without assuming where the run root is.

    `relative_to` raises when the artefact sits outside the repository, which is the normal
    case for a linked worktree whose run root the launcher places in the shared
    `.project-local`; a recorded path must never be able to fail a passing gate.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

RUN_ROOT = Path(os.environ.get("ARCHEAXIS_RUN_ROOT", ROOT / ".project-local" / "task-runtime"))
RUNTIME = RUN_ROOT / ("runtime" if os.environ.get("ARCHEAXIS_RUN_ROOT") else "")
ARTIFACTS = (RUN_ROOT / "artifacts" / "browser-smoke") if os.environ.get("ARCHEAXIS_RUN_ROOT") else (RUN_ROOT / "browser-smoke")
def browser_smoke_port() -> int:
    """Allocate an ephemeral loopback port so parallel/retry runs cannot collide."""
    configured = os.environ.get("ARCHEAXIS_BROWSER_SMOKE_PORT")
    if configured:
        return int(configured)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


PORT = browser_smoke_port()
URL = f"http://127.0.0.1:{PORT}"
API_PREFIX = "/" + "api"
WORKSPACE_PREFIX = "/" + "workspace"

# The owner scoped the formal UI to the desktop host on 2026-10-07 and retired the phone
# end, so this matrix is Windows desktop resolutions plus the CSS viewports that
# 125/150/200% display scaling leaves behind them (physical pixels / scale).
DESKTOP_MATRIX: tuple[tuple[str, int, int, float], ...] = (
    ("1920x1080@100", 1920, 1080, 1.0),
    ("2560x1440@100", 2560, 1440, 1.0),
    ("1440x1000@100", 1440, 1000, 1.0),
    ("1280x800@100", 1280, 800, 1.0),
    ("1024x768@100", 1024, 768, 1.0),
    # Retain the inherited 900/840 content-layout boundaries; chrome now also compacts
    # at <=1100 CSS width or <=760 CSS height, covered by 1024/1280@150/960@200.
    ("900x800@100", 900, 800, 1.0),
    ("840x800@100", 840, 800, 1.0),
    # 760 and 640 are inside the shell's supported range; 640x480 is the exact floor the
    # window now refuses to go below, so the gate measures the boundary rather than a
    # fictional one. Measured before the minimum was declared: 640 renders clean, 520 pushes
    # 120px of the reading column outside the viewport.
    ("760x800@100", 760, 800, 1.0),
    ("640x800@100", 640, 800, 1.0),
    ("640x480@100", 640, 480, 1.0),
    ("1920x1080@125", 1536, 864, 1.25),
    ("1920x1080@150", 1280, 720, 1.5),
    ("1920x1080@200", 960, 540, 2.0),
)
AAOS_THEME_IDS = ("blueprint", "blueprint-light", "black", "white", "cosmic")
BRAND_THEME_ASSETS = {"blueprint":"cosmic", "blueprint-light":"white", "black":"black", "white":"white", "cosmic":"cosmic"}

# The landmark bands the non-stacking check must find, declared per surface instead of discovered
# from whatever the page happened to mount: an overlap check over a silently-shrinking landmark set
# still "passes", so an absent band is a finding rather than a skipped pair. `templates` belongs to
# the canonical library surface, and `SpaceView` mounts the canonical spaces only when
# `window.__TAURI__` exists - so the browser-fallback sweep must not be required to find it, and the
# host sweep must not be allowed to stop looking for it either.
CHROME_BANDS: dict[str, str] = {
    "top_navigation": ".top-nav-bar",
    "status": ".status-bar",
    "rail": ".space-rail",
    "context": ".context-subnav",
    "center": ".app-center",
    "dock": ".activity-dock",
}
LIBRARY_BANDS: dict[str, str] = {**CHROME_BANDS, "templates": "details.template-launcher"}
# The 学科模板 workspace is the widest component on this product entry, so it is measured at every
# narrow size the window will actually render down to its declared 640x480 floor.
LIBRARY_GEOMETRY_VIEWPORTS = ("900x800@100", "840x800@100", "760x800@100", "640x800@100", "640x480@100")


def compact_chrome(viewport: tuple[str, int, int, float]) -> bool:
    """CSS-space policy; DPR alone does not select a different layout."""
    return viewport[1] <= 1100 or viewport[2] <= 760


def console_dimensions(page) -> tuple[float, float]:
    """Use declared console geometry, never infer expected navigation from missing nodes."""
    box = page.locator(".console-window").bounding_box()
    if box is None:
        box = page.locator(".app-shell").bounding_box()
    assert box and box["width"] > 0 and box["height"] > 0, "missing console dimensions"
    return box["width"], box["height"]


def console_viewport(page) -> tuple[str, float, float, float]:
    width, height = console_dimensions(page)
    return "console", width, height, 1


def check_brand_identity(page, theme: str, viewport) -> dict[str, object]:
    """The top mark is required at every density; duplicate status branding has an explicit state."""
    compact = compact_chrome(console_viewport(page))
    asset_theme = BRAND_THEME_ASSETS[theme]
    expected = png_size(BRAND_ASSET_DIR / f"aaos-brand-mark-{asset_theme}.png")
    result = {}
    for key, selector in (("top_mark", ".top-nav-logo"), ("status_mark", ".status-bar-brand img")):
        node = page.locator(selector)
        assert node.count() == 1, (selector, node.count())
        mark = node.evaluate("""img => {
          const r=img.getBoundingClientRect(), style=getComputedStyle(img);
          return {src:img.getAttribute('src'),decoded:[img.naturalWidth,img.naturalHeight],
            attributes:[img.width,img.height],complete:img.complete,visible:img.checkVisibility(),
            box:[+r.width.toFixed(1),+r.height.toFixed(1)],objectFit:style.objectFit,glow:style.filter,
            token:getComputedStyle(document.documentElement).getPropertyValue('--ax-brand-glow').trim()};
        }""")
        assert mark['complete'] and tuple(mark['decoded']) == expected, (selector, theme, mark, expected)
        assert asset_theme in (mark['src'] or ''), (selector, theme, mark)
        if key == 'top_mark':
            size = 28 if compact else 32
            assert mark['visible'] and mark['box'] == [size, size], (viewport, mark)
            assert mark['objectFit'] == 'contain', mark
            target = visible_control_box(node)
            assert target['reachable'] and target['width'] == size and target['height'] == size, target
            mark['target'] = target
        else:
            assert mark['visible'] == (not compact), (viewport, mark)
            if compact:
                assert mark['box'] == [0, 0], mark
            else:
                assert mark['box'][0] == 38.0, mark
                assert abs(mark['box'][0] / mark['box'][1] - expected[0] / expected[1]) < 0.02, mark
                assert 20 <= mark['box'][1] <= 40, mark
                assert mark['glow'].startswith('drop-shadow') and mark['token'], mark
        result[key] = mark
    return result


def navigate_ui_page(page, page_id: str) -> None:
    trigger = page.get_by_role("button", name="打开产品导航")
    if trigger.is_visible():
        trigger.click()
        drawer = page.get_by_role("dialog", name="产品导航")
        drawer.wait_for()
        drawer.locator(f'[data-page-id="{page_id}"]').click()
        drawer.wait_for(state="detached")
    else:
        page.locator(f'.navigation-sidebar [data-page-id="{page_id}"]').click()


def select_ui_theme(page, theme: str) -> None:
    """Use the visible settings disclosure when the home page owns the picker."""
    picker = page.get_by_label("界面主题")
    opened = not picker.is_visible()
    summary = page.get_by_label("界面设置", exact=True)
    if opened:
        summary.click()
    try:
        picker.select_option(theme)
        page.wait_for_function("theme => document.documentElement.dataset.aaosTheme === theme", arg=theme)
    finally:
        if opened:
            summary.click()


def chrome_bands(page, *, library: bool = False) -> dict[str, str]:
    # Expected structure is declared by actual console size and surface, never by missing nodes.
    width, height = console_dimensions(page)
    bands = {"top_navigation":".top-nav-bar", "status":".status-bar", "center":".app-center", "dock":".activity-dock"}
    narrow = (compact_chrome(("console", width, height, 1))
              or (page.locator(".cabin-shell").get_attribute("data-navigation-appearance") == "top"
                  and width <= 1200))
    if narrow:
        assert not page.locator(".navigation-sidebar").is_visible(), "narrow sidebar consumes reading space"
        assert page.get_by_role("button", name="打开产品导航").is_visible(), "narrow navigation cannot be opened"
        bands["navigation_trigger"] = ".ui-navigation-trigger"
    else:
        bands["rail"] = ".space-rail"
        if library:
            bands["context"] = ".context-subnav"
    return bands


def library_bands(page) -> dict[str, str]:
    return {**chrome_bands(page, library=True), "templates":"details.template-launcher"}


def check_navigation_drawer(page) -> dict[str, object]:
    trigger = page.get_by_role("button", name="打开产品导航")
    if not trigger.is_visible():
        return {"state":"desktop-sidebar", "drawer_required":False}
    trigger.click()
    drawer = page.get_by_role("dialog", name="产品导航")
    drawer.wait_for()
    # Oct09 layout exposes five daily entry groups and two fixed entries;
    # child pages belong to their active group, rather than a flat 22-item rail.
    expected = {"01", "02", "06", "13", "15", "17", "19"}
    actual = drawer.locator('[data-page-id]').evaluate_all(
        '(nodes) => nodes.map(node => node.dataset.pageId)')
    assert len(actual) == len(expected) and set(actual) == expected, actual
    assert page.evaluate("() => !!document.activeElement?.closest('[role=dialog]')"), "drawer autofocus escaped"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("() => !!document.activeElement?.closest('[role=dialog]')"), "drawer keyboard focus escaped"
    page.keyboard.press("Escape")
    drawer.wait_for(state="detached")
    page.wait_for_timeout(150)
    assert trigger.evaluate("node => document.activeElement === node"), "drawer did not restore trigger focus"
    return {"state":"PASS", "drawer_required":True, "primary_entry_count":len(expected), "focus_trapped":True}

BRAND_ASSET_DIR = ROOT / "frontend" / "src" / "assets"


def png_size(path: Path) -> tuple[int, int]:
    """The canvas an asset was cut at, read from its own IHDR.

    The browser-side brand assertions compare against this rather than a number written into the
    gate, so re-cutting the artwork at a new size moves the expectation with it - and a mismatch
    between the file and what the page decoded is still a red.
    """
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", f"not a PNG: {path}"
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")

HANDSHAKE = {
    "product_id": "archeaxis-workspace",
    "product_name": "ArcheAxis Knowledge",
    "api_contract": "1.x",
    "backend_version": "browser-smoke",
    "source_commit": os.environ.get("GITHUB_SHA", "worktree"),
    "schema_version": 15,
    "runtime_mode": "browser-smoke",
    "workspace_id": "browser-smoke",
    "capabilities": [],
    "migration_state": "ready",
}


def api_payload(url: str) -> dict[str, object]:
    path = urlsplit(url).path
    if path == f"{API_PREFIX}/v1/system/handshake":
        return HANDSHAKE
    if path == f"{WORKSPACE_PREFIX}/api/v1/home":
        return {
            "release": {"version": "candidate", "status": "candidate", "public": False},
            "counts": {"research": {"candidate": 0}, "jobs": {"succeeded": 0}},
            "components": {"api": "available", "database": "available"},
            "capabilities": {"local_url_file_github_intake": "available"},
            "recent_activity": [],
        }
    if path == f"{WORKSPACE_PREFIX}/api/v1/activity":
        return {"items": [], "next_cursor": None}
    if path == f"{WORKSPACE_PREFIX}/api/delivery":
        return {"summary": {"jobs": 0, "outbox": {}, "receipts": {}}}
    if path == f"{WORKSPACE_PREFIX}/api/library":
        return {"items": []}
    if path == f"{WORKSPACE_PREFIX}/api/evidence/anchors":
        return {"count": 0, "items": [], "next_cursor": None}
    if path == f"{WORKSPACE_PREFIX}/api/evidence/bundles":
        return {"items": []}
    if path == f"{WORKSPACE_PREFIX}/api/research":
        return {"items": []}
    if path in {
        f"{WORKSPACE_PREFIX}/api/runtime/knowledge",
        f"{WORKSPACE_PREFIX}/api/runtime/candidates",
    }:
        return {"items": []}
    if path == f"{API_PREFIX}/v1/setup/status":
        return {
            "schema_version": "v1",
            "ready": True,
            "workspace_id": "browser-smoke",
            "workspace_root": "browser-smoke",
            "steps": [{"id": "paths_writable", "state": "ready", "message": "ready", "action_hint": ""}],
        }
    if path == f"{API_PREFIX}/v1/learning/review-queue":
        return {"due_count": 0, "due": []}
    if path == f"{WORKSPACE_PREFIX}/api/status":
        return {
            "schema_version": "v1",
            "observed_at": "2026-08-29T00:00:00Z",
            "release": {"version": "candidate", "status": "candidate", "public": False},
            "components": {},
            "migrations": {},
            "counts": {},
            "capabilities": {},
        }
    return {}


def _declared_tool(resource_id="ext.toolchains.nodejs-lts", name="nodejs-lts") -> str | None:
    """Resolve Node through the project's declared resource index, not an ambient PATH.

    This gate used to need `node` already on PATH, so it died with "Vite requires Node" on a
    host where the sanctioned interpreter exists only under the registered external root -
    the result depended on which shell or agent launched it.
    """
    index = ROOT / "config" / "environment" / "external-resources-index.json"
    if not index.is_file():
        return None
    try:
        document = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    def walk(node: object):
        if isinstance(node, dict):
            if node.get("resource_id") == resource_id or node.get("name") == name:
                yield node
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)

    for row in walk(document):
        candidates = [row.get("resolved_absolute")]
        candidates += [
            entry.get("resolved")
            for entry in row.get("external_paths", [])
            if isinstance(entry, dict)
        ]
        for candidate in candidates:
            if candidate and Path(candidate).drive.upper() in {"E:","F:"}:
                raise RuntimeError("declared tool is on a protected drive")
            if candidate and Path(candidate).is_file():
                return str(candidate)
    return None

def _declared_node() -> str | None:
    return _declared_tool()


def start_vite(log_path: Path) -> tuple[subprocess.Popen[bytes], object]:
    log = log_path.open("wb")
    if os.name == "nt":
        from_path = shutil.which("node")
        node = from_path or _declared_node()
        vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        if not node or not vite.is_file():
            log.close()
            consulted = [
                "PATH" if not from_path else None,
                "config/environment/external-resources-index.json (ext.toolchains.nodejs-lts)",
            ]
            raise RuntimeError(
                "Vite needs Node and frontend/node_modules/vite/bin/vite.js; resolved no Node from "
                + ", ".join(item for item in consulted if item)
                + f"; vite present: {vite.is_file()}"
            )
        # Running Vite through cmd/npm can orphan the actual Node server when
        # cmd.exe exits. Start the server process itself so taskkill /T can
        # deterministically reclaim the smoke-run process tree.
        command = [node, str(vite), "--host", "127.0.0.1", "--port", str(PORT)]
        cwd = ROOT / "frontend"
    else:
        command = [
            "npm", "--prefix", "frontend", "run", "dev", "--",
            "--host", "127.0.0.1", "--port", str(PORT),
        ]
        cwd = ROOT
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log.flush()
            stop_vite(process, log)
            raise RuntimeError(f"Vite exited before readiness; inspect {log_path}")
        try:
            with urlopen(URL, timeout=1) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return process, log
        except OSError:
            time.sleep(0.2)
    stop_vite(process, log)
    raise RuntimeError(f"Vite readiness timed out; inspect {log_path}")


def stop_vite(process: subprocess.Popen[bytes], log: object) -> None:
    if os.name == "nt":
        # The smoke runner starts Vite's Node process directly.  Prefer its
        # handle over taskkill, which can be blocked by an execution sandbox.
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            process.wait(timeout=5)
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    log.close()


def source_revision() -> dict[str, object]:
    """Identify the tested tree without writing the Git index."""
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    diff = subprocess.check_output(
        ["git", "diff", "--no-ext-diff", "--binary"], cwd=ROOT
    )
    return {
        "base_commit": base_commit,
        "worktree_dirty": bool(diff),
        "worktree_diff_sha256": sha256(diff).hexdigest() if diff else None,
    }



HOST_BRIDGE_STUB_TEMPLATE = """
(() => {
  // Enough of a Tauri host for the formal surfaces to mount. The app decides it is on the desktop
  // host by the presence of `window.__TAURI__.core.invoke`, and the recovery contract decides
  // whether it shows the shell or the recovery screen; nothing here claims to be the native host.
  const bodies = {
    sources_list: { sources: __A0_SOURCES__ },
    documents_list: { documents: __A0_DOCUMENTS__, next_cursor: null, snapshot_count: __A0_DOCUMENTS__.length },
    learning_items: { items: [], count: 0 },
    capabilities_list: { capabilities: [] },
    anchors_list: { anchors: [] },
    source_original: __A0_ORIGINAL__,
    workspace_backups: { backups: [] },
    system_version: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 1,
                      sqlite_version: "3.51.3" },
  };
  // A declared outage, not a silent one: the named operations answer with this status so the gate
  // can read what the surface claims when a Core read cannot be finished.
  const faults = __A0_FAULTS__;
  __A0_STATEFUL_DOCUMENTS__
  // Explicit SIMULATED journal: new desktop startup must read a valid Core
  // working-state contract. An absent fixture is not a product persistence ACK.
  const copyJournal=value=>JSON.parse(JSON.stringify(value));
  const emptyJournal=()=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
  let journal={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,
    state:emptyJournal(),draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  async function journalHash(value) {
    const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value));
    return [...new Uint8Array(hash)].map(n=>n.toString(16).padStart(2,"0")).join("");
  }
  async function journalFixture(operation,payload) {
    if(operation==="ui_state_read")return {status:200,body:copyJournal(journal)};
    if(!["ui_state_write","ui_state_clear_saved","ui_state_recover"].includes(operation))return null;
    const body=payload.body;
    if(!body||body.workspace_id!==journal.workspace_id||body.restore_epoch!==journal.restore_epoch||body.state_revision!==journal.state_revision)
      return {status:409,body:{error:"UI_STATE_CONFLICT",workspace_id:journal.workspace_id,restore_epoch:journal.restore_epoch,state_revision:journal.state_revision}};
    if(operation==="ui_state_recover")return {status:409,body:{error:"NO_SIMULATED_RECOVERY_CANDIDATE"}};
    let state;
    if(operation==="ui_state_write") {
      state=copyJournal(body.state);
      if(journal.state.pending_original&&state.pending_original&&JSON.stringify(journal.state.pending_original)!==JSON.stringify(state.pending_original))return {status:422,body:{error:"FROZEN_ORIGINAL_CHANGED"}};
    } else {
      const draft=journal.state.drafts[body.document_id];
      const saved=window.__A0_DOCUMENT_FIXTURE__?.snapshot().find(doc=>doc.document_id===body.document_id);
      if(!draft||!saved||draft.base_version!==body.base_version||body.saved_version!==body.base_version+1||saved.version!==body.saved_version
        ||journal.draft_digests[body.document_id]!==body.content_sha256||JSON.stringify(saved.editor_json)!==JSON.stringify(draft.editor_json))return {status:409,body:{error:"SIMULATED_CLEAR_REFUSED"}};
      state=copyJournal(journal.state);delete state.drafts[body.document_id];
    }
    const digests={};for(const [id,draft] of Object.entries(state.drafts))digests[id]=await journalHash(JSON.stringify(draft.editor_json));
    journal={...journal,state_revision:journal.state_revision+1,state,draft_digests:digests,
      pending_document_id:state.pending_original?"doc_req_"+await journalHash(state.pending_original.create_request_id):null};
    return {status:200,body:copyJournal(journal)};
  }
  window.__TAURI__ = {
    core: {
      invoke: async (command, request) => {
        if (command === "recovery_status") {
          return { state: "ready", safe_mode: false, backend_available: true,
                   message: "browser smoke host", backups: [], external_dev: false };
        }
        if (command === "core_command") {
          const operation = request?.request?.operation;
          if (Object.prototype.hasOwnProperty.call(faults, operation)) {
            return { status: faults[operation], body: {} };
          }
          const journalAnswer=await journalFixture(operation,request?.request?.payload??{});
          if(journalAnswer)return journalAnswer;
          if(operation==="source_jobs") {
            const sourceId=request?.request?.payload?.source_id;
            return bodies.sources_list.sources.some(source=>source.source_id===sourceId)
              ? {status:200,body:{source_id:sourceId,jobs:[],jobs_capped:false}}
              : {status:404,body:{error:"SOURCE_NOT_FOUND"}};
          }
          if (documentFixture) {
            const answer = await documentFixture(operation, request?.request?.payload ?? {});
            if (answer) return answer;
          }
          return { status: 200, body: bodies[operation] ?? {} };
        }
        return null;
      },
    },
  };
})();
"""

# The page re-hashes the returned bytes and refuses to open an original whose digest differs,
# so the fixture digest has to be the real one rather than a plausible-looking string.
A0_ORIGINAL_CONTENT = "YTAg6Zeo56aB5qC35p2/5Y6f5Lu277ya5LuF5L6b5a6/5Li75Zue6K+75a+86Iiq5bGC57qn5L2/55So"
A0_SOURCE = {
    "source_id": "src_a0_nav3",
    "source_revision": "sha256:de81c167a8e05757e6fba2e6",
    "sha256": "de81c167a8e05757e6fba2e6123703873fb3d4219cb3a3ef01b55af7cbfb471e",
    "original_name": "a0-nav3-sample.txt",
    "imported_at": "2026-10-08T00:00:00Z",
}
# One saved document, so `documents_list` answers non-empty while `document_get` is out of reach:
# the shape of a partial Core outage, which is the case a template list must not paper over.
A0_DOCUMENT_SUMMARY = {
    "document_id": "doc_a0_unreadable",
    "source_id": None,
    "source_revision": None,
    "title": "a0 读取失败样本",
    "version": 1,
    "content_sha256": A0_SOURCE["sha256"],
}


A0_STATEFUL_DOCUMENTS = r"""
  const current = new Map(), history = new Map(), calls = [];
  const copy = value => structuredClone(value);
  const text = node => node.text ?? (node.content ?? []).map(text).join("\n");
  async function makeDocument(id, title, editor, version) {
    editor = copy(editor);
    editor.content.forEach((node, ordinal) => {node.attrs = {...node.attrs, block_id:node.attrs?.block_id ?? `a0_p${ordinal + 1}`};});
    const projection = text(editor);
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(editor)));
    return {document_id:id,source_id:null,source_revision:null,title,version,editor_json:copy(editor),
      text_projection:projection,content_sha256:[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,"0")).join(""),blocks:editor.content.map((node,ordinal)=>({block_id:node.attrs.block_id,kind:node.type,ordinal,node_json:copy(node),text_projection:text(node),codec_status:"known"}))};
  }
  function retain(doc) { current.set(doc.document_id,copy(doc)); history.set(`${doc.document_id}:${doc.version}`,copy(doc)); }
  const ready = Promise.all([1,2,3].map(async n => retain(await makeDocument(`a0_target_${n}`,
    `引用目标 ${n} · 独立历史正文`,{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:`绑定历史正文 ${n} v1`}]}]},1))));
  window.__A0_DOCUMENT_FIXTURE__ = {calls, snapshot:()=>copy([...current.values()]), advance:async()=>{
    await ready;
    for (const n of [1,2,3]) retain(await makeDocument(`a0_target_${n}`,`引用目标 ${n} · 独立历史正文`,
      {type:"doc",content:[{type:"paragraph",content:[{type:"text",text:`当前新正文 ${n} v2`}]}]},2));
  }};
  const documentFixture = async (operation,payload) => {
    await ready; calls.push({operation,payload:copy(payload)});
    if (operation === "documents_list") return {status:200,body:{documents:[...current.values()].map(d=>({
      document_id:d.document_id,source_id:d.source_id,source_revision:d.source_revision,title:d.title,version:d.version,content_sha256:d.content_sha256})),next_cursor:null,snapshot_count:current.size}};
    if (operation === "document_create") {
      const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(payload.body.create_request_id));
      const id="doc_req_"+[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,"0")).join("");
      if(current.has(id)) return {status:201,body:copy(current.get(id))};
      const doc=await makeDocument(id,payload.body.title,payload.body.editor_json,1); retain(doc);
      return {status:201,body:copy(doc)};
    }
    if (operation === "document_draft") {
      const prior=current.get(payload.document_id);
      if (!prior) return {status:404,body:{}};
      if (prior.version !== payload.body.expected_version) return {status:409,body:{}};
      const doc=await makeDocument(prior.document_id,prior.title,payload.body.editor_json,prior.version+1); retain(doc);
      return {status:200,body:copy(doc)};
    }
    if (operation === "document_get" || operation === "document_version") {
      const doc=operation === "document_get" ? current.get(payload.document_id) : history.get(`${payload.document_id}:${payload.version}`);
      return doc ? {status:200,body:copy(doc)} : {status:404,body:{}};
    }
    return null;
  };
"""


def host_bridge_stub(
    *,
    documents: list[dict[str, object]] | None = None,
    failing_operations: dict[str, int] | None = None,
    stateful_documents: bool = False,
) -> str:
    import json

    return (
        HOST_BRIDGE_STUB_TEMPLATE.replace("__A0_SOURCES__", json.dumps([A0_SOURCE]))
        .replace("__A0_DOCUMENTS__", json.dumps(documents if documents is not None else []))
        .replace("__A0_FAULTS__", json.dumps(failing_operations or {}))
        .replace("__A0_STATEFUL_DOCUMENTS__", A0_STATEFUL_DOCUMENTS if stateful_documents else "const documentFixture = null;")
        .replace("__A0_ORIGINAL__", json.dumps({
            "source_id": A0_SOURCE["source_id"],
            "name": A0_SOURCE["original_name"],
            "media_type": "text/plain",
            "sha256": A0_SOURCE["sha256"],
            "content_base64": A0_ORIGINAL_CONTENT,
        }))
    )


TEMPLATE_SUMMARY_TEXT = "学科模板 · 知识网络 / 研究与项目 / 学习与实践"
TEMPLATE_SECTION_SELECTOR = "section[aria-label='学科模板工作区']"
LIVE_REGION_SELECTOR = (
    '[role="status"],[role="alert"],[role="log"],[role="timer"],[role="marquee"],'
    '[aria-live]:not([aria-live="off"])'
)
# Retain both inherited narrow content-layout samples for template disclosure reachability.
TEMPLATE_NARROW_VIEWPORTS = ("900x800@100", "840x800@100")


def template_catalog() -> tuple[list[str], list[str]]:
    """The discipline and template labels the page renders, read from the source it renders from.

    The gate must not pin 28: pinning the number keeps the gate green when a discipline is added
    to `disciplines.ts` and the `<select>` silently stops offering it.
    """
    source = (ROOT / "frontend" / "src" / "templates" / "disciplines.ts").read_text(encoding="utf-8")
    disciplines_block = source.split("export const DISCIPLINES", 1)[1].split("];", 1)[0]
    templates_block = source.split("export const TEMPLATES", 1)[1].split("] as const", 1)[0]

    def labels(block: str) -> list[str]:
        return re.findall(r'\{id:"[^"]+",name:"([^"]+)"', block)

    disciplines, templates = labels(disciplines_block), labels(templates_block)
    assert len(disciplines) == disciplines_block.count('{id:"'), (len(disciplines), disciplines_block.count('{id:"'))
    assert len(templates) == templates_block.count('{id:"'), (len(templates), templates_block.count('{id:"'))
    assert disciplines and templates, (disciplines, templates)
    return disciplines, templates


def live_region_texts(page, scope: str = "") -> list[str]:
    """Every region assistive tech would treat as live, optionally only those inside `scope`."""
    return page.evaluate(
        """({selector, scope}) => [...document.querySelectorAll(selector)]
          .filter((node) => !scope || Boolean(node.closest(scope)))
          .map((node) => node.textContent.trim())""",
        {"selector": LIVE_REGION_SELECTOR, "scope": scope},
    )



def read_navigation_levels(page) -> dict[str, object]:
    """UI-02 in a real layout engine: primary labels, secondary groups, tertiary object path."""
    # The icon span sits in the same button; only the label span carries text. Selecting the
    # label explicitly is what the requirement is about: a primary entry the user can read.
    labels = page.evaluate(
        """() => [...document.querySelectorAll("[data-page-id]")]
          .map((node) => ({ text: node.textContent.trim(), width: node.getBoundingClientRect().width }))"""
    )
    assert labels and all(entry["width"] > 8 for entry in labels), labels
    assert len(labels) == 10, labels  # seven primary entries + three knowledge children
    assert [entry["text"] for entry in labels][:5] == ["工作台", "知识", "学习", "AI", "资源"], labels
    assert {entry["text"] for entry in labels[5:]} == {
        "阅读与编辑", "双链与图谱", "研究空间", "全部能力", "设置"}, labels

    sections = page.locator("ul[aria-label='资料库对象导航'] button")
    section_count = sections.count()
    assert section_count == 4, section_count
    widths = [sections.nth(index).bounding_box()["width"] for index in range(section_count)]
    assert all(width > 60 for width in widths), widths

    sections.filter(has_text="来源锚点").first.click()
    focused = page.evaluate("() => document.activeElement?.dataset?.section ?? null")
    assert focused == "anchors", focused

    source_button = page.locator("nav[aria-label='保留原件']").get_by_role(
        "button", name=A0_SOURCE["original_name"], exact=True)
    source_button.click()
    # The ordinary trail carries the source's display name and saved-version state.
    # Read the immutable identity through the actual diagnostics action instead.
    receipt_button = page.get_by_role("button", name="查看原始回执（诊断）：原件与来源详细信息", exact=True)
    receipt_button.wait_for()
    page.locator("nav[aria-label='对象导航路径']").wait_for()
    trail = page.inner_text("nav[aria-label='对象导航路径']")
    assert A0_SOURCE["original_name"] in trail and "来源原件" in trail and "已保存原件" in trail, trail
    assert A0_SOURCE["source_id"] not in trail and A0_SOURCE["source_revision"] not in trail, trail
    assert source_button.get_attribute("aria-current") == "true", "source selection was not retained"
    receipt_button.click()
    diagnostic = page.get_by_role("dialog", name="运行诊断", exact=True)
    diagnostic.wait_for()
    payload = diagnostic.locator(".diagnostic-console-list details[open] pre")
    assert payload.count() == 1, "the selected source diagnostic payload is not unique"
    source_identity = json.loads(payload.inner_text())
    assert source_identity == {key: A0_SOURCE[key] for key in ("source_id", "source_revision", "sha256")}, source_identity
    diagnostic.get_by_role("button", name="关闭运行诊断", exact=True).click()
    diagnostic.wait_for(state="detached")
    assert page.inner_text("nav[aria-label='对象导航路径']") == trail, "diagnostics changed the selected source"

    page.evaluate("location.hash = 'space=learning'")
    page.get_by_role("heading", name="学习").first.wait_for()
    review = page.locator("ul[aria-label='学习对象导航'] button").filter(has_text="复习队列")
    assert review.count() == 1, review.count()
    assert review.first.bounding_box()["width"] > 40
    return {
        "primary_label_count": len(labels),
        "secondary_section_count": section_count,
        "secondary_focused_region": focused,
        "tertiary_trail_display": trail,
        "tertiary_trail_identity": source_identity["source_id"],
        "tertiary_source_diagnostic": source_identity,
        "learning_review_group_present": True,
    }


def measure_geometry(page, bands: dict[str, str]) -> dict[str, object]:
    """Measure the named landmark bands the way the engine paints them.

    Two rules, learned the hard way:

    * A band's box is not what the user sees. A tall descendant of a scroll container keeps a
      `getBoundingClientRect` that runs past the container's edge while painting nothing there, so
      comparing raw boxes reports "stacking" for ordinary scrolling. Each band is therefore reduced
      to its visible box by intersecting with every clipping ancestor and with the viewport, and a
      pair only counts as overlapping if those visible boxes intersect and neither paints inside
      the other's own subtree.
    * Clipped is not the same as reachable. A band that is clipped by an ancestor which cannot
      scroll is invisible with no way back, which is worse than overlap - so every clipped band is
      checked against its nearest overflowing scroll ancestor, and one that cannot be scrolled into view is
      reported separately rather than passing as "no overlap".
    """
    return page.evaluate(
        """(selectors) => {
          const VISIBLE_OVERFLOW = 'visible';
          const box = (selector) => {
            const rect = document.querySelector(selector)?.getBoundingClientRect();
            return rect && {x:rect.x,y:rect.y,width:rect.width,height:rect.height,bottom:rect.bottom};
          };
          const clipBox = (node) => {
            const rect = node.getBoundingClientRect();
            let box = {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
            // A fixed-position band is out of flow: ancestor overflow does not clip it, so
            // intersecting its ancestors would report a real painted overlap as "no overlap".
            if (getComputedStyle(node).position === 'fixed') {
              return {left: Math.max(box.left, 0), top: Math.max(box.top, 0),
                      right: Math.min(box.right, window.innerWidth),
                      bottom: Math.min(box.bottom, window.innerHeight)};
            }
            let ancestor = node.parentElement;
            while (ancestor) {
              const style = getComputedStyle(ancestor);
              if (style.overflowY !== VISIBLE_OVERFLOW || style.overflowX !== VISIBLE_OVERFLOW) {
                const outer = ancestor.getBoundingClientRect();
                box.left = Math.max(box.left, outer.left);
                box.top = Math.max(box.top, outer.top);
                box.right = Math.min(box.right, outer.right);
                box.bottom = Math.min(box.bottom, outer.bottom);
              }
              if (style.position === 'fixed') break;
              ancestor = ancestor.parentElement;
            }
            box.left = Math.max(box.left, 0);
            box.top = Math.max(box.top, 0);
            box.right = Math.min(box.right, window.innerWidth);
            box.bottom = Math.min(box.bottom, window.innerHeight);
            return box;
          };
          const scrollAncestor = (node) => {
            let ancestor = node.parentElement;
            while (ancestor) {
              const style = getComputedStyle(ancestor);
              // An unconstrained auto wrapper grows with its content. Keep looking for
              // the bounded outer scroller instead of reporting that reachable content is lost.
              if (['auto', 'scroll'].includes(style.overflowY)
                  && ancestor.scrollHeight > ancestor.clientHeight) return ancestor;
              if (['hidden', 'clip'].includes(style.overflowY)) return null;
              ancestor = ancestor.parentElement;
            }
            return null;
          };
          const context = document.querySelector('.context-subnav');
          const bar = [...(document.querySelector('.status-bar')?.children ?? [])];
          const overlaps = [];
          for (let i = 0; i < bar.length; i++) for (let j = i + 1; j < bar.length; j++) {
            const a = clipBox(bar[i]), b = clipBox(bar[j]);
            const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            if (width > 1 && height > 1) {
              overlaps.push([bar[i].className || bar[i].tagName, bar[j].className || bar[j].tagName, +width.toFixed(1)]);
            }
          }
          const bands = {};
          const missingBands = [];
          for (const [name, selector] of Object.entries(selectors)) {
            const node = document.querySelector(selector);
            if (!node || getComputedStyle(node).display === 'none') {
              missingBands.push(name);
              continue;
            }
            const rect = node.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              bands[name] = {node, rect, visible: clipBox(node)};
            } else missingBands.push(name);
          }
          const contains = (outer, inner) => inner.left >= outer.left - 1
            && inner.top >= outer.top - 1
            && inner.right <= outer.right + 1 && inner.bottom <= outer.bottom + 1;
          const landmarkOverlaps = [];
          const names = Object.keys(bands).sort();
          for (let i = 0; i < names.length; i++) for (let j = i + 1; j < names.length; j++) {
            const a = bands[names[i]], b = bands[names[j]];
            if (contains(a.visible, b.visible) || contains(b.visible, a.visible)) continue;
            const width = Math.min(a.visible.right, b.visible.right) - Math.max(a.visible.left, b.visible.left);
            const height = Math.min(a.visible.bottom, b.visible.bottom) - Math.max(a.visible.top, b.visible.top);
            if (width <= 2 || height <= 2) continue;
            // The boxes agree; record who actually paints at the crossing so a red names the
            // element to look at instead of a pair of numbers.
            const x = (Math.max(a.visible.left, b.visible.left) + Math.min(a.visible.right, b.visible.right)) / 2;
            const y = (Math.max(a.visible.top, b.visible.top) + Math.min(a.visible.bottom, b.visible.bottom)) / 2;
            const hit = document.elementFromPoint(x, y);
            landmarkOverlaps.push([names[i], names[j], +width.toFixed(1), +height.toFixed(1),
              hit ? `${hit.tagName}.${String(hit.className).slice(0, 32)}` : 'nothing']);
          }
          const clippedBands = names.filter((name) => bands[name].visible.right > window.innerWidth + 1
            || bands[name].visible.left < -1);
          const unreachableBands = [];
          for (const name of names) {
            const band = bands[name];
            const spilled = band.rect.bottom > band.visible.bottom + 1 || band.rect.right > band.visible.right + 1
              || band.rect.top < band.visible.top - 1;
            if (!spilled) continue;
            const scroller = scrollAncestor(band.node);
            if (!scroller || scroller.scrollHeight <= scroller.clientHeight) {
              unreachableBands.push([name, +band.rect.height.toFixed(1), +band.visible.bottom.toFixed(1)]);
            }
          }
          // The band box fitting its own slot says nothing about what is inside it: a landmark can
          // be the clipper, and then its own overflowing content is cut with no way back. That is
          // how a nav row ends mid-label under a dock while every rect still "fits".
          const unscrollableBands = [];
          for (const name of names) {
            const band = bands[name];
            const style = getComputedStyle(band.node);
            if (band.node.scrollHeight > band.node.clientHeight + 1
                && !['auto', 'scroll'].includes(style.overflowY)) {
              unscrollableBands.push([name, band.node.scrollHeight, band.node.clientHeight, style.overflowY]);
            }
          }
          const escapedChildren = [];
          for (const name of names) {
            const band = bands[name];
            const style = getComputedStyle(band.node);
            for (const child of band.node.children) {
              const rect = child.getBoundingClientRect();
              if (rect.width <= 0 || rect.height <= 0) continue;
              // Compare painted child boxes. A band's own scrolling can recover clipped
              // children, but visible overflow still paints over neighbouring landmarks.
              const painted = clipBox(child);
              const spillX = painted.left < band.visible.left - 1 || painted.right > band.visible.right + 1;
              const spillY = painted.top < band.visible.top - 1 || painted.bottom > band.visible.bottom + 1;
              if ((spillX && !['auto', 'scroll'].includes(style.overflowX))
                  || (spillY && !['auto', 'scroll'].includes(style.overflowY))) {
                escapedChildren.push([name, child.className || child.tagName,
                  +rect.width.toFixed(1), +rect.height.toFixed(1)]);
              }
            }
          }
          return {
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            devicePixelRatio: window.devicePixelRatio,
            console: box(document.querySelector(".console-window") ? ".console-window" : ".app-shell"),
            expectedBands: Object.keys(selectors).sort(),
            rail: box('.space-rail'),
            dock: box('.activity-dock'),
            main: box('.app-center'),
            body: box('.app-body'),
            inspector: Boolean(document.querySelector('.inspector')),
            context: Boolean(context) && getComputedStyle(context).display !== 'none',
            statusBarOverlaps: overlaps,
            landmarkOverlaps: landmarkOverlaps,
            clippedBands: clippedBands,
            missingBands: missingBands,
            unreachableBands: unreachableBands,
            unscrollableBands: unscrollableBands,
            escapedChildren: escapedChildren,
            landmarkCount: names.length,
            motionFast: getComputedStyle(document.documentElement).getPropertyValue('--ax-motion-fast').trim(),
          };
        }""",
        bands,
    )


def check_geometry(
    geometry: dict[str, object],
    *,
    width: int,
    height: int,
    scale: float,
    bands: dict[str, str],
) -> dict[str, object]:
    """Fail unless every declared band is present, none overlaps, and none escapes the viewport."""
    assert geometry["scrollWidth"] <= geometry["clientWidth"], geometry
    assert geometry["dock"]["bottom"] <= height + 0.5, geometry
    if "rail" in bands:
        assert 140 <= geometry["rail"]["width"] <= 300, geometry
        assert geometry["main"]["x"] >= geometry["rail"]["width"] - 1, geometry
    else:
        assert "navigation_trigger" in bands, "missing declared narrow navigation affordance"
        assert geometry["rail"]["width"] == 0, geometry
        assert abs(geometry["main"]["x"] - geometry["body"]["x"]) <= 1, geometry
        assert abs(geometry["main"]["width"] - geometry["body"]["width"]) <= 1, geometry
    assert geometry["main"]["bottom"] <= geometry["dock"]["y"] + 0.5, geometry
    assert not geometry["inspector"], geometry
    if "context" in bands:
        assert geometry["context"], geometry
    assert geometry["devicePixelRatio"] == scale, geometry
    assert not geometry["statusBarOverlaps"], geometry
    assert not geometry["missingBands"], geometry
    assert geometry["landmarkCount"] == len(bands), geometry
    assert geometry["expectedBands"] == sorted(bands), geometry
    assert not geometry["landmarkOverlaps"], geometry
    assert not geometry["clippedBands"], geometry
    # A band that runs past its container is only acceptable if the container can bring it back:
    # clipped-and-unreachable would pass an overlap check while showing the user nothing.
    assert not geometry["unreachableBands"], geometry
    assert not geometry["unscrollableBands"], geometry
    assert not geometry["escapedChildren"], geometry
    assert geometry["motionFast"] == "0ms", geometry
    console = geometry.get("console", {"width": width, "height": height})
    if console["width"] <= 1200 or console["height"] <= 760:
        # Compact chrome also serves short scaled desktop viewports. Keep the reading floor.
        assert geometry["main"]["width"] >= 280, geometry
    return geometry


def check_status_accessibility(page) -> dict[str, object]:
    """Rendered status text, targets and actual focus shadows, including alpha composition."""
    layout = page.evaluate("""() => {
      const bar = document.querySelector('.status-bar').getBoundingClientRect();
      const pill = document.querySelector('.status-pill');
      const rect = pill.getBoundingClientRect();
      const range = document.createRange(); range.selectNodeContents(pill);
      return {lines: new Set([...range.getClientRects()].map(r => r.top)).size,
        spillsAboveBar: Math.max(0, bar.top - rect.top),
        spillsBelowBar: Math.max(0, rect.bottom - bar.bottom),
        controls: [...document.querySelectorAll('.status-bar > button, .status-bar > .theme-picker select, .cabin-settings > summary')]
          .filter(el => el.checkVisibility())
          .map(el => { const r = el.getBoundingClientRect();
            const hit = document.elementFromPoint(r.x + r.width/2, r.y + r.height/2);
            return {label: el.getAttribute('aria-label'), width: r.width, height: r.height,
              reachable: el.contains(hit), inBar: r.left >= bar.left && r.right <= bar.right
                && r.top >= bar.top && r.bottom <= bar.bottom}; })};
    }""")
    labels = {c["label"] for c in layout["controls"]}
    assert {"打开全局命令", "界面设置"} <= labels, layout
    assert layout["lines"] == 1, layout
    assert layout["spillsAboveBar"] == layout["spillsBelowBar"] == 0, layout
    assert all(c["width"] >= 24 and c["height"] >= 24 and c["reachable"] and c["inBar"]
               for c in layout["controls"]), layout

    def contrast(a, b) -> float:
        def luminance(rgb):
            channels = [v / 255 for v in rgb]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
            return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
        levels = sorted((luminance(a), luminance(b)))
        return (levels[1] + 0.05) / (levels[0] + 0.05)

    focus = []
    page.keyboard.press("Tab")  # establish keyboard modality for :focus-visible
    controls = page.locator('.status-bar > button, .status-bar > .theme-picker select, .cabin-settings > summary')
    for index in range(controls.count()):
        control = controls.nth(index)
        if not control.is_visible():
            continue
        control.focus()
        page.wait_for_timeout(200)
        style = control.evaluate("""el => {
          const s = getComputedStyle(el);
          return {shadow: s.boxShadow, background: s.backgroundColor,
            bar: getComputedStyle(el.closest('.status-bar')).backgroundColor,
            label: el.getAttribute('aria-label'), visible: el.matches(':focus-visible')};
        }""")
        bar = composite(style["bar"], (0, 0, 0))
        background = composite(style["background"], bar)
        # Inset shadows are decorative and cannot stand in for an outer focus indicator.
        outer = re.split(r",\s*(?![^()]*\))", style["shadow"])
        colors = [re.search(r"rgba?\([^)]*\)", shadow).group(0)
                  for shadow in outer if 'inset' not in shadow and re.search(r"rgba?\([^)]*\)", shadow)]
        ratios = [contrast(composite(color, bg), bg) for color in colors for bg in (bar, background)]
        assert style["visible"] and ratios and min(ratios) >= 3, (style, ratios)
        focus.append({"label": style["label"], "worst": min(ratios), "shadow": style["shadow"]})
    page.evaluate("document.activeElement.blur()")
    return {**layout, "focus": focus}


def status_fault_selftest(page, width: int, height: int, scale: float) -> list[dict[str, object]]:
    """Prove the rendered gates reject injected defects and recover after removal."""
    results = []
    def geometry():
        return check_geometry(measure_geometry(page, chrome_bands(page)), width=width, height=height,
                              scale=scale, bands=chrome_bands(page))
    faults = (
        ("status-child-overflow", '.status-bar', geometry),
        ("navigation-child-overflow", '.context-subnav' if "context" in chrome_bands(page) else '.navigation-sidebar' if "rail" in chrome_bands(page) else '.activity-dock', geometry),
        ("pill-wrap", '.status-pill {white-space:normal!important;width:30px!important;overflow:visible!important}',
         lambda: check_status_accessibility(page)),
        ("compressed-target", '.command-trigger {width:13px!important;min-width:13px!important;max-width:13px!important;flex:0 0 13px!important;padding:0!important;border:0!important;box-sizing:border-box!important}', lambda: check_status_accessibility(page)),
        ("invisible-focus", ':root {--ax-focus-ring:transparent!important}', lambda: check_status_accessibility(page)),
    )
    for name, fault, checker in faults:
        if name.endswith('child-overflow'):
            page.evaluate("""selector => {
              const parent = document.querySelector(selector);
              parent.dataset.savedStyle = parent.getAttribute('style') || '';
              parent.style.overflow = 'visible';
              const el = document.createElement('div'); el.id = 'a0-injected-fault';
              el.style.cssText = 'position:fixed;left:10px;top:0;width:80px;height:100vh;background:red';
              parent.appendChild(el);
            }""", fault)
        else:
            page.evaluate("""css => { const el=document.createElement('style');
              el.id='a0-injected-fault'; el.textContent=css; document.head.appendChild(el); }""", fault)
        rejected = False
        try:
            checker()
        except AssertionError:
            rejected = True
        finally:
            page.evaluate("""() => {
              document.querySelector('#a0-injected-fault')?.remove();
              for (const el of document.querySelectorAll('[data-saved-style]')) {
                el.setAttribute('style', el.dataset.savedStyle); delete el.dataset.savedStyle;
              }
            }""")
        assert rejected, f'gate accepted injected {name}'
        checker()
        results.append({"fault": name, "injected": "FAIL", "removed": "PASS"})
    # Use the actual product labels, including the longer native-host states.
    source = (ROOT / 'frontend/src/components/StatusBar.tsx').read_text(encoding='utf-8')
    block = source.split('const BACKEND_LABELS:', 1)[1].split('};', 1)[0]
    labels = re.findall(r'^\s*\w+: "([^"]+)"', block, flags=re.MULTILINE)
    assert labels, 'backend labels missing from product source'
    original = page.locator('.status-pill').inner_text()
    try:
        for label in labels:
            page.locator('.status-pill').evaluate('(el, text) => el.textContent=text', label)
            check_status_accessibility(page)
            results.append({"backend_label": label, "status": "PASS"})
    finally:
        page.locator('.status-pill').evaluate('(el, text) => el.textContent=text', original)
    return results


def open_library_page(
    browser,
    problems: list[str],
    *,
    stub: str,
    viewport: tuple[str, int, int, float],
) -> tuple[object, object]:
    """A canonical-host page parked on 资料库, with the same console wiring as the main probe.

    The template probes each need their own browsing context (a faulted transport must not leak
    into the geometry run and back), so the shared set-up lives here rather than being copied.
    """
    _, width, height, scale = viewport
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=scale,
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.on("pageerror", lambda error: problems.append(f"canonical-pageerror:{error}"))
    page.on(
        "console",
        lambda message: problems.append(f"canonical-console:{message.text}")
        if message.type == "error" else None,
    )

    def route_api(route: Route) -> None:
        path = urlsplit(route.request.url).path
        if path.startswith(f"{API_PREFIX}/") or path.startswith(f"{WORKSPACE_PREFIX}/api/"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(api_payload(route.request.url)),
            )
        else:
            route.continue_()

    context.add_init_script(stub)
    page.route("**/*", route_api)
    page.goto(URL, wait_until="networkidle")
    # Import/template regression belongs to the explicit canonical compatibility route.
    page.evaluate("location.hash = 'space=library'")
    page.get_by_role("heading", name="资料库").first.wait_for()
    page.locator("details.template-launcher > summary").first.wait_for()
    return context, page


def launcher_is_open(page) -> bool:
    """The disclosure's real open state, and nothing else.

    `open` belongs to the `<details>`, not to its `<summary>`: reading it off the wrong element
    yields undefined, which turns an assertion that should describe the product into one that can
    never pass. The type check makes a mis-planted selector fail here rather than as a false claim.
    """
    state = page.evaluate("() => document.querySelector('details.template-launcher')?.open ?? null")
    assert isinstance(state, bool), f"no template disclosure found to read (got {state!r})"
    return state


def read_template_surface(page, label: str) -> dict[str, object]:
    """What the 学科模板 disclosure actually offers once opened, measured in a real layout engine.

    jsdom already covers the create/save/reference loop (TemplateBindings.test.tsx). What jsdom
    cannot answer is whether the row is reachable, whether the workspace has a box at all, and
    whether the surface lies when Core cannot be read - so this measures exactly those.
    """
    disciplines, templates = template_catalog()
    launcher = page.locator("details.template-launcher")
    summary = launcher.locator("> summary")
    assert summary.count() == 1, f"expected exactly one 学科模板 disclosure on 资料库, found {summary.count()}"
    assert summary.first.inner_text().strip() == TEMPLATE_SUMMARY_TEXT, summary.first.inner_text()
    box = summary.first.bounding_box()
    assert box and box["width"] > 120 and box["height"] > 16, box
    # Default-collapsed is a deliberate product decision (the launcher must not push the library
    # reading column down), so the gate pins it: an always-open workspace would be a different UI.
    assert not launcher_is_open(page), "the template workspace is open by default"
    assert page.locator(TEMPLATE_SECTION_SELECTOR).count() == 0, "the workspace mounted before it was opened"
    # A closed disclosure must contribute no announcement of its own: the page outcome region
    # already speaks for this surface. This is the browser-side half of LiveRegionBudget.
    assert live_region_texts(page, "details.template-launcher") == [], live_region_texts(page, "details.template-launcher")

    summary.first.click()
    section = page.locator(TEMPLATE_SECTION_SELECTOR)
    section.first.wait_for(state="attached")
    assert section.count() == 1, section.count()
    rect = section.first.bounding_box()
    assert rect and rect["width"] > 200 and rect["height"] > 100, rect

    selects = page.evaluate(
        """(selector) => {
          const root = document.querySelector(selector);
          const read = {};
          for (const node of root.querySelectorAll(":scope > label")) {
            const select = node.querySelector("select");
            if (select) read[node.childNodes[0].textContent.trim()] = [...select.options].map(o => o.textContent.trim());
          }
          return read;
        }""",
        TEMPLATE_SECTION_SELECTOR,
    )
    assert selects.get("学科") == disciplines, selects.get("学科")
    assert selects.get("模板") == templates, selects.get("模板")

    buttons = page.evaluate(
        """(selector) => [...document.querySelectorAll(selector + " > button")].map((b) => ({
          text: b.textContent.trim(), width: +b.getBoundingClientRect().width.toFixed(1), disabled: b.disabled,
        }))""",
        TEMPLATE_SECTION_SELECTOR,
    )
    by_text = {entry["text"]: entry for entry in buttons}
    for name in ("创建学科对象", "重新读取模板集合"):
        assert name in by_text, sorted(by_text)
        assert by_text[name]["width"] > 60, by_text[name]
        assert by_text[name]["disabled"] is False, by_text[name]
    # No selection exists yet, so a save affordance here would advertise an action with no object.
    assert "保存模板属性与关系" not in by_text, by_text

    list_buttons = page.locator("nav[aria-label='已保存模板'] button")
    list_state = page.locator("nav[aria-label='已保存模板'] p")
    assert list_buttons.count() == 0, list_buttons.count()
    assert list_state.count() == 1, list_state.count()
    # Read once and reuse: the disclosure is collapsed below, so a later lookup would time out
    # against a detached element rather than report what the surface said.
    empty_state = list_state.first.inner_text()
    assert "尚无已保存的模板对象" in empty_state, empty_state
    assert list_state.first.get_attribute("role") is None, "the empty list speaks twice"
    text = section.first.inner_text()
    # The count line has to report the read it performed, not a plausible collection.
    assert "本次完整读回 0 个文档对象，其中 0 个带可解析模板属性" in text, text
    assert "无效模板属性不参与集合汇总" not in text, text
    assert live_region_texts(page, "details.template-launcher") == [""], live_region_texts(page, "details.template-launcher")

    shot = ARTIFACTS / f"canonical-host-templates-{label}.png"
    page.screenshot(path=str(shot), full_page=True)
    # Closing from the same control is part of the affordance, and it leaves the surface as found
    # so the frames captured after this one still depict what their names claim.
    summary.first.click()
    section.first.wait_for(state="detached")
    assert not launcher_is_open(page)
    return {
        "viewport": label,
        "summary_box": box,
        "expanded_rect": rect,
        "discipline_option_count": len(disciplines),
        "template_options": templates,
        "section_buttons": by_text,
        "saved_template_rows": 0,
        "empty_state": empty_state,
        "screenshot": _recorded(shot),
    }


def read_template_roundtrip(browser, viewport, problems, theme="black") -> dict:
    """Real rendering and interaction over synthetic versioned document commands."""
    context, page = open_library_page(browser, problems, stub=host_bridge_stub(stateful_documents=True), viewport=viewport)
    page.set_default_timeout(8000)
    try:
        select_ui_theme(page, theme)
        page.locator("details.template-launcher > summary").click()
        section = page.locator(TEMPLATE_SECTION_SELECTOR)
        section.get_by_role("button", name="创建学科对象", exact=True).click()
        section.get_by_text("模板对象与属性已保存并完整读回；内容仍未评估。", exact=True).wait_for()
        for n in [1, 2, 3]:
            section.get_by_label("关系目标", exact=False).select_option(f"a0_target_{n}")
            section.get_by_label("目标块 ID（可空）", exact=True).fill("a0_p1" if n == 1 else "")
            section.get_by_role("button", name="加入版本绑定引用", exact=True).click()
            page.wait_for_function("n => document.querySelector('[aria-label=局部图谱]').children.length === n", arg=n)
        canvas = section.locator('[aria-label="引用式画布"]')
        def check_cards(stage):
            cards = canvas.evaluate("""node => [...node.children].map(card=>{const r=card.getBoundingClientRect();
              return {x:r.x,y:r.y,width:r.width,height:r.height,savedX:parseFloat(card.style.left),savedY:parseFloat(card.style.top)};})""")
            for i, a in enumerate(cards):
                for b in cards[i+1:]:
                    assert not (min(a['x']+a['width'],b['x']+b['width']) > max(a['x'],b['x'])
                                and min(a['y']+a['height'],b['y']+b['height']) > max(a['y'],b['y'])), (stage,"overlapping reference cards",cards)
            for button in canvas.locator("button").all():
                button.scroll_into_view_if_needed()
                assert button.evaluate("""node=>{const r=node.getBoundingClientRect();
                  const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                  return r.width>=24 && r.height>=24 && (hit===node || node.contains(hit));}"""), (stage,button.inner_text())
            return cards
        check_cards("created")
        for _ in range(2):
            old=canvas.locator(":scope > div").nth(0).evaluate("node=>node.style.top")
            section.get_by_role("button", name="移动引用卡片 1", exact=True).click()
            page.wait_for_function("old=>document.querySelector('[aria-label=引用式画布]').children[0].style.top!==old",arg=old)
        check_cards("first card moved twice")
        for _ in range(12):
            old=canvas.locator(":scope > div").nth(2).evaluate("node=>node.style.top")
            section.get_by_role("button", name="移动引用卡片 3", exact=True).click()
            page.wait_for_function("old=>document.querySelector('[aria-label=引用式画布]').children[2].style.top!==old",arg=old)
        check_cards("last card moved twelve times")
        section.get_by_role("button", name="删除引用 3", exact=True).click()
        page.wait_for_function("() => document.querySelector('[aria-label=局部图谱]').children.length === 2")
        section.get_by_label("关系目标", exact=False).select_option("a0_target_3")
        section.get_by_role("button", name="加入版本绑定引用", exact=True).click()
        page.wait_for_function("() => document.querySelector('[aria-label=局部图谱]').children.length === 3")
        cards=check_cards("removed and added")
        page.evaluate("() => window.__A0_DOCUMENT_FIXTURE__.advance()")
        section.get_by_role("button", name="保存模板属性与关系", exact=True).click()
        section.get_by_text("模板对象与属性已保存并完整读回；内容仍未评估。", exact=True).wait_for()
        page.locator("nav[aria-label='已保存模板'] button").filter(has_text="· v2").wait_for()
        section.locator('[aria-label="局部图谱"] button').first.click()
        aside = section.locator('[aria-label="引用原文"]')
        aside.get_by_text("绑定历史正文 1 v1", exact=True).wait_for()
        assert "当前新正文" not in aside.inner_text(), aside.inner_text()
        page.locator("details.template-launcher > summary").click()
        section.wait_for(state="detached")
        page.locator("details.template-launcher > summary").click()
        page.locator("nav[aria-label='已保存模板'] button").filter(has_text="· v2").click()
        page.wait_for_function("() => document.querySelector('[aria-label=局部图谱]').children.length === 3")
        reloaded=check_cards("reloaded")
        assert [(r["savedX"],r["savedY"]) for r in cards] == [(r["savedX"],r["savedY"]) for r in reloaded], (cards,reloaded)
        audit = page.evaluate("() => ({calls:window.__A0_DOCUMENT_FIXTURE__.calls,documents:window.__A0_DOCUMENT_FIXTURE__.snapshot()})")
        writes=[call for call in audit['calls'] if call['operation'] in ('document_create','document_draft')]
        assert len(writes)==2, writes
        assert writes[1]['payload']['body']['expected_version']==1, writes
        saved=next(doc for doc in audit['documents'] if doc['document_id']==writes[1]['payload']['document_id'])
        refs=saved['editor_json']['attrs']['archeaxis_template']['references']
        assert len(refs)==3 and all(ref['version']==1 for ref in refs), refs
        assert refs[0]['block_id']=='a0_p1', refs
        assert [(r['x'],r['y']) for r in refs]==[(r['savedX'],r['savedY']) for r in reloaded], (refs,reloaded)
        return {"viewport":viewport[0],"theme":theme,"status":"PASS","cards":cards,
                "writes":len(writes),"saved_version":saved['version'],"references":refs,
                "rendering_evidence":"REAL","document_bridge_evidence":"SYNTHETIC"}
    except Exception:
        (ARTIFACTS / "template-roundtrip-failure.json").write_text(json.dumps({
            "text":page.locator("body").inner_text(),"problems":problems,
            "fixture":page.evaluate("() => window.__A0_DOCUMENT_FIXTURE__ ? {calls:window.__A0_DOCUMENT_FIXTURE__.calls,documents:window.__A0_DOCUMENT_FIXTURE__.snapshot()} : null")},ensure_ascii=False,indent=2),encoding="utf-8")
        page.screenshot(path=str(ARTIFACTS / "template-roundtrip-failure.png"),full_page=True)
        raise
    finally:
        context.close()


def read_template_failure(browser, problems: list[str]) -> dict[str, object]:
    """What the surface says when Core cannot finish the read - the only honest answer available.

    `documents_list` names one saved document and `document_get` answers 503 for it, which is a
    partial outage rather than an empty library. A list that then reads "no template objects yet"
    would be a fabricated negative, and a list that renders the document it never retrieved would
    be a fabricated positive.
    """
    context, page = open_library_page(
        browser,
        problems,
        stub=host_bridge_stub(
            documents=[A0_DOCUMENT_SUMMARY],
            failing_operations={"document_get": 503},
        ),
        viewport=DESKTOP_MATRIX[0],
    )
    try:
        page.locator("details.template-launcher > summary").first.click()
        section = page.locator(TEMPLATE_SECTION_SELECTOR)
        section.first.wait_for(state="attached")
        page.wait_for_timeout(400)
        assert section.first.get_by_text("模板对象读取失败，请重试。").count() == 1, section.first.inner_text()
        assert page.locator("nav[aria-label='已保存模板'] button").count() == 0, "an unretrieved object was listed"
        empty_state = page.locator("nav[aria-label='已保存模板'] p").first.inner_text()
        assert "未能完整读回" in empty_state and "当前集合是否为空未知" in empty_state, empty_state
        assert "本次完整读回" not in section.first.inner_text(), section.first.inner_text()
        # One event, one region: the failure is announced from the launcher's own status element
        # and from nowhere else on the page.
        spoken = live_region_texts(page, "details.template-launcher")
        assert spoken == ["模板对象读取失败，请重试。"], spoken
        assert live_region_texts(page).count("模板对象读取失败，请重试。") == 1, live_region_texts(page)
        shot = ARTIFACTS / f"canonical-host-templates-unreadable-{DESKTOP_MATRIX[0][0]}.png"
        page.screenshot(path=str(shot), full_page=True)
        return {
            "failure_message": "模板对象读取失败，请重试。",
            "listed_rows": 0,
            "empty_state": empty_state,
            "launcher_live_regions": spoken,
            "screenshot": _recorded(shot),
        }
    finally:
        context.close()


def read_template_reachability(browser, viewport: tuple[str, int, int, float], problems: list[str]) -> dict[str, object]:
    """Keyboard-only reach and narrow-window geometry for the disclosure, in a real layout engine."""
    label, width, height, scale = viewport
    context, page = open_library_page(browser, problems, stub=host_bridge_stub(), viewport=viewport)
    try:
        summary = page.locator("details.template-launcher > summary")
        assert not launcher_is_open(page), f"open by default at {label}"
        on_summary = "() => document.activeElement === document.querySelector('details.template-launcher > summary')"
        page.evaluate("() => document.activeElement?.blur()")
        presses = 0
        while presses < 150 and not page.evaluate(on_summary):
            page.keyboard.press("Tab")
            presses += 1
        assert page.evaluate(on_summary), f"the disclosure is not a Tab stop at {label} after {presses} presses"

        page.keyboard.press("Enter")
        section = page.locator(TEMPLATE_SECTION_SELECTOR)
        section.first.wait_for(state="attached")
        rect = section.first.bounding_box()
        assert rect and rect["width"] > 0 and rect["height"] > 0, rect
        assert page.evaluate(on_summary), f"Enter moved focus off the disclosure at {label}"
        launcher_box = page.locator("details.template-launcher").first.bounding_box()
        assert launcher_box["x"] + launcher_box["width"] <= width + 0.5, (launcher_box, width)
        # The workspace must stay inside its own disclosure: a child escaping the launcher is how
        # a grid column overflow reads as "the page scrolls sideways".
        assert rect["x"] >= launcher_box["x"] - 0.5, (rect, launcher_box)
        assert rect["x"] + rect["width"] <= launcher_box["x"] + launcher_box["width"] + 0.5, (rect, launcher_box)
        overflow = page.evaluate(
            """() => {
              const launcher = document.querySelector('details.template-launcher');
              return {
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                launcherScroll: launcher.scrollWidth,
                launcherClient: launcher.clientWidth,
              };
            }"""
        )
        assert overflow["scrollWidth"] <= overflow["clientWidth"], (label, overflow)
        assert overflow["launcherScroll"] <= overflow["launcherClient"] + 1, (label, overflow)
        page.keyboard.press("Enter")
        section.first.wait_for(state="detached")
        assert page.evaluate(on_summary), f"closing moved focus off the disclosure at {label}"
        # Geometry says it fits; the frame is what says it still reads. Named for the viewport it
        # was taken in, so a frame cannot be cited as evidence for a window it does not depict.
        narrow_shot = ARTIFACTS / f"canonical-host-templates-keyboard-{label}.png"
        page.keyboard.press("Enter")
        section.first.wait_for(state="attached")
        page.screenshot(path=str(narrow_shot), full_page=True)
        return {
            "viewport": label,
            "tab_presses_to_reach": presses,
            "expanded_rect": rect,
            "launcher_box": launcher_box,
            "overflow": overflow,
            "screenshot": _recorded(narrow_shot),
        }
    finally:
        context.close()


def read_library_geometry(
    browser, viewport: tuple[str, int, int, float], problems: list[str]
) -> dict[str, object]:
    """The 资料库 landmark set at a real window size, collapsed and expanded.

    The unconnected browser sweep has no objects for this surface, and the template disclosure is the
    widest component on the product entry, so without this the non-stacking check would stop at
    the sizes where nothing is likely to stack. Both states are measured: the collapsed row is
    what the user sees first, the expanded workspace is where a non-wrapping grid escapes.
    """
    label, width, height, scale = viewport
    context, page = open_library_page(browser, problems, stub=host_bridge_stub(), viewport=viewport)
    try:
        summary = page.locator("details.template-launcher > summary")
        summary.first.wait_for()
        collapsed = check_geometry(
            measure_geometry(page, chrome_bands(page, library=True)),
            width=width, height=height, scale=scale, bands=chrome_bands(page, library=True),
        )
        summary.first.click()
        page.locator(TEMPLATE_SECTION_SELECTOR).first.wait_for(state="attached")
        expanded = check_geometry(
            measure_geometry(page, library_bands(page)),
            width=width, height=height, scale=scale, bands=library_bands(page),
        )
        shot = ARTIFACTS / f"canonical-host-library-geometry-{label}.png"
        page.screenshot(path=str(shot), full_page=True)
        summary.first.click()
        page.locator(TEMPLATE_SECTION_SELECTOR).first.wait_for(state="detached")
        return {
            "viewport": label,
            "collapsed": collapsed,
            "expanded": expanded,
            "screenshot": _recorded(shot),
        }
    finally:
        context.close()



def visible_control_box(locator) -> dict[str, object]:
    """Intersect every clipping ancestor before asking which element receives a pointer."""
    return locator.evaluate("""node => {
      const r=node.getBoundingClientRect(), style=getComputedStyle(node);
      let left=Math.max(0,r.left),top=Math.max(0,r.top),right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
      for(let a=node.parentElement;a;a=a.parentElement){const s=getComputedStyle(a),b=a.getBoundingClientRect();
        if(/auto|scroll|hidden|clip/.test(s.overflowX)){left=Math.max(left,b.left);right=Math.min(right,b.right)}
        if(/auto|scroll|hidden|clip/.test(s.overflowY)){top=Math.max(top,b.top);bottom=Math.min(bottom,b.bottom)}}
      const hit=document.elementFromPoint((left+right)/2,(top+bottom)/2);
      return {width:Math.max(0,right-left),height:Math.max(0,bottom-top),rawWidth:r.width,rawHeight:r.height,
        lineHeight:parseFloat(style.lineHeight),fontSize:parseFloat(style.fontSize),
        reachable:!!hit&&(hit===node||node.contains(hit)),label:node.getAttribute('aria-label')||node.textContent};
    }""")


def check_top_navigation_actions(page, *, diagnostics_suspended: bool) -> None:
    """Require each action; quarantine adds recheck instead of removing diagnostics."""
    actions = page.locator('.top-nav-right')
    for name in ('通知', '设置', '运行诊断'):
        node = actions.get_by_role('button', name=name, exact=True)
        assert node.count() == 1 and node.is_visible(), ('missing top navigation action', name)
        assert node.is_disabled() == (name == '运行诊断' and diagnostics_suspended), ('action state', name)
    avatar = actions.locator('button.top-nav-user')
    assert avatar.count() == 1 and avatar.is_visible() and avatar.is_enabled(), 'missing user action'
    recheck = actions.get_by_role('button', name='重新检查诊断连接', exact=True)
    assert recheck.count() == int(diagnostics_suspended), 'diagnostic recheck disagrees with quarantine'
    if diagnostics_suspended:
        assert recheck.is_visible() and recheck.is_enabled(), 'diagnostic recheck unavailable'
    mode = page.locator('.console-window').get_attribute('data-console-mode')
    assert mode in {'floating', 'full', 'compact'}, ('unknown console mode', mode)
    toggle_name = '铺满主控台' if mode == 'floating' else '还原主控台'
    for name, disabled in ((toggle_name, mode == 'compact'), ('复位主控台', False)):
        node = actions.get_by_role('button', name=name, exact=True)
        assert node.count() == 1 and node.is_visible(), ('missing console action', name)
        assert node.is_disabled() == disabled, ('console action state', name, mode)
        box = visible_control_box(node)
        assert box['width'] >= 24 and box['height'] >= 24 and box['reachable'], box
        assert abs(box['height'] - box['rawHeight']) <= 1 and abs(box['width'] - box['rawWidth']) <= 1, box
    assert actions.locator('button').count() == 6 + int(diagnostics_suspended), 'unexpected top navigation actions'


def check_shell_pointer_targets(page, *, diagnostics_suspended: bool = False) -> list[dict[str, object]]:
    compact = compact_chrome(console_viewport(page))
    check_top_navigation_actions(page, diagnostics_suspended=diagnostics_suspended)
    assert page.get_by_role('button', name='打开全局命令', exact=True).is_visible()
    assert page.get_by_label('界面设置', exact=True).is_visible()
    assert page.get_by_role('button', name='搜索页面、能力与内容', exact=True).is_visible() == (not compact)
    if compact:
        assert page.get_by_role('button', name='打开产品导航', exact=True).is_visible()
    targets=[]
    for node in page.locator('.top-nav-bar button,.status-bar button,.status-bar select,.status-bar summary,.ui-navigation-trigger').all():
        if not node.is_visible():
            continue
        box=visible_control_box(node)
        assert box['width'] >= 24 and box['height'] >= 24 and box['reachable'], box
        assert abs(box['height']-box['rawHeight']) <= 1 and abs(box['width']-box['rawWidth']) <= 1, box
        targets.append(box)
    assert len(targets) >= 7, targets
    return targets


def check_product_navigation_targets(page) -> dict[str, object]:
    trigger=page.get_by_role('button', name='打开产品导航', exact=True)
    if not trigger.is_visible():
        return {'presentation':'sidebar', 'tested':False}
    entries=[]
    for target in ('01','02','06','13','15','17','19'):
        trigger.click()
        drawer=page.get_by_role('dialog', name='产品导航', exact=True)
        drawer.wait_for()
        node=drawer.locator(f'[data-page-id="{target}"]')
        node.scroll_into_view_if_needed()
        box=visible_control_box(node)
        close=visible_control_box(drawer.get_by_role('button', name='关闭导航', exact=True))
        assert box['reachable'] and box['height'] >= 24 and box['width'] >= 24, box
        assert close['reachable'] and close['height'] >= 24, close
        node.click()
        drawer.wait_for(state='detached')
        page.locator(f'[data-current-page-id="{target}"]').wait_for()
        entries.append({'page_id':target,'target':box,'close':close})
    trigger.click()
    drawer=page.get_by_role('dialog', name='产品导航', exact=True)
    drawer.get_by_role('button', name='关闭导航', exact=True).click()
    drawer.wait_for(state='detached')
    page.wait_for_timeout(150)
    assert trigger.evaluate('node => document.activeElement === node')
    return {'presentation':'drawer','tested':True,'entries':entries,'close_restores_focus':True}


def wait_reader_fit(page) -> None:
    # Dockview's ResizeObserver must finish reflowing after the explicit rail toggle.
    # A timeout is a failure: a permanently clipped document never becomes acceptable.
    page.wait_for_function("""() => {
      const card=document.querySelector('.ui-reader-document')?.getBoundingClientRect();
      const center=document.querySelector('.app-center')?.getBoundingClientRect();
      return card && center && card.left >= center.left && card.right <= center.right;
    }""")



def read_semantic_reading(browser, viewport, problems, theme):
    """New 02/03 layout evidence, separate from the legacy import/template regression."""
    context, page = open_library_page(browser, problems,
        stub=host_bridge_stub(stateful_documents=True), viewport=viewport)
    try:
        label = viewport[0]
        select_ui_theme(page, theme)
        navigate_ui_page(page, "02")
        library = page.get_by_role("region", name="知识库文档视图", exact=True)
        library.wait_for()
        row = library.get_by_role("button", name="打开文档 引用目标 1 · 独立历史正文", exact=True)
        row.wait_for()
        library_targets = check_shell_pointer_targets(page)
        library_row = visible_control_box(row)
        assert library_row["reachable"] and library_row["height"] >= 24, library_row
        library_shot = ARTIFACTS / f"semantic-library-{theme}-{label}.png"
        page.screenshot(path=str(library_shot), full_page=True)
        row.click()
        reader = page.get_by_role("region", name="阅读与编辑文档视图", exact=True)
        reader.wait_for()
        editor = reader.get_by_role("textbox", name="文档草稿")
        editor.wait_for()
        assert "绑定历史正文 1 v1" in editor.inner_text()
        assert reader.locator("details.template-launcher").count() == 0
        assert reader.locator("input[aria-label='导入原件']").count() == 0
        assert reader.locator("input[aria-label='选择文件夹']").count() == 0
        calls = page.evaluate("() => window.__A0_DOCUMENT_FIXTURE__.calls")
        assert any(call["operation"] == "document_get" and
            call["payload"].get("document_id") == "a0_target_1" for call in calls), calls
        assert not any(call["operation"] == "document_draft" for call in calls), calls
        inspector = page.get_by_role("complementary", name="检查器", exact=True)
        if console_dimensions(page)[0] <= 900:
            # Automatic document synchronization intentionally leaves narrow reading
            # space unobstructed. Exercise the real explicit Inspector control.
            assert inspector.count() == 0, "automatic inspection opened the narrow rail"
            page.get_by_role("button", name="展开检查器", exact=True).click()
        if inspector.count() == 0:
            page.get_by_role("button", name="展开检查器", exact=True).click()
        inspector.wait_for(state="visible")
        wait_reader_fit(page)
        assert "引用目标 1" in inspector.inner_text()
        geometry = page.evaluate("""() => {
          const rect = selector => { const r=document.querySelector(selector).getBoundingClientRect();
            return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
          const center = document.querySelector('.app-center'), style = getComputedStyle(center);
          const containerWidth = center.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
          const console=document.querySelector(".console-window")||document.querySelector(".app-shell"), size=console.getBoundingClientRect();
          return {width:innerWidth,height:innerHeight,console_width:size.width,console_height:size.height,container_width:containerWidth,document:rect('.ui-reader-document'),details:rect('.ui-reader-details'),
            center:rect('.app-center'),body:rect('.app-body'),inspector:rect('.inspector'),
            scroll_width:document.documentElement.scrollWidth};
        }""")
        doc, details = geometry["document"], geometry["details"]
        assert doc["width"] > 100 and doc["right"] <= geometry["width"] + 1, geometry
        assert details["width"] > 100 and details["right"] <= geometry["width"] + 1, geometry
        # Side rails leave less room than the window width; the selected UI
        # stacks reading details below the document in a narrow content container.
        if geometry["console_width"] > 1100 and geometry["container_width"] > 900:
            assert doc["right"] <= details["x"], geometry
        else:
            assert doc["bottom"] <= details["y"], geometry
        compact = geometry["console_width"] <= 1100 or geometry["console_height"] <= 760
        short_side = geometry["console_width"] >= 600 and geometry["console_height"] <= 600
        if short_side:
            assert geometry["center"]["right"] <= geometry["inspector"]["x"] + 1, geometry
            assert geometry["center"]["width"] >= 280 and geometry["inspector"]["width"] == 220, geometry
            assert abs(geometry["center"]["height"] - geometry["body"]["height"]) <= 1, geometry
        elif compact:
            assert abs(geometry["center"]["width"] - geometry["body"]["width"]) <= 1, geometry
            assert geometry["center"]["bottom"] <= geometry["inspector"]["y"] + 1, geometry
            assert geometry["inspector"]["height"] == 96, geometry
        assert geometry["inspector"]["bottom"] <= geometry["body"]["bottom"] + 1, geometry
        assert geometry["scroll_width"] <= geometry["width"], geometry
        geometry["layout_target"] = visible_control_box(page.locator('.dock-layout-options > summary'))
        assert geometry["layout_target"]["reachable"], geometry
        page.locator('.dock-layout-options > summary').click()
        assert page.locator('.dock-layout-options').get_attribute('open') is not None
        page.locator('.dock-layout-options > summary').click()
        geometry["shell_targets"] = check_shell_pointer_targets(page)
        geometry["library_targets"] = library_targets
        geometry["close_target"] = visible_control_box(inspector.get_by_role("button", name="关闭检查器", exact=True))
        assert geometry["close_target"]["reachable"], geometry
        inspector.get_by_role("button", name="关闭检查器", exact=True).click()
        assert inspector.count() == 0
        assert "绑定历史正文 1 v1" in editor.inner_text()
        page.get_by_role("button", name="展开检查器", exact=True).click()
        assert "引用目标 1" in inspector.inner_text()
        wait_reader_fit(page)
        geometry["paragraph"] = visible_control_box(editor.locator("p").first)
        geometry["reading_area"] = visible_control_box(editor)
        paragraph, area = geometry["paragraph"], geometry["reading_area"]
        assert paragraph["reachable"] and paragraph["height"] >= paragraph["lineHeight"] - 1, geometry
        assert abs(area["width"] - area["rawWidth"]) <= 1 and area["width"] >= 280, geometry
        assert abs(paragraph["width"] - paragraph["rawWidth"]) <= 1, geometry
        assert area["fontSize"] >= 17 and area["height"] >= min(4 * area["lineHeight"], area["rawHeight"]), geometry
        reader_shot = ARTIFACTS / f"semantic-reader-{theme}-{label}.png"
        page.screenshot(path=str(reader_shot), full_page=True)
        geometry["status_accessibility"] = check_status_accessibility(page)
        geometry["navigation"] = check_product_navigation_targets(page)
        return {"evidence":"SIMULATED_HOST_CORE_FIXTURE", "theme":theme,"viewport":label,
            "document_id":"a0_target_1","new_library":True,"new_reader":True,
            "geometry":geometry,"library_screenshot":_recorded(library_shot),
            "reader_screenshot":_recorded(reader_shot)}
    finally:
        context.close()


def read_top_navigation(browser, viewport, problems, theme):
    """Exercise actual alternate chrome, existing routes and editor identity."""
    context, page = open_library_page(browser, problems,
        stub=host_bridge_stub(stateful_documents=True), viewport=viewport)
    label, width, _, _ = viewport
    try:
        select_ui_theme(page, theme)
        navigate_ui_page(page, "01")
        settings = page.get_by_label("界面设置", exact=True)
        settings.click()
        page.get_by_label("导航呈现", exact=True).select_option("top")
        settings.click()
        page.locator('[data-working-state="ready"]').wait_for(state="attached")
        assert "读取未完成" not in page.get_by_role("contentinfo", name="活动坞", exact=True).inner_text()
        assert page.evaluate("localStorage.getItem('aaos.navigation-appearance.v1')") == "top"
        assert not page.locator('.navigation-sidebar').is_visible()
        nav = page.get_by_role("navigation", name="顶部空间导航", exact=True)
        if console_dimensions(page)[0] > 1200 and not compact_chrome(console_viewport(page)):
            assert nav.is_visible()
            nav.get_by_role("button", name="知识", exact=True).click()
            menu = nav.get_by_role("menu", name="知识页面", exact=True)
            assert menu.get_by_role("menuitem").count() == 4
            shot = ARTIFACTS / f"top-menu-{theme}-{label}.png"
            page.screenshot(path=str(shot), full_page=True)
            geometry = nav.evaluate("""node => {
              const bounds = element => { const r=element.getBoundingClientRect();
                return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
              return {shell:bounds(document.querySelector('.cabin-shell')),nav:bounds(node),
                menu:bounds(node.querySelector('[role=menu]')),
                entries:[...node.querySelectorAll('[data-top-page]')].map(el=>{
                  const r=el.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                  return {label:el.textContent,rect:bounds(el),reachable:el.contains(hit)};}),
                hero:bounds(document.querySelector('.workspace-planet-hero')),
                actions:bounds(document.querySelector('.workspace-start')),
                overflow:document.documentElement.scrollWidth>innerWidth};
            }""")
            assert not geometry['overflow'], geometry
            assert len(geometry['entries']) == 7 and all(item['reachable'] for item in geometry['entries']), geometry
            assert geometry['menu']['right'] <= geometry['shell']['right'], geometry
            assert geometry['actions']['right'] <= geometry['hero']['x'], geometry
            menu.get_by_role("menuitem", name="知识库", exact=True).click()
        else:
            assert not nav.is_visible()
            check_shell_pointer_targets(page)
            navigation = check_product_navigation_targets(page)
            assert navigation["tested"] and len(navigation["entries"]) == 7, navigation
            navigate_ui_page(page, "02")
            shot = ARTIFACTS / f"top-drawer-{theme}-{label}.png"
            page.screenshot(path=str(shot), full_page=True)
            geometry = {"drawer_used": True, "navigation": navigation,
                        "overflow": page.evaluate("document.documentElement.scrollWidth>innerWidth")}
            assert not geometry['overflow'], geometry
        page.get_by_role("button", name="打开文档 引用目标 1 · 独立历史正文", exact=True).click()
        editor = page.get_by_role("region", name="阅读与编辑文档视图", exact=True).get_by_role("textbox", name="文档草稿")
        editor.wait_for()
        assert "绑定历史正文 1 v1" in editor.inner_text()
        editor.evaluate("node => window.__A0_NAV_EDITOR__ = node")
        for appearance in ("sidebar", "top"):
            settings.click()
            page.get_by_label("导航呈现", exact=True).select_option(appearance)
            settings.click()
            assert editor.evaluate("node => node === window.__A0_NAV_EDITOR__"), "Navigation appearance remounted editor"
        status = check_status_accessibility(page)
        calls = page.evaluate("window.__A0_DOCUMENT_FIXTURE__.calls")
        assert not any(call['operation'] == 'document_draft' for call in calls), calls
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        return {"evidence":"SIMULATED_HOST_CORE_FIXTURE", "viewport":label, "theme":theme,
                "geometry":geometry, "editor_preserved":True, "status_accessibility":status, "screenshot":_recorded(shot)}
    finally:
        context.close()


def read_narrow_dock_library(browser, problems, theme, viewport=("1600x1000@100", 1600, 1000, 1.0)):
    """A wide window can contain narrow real Dock panels; clicks must still work."""
    context, page = open_library_page(browser, problems,
        stub=host_bridge_stub(stateful_documents=True), viewport=viewport)
    try:
        select_ui_theme(page, theme)
        navigate_ui_page(page, "02")
        # Match the native reopened layout with the real document inspector retained.
        page.get_by_role("region", name="知识库文档视图", exact=True).get_by_role("button",
            name="打开文档 引用目标 1 · 独立历史正文", exact=True).click()
        page.get_by_role("region", name="阅读与编辑文档视图", exact=True).wait_for()
        navigate_ui_page(page, "02")
        page.locator("details.dock-layout-options > summary").click()
        page.get_by_role("button", name="左右分栏", exact=True).click()
        navigate_ui_page(page, "02")
        library = page.get_by_role("region", name="知识库文档视图", exact=True)
        library.wait_for()
        row = library.get_by_role("button", name="打开文档 引用目标 1 · 独立历史正文", exact=True)
        row.wait_for()
        geometry = library.evaluate("""node => {
          const box = el => { const r=el.getBoundingClientRect();
            return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width}; };
          return {window_width:innerWidth,library:box(node),
            content:box(node.querySelector('.ui-content-main-side > section')),
            details:box(node.querySelector('.ui-content-main-side > aside'))};
        }""")
        library_shot = ARTIFACTS / f"narrow-dock-library-{theme}-{viewport[0]}.png"
        page.screenshot(path=str(library_shot), full_page=True)
        assert geometry["window_width"] == viewport[1], geometry
        assert 220 <= geometry["library"]["width"] < 700, geometry
        assert geometry["content"]["width"] >= geometry["library"]["width"] - 2, geometry
        assert geometry["details"]["y"] >= geometry["content"]["bottom"], geometry
        from probes.aaos01_grouped_owner_loop import GroupedUI
        scroll_actions = []
        def wheel(_element, action, body):
            if action == "pointer_click":
                page.mouse.click(body["x"], body["y"])
                return
            assert action == "wheel", action
            page.mouse.move(body["x"], body["y"])
            page.mouse.wheel(body["deltaX"], body["deltaY"])
        control = GroupedUI(lambda script:page.evaluate("() => {"+script+"}"),
            lambda script:page.wait_for_function("() => {"+script+"}"),
            lambda using, selector:page.locator("xpath="+selector), wheel, scroll_actions)
        control.click_revealed_selector("//section[@aria-label='知识库文档视图']//button[@aria-label='打开文档 引用目标 1 · 独立历史正文']")
        reader = page.get_by_role("region", name="阅读与编辑文档视图", exact=True)
        editor = reader.get_by_role("textbox", name="文档草稿")
        editor.wait_for()
        assert "绑定历史正文 1 v1" in editor.inner_text()
        reader_geometry = reader.evaluate("""node => {
          const box = el => { const r=el.getBoundingClientRect();
            return {width:r.width,bottom:r.bottom,y:r.y}; };
          return {reader:box(node),document:box(node.querySelector('.ui-reader-document')),
            details:box(node.querySelector('.ui-reader-details'))};
        }""")
        assert reader_geometry["document"]["width"] >= reader_geometry["reader"]["width"] - 2, reader_geometry
        assert reader_geometry["details"]["y"] >= reader_geometry["document"]["bottom"], reader_geometry
        calls = page.evaluate("() => window.__A0_DOCUMENT_FIXTURE__.calls")
        assert not any(call["operation"] == "document_draft" for call in calls), calls
        reader_shot = ARTIFACTS / f"narrow-dock-reader-{theme}-{viewport[0]}.png"
        page.screenshot(path=str(reader_shot), full_page=True)
        return {"evidence":"SIMULATED_HOST_CORE_FIXTURE", "theme":theme, "viewport":viewport[0],
            "library_geometry":geometry, "reader_geometry":reader_geometry,
            "real_split_and_document_click":True, "document_id":"a0_target_1",
            "scroll_actions":scroll_actions,
            "library_screenshot":_recorded(library_shot), "reader_screenshot":_recorded(reader_shot)}
    finally:
        context.close()


def canonical_host_surface(browser, problems: list[str]) -> dict[str, object]:
    """Render the formal Tauri host UI in a real Chromium engine, once, and read its affordances.

    Until now this job only ever drove the browser *fallback* surface: `SpaceView` mounts the
    canonical spaces only when `window.__TAURI__` exists. WebView2 is the same engine family as
    Chromium, so this is where a host-only affordance such as the directory picker becomes a
    measurement rather than a jsdom assumption. It does not open a native dialog, and claims none.
    """
    label, width, height, scale = DESKTOP_MATRIX[0]
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=scale,
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.on("pageerror", lambda error: problems.append(f"canonical-pageerror:{error}"))
    page.on(
        "console",
        lambda message: problems.append(f"canonical-console:{message.text}")
        if message.type == "error" else None,
    )

    def route_api(route: Route) -> None:
        path = urlsplit(route.request.url).path
        if path.startswith(f"{API_PREFIX}/") or path.startswith(f"{WORKSPACE_PREFIX}/api/"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(api_payload(route.request.url)),
            )
        else:
            route.continue_()

    context.add_init_script(host_bridge_stub())
    page.route("**/*", route_api)
    page.goto(URL, wait_until="networkidle")

    assert page.evaluate("() => Boolean(window.__TAURI__?.core?.invoke)"), "the host stub did not reach the page"
    # The desktop surface names its own liveness, which the browser fallback never shows; that is
    # the discriminator between "mounted the host UI" and "silently rendered the fallback shell".
    page.locator(".ui-page-navigation").first.wait_for()
    liveness = page.locator('.status-bar .status-pill[data-status="available"][title="本地连接可用"]')
    liveness.wait_for(state="visible")
    assert "本地可用" in liveness.inner_text(), "no desktop liveness on the surface"
    assert page.get_by_text("本地桌面恢复").count() == 0, "the canonical surface fell back to the recovery shell"

    # A confirmed host fixture must retain usable diagnostics, not silently become preview.
    check_shell_pointer_targets(page)
    diagnostic = page.locator(".top-nav-right").get_by_role("button", name="运行诊断", exact=True)
    diagnostic.click()
    diagnostic_dialog = page.get_by_role("dialog", name="运行诊断", exact=True)
    diagnostic_dialog.wait_for()
    diagnostic_dialog.get_by_role("button", name="关闭运行诊断", exact=True).click()
    diagnostic_dialog.wait_for(state="detached")
    diagnostic.wait_for()
    page.wait_for_function("() => document.activeElement === document.querySelector('.top-nav-right [data-diagnostic-trigger=\"true\"]')")

    # Import/template regression belongs to the explicit canonical compatibility route.
    page.evaluate("location.hash = 'space=library'")
    page.get_by_role("heading", name="资料库").first.wait_for()
    folder = page.locator("input[aria-label='选择文件夹']")
    folder.wait_for()
    # `选择文件夹` exists only on the canonical library surface, so its presence is also the proof
    # that this page really mounted the host UI rather than the fallback one.
    affordance = folder.evaluate(
        "(node) => ({directory: node.webkitdirectory === true, multiple: node.multiple,"
        " hasDirectoryAttribute: node.hasAttribute('directory')})"
    )
    assert affordance == {"directory": True, "multiple": True, "hasDirectoryAttribute": True}, affordance
    single_file_inputs = page.locator("input[aria-label='导入原件']").count()
    assert single_file_inputs == 1, single_file_inputs

    # The frame must show the surface its name claims. read_navigation_levels() navigates away
    # to the learning space, so capturing after it produced a file called
    # "canonical-host-library-*.png" that actually depicted 学习 - and the ledger row citing it
    # as library evidence inherited that mismatch.
    shot = ARTIFACTS / f"canonical-host-library-{label}.png"
    page.screenshot(path=str(shot), full_page=True)
    # The one genuinely new visible surface on this product entry, asserted here because nothing
    # guarded it before: deleting the launcher entirely left every prior gate green.
    templates = read_template_surface(page, label)
    navigation = read_navigation_levels(page)
    # The navigation probe ends on the learning space; keep that frame under its own name.
    navigation_shot = ARTIFACTS / f"canonical-host-learning-{label}.png"
    page.screenshot(path=str(navigation_shot), full_page=True)
    result: dict[str, object] = {
        "viewport": label,
        "host_bridge_stubbed": True,
        "recovery_shell": False,
        "diagnostic_center": {"ready_trigger_required": True, "opened_and_closed": True, "focus_restored": True},
        "canonical_library_mounted": True,
        "single_file_import_inputs": single_file_inputs,
        "folder_affordance": affordance,
        "template_workspace": templates,
        "navigation_levels": navigation,
        "screenshot": _recorded(shot),
        "navigation_screenshot": _recorded(navigation_shot),
    }
    context.close()
    # Separate contexts: the outage fixture and the narrow windows must not contaminate the
    # affordance run above, and each declares its own viewport rather than inheriting one.
    result["template_roundtrip"] = [read_template_roundtrip(browser, viewport, problems, theme)
        for viewport in DESKTOP_MATRIX if viewport[0] in ("900x800@100", "640x480@100")
        for theme in AAOS_THEME_IDS]
    result["template_unreadable"] = read_template_failure(browser, problems)
    result["template_reachability"] = [
        read_template_reachability(browser, viewport, problems)
        for viewport in DESKTOP_MATRIX
        if viewport[0] in TEMPLATE_NARROW_VIEWPORTS
    ]
    result["library_geometry"] = [
        read_library_geometry(browser, viewport, problems)
        for viewport in DESKTOP_MATRIX
        if viewport[0] in LIBRARY_GEOMETRY_VIEWPORTS
    ]
    result["semantic_reading"] = [read_semantic_reading(browser, viewport, problems, theme)
        for viewport in DESKTOP_MATRIX if viewport[0] in ("1440x1000@100", "640x800@100", "640x480@100",
            "1920x1080@125", "1920x1080@150", "1920x1080@200")
        for theme in ("blueprint", "blueprint-light")]
    result["semantic_reading"].append(read_semantic_reading(
        browser, ("390x844@100", 390, 844, 1), problems, "cosmic"))
    result["narrow_dock_reading"] = [read_narrow_dock_library(browser, problems, theme)
        for theme in AAOS_THEME_IDS]
    result["narrow_dock_reading"].append(read_narrow_dock_library(browser, problems, "cosmic", ("1600x1000@125",1280,800,1.25)))
    result["top_navigation"] = [read_top_navigation(browser, viewport, problems, "cosmic")
        for viewport in (("1672x941@100",1672,941,1), ("390x844@100",390,844,1),
            ("640x480@100",640,480,1), ("640x800@100",640,800,1),
            ("1920x1080@125",1536,864,1.25), ("1920x1080@150",1280,720,1.5),
            ("1920x1080@200",960,540,2))]
    return result


def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    process, log = start_vite(RUNTIME / "a0-canonical-vite.log")
    errors: list[str] = []
    viewports: dict[str, object] = {}
    themes: dict[str, object] = {}
    canonical_problems: list[str] = []
    canonical: dict[str, object] = {}
    try:
        with sync_playwright() as playwright:
            browser_options = {"headless":True}
            if os.name == "nt":
                chromium = _declared_tool("ext.toolchains.playwright-chromium","playwright-chromium")
                if not chromium:
                    raise RuntimeError("Declared playwright-chromium executable is missing; no automatic install")
                declared_build = next((p for p in Path(chromium).parts if p.startswith("chromium-")),None)
                expected_build = next((p for p in Path(playwright.chromium.executable_path).parts if p.startswith("chromium-")),None)
                if not declared_build or declared_build!=expected_build:
                    raise RuntimeError("Declared Chromium build does not match this Playwright runtime")
                browser_options["executable_path"] = chromium
            browser = playwright.chromium.launch(**browser_options)
            for label, width, height, scale in DESKTOP_MATRIX:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=scale,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(f"pageerror:{error}"))
                page.on(
                    "console",
                    lambda message: errors.append(f"console:{message.text}")
                    if message.type == "error" else None,
                )

                def route_api(route: Route) -> None:
                    path = urlsplit(route.request.url).path
                    if path.startswith(f"{API_PREFIX}/") or path.startswith(
                        f"{WORKSPACE_PREFIX}/api/"
                    ):
                        route.fulfill(
                            status=200,
                            content_type="application/json",
                            body=json.dumps(api_payload(route.request.url)),
                        )
                    else:
                        route.continue_()

                page.route("**/*", route_api)
                page.goto(URL, wait_until="networkidle")
                page.get_by_role("heading", name="今日工作台", exact=True).first.wait_for()
                drawer_result = check_navigation_drawer(page)
                geometry = check_geometry(
                    measure_geometry(page, chrome_bands(page)),
                    width=width, height=height, scale=scale, bands=chrome_bands(page),
                )

                accessibility = {}
                brand_identity = {}
                shell_targets = {}
                for theme in AAOS_THEME_IDS:
                    select_ui_theme(page, theme)
                    page.wait_for_timeout(200)
                    check_geometry(measure_geometry(page, chrome_bands(page)),
                                   width=width, height=height, scale=scale, bands=chrome_bands(page))
                    accessibility[theme] = check_status_accessibility(page)
                    brand_identity[theme] = check_brand_identity(page, theme, (label, width, height, scale))
                    # Browser preview has no confirmed Core working-state identity: diagnostics
                    # stay quarantined and expose their explicit connection recheck action.
                    shell_targets[theme] = check_shell_pointer_targets(page, diagnostics_suspended=True)
                select_ui_theme(page, "black")

                faults = status_fault_selftest(page, width, height, scale) if (width, height) == (640, 480) else []

                page.get_by_role("button", name="打开全局命令").click()
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.get_by_role("button", name="关闭全局命令").click()
                # Focus contract, measured in the browser rather than in jsdom: closing
                # with Escape returns focus to the trigger that opened it, and Ctrl+K
                # lands the caret in the search field.
                page.get_by_role("button", name="打开全局命令").click()
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.keyboard.press("Escape")
                page.get_by_role("dialog", name="全局命令").wait_for(state="detached")
                # Radix restores focus on the next frame, so read it after a settle rather
                # than in the same tick as the detach.
                page.wait_for_timeout(200)
                restored = page.evaluate(
                    "() => { const el = document.activeElement;"
                    " return el && {tag: el.tagName, label: el.getAttribute('aria-label'), cls: el.className}; }"
                )
                assert restored == {"tag": "BUTTON", "label": "打开全局命令", "cls": "command-trigger"}, restored
                page.keyboard.press("Control+k")
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.wait_for_timeout(200)
                opened = page.evaluate(
                    "() => { const el = document.activeElement; return el && {tag: el.tagName, label: el.getAttribute('aria-label')}; }"
                )
                assert opened == {"tag": "INPUT", "label": "搜索空间或命令"}, opened
                page.keyboard.press("Escape")
                page.get_by_role("dialog", name="全局命令").wait_for(state="detached")
                page.evaluate("location.hash = 'space=learning'")
                page.get_by_role("heading", name="学习", exact=True).first.wait_for()
                assert page.get_by_role("button", name="视觉课件").count() == 0
                assert page.get_by_role("button", name="空间记忆").count() == 0
                page.get_by_role("button", name="展开活动坞").click()
                assert page.get_by_role("button", name="取消投递（不可用）").count() == 0

                if label == DESKTOP_MATRIX[0][0]:
                    glows: dict[str, str] = {}
                    for theme in AAOS_THEME_IDS:
                        select_ui_theme(page, theme)
                        page.wait_for_timeout(150)
                        applied = page.evaluate("document.documentElement.dataset.aaosTheme")
                        brand = check_brand_identity(page, theme, (label, width, height, scale))["status_mark"]
                        surface = page.evaluate("getComputedStyle(document.body).backgroundColor")
                        assert applied == theme, (applied, theme)
                        assert brand and brand["complete"], (theme, brand)
                        asset_theme = BRAND_THEME_ASSETS[theme]
                        assert asset_theme in (brand["src"] or ""), brand
                        # The asset on disk is the expectation: an <img> whose file went missing
                        # keeps its 31x28 box and paints nothing, which a DOM-only check would
                        # read as a correct brand mark.
                        expected = png_size(BRAND_ASSET_DIR / f"aaos-brand-mark-{asset_theme}.png")
                        assert tuple(brand["decoded"]) == expected, (theme, brand["decoded"], expected)
                        # The reference cabin declares a 38px desktop mark; its CSS box
                        # scales the intrinsic ratio instead of the legacy HTML fallback slot.
                        # Keep the decoded-file, aspect-ratio and target-size assertions.
                        assert brand["box"][0] == 38.0, brand
                        drawn = brand["box"][0] / brand["box"][1]
                        assert abs(drawn - expected[0] / expected[1]) < 0.02, (theme, drawn, expected)
                        assert 20 <= brand["box"][1] <= 40, (theme, brand["box"])
                        # The light effect is part of the mark now, and it is the theme's own: a
                        # glow that never changed across themes would mean the token is dead CSS.
                        assert brand["glow"].startswith("drop-shadow"), (theme, brand["glow"])
                        assert brand["token"], (theme, brand)
                        glows[theme] = brand["token"]
                        shot = ARTIFACTS / f"canonical-theme-{theme}-{label}.png"
                        page.screenshot(path=str(shot))
                        themes[theme] = {
                            "root_attribute": applied,
                            "brand_mark": brand,
                            "body_surface": surface,
                            "screenshot": _recorded(shot),
                        }
                    assert len({glows[id] for id in ("black", "white", "cosmic")}) == 3, glows
                    assert all(glows[id] for id in AAOS_THEME_IDS), glows
                    select_ui_theme(page, "black")

                screenshot = ARTIFACTS / f"canonical-shell-{label}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                viewports[label] = {
                    "geometry": geometry,
                    "navigation_drawer": drawer_result,
                    "status_accessibility": accessibility,
                    "brand_identity": brand_identity,
                    "shell_targets": shell_targets,
                    "status_fault_selftest": faults,
                    "screenshot": _recorded(screenshot),
                }
                context.close()
            canonical = canonical_host_surface(browser, canonical_problems)
            browser.close()
    finally:
        stop_vite(process, log)

    assert not errors, errors
    assert not canonical_problems, canonical_problems
    revision = source_revision()
    report = {
        "schema": "archeaxis/canonical-browser-smoke/v4",
        "status": "PASS",
        "source_revision": revision,
        "errors": errors,
        "viewports": viewports,
        "themes": themes,
        "canonical_host_surface": canonical,
        "canonical_host_problems": canonical_problems,
    }
    output = ARTIFACTS / "canonical-browser-smoke.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
