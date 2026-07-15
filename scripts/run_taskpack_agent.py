"""Run one TaskPack through one persistent Hermes writer lineage.

Unlike the retired fixed-window loop, this runner never kills and restarts a writer
on a timer. High-risk work is frozen, reviewed synchronously, resumed by session ID
for findings, and released only after an exact-tree GO.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DEFAULT_SKILLS = (
    "cognitive-loop-os,agent-workflow-fortress,test-driven-development,"
    "systematic-debugging,github-pr-workflow"
)
SESSION_PATTERN = re.compile(r"(?m)^session_id:\s*(\S+)\s*$")


class RunnerError(RuntimeError):
    """Raised when an orchestration or release invariant fails."""


@dataclass(frozen=True)
class AgentResult:
    stdout: str
    stderr: str
    session_id: str


class Repository(Protocol):
    def head(self) -> str: ...

    def head_tree(self) -> str: ...

    def staged_tree(self) -> str: ...

    def snapshot(self) -> tuple[str, str]: ...

    def verify_released(self, baseline_head: str) -> None: ...


class AgentBackend(Protocol):
    def run_writer(self, prompt: str, *, resume: str | None = None) -> AgentResult: ...

    def run_reviewer(self, prompt: str) -> str: ...


class GitRepository:
    def __init__(
        self,
        root: Path,
        *,
        remote_ref: str = "origin/main",
        ci_timeout_seconds: int = 1200,
        ci_poll_seconds: int = 6,
    ) -> None:
        self.root = root.resolve()
        self.remote_ref = remote_ref
        self.ci_timeout_seconds = ci_timeout_seconds
        self.ci_poll_seconds = ci_poll_seconds

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise RunnerError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.rstrip("\r\n")

    def head(self) -> str:
        return self._git("rev-parse", "HEAD")

    def head_tree(self) -> str:
        return self._git("rev-parse", "HEAD^{tree}")

    def staged_tree(self) -> str:
        return self._git("write-tree")

    def snapshot(self) -> tuple[str, str]:
        return self.staged_tree(), self._git("status", "--porcelain=v1", "--untracked-files=all")

    def verify_released(self, baseline_head: str) -> None:
        tree, status = self.snapshot()
        del tree
        if status:
            raise RunnerError(f"writer returned with a dirty worktree:\n{status}")
        head = self.head()
        if head == baseline_head:
            raise RunnerError("writer did not create a release commit")
        self._git("fetch", "--prune", "origin")
        remote_head = self._git("rev-parse", self.remote_ref)
        if head != remote_head:
            raise RunnerError(f"release is not synchronized: HEAD={head} {self.remote_ref}={remote_head}")
        self._wait_for_ci(head)

    def _wait_for_ci(self, head: str) -> None:
        if not shutil.which("gh"):
            raise RunnerError("gh executable not found; cannot verify exact-SHA CI")
        deadline = time.monotonic() + self.ci_timeout_seconds
        while time.monotonic() < deadline:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--commit",
                    head,
                    "--limit",
                    "20",
                    "--json",
                    "status,conclusion,name,url,databaseId",
                ],
                cwd=self.root,
                check=False,
                text=True,
                capture_output=True,
            )
            if result.returncode:
                raise RunnerError(f"gh run list failed: {result.stderr.strip()}")
            runs = json.loads(result.stdout)
            if runs and all(run["status"] == "completed" for run in runs):
                failed = [run for run in runs if run.get("conclusion") != "success"]
                if failed:
                    raise RunnerError(f"exact-SHA CI failed: {json.dumps(failed, ensure_ascii=False)}")
                return
            time.sleep(self.ci_poll_seconds)
        raise RunnerError(f"timed out waiting for exact-SHA CI for {head}")


class HermesAgentBackend:
    def __init__(
        self,
        root: Path,
        *,
        hermes: str = "hermes",
        skills: str = DEFAULT_SKILLS,
    ) -> None:
        executable = shutil.which(hermes)
        if not executable:
            raise RunnerError(f"Hermes executable not found: {hermes}")
        self.root = root.resolve()
        self.hermes = executable
        self.skills = skills

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
        if result.returncode:
            raise RunnerError(
                f"Hermes exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def run_writer(self, prompt: str, *, resume: str | None = None) -> AgentResult:
        command = [
            self.hermes,
            "chat",
            "-Q",
            "--pass-session-id",
            "-t",
            "terminal,file",
            "-s",
            self.skills,
        ]
        if resume:
            command.extend(["--resume", resume])
        command.extend(["-q", prompt])
        result = self._run(command)
        match = SESSION_PATTERN.search(result.stderr)
        if not match:
            raise RunnerError(f"Hermes did not emit a parseable session_id: {result.stderr.strip()}")
        return AgentResult(result.stdout, result.stderr, match.group(1))

    def run_reviewer(self, prompt: str) -> str:
        result = self._run([self.hermes, "-t", "terminal,file", "-z", prompt])
        return result.stdout.strip()


class TaskPackRunner:
    def __init__(
        self,
        *,
        repo: Repository,
        agent: AgentBackend,
        max_review_rounds: int = 3,
    ) -> None:
        if max_review_rounds < 1:
            raise ValueError("max_review_rounds must be positive")
        self.repo = repo
        self.agent = agent
        self.max_review_rounds = max_review_rounds

    def run(self, mission: str, *, risk: str) -> None:
        if risk not in {"low", "high"}:
            raise ValueError("risk must be 'low' or 'high'")
        baseline_head = self.repo.head()
        baseline_tree = self.repo.head_tree()
        _, baseline_status = self.repo.snapshot()
        if baseline_status:
            raise RunnerError(f"TaskPack must start from a clean worktree:\n{baseline_status}")

        if risk == "low":
            result = self.agent.run_writer(self._low_risk_prompt(mission))
            if not result.session_id:
                raise RunnerError("writer session ID is empty")
            self.repo.verify_released(baseline_head)
            return

        result = self.agent.run_writer(self._freeze_prompt(mission))
        session_id = result.session_id
        self._assert_frozen(baseline_head, baseline_tree)

        for review_round in range(1, self.max_review_rounds + 2):
            frozen_tree, frozen_status = self.repo.snapshot()
            review = self.agent.run_reviewer(
                self._review_prompt(mission, frozen_tree, review_round)
            )
            if self.repo.snapshot() != (frozen_tree, frozen_status):
                raise RunnerError("reviewer changed the frozen tree or worktree status")
            decision = self._review_decision(review)
            if decision == "GO":
                result = self.agent.run_writer(
                    self._release_prompt(mission, frozen_tree, review), resume=session_id
                )
                session_id = result.session_id
                del session_id
                self.repo.verify_released(baseline_head)
                return

            if review_round > self.max_review_rounds:
                raise RunnerError(
                    "review did not reach GO after "
                    f"{self.max_review_rounds} repair rounds"
                )

            previous_tree = frozen_tree
            result = self.agent.run_writer(
                self._repair_prompt(mission, frozen_tree, review), resume=session_id
            )
            session_id = result.session_id
            self._assert_frozen(baseline_head, baseline_tree)
            if self.repo.staged_tree() == previous_tree:
                raise RunnerError("writer returned the same frozen tree after NO-GO findings")

        raise RunnerError(f"review did not reach GO in {self.max_review_rounds} rounds")

    def _assert_frozen(self, baseline_head: str, baseline_tree: str) -> None:
        if self.repo.head() != baseline_head:
            raise RunnerError("high-risk writer committed before reviewer GO")
        staged_tree, status = self.repo.snapshot()
        if not status or staged_tree == baseline_tree:
            raise RunnerError("writer did not produce a staged frozen tree for review")
        invalid = [
            line
            for line in status.splitlines()
            if len(line) < 3 or line[:2] == "??" or line[0] == " " or line[1] != " "
        ]
        if invalid:
            raise RunnerError(
                "frozen review state must be fully staged with no untracked, unstaged, "
                f"or conflicted files: {invalid}"
            )

    @staticmethod
    def _review_decision(review: str) -> str:
        first_line = next((line.strip() for line in review.splitlines() if line.strip()), "")
        if first_line == "GO":
            return "GO"
        if first_line == "NO-GO":
            return "NO-GO"
        raise RunnerError("reviewer output must start with GO or NO-GO on its own line")

    @staticmethod
    def _freeze_prompt(mission: str) -> str:
        return f"""Execute exactly one HIGH-RISK TaskPack in this repository.

