# CC+CW Complete Source Absorption into Dual-System

## CC Source (Leaked) + CW Source (Python Port)

This document catalogs EVERY subsystem from both projects
and maps each to the dual-system architecture.

---
## Part 1: CC Source ? Complete Subsystem Catalog

### 1.1 Core Engine
| File | Size | Lines | Function |
|---|---|---|---|
- **bridge/** ? Cross-session bridge (31 files) (31 files, 467KB)
- **buddy/** ? Buddy companion AI (6 files) (6 files, 72KB)
- **cli/** ? CLI handlers and output (6+7 files) (19 files, 488KB)
- **commands/** ? Slash commands and user-facing features (207 files across 80+ subdirs) (189 files, 2429KB)
- **context/** ? React context providers (9 files) (9 files, 106KB)
- **hooks/** ? React hooks (10 files) (104 files, 1219KB)
- **memdir/** ? Memory directory system (13 files) (8 files, 80KB)
- **migrations/** ? Settings/model migrations (11 files) (11 files, 19KB)
- **plugins/** ? Plugin system (8 files) (2 files, 5KB)
- **root/** ? Core entry points and engine (0 files, 0KB)
- **schemas/** ? Zod schemas (1 file) (1 files, 7KB)
- **services/** ? API services (service provider abstraction) (130 files, 1805KB)
- **skills/** ? Skill system (4 files) (20 files, 146KB)
- **state/** ? State management (AppState) (6 files, 57KB)
- **tasks/** ? Task system (DreamTask, LocalAgentTask, etc.) (12 files, 320KB)
- **tools/** ? Tool system (40+ built-in tools) (184 files, 2623KB)
- **types/** ? Type definitions (7 files) (11 files, 110KB)
- **utils/** ? Utility functions (298 files across 20+ subdirs) (564 files, 6493KB)

### 1.2 Agent Loop Architecture (QueryEngine.ts ? 1295 lines)

The QueryEngine is the central agent loop that:
- Accepts user messages + tool results
- Manages SDK message lifecycle (user msg -> tool call -> tool result -> loop)
- Handles permissions, compacting, context management
- Tracks usage/cost per turn
- Loads memory prompts (memdir)
- Integrates hooks (pre/post tool execution)
- Manages multi-agent orchestration (AgentTool)
- Handles API errors with retry logic

Key types: SDKMessage, ToolUseBlockParam, PermissionMode, CanUseToolFn

### 1.3 Tool System (Tool.ts ? 792 lines)

The Tool system defines:
- Tool interface: name, schema, execute, validate
- ToolUseContext: appState, permissions, progress callbacks
- ValidationResult: strict pre-execution validation
- ToolProgressData: progress streaming per tool type
- 40+ built-in tools: BashTool, FileReadTool, WebSearchTool, GrepTool, etc.

### 1.4 Permission System (utils/permissions/ ? 24 files, ~200KB)

Multilayer permission model:
1. PermissionMode (bypass/plan/default/tight) ? useCanUseTool hook
2. Filesystem scope ? workspace root validation
3. BashTool security ? 100KB+ of command analysis + path validation + sandbox
4. Hook system ? pre/post tool hooks with command/prompt/http/agent types
5. Denial tracking ? tool denial state machine

### 1.5 Cost Tracker (cost-tracker.ts ? 323 lines)

Tracks: totalCostUSD, totalInputTokens, totalOutputTokens,
totalCache*Tokens, totalAPIDuration, totalToolDuration, 
totalLinesAdded/Removed, totalWebSearchRequests
Per-model tracking via getUsageForModel()

### 1.6 Bridge System (bridge/ ? 31 files, ~400KB)

Cross-session communication:
- JWT authentication with work secrets
- WebSocket + SSE transport
- Environment registration and polling
- Session management with heartbeat/lease extension
- Multi-session worktree management
- REPL bridge for interactive sessions

### 1.7 Skill System (skills/ ? 4 files)

- loadSkillsDir.ts (34KB): Full skill loading from filesystem
  - Frontmatter parsing (name, description, paths, hooks)
  - Dynamic discovery from CLAUDE.md dirs
  - Conditional activation via path patterns (gitignore-style)
  - Deduplication via realpath symlink resolution
- bundledSkills.ts: Built-in skills
- mcpSkillBuilders.ts: MCP skill integration

### 1.8 Commands System (commands/ ? 207 files across 80+ subdirs)

Each command has: index.ts + implementation file
Notable commands:
- **plugin/**: 17 files, 954KB
- **install-github-app/**: 14 files, 252KB
- **terminalSetup/**: 2 files, 76KB
- **ide/**: 2 files, 75KB
- **thinkback/**: 2 files, 60KB
- **bridge/**: 2 files, 46KB
- **copy/**: 2 files, 41KB
- **model/**: 2 files, 37KB
- **resume/**: 2 files, 36KB
- **fast/**: 2 files, 33KB
- **mcp/**: 4 files, 31KB
- **chrome/**: 2 files, 31KB
- **review/**: 4 files, 31KB
- **btw/**: 2 files, 29KB
- **remote-setup/**: 3 files, 27KB
- **rate-limit-options/**: 2 files, 23KB
- **effort/**: 2 files, 22KB
- **mobile/**: 2 files, 21KB
- **add-dir/**: 3 files, 20KB
- **tag/**: 2 files, 20KB
- **context/**: 3 files, 20KB
- **login/**: 2 files, 16KB
- **clear/**: 4 files, 16KB
- **export/**: 2 files, 15KB
- **sandbox-toggle/**: 2 files, 14KB
- **plan/**: 2 files, 13KB
- **session/**: 2 files, 13KB
- **memory/**: 2 files, 12KB
- **logout/**: 2 files, 10KB
- **compact/**: 2 files, 10KB

---
## Part 2: CW Source ? Complete Subsystem Catalog

- **QueryEngine.py**: 731 bytes
- **Tool.py**: 341 bytes
- **__init__.py**: 941 bytes
- **_archive_helper.py**: 485 bytes
- **bootstrap_graph.py**: 830 bytes
- **command_graph.py**: 1281 bytes
- **commands.py**: 3260 bytes
- **context.py**: 1627 bytes
- **costHook.py**: 218 bytes
- **cost_tracker.py**: 335 bytes
- **deferred_init.py**: 802 bytes
- **dialogLaunchers.py**: 327 bytes
- **direct_modes.py**: 564 bytes
- **execution_registry.py**: 1450 bytes
- **history.py**: 581 bytes
- **ink.py**: 151 bytes
- **interactiveHelpers.py**: 134 bytes
- **main.py**: 10706 bytes
- **models.py**: 1148 bytes
- **parity_audit.py**: 5406 bytes
- **path_scope.py**: 6400 bytes
- **permissions.py**: 2099 bytes
- **port_manifest.py**: 1888 bytes
- **prefetch.py**: 663 bytes
- **projectOnboardingState.py**: 194 bytes
- **query.py**: 206 bytes
- **query_engine.py**: 8263 bytes
- **remote_runtime.py**: 778 bytes
- **replLauncher.py**: 174 bytes
- **runtime.py**: 9442 bytes
- **session_store.py**: 1057 bytes
- **setup.py**: 2392 bytes
- **system_init.py**: 721 bytes
- **task.py**: 98 bytes
- **tasks.py**: 432 bytes
- **tool_pool.py**: 1081 bytes
- **tools.py**: 4297 bytes
- **transcript.py**: 608 bytes

### CW Key Architectural Differences from CC:
- Python-native dataclass patterns vs CC TypeScript interfaces
- Manifest-driven architecture (port_manifest.py)
- Parity tracking against CC (parity_audit.py)
- Stub directories mirroring CC structure
- Active port from TS -> Python with progress tracking

---
## Part 3: Dual-System Cross-Reference Matrix

### A-Line Subsystem -> CC/CW Source -> KB Module

| 1. Capture | CC FileReadTool.ts, FileWriteTool.ts, WebFetchTool.ts | CC FileReadTool + CW port_manifest | cards CRUD (existing)
| 2. Understand | CC context.ts, context/*.tsx, migrations/*.ts | CW context.py | understanding.py (NEW)
| 3. Diagnose | CC commands/compact/, utils/compact.ts | CW task.py | diagnostics.py
| 4. Plan | CC tasks.ts, Task.ts, task/*.ts | CW tasks.py | plan endpoints
| 5. Encode | CC schemas/hooks.ts (Zod v4), utils/settings/types.ts | CW deferred_init.py | encoding.py (ENHANCED)
| 6. Remember | CC memdir/ (memory scanning/retrieval) | CW memdir/ | cards + FSRS (existing)
| 7. Palace | CC memdir/memoryTypes.ts, memoryAge.ts, memoryScan.ts | CW memdir/ | palace/ (ENHANCED)
| 8. Practice | CC hooks/*.ts, useCanUseTool.ts | CW hooks/ | cognitive_load.py
| 9. Execute | CC tools/BashTool/ (sandbox + security), utils/sandbox/ | CW permissions.py | skills.py (ENHANCED)
| 10. Feedback | CC toolExecution, commands/feedback/ | CW query_engine.py | diagnostics.py
| 11. Metacognition | CC Thinking mode, utils/thinking.ts | CW direct_modes.py | metacognition.py
| 12. Teach | CC skills/loadSkillsDir.ts, SkillTool | CW skills/ | teach_back.py + skills.py
| 13. Profile | CC cost-tracker.ts, learner profile | CW cost_tracker.py | profile.py
| 14. Consolidate | CC commands/compact/compact.ts | CW - | consolidation.py
| 15. Transfer | CC bridge/ (31 files, JWT+WS) | CW bridge/ (stub) | transfer.py (NEW)
| 16. Govern | CC permissions/*.ts, ToolPermissionContext | CW permissions.py, path_scope.py | governance/

### B-Line Subsystem -> Source -> KB Module

| 1. Coordinator | CC coordinator/ | CW coordinator/ | b_line_coordinator.py (NEW)
| 2. Orchestration | CC Task.ts, tasks.ts | CW tasks.py | plan endpoints
| 3. Streaming | CC QueryEngine.ts, query.ts | CW query_engine.py | transfer + stream
| 4. Event Routing | CC bridge/bridgeMessaging.ts | CW - | transfer.py
| 5. Permission | CC permissions/*.ts | CW permissions.py | governance/
| 6. MCP Extension | CC tools/MCPTool/*, utils/mcp/ | CW - | plugin system

---
## Part 4: Key Algorithms and Design Patterns Extracted

### 4.1 Zod v4 Chain (CC schemas/hooks.ts)
`python
class ValidationChain:
    def __init__(self):
        self._rules = []
    def add(self, name, validator):
        self._rules.append((name, validator))
        return self
    def validate(self, data):
        for name, validator in self._rules:
            result = validator(data)
            if result is not True:
                return {"valid": False, "errors": [{"rule": name, "error": result}]}
        return {"valid": True, "errors": []}
`

### 4.2 Memoized Cache (CC context.ts + lodash-es/memoize.js)
`python
class ContextCache:
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds
    def get_or_compute(self, key, factory):
        now = datetime.now(timezone.utc).timestamp()
        if key in self._cache:
            val, ts = self._cache[key]
            if (now - ts) < self._ttl:
                return val
        val = factory()
        self._cache[key] = (val, now)
        return val
    def invalidate(self, key=None):
        if key: self._cache.pop(key, None)
        else: self._cache.clear()
`

### 4.3 Sandbox Security (CC tools/BashTool/* + utils/sandbox/)
- Destructive command detection (rm -rf, sudo, mkfs, dd)
- Workspace path scope validation
- Read-only vs write command classification
- Sed command parser with pattern validation
- PowerShell dangerous cmdlet detection
- Timeout enforcement per command

### 4.4 Hook System (CC hooks/ + utils/hooks/)
4 hook types:
- **command**: shell command execution with timeout
- **prompt**: LLM prompt hook (evaluate with model)
- **http**: HTTP POST hook with JWT auth
- **agent**: Agentic verifier hook (spawn sub-agent)

Hook lifecycle: if condition -> pre-hooks -> tool execution -> post-hooks

### 4.5 Bridge Protocol (CC bridge/)
- Environment registration with API key
- Poll-based work distribution (long polling)
- JWT session tokens with ingress auth
- WebSocket for bidirectional messaging
- Heartbeat with lease extension
- Multi-session worktree management
- Session activity tracking (ring buffer)

### 4.6 Permission Model (CC types/permissions.ts + utils/permissions/)
`
PermissionMode: bypass | plan | default | tight
  - bypass: all tools allowed, no confirmation
  - plan: tools blocked, plan-only mode
  - default: standard interactive confirmation
  - tight: strict rules, skip/peek blocked

Filesystem safety:
  - Workspace root isolation
  - Minified JSON write detection
  - Environment variable leak detection
  - Write-after-write conflict detection
`

### 4.7 Memory System (CC memdir/)
- 4 memory types: user, feedback, project, reference
- Private/team scoping with XML tags
- Memory age tracking (freshness tiers)
- Automatic memory scanning on context loads
- Path-based memory directory hierarchy

### 4.8 Skill Loading (CC skills/loadSkillsDir.ts)
- Frontmatter-driven skill definition (name/description/whenToUse/paths/hooks)
- Dynamic discovery from .claude/skills/ directories
- Conditional activation via gitignore-style path patterns
- Deduplication via realpath symlink resolution
- Token estimation for context management

---
## Part 5: CW Source Python-Native Patterns

### 5.1 Port Manifest (port_manifest.py)
- Declarative subsystem registry
- File-by-file porting progress tracking
- Markdown summary generation

### 5.2 Query Engine Port (query_engine.py ? 200 lines)
- Pythonic dataclass-based engine
- Turn management with token budgeting
- Streaming generator for SSE-like output
- Session persistence (save/load from SQLite)
- Transcript store with automatic compaction

### 5.3 Permission Context (permissions.py + path_scope.py)
- ToolPermissionContext: deny_names, deny_prefixes, workspace_scope
- WorkspacePathScope: root validation, path escape detection
- Python-native frozenset-based deny lists

### 5.4 Parity Tracking (parity_audit.py)
- Programmatic parity matrix against CC
- Per-subsystem porting status tracking
- Source hints linking to CC TypeScript originals

---
## Part 6: Knowledge-Base Integration Summary

### A-Line Modules (16/16 complete)
All 16 subsystems mapped from CC/CW into Knowledge-Base learning_final/

### B-Line Modules (6/6 complete)
All 6 multi-agent subsystems mapped with coordination module

### Database Schema
- 13 migration files total
- New: knowledge_nodes, knowledge_edges, transfer_sessions, b_line_tasks
- Enhanced: palace_rooms, palace_items, skill_tasks, skill_attempts

### API Surface
30+ endpoints across /learning/* namespace

---

## Part 7: CC Core Features Absorbed
All non-UI CC core features (1884 files - all engine, tools, permissions, bridge, commands, skills, memdir, schemas, services, utils) have been analyzed and mapped to the 27 KB modules.
UI-only features (components 389 files, hooks 104 files, CLI 19 files, Ink 96 files, vim/voice/keybindings/screens/outputStyles) were excluded as not applicable to a Python backend learning system.
