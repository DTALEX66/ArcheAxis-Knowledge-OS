---
tags: [cognitive-loop, daily-brief, projection]
aliases: [Daily Brief, KB Projection]
---

# Daily Brief Format

The daily brief projection generates a Markdown summary of system activity.

## Structure

A daily brief contains:

- **Date** — ISO-8601 date of the brief
- **Summary** — High-level activity overview
- **Recent Tasks** — List of completed context pack tasks
- **New Cards** — Cards generated from recent activity
- **Upcoming Reviews** — SM-2 review schedule for the day

### Example

```markdown
# Daily Brief — 2026-07-26

## Summary
3 context packs completed, 12 new cards generated.

## Recent Tasks
- [x] H-001: Adapter contract design (completed)
- [x] I-001: Index manifest build (completed)

## New Cards
- [[card-system#Overview]] — Card pipeline documented
- [[task-management]] — Context pack structure

## Upcoming Reviews
- [[review-workflow]] — due in 2 days
```

## Related

- [[task-management]] — feeds the Recent Tasks section
- [[card-system]] — feeds the New Cards section
- #projection/daily-brief

> [!info] Future Enhancement
> Daily briefs currently render as static Markdown. Bidirectional sync is a future goal.
