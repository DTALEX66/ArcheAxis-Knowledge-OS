# AAOS P3 Avalonia First-Use Implementation Plan

> Status: this original five-rail-surface plan is historical and superseded for
> remaining frontend completion by `2026-09-24-aaos-commercial-frontend-completion.md`.
> Its constraints and evidence remain useful; do not use its unchecked task list
> as the current full-frontend queue.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing formal Avalonia window into a navigable, honest P3 first-use shell while preserving Core-owned learning behavior.

**Architecture:** Keep `MainWindow` and `CoreSupervisor` as the single desktop/Core boundary. Add UI-only navigation state and explicit empty states for domains without read models; do not add persistence or new dependencies.

**Tech Stack:** C#, Avalonia 12.1.2, existing Python source-contract tests, existing Rust/Core HTTP API.

**Spec:** `docs/superpowers/specs/2026-09-21-aaos-p3-avalonia-first-use-design.md`

## Global Constraints

- Avalonia is the only canonical product shell.
- Rust Core is the canonical writer and learning truth.
- No Green replacement, release, signing, installer, external resource, or unknown-history cleanup.
- Preserve current import, assessment, review, provenance, idempotency, and restart-readback behavior.

### Task 1: Add navigation contract coverage

**Files:**
- Create: `tests/test_desktop_navigation_contract.py`
- Test: `tests/test_desktop_navigation_contract.py`

- [ ] **Step 1: Write failing source-contract tests** for the five rail labels, the five navigation handlers, and honest empty-state text for Library, Jobs, and Settings.
- [ ] **Step 2: Run `pytest -q tests/test_desktop_navigation_contract.py`** and confirm it fails because the current XAML has only static buttons and no navigation state/handlers.

### Task 2: Implement the UI-only navigation shell

**Files:**
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`

- [ ] **Step 1: Add named rail buttons** for Home, Library, Learning, Jobs, and Settings, with click handlers and no new package.
- [ ] **Step 2: Add a named workspace heading/body region** that switches using in-memory state only.
- [ ] **Step 3: Move existing Home cards and Learning review controls into explicit regions without changing their event handlers or Core endpoints.
- [ ] **Step 4: Add honest empty states** for Library, Jobs, and Settings that identify the missing Core projection instead of fabricating content.

### Task 3: Verify the bounded slice

**Files:**
- No additional production files.

- [ ] **Step 1: Run `pytest -q tests/test_desktop_navigation_contract.py tests/test_desktop_routes_v1.py tests/test_desktop_learning_review_contract.py tests/test_project_output_routing_contract.py`.
- [ ] **Step 2: Run `dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --no-restore --nologo` using the registered project-local SDK/toolchain if available.
- [ ] **Step 3: Run `git diff --check`, `git diff --stat`, and `git status --short`; confirm only the planned files changed and unknown untracked history remains untouched.
- [ ] **Step 4: Record evidence as local contract/build evidence only; do not upgrade P3 to GUI runtime PASS without actual UI interaction and restart readback.
