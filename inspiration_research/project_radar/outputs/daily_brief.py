"""Daily brief builder — assembles 5-section report."""
from dataclasses import dataclass, field


@dataclass
class DailyBrief:
    brief_id: str = ""
    date: str = ""
    sections: dict = field(default_factory=lambda: {"gold": [], "design": [], "technology": [], "ai": []})
    github_ai_projects: list = field(default_factory=list)
    recommended_intake_cards: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "date": self.date,
            "sections": self.sections,
            "github_ai_projects": self.github_ai_projects,
            "recommended_intake_cards": self.recommended_intake_cards,
        }
