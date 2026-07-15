from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.run_taskpack_agent import (
    AgentResult,
    HermesAgentBackend,
    RunnerError,
    TaskPackRunner,
)


@dataclass
class FakeRepo:
    head_value: str = "base"
    staged_tree_value: str = "tree-base"
    status_value: str = ""
    released: bool = False

    def head(self) -> str:
        return self.head_value

    def head_tree(self) -> str:
        return "tree-base"

    def staged_tree(self) -> str:
        return self.staged_tree_value

    def snapshot(self) -> tuple[str, str]:
        return self.staged_tree_value, self.status_value

    def verify_released(self, baseline_head: str) -> None:
        assert baseline_head == "base"
        self.released = True


class FakeAgent:
    def __init__(self, repo: FakeRepo, decisions: list[str]) -> None:
        self.repo = repo
        self.decisions = iter(decisions)
        self.writer_calls: list[tuple[str | None, str]] = []
        self.review_calls: list[str] = []

    def run_writer(self, prompt: str, *, resume: str | None = None) -> AgentResult:
        self.writer_calls.append((resume, prompt))
        if resume is None:
            self.repo.staged_tree_value = "tree-v1"
            self.repo.status_value = "M  shared/migration.py"
        elif "NO-GO" in prompt:
            self.repo.staged_tree_value = "tree-v2"
        elif "GO" in prompt:
            self.repo.head_value = "released"
            self.repo.status_value = ""
        return AgentResult(stdout="writer complete", stderr="", session_id="session-A")

    def run_reviewer(self, prompt: str) -> str:
        self.review_calls.append(prompt)
        return next(self.decisions)


def test_hermes_backend_resumes_session_without_agent_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    monkeypatch.setattr("scripts.run_taskpack_agent.shutil.which", lambda command: command)

    def fake_run(command: list[str], **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="writer complete\n",
            stderr="\nsession_id: continued-session\n",
        )

    monkeypatch.setattr("scripts.run_taskpack_agent.subprocess.run", fake_run)
    result = HermesAgentBackend(tmp_path, hermes="hermes").run_writer(
        "continue work", resume="initial-session"
    )

    assert result.session_id == "continued-session"
    assert calls[0][0][calls[0][0].index("--resume") + 1] == "initial-session"
    assert "timeout" not in calls[0][1]


def test_high_risk_runner_resumes_one_writer_lineage_until_review_go() -> None:
    repo = FakeRepo()
    agent = FakeAgent(repo, ["NO-GO\nshared/migration.py:10 missing proof", "GO"])

    TaskPackRunner(repo=repo, agent=agent, max_review_rounds=3).run(
        "repair the migration", risk="high"
    )

    assert [resume for resume, _ in agent.writer_calls] == [None, "session-A", "session-A"]
    assert len(agent.review_calls) == 2
    assert "tree-v1" in agent.review_calls[0]
    assert "tree-v2" in agent.review_calls[1]
    assert repo.released is True


def test_reviewer_must_not_change_the_frozen_tree() -> None:
    repo = FakeRepo()
    agent = FakeAgent(repo, ["GO"])

    def editing_review(prompt: str) -> str:
        repo.status_value = "M  shared/migration.py\n?? reviewer-note.txt"
        return "GO"

    agent.run_reviewer = editing_review  # type: ignore[method-assign]

    with pytest.raises(RunnerError, match="reviewer changed"):
        TaskPackRunner(repo=repo, agent=agent).run("repair", risk="high")


def test_low_risk_runner_uses_one_writer_call_without_reviewer() -> None:
    repo = FakeRepo()
    agent = FakeAgent(repo, [])

    TaskPackRunner(repo=repo, agent=agent).run("add a pure adapter", risk="low")

    assert [resume for resume, _ in agent.writer_calls] == [None]
    assert agent.review_calls == []
    assert repo.released is True


def test_runner_rejects_untracked_or_unstaged_files_at_freeze() -> None:
    repo = FakeRepo()
    agent = FakeAgent(repo, ["GO"])

    original_run_writer = agent.run_writer

    def dirty_writer(prompt: str, *, resume: str | None = None) -> AgentResult:
        result = original_run_writer(prompt, resume=resume)
        if resume is None:
            repo.status_value = "M  shared/migration.py\n?? omitted-proof.txt"
        return result

    agent.run_writer = dirty_writer  # type: ignore[method-assign]

    with pytest.raises(RunnerError, match="fully staged"):
        TaskPackRunner(repo=repo, agent=agent).run("repair", risk="high")


def test_runner_rejects_ambiguous_reviewer_output() -> None:
    repo = FakeRepo()
    agent = FakeAgent(repo, ["looks fine to me"])

    with pytest.raises(RunnerError, match="must start with GO or NO-GO"):
        TaskPackRunner(repo=repo, agent=agent).run("repair", risk="high")
