"""Tests for shared.json_canvas (ADS-003: JSON Canvas format adoption)."""

import pytest

from shared.json_canvas import (
    CanvasError,
    make_edge_id,
    make_node_id,
    validate_json_canvas,
)


class TestValidateJsonCanvas:
    def test_valid_minimal(self) -> None:
        validate_json_canvas({"nodes": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50}]})

    def test_valid_with_edges(self) -> None:
        validate_json_canvas({
            "nodes": [
                {"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50},
                {"id": "b", "type": "text", "x": 200, "y": 0, "width": 100, "height": 50},
            ],
            "edges": [
                {"id": "e1", "fromNode": "a", "toNode": "b", "fromSide": "right", "toSide": "left", "fromEnd": "none", "toEnd": "arrow"},
            ],
        })

    def test_preserves_unknown_fields(self) -> None:
        data = {"nodes": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50, "custom": "kept"}], "meta": {"foo": 1}}
        result = validate_json_canvas(data)
        assert result["nodes"][0]["custom"] == "kept"
        assert result["meta"]["foo"] == 1

    def test_rejects_non_dict(self) -> None:
        with pytest.raises(CanvasError, match="must be object"):
            validate_json_canvas([])

    def test_rejects_bad_type(self) -> None:
        with pytest.raises(CanvasError, match="invalid type"):
            validate_json_canvas({"nodes": [{"id": "a", "type": "bogus", "x": 0, "y": 0, "width": 100, "height": 50}]})

    def test_rejects_non_integer_coords(self) -> None:
        with pytest.raises(CanvasError, match="must be integer"):
            validate_json_canvas({"nodes": [{"id": "a", "type": "text", "x": 0.5, "y": 0, "width": 100, "height": 50}]})

    def test_rejects_duplicate_node_id(self) -> None:
        with pytest.raises(CanvasError, match="duplicate"):
            validate_json_canvas({
                "nodes": [
                    {"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50},
                    {"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50},
                ]
            })

    def test_rejects_invalid_color(self) -> None:
        with pytest.raises(CanvasError, match="invalid color"):
            validate_json_canvas({"nodes": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50, "color": "bogus"}]})

    def test_accepts_color_preset(self) -> None:
        validate_json_canvas({"nodes": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50, "color": "3"}]})

    def test_accepts_hex_color(self) -> None:
        validate_json_canvas({"nodes": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 50, "color": "#FF8800"}]})


class TestIdGeneration:
    def test_node_id_unique(self) -> None:
        ids = {make_node_id() for _ in range(100)}
        assert len(ids) == 100

    def test_edge_id_unique(self) -> None:
        ids = {make_edge_id() for _ in range(100)}
        assert len(ids) == 100

    def test_ids_are_strings(self) -> None:
        assert isinstance(make_node_id(), str)
        assert isinstance(make_edge_id(), str)
