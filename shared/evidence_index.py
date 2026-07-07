"""Evidence index builder — adapted from Obsidian-Assistance v6.

Tracks evidence metadata (source files, verification status, confidence)
for KB documents and cards.  Provides health scoring per knowledge asset.

Adapted from: scripts/v6/evidence_index_builder.py + vault_health_radar.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import insert, select_all  # noqa: E402


def index_evidence(
    doc_id: str,
    source_type: str = "manual",
    source_path: str = "",
    confidence: str = "medium",
    status: str = "pending",
    caption: str = "",
) -> dict[str, Any]:
    """Create or update an evidence record for a KB asset.

    Args:
        doc_id: the document/card ID this evidence supports.
        source_type: 'pdf' | 'video' | 'image' | 'audio' | 'web' | 'manual'.
        source_path: path or URL to the source.
        confidence: 'high' | 'medium' | 'low' | 'unverified'.
        status: 'pending' | 'verified' | 'rejected'.
        caption: human-readable description.

    Returns:
        The evidence record dict.
    """
    import uuid

    eid = f"ev_{uuid.uuid4().hex[:12]}"
    evidence = {
        "id": eid,
        "doc_id": doc_id,
        "source_type": source_type,
        "source_path": source_path,
        "confidence": confidence,
        "status": status,
        "caption": caption,
    }
    insert("kb_evidence", evidence)
    return evidence


def get_evidence(doc_id: str) -> list[dict[str, Any]]:
    """Get all evidence records for a document."""
    all_ev = select_all("kb_evidence", limit=500)
    return [e for e in all_ev if e.get("doc_id") == doc_id]


def evidence_health(doc_id: str) -> dict[str, Any]:
    """Compute evidence health score for a KB asset.

    Returns:
        {total, verified, pending, rejected, by_type, health_score, status}.
    """
    evidence = get_evidence(doc_id)
    total = len(evidence)
    verified = sum(1 for e in evidence if e.get("status") == "verified")
    pending = sum(1 for e in evidence if e.get("status") == "pending")
    rejected = sum(1 for e in evidence if e.get("status") == "rejected")

    by_type: dict[str, int] = {}
    for e in evidence:
        t = e.get("source_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    if total == 0:
        score = 0
        status = "no_evidence"
        recommendation = "No evidence recorded. Consider adding source references."
    elif verified == 0:
        score = max(10, pending * 5)
        status = "unverified"
        recommendation = f"{pending} evidence items pending verification."
    elif verified >= total * 0.7:
        score = min(100, verified * 20)
        status = "healthy"
        recommendation = "Evidence coverage is strong."
    else:
        score = min(80, verified * 15 + pending * 5)
        status = "partial"
        recommendation = f"{verified}/{total} verified. Review pending items."

    return {
        "doc_id": doc_id,
        "total": total,
        "verified": verified,
        "pending": pending,
        "rejected": rejected,
        "by_type": by_type,
        "health_score": score,
        "status": status,
        "recommendation": recommendation,
    }


def vault_health_radar() -> dict[str, Any]:
    """Global KB evidence health overview.

    Scans all documents/cards and computes aggregate health metrics.
    Adapted from v6 vault_health_radar.py.
    """
    docs = select_all("kb_documents", limit=500)
    cards = select_all("kb_cards", limit=500)

    all_items = list(docs) + list(cards)
    results = []

    for item in all_items:
        iid = item.get("id") or item.get("card_id", "")
        if not iid:
            continue
        health = evidence_health(iid)
        results.append(
            {
                "id": iid,
                "title": item.get("title", iid)[:60],
                "type": "card" if "card_id" in item or "review_status" in item else "document",
                "health": health["status"],
                "score": health["health_score"],
                "verified": health["verified"],
                "total": health["total"],
            }
        )

    # Aggregate
    healthy = sum(1 for r in results if r["health"] == "healthy")
    partial = sum(1 for r in results if r["health"] == "partial")
    unverified = sum(1 for r in results if r["health"] == "unverified")
    no_evidence = sum(1 for r in results if r["health"] == "no_evidence")

    total = len(results)
    avg_score = round(sum(r["score"] for r in results) / max(total, 1), 1)

    return {
        "total_assets": total,
        "healthy": healthy,
        "partial": partial,
        "unverified": unverified,
        "no_evidence": no_evidence,
        "average_health_score": avg_score,
        "coverage_pct": round((healthy + partial) / max(total, 1) * 100, 1),
        "items": sorted(results, key=lambda r: r["score"])[:20],
    }
