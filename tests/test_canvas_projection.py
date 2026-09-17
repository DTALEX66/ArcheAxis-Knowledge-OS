"""Tests for persisting accepted JSON Canvas worker projections."""

from shared.canvas import persist_worker_projection


def test_persist_worker_projection_replaces_snapshot_rows(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("shared.canvas.delete_canvas", lambda canvas_id: calls.append(("delete", canvas_id)) or True)
    monkeypatch.setattr("shared.canvas.insert", lambda table, row: calls.append((table, row)))

    result = persist_worker_projection(
        "canvas_demo",
        {
            "node_geometry": [
                {"node_id": "n1", "type": "text", "geometry": {"x": 12, "y": 8}},
                {"node_id": "n2", "type": "file", "geometry": {}},
            ],
            "edges": [{"id": "e1", "fromNode": "n1", "toNode": "n2", "label": "uses"}],
        },
    )

    assert result == {"canvas_id": "canvas_demo", "nodes": 2, "edges": 1}
    assert calls[0] == ("delete", "canvas_demo")
    assert calls[1][0] == "canvases"
    node_rows = [row for table, row in calls if table == "canvas_nodes"]
    edge_rows = [row for table, row in calls if table == "canvas_edges"]
    assert node_rows[0]["x"] == 12
    assert node_rows[0]["object_type"] == "text"
    assert edge_rows[0]["source_node_id"] == "n1"

