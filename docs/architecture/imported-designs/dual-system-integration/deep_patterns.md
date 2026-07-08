# CC+CW Deep Pattern Extraction ? All Subsystems

---
## 1. CC Hooks System (84 hooks files)

### Permission Hook: useCanUseTool.tsx (40KB)
- Central permission gate for ALL tool calls
- Pattern: PermissionMode + PermissionRule + PermissionResult
- Evaluates: tool_name, tool_input, workspace_path, user preference
- Returns: allow/deny/ask with reason

### Bridge Hook: useReplBridge.tsx (115KB)
- Full REPL bridge lifecycle management
- WebSocket connection, session creation, message routing
- JWT token refresh, error recovery

### Other Key Hooks:
| Hook | Size | Purpose |
|---|---|---|
| fileSuggestions.ts | 26KB | import { statSync } from 'fs' |
| useArrowKeyHistory.tsx | 33KB | import React, { useCallback, useRef, useState } from 'react'; |
| useCanUseTool.tsx | 39KB | import { c as _c } from "react/compiler-runtime"; |
| useCancelRequest.ts | 9KB | /** |
| useClaudeCodeHintRecommendation.tsx | 15KB | import { c as _c } from "react/compiler-runtime"; |
| useCommandKeybindings.tsx | 10KB | import { c as _c } from "react/compiler-runtime"; |
| useGlobalKeybindings.tsx | 30KB | /** |
| useIDEIntegration.tsx | 10KB | import { c as _c } from "react/compiler-runtime"; |
| useInboxPoller.ts | 33KB | import { randomUUID } from 'crypto' |
| useLspPluginRecommendation.tsx | 21KB | import { c as _c } from "react/compiler-runtime"; |
| useManagePlugins.ts | 11KB | import { useCallback, useEffect } from 'react' |
| usePasteHandler.ts | 9KB | import { basename } from 'path' |
| usePluginRecommendationBase.tsx | 11KB | import { c as _c } from "react/compiler-runtime"; |
| usePromptsFromClaudeInChrome.tsx | 11KB | import { c as _c } from "react/compiler-runtime"; |
| useRemoteSession.ts | 22KB | import { useCallback, useEffect, useMemo, useRef } from 'react' |
| useReplBridge.tsx | 112KB | import { feature } from 'bun:bundle'; |
| useSearchInput.ts | 10KB | import { useCallback, useState } from 'react' |
| useTextInput.ts | 16KB | import { isInputModeCharacter } from 'src/components/PromptInput/inputModes.js' |
| useTypeahead.tsx | 207KB | import * as React from 'react'; |
| useVirtualScroll.ts | 34KB | import type { RefObject } from 'react' |
| useVoice.ts | 44KB | // React hook for hold-to-talk voice input using Source voice_stream STT. |
| useVoiceIntegration.tsx | 97KB | import { feature } from 'bun:bundle'; |

---
## 2. CC Permission System (utils/permissions/ ? 24 files, 310KB)

Architecture:
1. **PermissionMode** ? bypass/plan/default/tight
2. **PermissionRule** ? tool_name + behavior (allow/deny/ask/plan)
3. **PermissionResult** ? allow | deny + reason + update
4. **PermissionUpdate** ? user decisions persisted to settings.json
5. **DenialTracking** ? Tracks denial state machine per tool
6. **ClassifierDecision** ? Auto-mode classifier (yoloClassifier)
7. **Filesystem** ? Path scope, minified JSON, env var leak, write-after-write checks

Permission Flow:
1. Tool call triggers useCanUseTool hook
2. Hook checks PermissionMode for bypass/tight
3. Evaluates PermissionRules from settings.json
4. Falls back to interactive user prompt (ask mode)
5. User decision creates PermissionUpdate
6. Update persisted to settings.json (project/user scope)
7. DenialTracking records denial for diagnostics

---
## 3. CC BashTool Security (5 core files, ~300KB)

bashSecurity.ts (102KB) ? Comprehensive command analysis:
- Destructive command matching (blacklist patterns)
- Output redirection analysis (>, >>, |)
- Pipe chain evaluation
- Background process detection (&, nohup)
- Shell injection detection (eval, exec, , backtick)

bashPermissions.ts (98KB) ? Permission integration:
- Per-command permission lookup
- Mode-specific permission behavior
- Sandbox enforcement

readOnlyValidation.ts (68KB) ? Read-only command validation:
- Classifies commands as read-only vs write
- Git command read/write classification
- Package manager write detection

pathValidation.ts (43KB) ? Path security:
- Workspace root path checking
- Path escape detection
- Symlink resolution

---
## 4. CC Settings System (utils/settings/ ? 16 files, 133KB)

Architecture:
- **types.ts** (42KB) ? All settings schemas with Zod v4
- **settings.ts** (32KB) ? Settings CRUD + persistence
- **changeDetector.ts** (16KB) ? Settings change detection
- **constants.ts** ? SettingSource enum (user/project/policy/bundled)
- **managedPath.ts** ? Managed settings file path resolution

Setting Sources (priority order):
1. policySettings (highest ? admin/org policy)
2. userSettings
3. projectSettings
4. bundledSettings (lowest ? built-in defaults)

---
## 5. CC Plugin System (utils/plugins/ ? 44 files, 682KB + commands/plugin/ ? 17 files, 954KB)

This is the LARGEST subsystem in CC:
- **pluginLoader.ts** (110KB) ? Plugin loading, validation, activation
- **marketplaceManager.ts** (93KB) ? Plugin marketplace management
- **schemas.ts** (58KB) ? Plugin manifest schemas
- **ManagePlugins.tsx** (321KB!) ? Plugin management UI (largest single UI file)
- **PluginSettings.tsx** (128KB) ? Plugin settings UI
- **BrowseMarketplace.tsx** (119KB) ? Marketplace browsing UI

---
## 6. CC Command System (commands/ ? 68 subdirectories, 207 files)

Each command follows: index.ts + handler.tsx pattern

By category:
| Category | Commands |
|---|---|
| Plugin/Marketplace | plugin, mcp, install-github-app, install-slack-app
| Session/Lifecycle | resume, exit, clear, copy, export, rename, rewind
| Communication | bridge, btw, copy, feedback, mobile, remote-setup, remote-env
| Model/Settings | model, effort, rate-limit-options, fast, config, cost
| Knowledge | memory, tag, compact, context
| Development | ide, diff, branch, files, add-dir, permissions, hooks
| Debug/Diagnostics | doctor, heapdump, debug-tool-call, perf-issue, ant-trace
| UX | color, output-style, help, keybindings, plan, sandbox-toggle, env
| Auth | login, logout, oauth-refresh, privacy-settings
| Advanced | ultraplan, thinkback, swarm, agents, desktop, chrome, voice

---
## 7. CW Complete Architecture

CW is a Python port of CC with these key files:
- **main.py** (10706 bytes) ? Entry point, CLI args, bootstrap
- **runtime.py** (9442 bytes) ? Port runtime with command/tool dispatch
- **query_engine.py** (8263 bytes) ? Query engine with turn management
- **bootstrap_graph.py** (830 bytes) ? Bootstrap dependency graph
- **command_graph.py** (1281 bytes) ? Command dependency graph
- **path_scope.py** (6400 bytes) ? Workspace path scope validation
- **permissions.py** (2099 bytes) ? Tool permission context
- **parity_audit.py** (5406 bytes) ? Parity matrix against CC
- **port_manifest.py** (1888 bytes) ? Subsystem manifest
- **commands.py** (3260 bytes) ? Command backlog builder
- **tools.py** (4297 bytes) ? Tool backlog builder
- **context.py** (1627 bytes) ? Port context builder
- **setup.py** (2392 bytes) ? Port runtime setup
- **session_store.py** (1057 bytes) ? Session persistence
- **transcript.py** (608 bytes) ? Message transcript store
- **models.py** (1148 bytes) ? Data models (Subsystem, PortingModule, UsageSummary)
- **execution_registry.py** (1450 bytes) ? Tool execution registry
- **tool_pool.py** (1081 bytes) ? Tool pool management
- **deferred_init.py** (802 bytes) ? Deferred initialization
- **prefetch.py** (663 bytes) ? Preloading system
- **remote_runtime.py** (778 bytes) ? Remote runtime config
- **system_init.py** (721 bytes) ? System initialization
- **QueryEngine.py** (731 bytes) ? Query engine wrapper

---
## 8. KB Integration Complete ? All 22 Subsystems Mapped

### A-Line (16):
1. ? Capture ? isolated_learning/ capture tools
2. ? Understand ? understanding.py (NEW)
3. ? Diagnose ? diagnostics.py
4. ? Plan ? plan endpoints
5. ? Encode ? encoding.py (ENHANCED)
6. ? Remember ? FSRS + cards
7. ? Palace ? palace/ (ENHANCED)
8. ? Practice ? cognitive_load.py
9. ? Execute ? skills.py (ENHANCED)
10. ? Feedback ? diagnostics.py
11. ? Metacognition ? metacognition.py
12. ? Teach ? teach_back.py + skills.py
13. ? Profile ? profile.py
14. ? Consolidate ? consolidation.py
15. ? Transfer ? transfer.py (NEW)
16. ? Govern ? governance/

### B-Line (6):
1. ? Coordinator ? b_line_coordinator.py (NEW)
2. ? Orchestration ? plan routes
3. ? Streaming ? stream endpoints
4. ? Event Routing ? transfer.py
5. ? Permission ? governance/
6. ? MCP Extension ? plugin system

