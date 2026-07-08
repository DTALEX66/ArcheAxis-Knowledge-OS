# A-B Integration Blueprint

> Architecture Complete | 2026-06-25

## 1. The Big Picture

B-Line (Multi-Agent OS) manages workflow, routing, and automation.
A-Line (Human Learning OS) executes the actual learning processes.

Together they form a complete "learning machine" where:
- B-Line answers "what to learn and when"
- A-Line answers "how to learn effectively"

## 2. B-to-A Component Mapping

| B-Line Component | A-Line Subsystems | Function |
|-----------------|------------------|----------|
| 01 Coordinator | All 16 | Routes learning tasks |
| 02 Orchestrator | A-3 Diagnose, A-4 Plan, A-8 Practice | Step decomposition |
| 03 Parallel Streaming | A-1 Capture, A-7 Palace | Multi-source input |
| 04 Event Router | A-10 Reflect, A-11 Feedback | Event-driven feedback |
| 05 Permissions | A-16 Govern | Access control |
| 06 MCP Extension | A-9 Execute, A-12 Teach | External tool bridge |

## 3. Learning Flow: "Master Topic X"

### Phase 1: Discovery (B-Line led)
Coordinator receives goal -> Orchestrator breaks down -> Schedule start

### Phase 2: Learning (A-Line led, B-Line monitoring)
Capture -> Structure -> Diagnose -> Plan -> Encode -> File

### Phase 3: Practice (A+B协同)
Practice scheduled by B -> Execute in safe env -> Reflect prompted by B -> Feedback routed by B -> Review scheduled by A-14

### Phase 4: Mastery (A-Line led)
Teach (generate output) -> Transfer (apply to new domain) -> Govern (track progress)

## 4. Implementation Priority

1. B-2 Orchestrator -> A-4 Plan (quick wins)
2. B-4 Event Router -> A-11 Feedback loop (high value)
3. B-6 MCP -> A-9 Execute (enables real practice)
4. Full autonomy loop (long-term vision)

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| B-Line orchestrates, A-Line executes | Separation of concerns |
| Event-driven feedback | Low latency, async |
| MCP protocol for external tools | Standardized, extensible |
| A-Line owns knowledge state | Single source of truth |
