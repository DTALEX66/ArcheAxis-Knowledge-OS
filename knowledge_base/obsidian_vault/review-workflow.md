---
tags: [cognitive-loop, review, sm-2]
aliases: [Spaced Repetition, Review Workflow]
---

# Review Workflow

SM-2 spaced repetition review pipeline for knowledge cards.

## Algorithm

The SM-2 algorithm schedules reviews based on:

1. **Quality of response** (0–5 scale)
2. **Current interval** (days since last review)
3. **Easiness factor** (dynamic multiplier)

### Quality Scale

| Score | Meaning |
|-------|---------|
| 5 | Perfect recall |
| 3 | Recalled with difficulty |
| 0 | Complete blackout |

## Validation

> [!error] Validation Failure
> A card with `quality < 0` or `quality > 5` **must** be rejected with a clear error message.

## References

- [[card-system#Card Pipeline]] — upstream pipeline stage
- Original SM-2 paper by Piotr Wozniak

### Math (inline)

The easiness factor is updated as: `EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))`

> [!important]
> Always bound EF to [1.3, 3.0] to prevent extreme scheduling.
