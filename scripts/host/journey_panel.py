"""Host-facing journey panel: the project-side surface the host mounts (R10).

`docs/integrations/DEEPTUTOR_PRODUCT_BASE.md` records DeepTutor v1.5.17 as an
**immutable external dependency** with no upstream patch applied, and states that
"branding, route mounting and authority-adapter injection remain project-side
integration work". This is that project-side piece: a mountable URL that reads the
Core through `shared/core_client.py` and shows the two state views side by side.

What it serves (loopback only):

  GET /                     one page with two clearly separate panels
  GET /api/state?item_key=  learner reading and machine reading, as the Core reports them
  GET /api/health           whether the Core is reachable right now

Rules it keeps:

  * it never invents state. If the Core is unreachable, or an item has no history,
    the payload says so with `reachable: false` / `null` and the page shows that
    instead of zeros that look like real progress;
  * the learner panel and the machine panel are separate readings of the same Core,
    and learner progress is never rendered as machine competence;
  * the launch token is read from an environment variable and never printed, never
    written into the page and never accepted from a query string;
  * the panel is a projection: deleting it loses no truth, because the Core owns it.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE_CLIENT = REPO / "shared" / "core_client.py"
DEFAULT_ITEM_KEY = "card-host-panel"


def _load_core_client():
    """Load the host adapter by path so this module has no import-time coupling."""
    spec = importlib.util.spec_from_file_location("core_client_for_panel", CORE_CLIENT)
    if spec is None or spec.loader is None:  # pragma: no cover - broken checkout
        raise RuntimeError(f"cannot load {CORE_CLIENT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core_client = _load_core_client()

# The Core's routes live under one prefix and `call` expects a full path, so the
# panel takes the prefix from the adapter instead of hard-coding a second copy.
CORE_BASE = getattr(core_client, "BASE", "/api/v1")

PANEL_NOTE = (
    "two separate readings of the same Core: the learner panel shows human records, "
    "the machine panel shows machine capability receipts; learner progress is never "
    "presented as machine competence"
)
MEMBER_NOTE = (
    "the members imported from this container, not its whole inventory; readable means a "
    "transform exists, not that the content was understood"
)


def build_state(base_url: str, item_key: str, launch_token: str | None, call=None) -> tuple[int, dict]:
    """Assemble the panel payload. Returns (http_status, payload)."""
    call = call or core_client.call
    # safe="": a slash in an item key must not be allowed to add a path segment
    quoted = urllib.parse.quote(item_key, safe="")
    status, body = call(base_url, "GET", f"{CORE_BASE}/learning/items/{quoted}/state", launch_token)
    payload: dict = {"item_key": item_key, "note": PANEL_NOTE}
    if status != 200 or not isinstance(body, dict):
        payload["core"] = {
            "reachable": False,
            "status": status,
            "reason": body.get("error") if isinstance(body, dict) else str(body)[:200],
        }
        payload["learner"] = None
        payload["machine"] = None
        payload["rendering"] = "no state is shown while the Core is unreachable"
        return 503, payload
    payload["core"] = {"reachable": True, "status": status}
    payload["learner"] = body.get("learner")
    payload["machine"] = body.get("machine")
    return 200, payload


def build_health(base_url: str, launch_token: str | None, call=None) -> tuple[int, dict]:
    call = call or core_client.call
    status, body = call(base_url, "GET", f"{CORE_BASE}/system/version", launch_token)
    reachable = status == 200
    payload = {
        "reachable": reachable,
        "status": status,
        "core_url": base_url,
        "version": body if reachable and not isinstance(body, dict) else (body or {}).get("version"),
    }
    if not reachable:
        payload["reason"] = body.get("error") if isinstance(body, dict) else str(body)[:200]
    return (200 if reachable else 503), payload


def build_members(base_url: str, source_id: str, launch_token: str | None, call=None) -> tuple[int, dict]:
    """What is inside one container, and which parts were read (R15/F15).

    The same rule as the state endpoint applies: a Core that cannot be reached returns
    503 with no member list at all, and a container the Core does not know is reported
    as such, because an empty table would look like "this container holds nothing".
    """
    call = call or core_client.call
    # safe="": a slash in a source id must not be allowed to add a path segment
    quoted = urllib.parse.quote(source_id, safe="")
    status, body = call(base_url, "GET", f"{CORE_BASE}/sources/{quoted}/members", launch_token)
    payload: dict = {"container_source_id": source_id, "note": MEMBER_NOTE}
    if status == 404:
        payload.update(
            {
                "core": {"reachable": True, "status": status},
                "reason": "the Core does not know this source",
                "member_count": None,
                "members": None,
            }
        )
        return 404, payload
    if status != 200 or not isinstance(body, dict):
        payload.update(
            {
                "core": {
                    "reachable": False,
                    "status": status,
                    "reason": body.get("error") if isinstance(body, dict) else str(body)[:200],
                },
                "member_count": None,
                "members": None,
                "rendering": "no member list is shown while the Core cannot answer",
            }
        )
        return 503, payload
    payload["core"] = {"reachable": True, "status": status}
    payload["member_count"] = body.get("member_count")
    payload["readable_count"] = body.get("readable_count")
    payload["custody_only_count"] = body.get("custody_only_count")
    payload["members"] = body.get("members")
    payload["core_note"] = body.get("note")
    return 200, payload


PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>ArcheAxis 学习面板（宿主投影）</title>
<style>
 body {{ font-family: system-ui, "Microsoft YaHei", sans-serif; margin: 0; background: #12141a; color: #e8e8ea; }}
 header {{ padding: 16px 24px; background: #1b1e27; border-bottom: 1px solid #2a2f3c; }}
 h1 {{ font-size: 18px; margin: 0 0 4px; }}
 .sub {{ color: #9aa1b1; font-size: 12px; }}
 main {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 24px; }}
 section {{ background: #1b1e27; border: 1px solid #2a2f3c; border-radius: 10px; padding: 16px; }}
 h2 {{ font-size: 14px; margin: 0 0 12px; color: #cfd4e0; }}
 .learner h2 {{ color: #7fd1a8; }}
 .machine h2 {{ color: #7fb2d1; }}
 dl {{ display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; margin: 0; font-size: 13px; }}
 dt {{ color: #9aa1b1; }}
 dd {{ margin: 0; }}
 .banner {{ margin: 16px 24px 0; padding: 12px 16px; border-radius: 8px; background: #3a2326; border: 1px solid #7a3b42; color: #ffb4bc; }}
 .note {{ color: #8b93a5; font-size: 12px; margin-top: 12px; }}
 form {{ margin: 0 24px; display: flex; gap: 8px; align-items: center; }}
 input, button {{ background: #232734; color: #e8e8ea; border: 1px solid #343a4a; border-radius: 6px; padding: 6px 10px; font-size: 13px; }}
 button {{ cursor: pointer; }}
</style>
</head>
<body>
<header>
  <h1>ArcheAxis 学习面板</h1>
  <div class="sub">宿主投影面（project-side）：只读 Core，经 shared/core_client.py；删除本页面不丢失任何真相</div>
</header>
<form onsubmit="load(event)">
  <label for="item">学习项</label>
  <input id="item" value="{item_key}" size="28">
  <button type="submit">刷新</button>
  <span id="health" class="sub"></span>
</form>
<div id="banner"></div>
<main>
  <section class="learner">
    <h2>学习者记录（人类）</h2>
    <dl id="learner"></dl>
  </section>
  <section class="machine">
    <h2>机器能力收据（AI）</h2>
    <dl id="machine"></dl>
  </section>
</main>
<div class="note">{note}</div>
<section class="container-members">
  <h2>容器成员（容器 → 文件）</h2>
  <form onsubmit="loadMembers(event)">
    <label for="source">容器 source_id</label>
    <input id="source" size="34" placeholder="src_...">
    <button type="submit">查看成员</button>
  </form>
  <div id="members-banner" class="sub"></div>
  <table id="members">
    <thead><tr><th>成员</th><th>已读取</th><th>作业</th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="note" id="members-note">{member_note}</div>
</section>
<script>
function rows(target, pairs) {{
  const el = document.getElementById(target);
  el.innerHTML = "";
  for (const [k, v] of pairs) {{
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = (v === null || v === undefined) ? "—" : String(v);
    el.append(dt, dd);
  }}
}}
async function load(event) {{
  if (event) event.preventDefault();
  const item = document.getElementById("item").value;
  const response = await fetch("/api/state?item_key=" + encodeURIComponent(item));
  const data = await response.json();
  const banner = document.getElementById("banner");
  if (!data.core.reachable) {{
    banner.className = "banner";
    banner.textContent = "Core 不可达（状态 " + data.core.status + "）：" + (data.core.reason || "") + " — " + data.rendering;
    rows("learner", []); rows("machine", []);
    return;
  }}
  banner.className = ""; banner.textContent = "";
  const learner = data.learner || {{}};
  rows("learner", [
    ["学习项", data.item_key],
    ["事件数", learner.event_count],
    ["连续正确", learner.correct_streak],
    ["已排程复习", learner.scheduled_events],
    ["未排程（诚实记录）", learner.unscheduled_events],
    ["引用修订", (learner.references || []).map(r => r.knowledge_id + (r.active ? "（当前）" : "（已被超越）")).join("，") || "—"],
    ["记录方式", learner.recording],
  ]);
  const machine = data.machine || {{}};
  rows("machine", [
    ["状态", machine.status],
    ["说明", machine.note],
  ]);
}}
async function health() {{
  const response = await fetch("/api/health");
  const data = await response.json();
  document.getElementById("health").textContent = data.reachable
    ? "Core 在线（" + data.core_url + "）" : "Core 离线：" + (data.reason || "");
}}
async function loadMembers(event) {{
  if (event) event.preventDefault();
  const source = document.getElementById("source").value.trim();
  const banner = document.getElementById("members-banner");
  const body = document.querySelector("#members tbody");
  body.innerHTML = "";
  if (!source) {{
    banner.className = "sub"; banner.textContent = "请填写容器 source_id";
    return;
  }}
  const response = await fetch("/api/members?source_id=" + encodeURIComponent(source));
  const data = await response.json();
  if (response.status === 404) {{
    banner.className = "sub"; banner.textContent = "Core 不认识这个源：" + source;
    return;
  }}
  if (!data.core || !data.core.reachable) {{
    banner.className = "sub";
    banner.textContent = "Core 无法回答（状态 " + (data.core ? data.core.status : "?") + "）："
      + ((data.core && data.core.reason) || "") + " — " + (data.rendering || "");
    return;
  }}
  banner.className = "sub";
  banner.textContent = "成员 " + data.member_count + " 个：已读取 " + data.readable_count
    + "，仅保管 " + data.custody_only_count;
  for (const member of (data.members || [])) {{
    const row = document.createElement("tr");
    const name = document.createElement("td"); name.textContent = member.member;
    const readable = document.createElement("td"); readable.textContent = member.readable ? "是" : "否";
    const job = document.createElement("td"); job.textContent = member.job_id || "—";
    row.append(name, readable, job);
    body.append(row);
  }}
  if (data.core_note) document.getElementById("members-note").textContent = data.core_note;
}}
load(); health();
</script>
</body>
</html>
"""


