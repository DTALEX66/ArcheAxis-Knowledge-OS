# Intake Card 003: Tool Risk Registry

> Created: 2026-06-29
> Status: active
> Target phase: Phase 1 safety gate
> Scope: local tool registry, risk metadata, dry-run defaults, no external execution.

---

## 1. Source

| Source | Path |
|---|---|
| Delivery pack safety governance | `workspace/imports/inspiration-research/root/00_铁律.md` and `workspace/imports/knowledge-base/root/AGENTS.md` |
| KB MCP reference | `workspace/imports/knowledge-base/code-reference/mcp/permissions.py` |
| KB B-line guard reference | `workspace/imports/knowledge-base/code-reference/b_line/mcp_guard.py` |
| Current runtime | `app/tools/registry.py`, `app/agent/executor.py`, `config/tools.yaml` |

---

## 2. Problem

The current `run_tool()` dispatch is name-based only.

Issues:

```text
safe_write writes immediately
risk metadata is not enforced
unknown tools silently fall back to echo
no registry listing exists
medium/high risk default policy is unclear
```

This blocks safe Agent expansion.

---

## 3. Goal

Implement a minimal local Tool Risk Registry.

Required behavior:

```text
low risk tools run directly
medium risk tools default to dry-run unless explicitly allowed
high risk tools default to dry-run / blocked behavior
unknown tools return an error, not echo fallback
safe_write can only write under data/output
```

No network, shell execution, deletion, or real code execution is allowed in this Intake Card.

---

## 4. Runtime Contract

### Registry

Each tool should expose:

```text
name
risk_level
default_dry_run
description
```

### Tool Results

Every tool result should include:

```text
tool
risk_level
dry_run
status
```

### API

Add read-only endpoint:

```text
GET /tools
```

Do not add a general public tool execution endpoint yet.

---

## 5. Risk

| Risk | Control |
|---|---|
| Tool system becomes execution surface | No general tool execution API in this card |
| Writes escape project directory | Resolve and validate output path under `data/output` |
| Medium risk writes happen accidentally | `safe_write` defaults to dry-run |
| Unknown tool hides mistakes | Unknown tool returns error |
| High risk code execution slips in | `code_exec` only returns preview and remains dry-run |

---

## 6. Acceptance

Local verification must show:

```text
GET /tools returns registry metadata
run_tool("echo") succeeds with low risk
run_tool("safe_write") defaults to dry-run and does not write
run_tool("safe_write", dry_run=False) writes only under data/output
run_tool("missing") returns error
/run still completes and writes trace + lesson
high-risk delete/registry input still returns REVIEW high
```

---

## 7. Rollback

Revert only these files if needed:

```text
app/tools/registry.py
app/agent/executor.py
app/main.py
workspace/intake/003_tool_risk_registry.md
```
