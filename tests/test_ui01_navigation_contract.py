from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


class _RailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_rail = False
        self._button_depth = 0
        self._button_text: list[str] = []
        self._button_label: str | None = None
        self.daily_entries: list[str] = []
        self.system_entries: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "aside" and values.get("id") == "rail":
            self._inside_rail = True
            return
        if not self._inside_rail or tag != "button":
            return
        self._button_depth = 1
        self._button_text = []
        self._button_label = values.get("aria-label") or values.get("title")
        if "system-entry" in (values.get("class") or "").split():
            self._button_depth = -1

    def handle_endtag(self, tag: str) -> None:
        if tag == "aside" and self._inside_rail and self._button_depth == 0:
            self._inside_rail = False
            return
        if tag != "button" or not self._inside_rail or self._button_depth == 0:
            return
        label = self._button_label or "".join(self._button_text).strip()
        if self._button_depth == -1:
            self.system_entries.append(label)
        else:
            self.daily_entries.append(label)
        self._button_depth = 0
        self._button_text = []
        self._button_label = None

    def handle_data(self, data: str) -> None:
        if self._inside_rail and self._button_depth:
            self._button_text.append(data)


def test_ui01_exposes_only_four_daily_rail_entries_and_separates_system() -> None:
    """TP-UI01: daily navigation is four entries; System is a distinct bottom entry."""

    root = Path(__file__).resolve().parents[1]
    parser = _RailParser()
    parser.feed((root / "app/workspace/ui/index.html").read_text(encoding="utf-8"))

    assert parser.daily_entries == ["首页", "资料与知识", "学习"]
    assert parser.system_entries == ["系统"]
