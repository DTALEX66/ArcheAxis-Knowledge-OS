"""GitHub trending repos collector."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrendingRepo:
    repo: str
    description: str = ""
    stars_today: int = 0
    language: str = ""
    url: str = ""


def collect_trending(language: Optional[str] = None, since: str = "daily") -> list[TrendingRepo]:
    """Collect trending repos. Phase 1: manual/semi-auto input.
    
    Future: integrate with GitHub API / RSS.
    """
    return []  # stub — data fed manually or via API adapter