def render_page(item_key: str) -> str:
    return PAGE.format(item_key=item_key, note=PANEL_NOTE, member_note=MEMBER_NOTE)


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "ArcheAxisJourneyPanel/1"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server's interface
        parsed = urllib.parse.urlparse(self.path)
        token = os.environ.get(self.server.token_env)  # type: ignore[attr-defined]
        if parsed.path == "/":
            self._send(200, render_page(self.server.item_key).encode("utf-8"), "text/html; charset=utf-8")  # type: ignore[attr-defined]
            return
        if parsed.path == "/api/health":
            status, payload = build_health(self.server.core_url, token)  # type: ignore[attr-defined]
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        if parsed.path == "/api/members":
            query = urllib.parse.parse_qs(parsed.query)
            source_id = (query.get("source_id") or [""])[0]
            if not source_id:
                self._send(
                    400,
                    json.dumps({"error": "source_id is required"}, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
                return
            status, payload = build_members(self.server.core_url, source_id, token)  # type: ignore[attr-defined]
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        if parsed.path == "/api/state":
            query = urllib.parse.parse_qs(parsed.query)
            item_key = (query.get("item_key") or [self.server.item_key])[0]  # type: ignore[attr-defined]
            status, payload = build_state(self.server.core_url, item_key, token)  # type: ignore[attr-defined]
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        self._send(404, json.dumps({"error": "not found", "path": parsed.path}).encode("utf-8"), "application/json")

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - base signature
        # never log the request line blindly: a token must not be able to land in a log
        with contextlib.suppress(Exception):
            sys.stderr.write("panel: %s\n" % (format % args).split("?")[0])


def serve(core_url: str, item_key: str, port: int, token_env: str) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PanelHandler)
    httpd.core_url = core_url  # type: ignore[attr-defined]
    httpd.item_key = item_key  # type: ignore[attr-defined]
    httpd.token_env = token_env  # type: ignore[attr-defined]
    return httpd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-url", required=True, help="base URL of a running Core, e.g. http://127.0.0.1:64436")
    parser.add_argument("--item-key", default=DEFAULT_ITEM_KEY)
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument(
        "--token-env",
        default="ARCHEAXIS_LAUNCH_TOKEN",
        help="name of the environment variable holding the launch token (never passed on the command line)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    httpd = serve(args.core_url, args.item_key, args.port, args.token_env)
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    host, port = httpd.server_address[:2]
    print(
        json.dumps(
            {
                "panel_url": f"http://{host}:{port}/",
                "core_url": args.core_url,
                "item_key": args.item_key,
                "token_env": args.token_env,
                "token_present": bool(os.environ.get(args.token_env)),
                "note": "loopback only; the token is read from the environment and never printed",
            },
            ensure_ascii=False,
        )
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