MISSION:
{mission}

Use RED -> GREEN and affected checks while developing. Keep one writer session. Do not
spawn background reviewers. Do not commit or push. When implementation and the one
required full local gate are complete, stage only the intended files, verify staged diff,
secret scan and conventions, then stop with a frozen tree ready for exact-tree review.
Your final response must report READY_FOR_REVIEW plus git write-tree and test evidence.
"""

    @staticmethod
    def _low_risk_prompt(mission: str) -> str:
        return f"""Execute exactly one LOW-RISK TaskPack end to end in this repository.

MISSION:
{mission}

Use RED -> GREEN, affected checks during development, and one full gate after freezing the
diff. Do not spawn background reviewers. Stage only intended files, commit, fetch/prune,
refuse remote divergence, push, wait for the exact commit's CI, and leave a clean worktree
with HEAD equal to origin/main. Do not return a plan; finish or report a real blocker.
"""

    @staticmethod
    def _review_prompt(mission: str, tree: str, review_round: int) -> str:
        return f"""Read-only independent review. Never edit, stage, commit, or write files.
Review exact staged tree {tree} for Blocker/High findings only. Confirm git write-tree is
still {tree} before concluding. Check correctness, data loss, security, rollback and test
proof relevant to the mission below.

MISSION:
{mission}

