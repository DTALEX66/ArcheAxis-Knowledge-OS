"""Knowledge cards — atomic knowledge units for human learning."""
from dataclasses import dataclass, field


@dataclass
class KnowledgeCard:
    card_id: str = ""
    title: str = ""
    content: str = ""
    source_ids: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    review_status: str = "draft"

    def to_dict(self) -> dict:
        return {
            "card_id": self.card_id, "title": self.title,
            "content": self.content, "source_ids": self.source_ids,
            "tags": self.tags, "review_status": self.review_status,
        }
