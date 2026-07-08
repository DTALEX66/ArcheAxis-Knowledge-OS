# Dual System Integration: CC + CW -> Knowledge-Base A-Line + B-Line

## Overview
This directory documents how **CC Source (CC) v2.1.88** (TypeScript, archived) and 
**CW Source (CW)** (Python, open-source port) patterns were cross-referenced and 
integrated into the Knowledge-Base learning system.

## Architecture Mapping

### A-Line: Human Learning OS (16 subsystems)

| # | Subsystem | CC Source | CW Source (Python Port) | KB Module | Status |
|---|-----------|-----------|------------------------|-----------|--------|
| 1 | Capture | FileReadTool.ts | tools/BashTool/ | cards CRUD | Done |
| 2 | Understand | context.ts + migrations/ | context.py | learning_final/understanding.py | NEW |
| 3 | Diagnose | compact/ | task.py | learning_final/diagnostics.py | Done |
| 4 | Plan | tasks.ts | tasks.py | learning_final/plan.py | Done |
| 5 | Encode | schemas/hooks.ts (Zod v4) | deferred_init.py | learning_final/encoding.py | Enhanced |
| 6 | Remember | FSRS algorithm | session_store.py | built-in FSRS | Already have |
| 7 | Palace | memdir/ | memdir/ | learning_final/palace/ | Done |
| 8 | Practice | hooks/ | hooks/ | learning_final/cognitive_load.py | Done |
| 9 | Execute | tools/BashTool/sandbox | permissions.py | learning_final/skills.py | Enhanced |
|10 | Feedback | toolExecution | query_engine.py | learning_final/diagnostics.py | Done |
|11 | Metacognition | Thinking mode | direct_modes.py | learning_final/metacognition.py | Done |
|12 | Teach | skills/loadSkillsDir.ts | skills/ | learning_final/teach_back.py | Enhanced |
|13 | Profile | cost-tracker.ts | cost_tracker.py | learning_final/profile.py | Done |
|14 | Consolidate | compact/ | - | learning_final/consolidation.py | Done |
|15 | Transfer | bridge/ (31 files) | bridge/ (placeholder) | learning_final/transfer.py | NEW |
|16 | Govern | permissions/BashTool | permissions.py | learning_final/governance/ | Done |

### B-Line: Multi-Agent OS (6 subsystems)

| # | Subsystem | CC Source | CW Source | KB Module | Status |
|---|-----------|-----------|-----------|-----------|--------|
| 1 | Coordinator | coordinator/ | coordinator/ | learning_final/b_line_coordinator.py | NEW |
| 2 | Orchestration | Task.ts | task.py | plan routes | Done |
| 3 | Streaming | QueryEngine.ts | query_engine.py | stream endpoints | Done |
| 4 | Event Routing | bridge/bridgeMessaging.ts | - | transfer engine | Done |
| 5 | Permission | permissions/ | permissions.py | governance/ | Done |
| 6 | MCP Extension | tools/MCPTool/ | - | plugin system | Done |

## Key Patterns Extracted

### CC Patterns (TypeScript -> Python):
- **context.ts -> understanding.py**: Memoized cache, system/user context building, git status
- **schemas/hooks.ts -> encoding.py**: Zod v4 discriminated union chain, validation pipeline
- **tools/BashTool/ -> skills.py**: Sandbox validation, destructive command detection, path scoping
- **skills/loadSkillsDir.ts -> teach_back.py**: Skill loading, frontmatter parsing, conditional activation
- **bridge/types.ts -> transfer.py**: JWT bidirectional messaging, session management, environment registration
- **memdir/ -> palace/**: Memory type taxonomy, knowledge scanning, directory hierarchy

### CW Patterns (Python-native):
- **query_engine.py**: Turn management, budget tracking, transcript persistence
- **permissions.py**: ToolPermissionContext, workspace path scope, deny lists
- **path_scope.py**: Workspace root validation, path escape detection
- **session_store.py**: Session persistence with SQLite, transcript flush

## Database Migrations
- 012_palace_governance.sql: palace_rooms, palace_items, profile_records, teach_outputs
- 013_understanding_transfer.sql (NEW): knowledge_nodes, knowledge_edges, transfer_sessions, b_line_tasks

## Source Code Analysis

### CC Source Structure (1900+ files):
- src/ - Main source (1906 TS files)
- utils/ - Utility functions (564 files)
- commands/ - Slash commands (207 files)
- tools/ - Agent tools (184 files)
- components/ - Terminal UI (389 files)
- bridge/ - Cross-session communication (31 files)
- skills/ - Skill loading system (4 files)
- memdir/ - Knowledge directory hierarchy

### CW Source Structure (Python port):
- Direct CC -> Python translation
- All modules mirrored from CC
- Python-native versions of all key subsystems
- Active development with PRD tracking
