---
tags: [cognitive-loop, core-system, knowledge-card]
aliases: [Card Lifecycle, Card System]
created: 2026-07-01
---

# Card System

The card system manages the life-cycle of knowledge cards within archeaxis-workspace.

## Overview

Cards follow a pipeline: **Ingestion → Processing → Review → Mastery**.

### Card Pipeline

| Stage | Description | Gate |
|-------|-------------|------|
| Ingestion | Raw material enters the system | Content validation |
| Processing | Chunking and embedding | Index consistency |
| Review | SM-2 spaced repetition | Review threshold |
| Mastery | Archived with retention policy | Confidence score |

## Related

- [[review-workflow]] — handles the Review and Mastery stages
- [[task-management]] — orchestrates context packs that feed cards
- See also #card-system/pipeline

> [!tip] Pro Tip
> Cards are always processed through the full pipeline — skipping validation produces warnings in [[review-workflow#Validation]].

### Code Example

```python
from knowledge_base.cards import create_card
card = create_card(title="Example", content="# Hello")
```

## Frontmatter handling

YAML frontmatter fields:
- `tags`: used for topic classification
- `aliases`: alternative lookup names
- `created`: ISO-8601 timestamp
