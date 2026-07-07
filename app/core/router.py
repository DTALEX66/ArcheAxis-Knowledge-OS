"""Attention router — loads policy from config/route_policy.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml

from app.schemas import AttentionDecision, CoreObject

RouteName = Literal["KB", "IR", "TASK"]

# ── Load policy ─────────────────────────────────────────

_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "route_policy.yaml"

with open(_POLICY_PATH, encoding="utf-8") as f:
    _P = yaml.safe_load(f)

RISK_KEYWORDS: list[str] = _P["risk_keywords"]
MODERATE_RISK_KEYWORDS: list[str] = _P["moderate_risk_keywords"]
LOW_VALUE_TEXTS: set[str] = set(_P["low_value_texts"])
COMMAND_MARKERS: list[str] = _P["command_markers"]
ROUTE_KEYWORDS: dict[RouteName, list[str]] = _P["route_keywords"]
SOURCE_HINTS: dict[RouteName, list[str]] = _P["source_hints"]
ROUTE_BASE_SCORE: dict[RouteName, float] = _P["route_base_score"]
ROUTE_PRIORITY: tuple[RouteName, ...] = tuple(_P["route_priority"])
_SCORING = _P["scoring"]

ROUTE_PRIORITY_TUPLE: tuple[RouteName, ...] = ROUTE_PRIORITY


# ── Helpers ─────────────────────────────────────────────


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _matched_keywords(haystack: str, keywords: list[str]) -> list[str]:
    normalized = _normalize(haystack)
    return [kw for kw in keywords if kw.lower() in normalized]


def _compact_terms(terms: list[str], limit: int = 6) -> str:
    shown = terms[:limit]
    suffix = "" if len(terms) <= limit else f" +{len(terms) - limit}"
    return ", ".join(shown) + suffix


def _metadata_text(doc: CoreObject) -> str:
    parts: list[str] = [doc.source, doc.object_type]
    for key, value in doc.metadata.items():
        parts.append(str(key))
        if isinstance(value, (str, int, float, bool)):
            parts.append(str(value))
        elif isinstance(value, dict):
            parts.extend(str(item) for item in list(value.keys())[:6])
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in list(value)[:6])
    return " ".join(parts)


def _length_signal(text: str) -> float:
    if not text.strip():
        return 0.0
    return min(len(text.strip()) / _SCORING["length_max_chars"], 1.0)


def _route_signals(
    doc: CoreObject,
) -> tuple[
    dict[RouteName, list[str]], dict[RouteName, list[str]], list[str], dict[RouteName, float]
]:
    text = doc.content or ""
    source_text = _metadata_text(doc)
    keyword_matches = {
        route: _matched_keywords(text, ROUTE_KEYWORDS[route]) for route in ROUTE_PRIORITY
    }
    source_matches = {
        route: _matched_keywords(source_text, SOURCE_HINTS[route]) for route in ROUTE_PRIORITY
    }
    command_matches = _matched_keywords(text, COMMAND_MARKERS)

    strengths: dict[RouteName, float] = {}
    for route in ROUTE_PRIORITY:
        strengths[route] = (
            len(keyword_matches[route])
            + len(source_matches[route]) * _SCORING["source_hint_weight"]
        )

    if command_matches:
        strengths["TASK"] += min(
            len(command_matches) * _SCORING["command_weight"], _SCORING["command_cap"]
        )
        if keyword_matches["TASK"]:
            strengths["TASK"] += _SCORING["command_task_bonus"]

    return keyword_matches, source_matches, command_matches, strengths


def _select_route(strengths: dict[RouteName, float]) -> RouteName:
    best = max(ROUTE_PRIORITY, key=lambda route: (strengths[route], -ROUTE_PRIORITY.index(route)))
    if strengths[best] <= 0:
        return _SCORING["default_route"]  # type: ignore[return-value]
    return best


def _risk_level(route_name: RouteName, text: str) -> Literal["low", "medium", "high"]:
    if route_name == "TASK" and _matched_keywords(text, MODERATE_RISK_KEYWORDS):
        return "medium"
    return "low"


# ── Main entry ──────────────────────────────────────────


def route(doc: CoreObject) -> AttentionDecision:
    text = doc.content or ""
    normalized = _normalize(text)
    length_signal = _length_signal(text)

    if not normalized:
        return AttentionDecision(
            route="DROP", score=_SCORING["empty_score"], reasons=["empty content"]
        )

    if normalized in LOW_VALUE_TEXTS:
        return AttentionDecision(
            route="DROP", score=_SCORING["low_value_score"], reasons=["low-value short input"]
        )

    risk_matches = _matched_keywords(text, RISK_KEYWORDS)
    if risk_matches:
        return AttentionDecision(
            route="REVIEW",
            score=_SCORING["high_risk_score"],
            reasons=[
                f"high risk keywords: {_compact_terms(risk_matches)}",
                f"length_signal={length_signal:.2f}",
            ],
            risk_level="high",
        )

    keyword_matches, source_matches, command_matches, strengths = _route_signals(doc)
    route_name = _select_route(strengths)
    selected_strength = strengths[route_name]

    score = ROUTE_BASE_SCORE[route_name] + length_signal * _SCORING["length_weight"]
    if selected_strength > 0:
        score += min(selected_strength * _SCORING["strength_weight"], _SCORING["strength_cap"])
    else:
        score += 0.10
    score = min(round(score, 3), 1.0)

    reasons = [f"length_signal={length_signal:.2f}"]
    if keyword_matches[route_name]:
        reasons.append(
            f"{route_name.lower()} keywords: {_compact_terms(keyword_matches[route_name])}"
        )
    if source_matches[route_name]:
        reasons.append(f"source hints: {_compact_terms(source_matches[route_name])}")
    if route_name == "TASK" and command_matches:
        reasons.append(f"command intent: {_compact_terms(command_matches)}")
    if selected_strength <= 0:
        reasons.append("default non-empty material")
    reasons.append(f"selected route={route_name}")

    return AttentionDecision(
        route=route_name,
        score=score,
        reasons=reasons,
        risk_level=_risk_level(route_name, text),
    )