REVIEW ROUND: {review_round}
Output GO on the first non-empty line if there are no Blocker/High findings. Otherwise
output NO-GO on the first non-empty line followed by exact file:line findings.
"""

    @staticmethod
    def _repair_prompt(mission: str, tree: str, review: str) -> str:
        return f"""Continue the SAME TaskPack and writer lineage after an exact-tree NO-GO.
The reviewed tree was {tree}. Fix every finding below at its root, add RED/GREEN proof,
rerun affected checks and the full gate only after refreezing, stage only intended files,
and stop without committing or pushing.

MISSION:
{mission}

REVIEW FINDINGS:
{review}
"""

    @staticmethod
    def _release_prompt(mission: str, tree: str, review: str) -> str:
        return f"""Continue the SAME TaskPack after reviewer GO for exact tree {tree}.
First verify git write-tree is still exactly {tree}; do not alter reviewed production
content. Commit the frozen tree, fetch/prune, refuse remote divergence, push, wait for the
exact commit's CI, and leave a clean worktree with HEAD equal to origin/main. Report real
SHA, CI run URL and evidence.

MISSION:
{mission}

REVIEW RESULT:
{review}
"""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mission = parser.add_mutually_exclusive_group(required=True)
    mission.add_argument("--mission", help="Inline TaskPack mission")
    mission.add_argument("--mission-file", type=Path, help="UTF-8 mission file")
    parser.add_argument("--risk", choices=("low", "high"), required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--remote-ref", default="origin/main")
    parser.add_argument("--max-review-rounds", type=int, default=3)
    parser.add_argument("--skills", default=DEFAULT_SKILLS)
    parser.add_argument("--hermes", default="hermes")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    mission = (
        args.mission_file.read_text(encoding="utf-8")
        if args.mission_file is not None
        else args.mission
    )
    repo = GitRepository(args.repo, remote_ref=args.remote_ref)
    agent = HermesAgentBackend(args.repo, hermes=args.hermes, skills=args.skills)
    TaskPackRunner(
        repo=repo,
        agent=agent,
        max_review_rounds=args.max_review_rounds,
    ).run(mission, risk=args.risk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
