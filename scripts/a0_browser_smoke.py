#!/usr/bin/env python3
"""Real-browser geometry and theme gate for the formal Tauri/React desktop UI (SUP-022).

This proves the rendered shell in Chromium at desktop viewports; it does not prove the
installed WebView2 host, physical IME, or Owner acceptance, which stay separate Q14 tiers.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
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
    # 900 and 840 sit either side of the shell's own 900px breakpoint; without them a change
    # scoped to the 601-900 band was never exercised by the gate.
    ("900x800@100", 900, 800, 1.0),
    ("840x800@100", 840, 800, 1.0),
    ("1920x1080@125", 1536, 864, 1.25),
    ("1920x1080@150", 1280, 720, 1.5),
    ("1920x1080@200", 960, 540, 2.0),
)
AAOS_THEME_IDS = ("black", "white", "cosmic")

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


def _declared_node() -> str | None:
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
            if node.get("resource_id") == "ext.toolchains.nodejs-lts" or node.get("name") == "nodejs-lts":
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
            if candidate and Path(candidate).is_file():
                return str(candidate)
    return None


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
    documents_list: { documents: [] },
    learning_items: { items: [] },
    capabilities_list: { capabilities: [] },
    anchors_list: { anchors: [] },
    source_original: __A0_ORIGINAL__,
    workspace_backups: { backups: [] },
    system_version: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 1,
                      sqlite_version: "3.51.3" },
  };
  window.__TAURI__ = {
    core: {
      invoke: async (command, request) => {
        if (command === "recovery_status") {
          return { state: "ready", safe_mode: false, backend_available: true,
                   message: "browser smoke host", backups: [], external_dev: false };
        }
        if (command === "core_command") {
          return { status: 200, body: bodies[request?.request?.operation] ?? {} };
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


def host_bridge_stub() -> str:
    import json

    return (
        HOST_BRIDGE_STUB_TEMPLATE.replace("__A0_SOURCES__", json.dumps([A0_SOURCE]))
        .replace("__A0_ORIGINAL__", json.dumps({
            "source_id": A0_SOURCE["source_id"],
            "name": A0_SOURCE["original_name"],
            "media_type": "text/plain",
            "sha256": A0_SOURCE["sha256"],
            "content_base64": A0_ORIGINAL_CONTENT,
        }))
    )


def read_navigation_levels(page) -> dict[str, object]:
    """UI-02 in a real layout engine: primary labels, secondary groups, tertiary object path."""
    # The icon span sits in the same button; only the label span carries text. Selecting the
    # label explicitly is what the requirement is about: a primary entry the user can read.
    labels = page.evaluate(
        """() => [...document.querySelectorAll("ul[aria-label='产品空间'] .space-rail-item > span:not(.space-rail-icon)")]
          .map((node) => ({ text: node.textContent.trim(), width: node.getBoundingClientRect().width }))"""
    )
    assert labels and all(entry["width"] > 8 for entry in labels), labels
    assert len(labels) == 9, labels
    assert [entry["text"] for entry in labels][:3] == ["工作台", "资料库", "导入"], labels

    sections = page.locator("ul[aria-label='资料库对象导航'] button")
    section_count = sections.count()
    assert section_count == 4, section_count
    widths = [sections.nth(index).bounding_box()["width"] for index in range(section_count)]
    assert all(width > 60 for width in widths), widths

    sections.filter(has_text="来源锚点").first.click()
    focused = page.evaluate("() => document.activeElement?.dataset?.section ?? null")
    assert focused == "anchors", focused

    page.locator("nav[aria-label='保留原件'] button").first.click()
    page.locator("nav[aria-label='对象导航路径']").wait_for()
    trail = page.inner_text("nav[aria-label='对象导航路径']")
    assert A0_SOURCE["source_id"] in trail, trail
    assert A0_SOURCE["source_revision"] in trail, trail

    page.locator('[data-space-id="learning"]').click()
    page.get_by_role("heading", name="学习").first.wait_for()
    review = page.locator("ul[aria-label='学习对象导航'] button").filter(has_text="复习队列")
    assert review.count() == 1, review.count()
    assert review.first.bounding_box()["width"] > 40
    return {
        "primary_label_count": len(labels),
        "secondary_section_count": section_count,
        "secondary_focused_region": focused,
        "tertiary_trail_identity": A0_SOURCE["source_id"],
        "learning_review_group_present": True,
    }


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
    page.locator("ul[aria-label='产品空间']").first.wait_for()
    assert page.get_by_text("后端状态：本地可用").first.is_visible(), "no desktop liveness on the surface"
    assert page.get_by_text("本地桌面恢复").count() == 0, "the canonical surface fell back to the recovery shell"

    page.locator('[data-space-id="library"]').click()
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
    navigation = read_navigation_levels(page)
    # The navigation probe ends on the learning space; keep that frame under its own name.
    navigation_shot = ARTIFACTS / f"canonical-host-learning-{label}.png"
    page.screenshot(path=str(navigation_shot), full_page=True)
    result: dict[str, object] = {
        "viewport": label,
        "host_bridge_stubbed": True,
        "recovery_shell": False,
        "canonical_library_mounted": True,
        "single_file_import_inputs": single_file_inputs,
        "folder_affordance": affordance,
        "navigation_levels": navigation,
        "screenshot": str(shot.relative_to(ROOT)),
        "navigation_screenshot": str(navigation_shot.relative_to(ROOT)),
    }
    context.close()
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
            browser = playwright.chromium.launch(headless=True)
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
                page.get_by_role("heading", name="工作台").first.wait_for()
                geometry = page.evaluate("""() => {
                    const box = (selector) => {
                      const rect = document.querySelector(selector)?.getBoundingClientRect();
                      return rect && {x:rect.x,y:rect.y,width:rect.width,height:rect.height,bottom:rect.bottom};
                    };
                    const context = document.querySelector('.context-subnav');
                    const bar = [...(document.querySelector('.status-bar')?.children ?? [])];
                    const overlaps = [];
                    for (let i = 0; i < bar.length; i++) for (let j = i + 1; j < bar.length; j++) {
                      const a = bar[i].getBoundingClientRect(), b = bar[j].getBoundingClientRect();
                      const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
                      const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                      if (width > 1 && height > 1) {
                        overlaps.push([bar[i].className || bar[i].tagName, bar[j].className || bar[j].tagName, +width.toFixed(1)]);
                      }
                    }
                    return {
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth,
                      devicePixelRatio: window.devicePixelRatio,
                      rail: box('.space-rail'),
                      dock: box('.activity-dock'),
                      main: box('.app-center'),
                      inspector: Boolean(document.querySelector('.inspector')),
                      context: Boolean(context) && getComputedStyle(context).display !== 'none',
                      statusBarOverlaps: overlaps,
                      motionFast: getComputedStyle(document.documentElement).getPropertyValue('--ax-motion-fast').trim(),
                    };
                }""")
                assert geometry["scrollWidth"] <= geometry["clientWidth"], geometry
                assert geometry["dock"]["bottom"] <= height + 0.5, geometry
                assert 140 <= geometry["rail"]["width"] <= 300, geometry
                assert geometry["main"]["x"] >= geometry["rail"]["width"] - 1, geometry
                assert geometry["main"]["bottom"] <= geometry["dock"]["y"] + 0.5, geometry
                assert not geometry["inspector"], geometry
                assert geometry["context"], geometry
                assert geometry["devicePixelRatio"] == scale, geometry
                assert not geometry["statusBarOverlaps"], geometry
                assert geometry["motionFast"] == "0ms", geometry
                if width <= 1200:
                    # 601..1200 is where the chrome narrows so the reading column can survive; the
                    # floor is what the stylesheet promises, and it once silently collapsed to 304px.
                    assert geometry["main"]["width"] >= 280, geometry

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
                page.locator('[data-space-id="learning"]').click()
                page.locator("#space-learning").wait_for()
                assert page.get_by_role("button", name="视觉课件").count() == 0
                assert page.get_by_role("button", name="空间记忆").count() == 0
                page.get_by_role("button", name="展开活动坞").click()
                assert page.get_by_role("button", name="取消投递（不可用）").count() == 0

                if label == DESKTOP_MATRIX[0][0]:
                    for theme in AAOS_THEME_IDS:
                        page.get_by_label("界面主题").select_option(theme)
                        page.wait_for_timeout(150)
                        applied = page.evaluate("document.documentElement.dataset.aaosTheme")
                        brand = page.locator(".status-bar-brand img").get_attribute("src") or ""
                        surface = page.evaluate("getComputedStyle(document.body).backgroundColor")
                        assert applied == theme, (applied, theme)
                        assert theme in brand, brand
                        shot = ARTIFACTS / f"canonical-theme-{theme}-{label}.png"
                        page.screenshot(path=str(shot))
                        themes[theme] = {
                            "root_attribute": applied,
                            "brand_mark": brand,
                            "body_surface": surface,
                            "screenshot": str(shot.relative_to(ROOT)),
                        }
                    page.get_by_label("界面主题").select_option("black")

                screenshot = ARTIFACTS / f"canonical-shell-{label}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                viewports[label] = {
                    "geometry": geometry,
                    "screenshot": str(screenshot.relative_to(ROOT)),
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
