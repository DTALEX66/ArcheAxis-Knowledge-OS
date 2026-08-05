from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "workspace" / "ui"


def test_cognitive_canvas_contract():
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'data-page="canvas"' not in html  # secondary nav is rendered from the JS registry
    assert 'id="page-canvas"' in html
    assert 'id="canvas-board"' in html
    assert "GOVERNED KNOWLEDGE CANVAS" in html
    assert "fetchJson('/kb/canvas')" in js
    assert "function createCanvas()" in js
    assert "function selectCanvas(index)" in js
    assert "function renderCanvas(canvas)" in js
    assert "edges.forEach" in js
    assert "候选研究不会自动写入画布" in html


def test_cognitive_canvas_replay_uses_readback_only():
    js = (UI / "assets" / "app.js").read_text(encoding="utf-8")
    assert "fetchJson('/workspace/api/lifecycle')" in js
    assert "执行回放：" in js
    assert "node.title" in js
    assert "node.object_id" not in js
    assert "node.node_id" not in js
