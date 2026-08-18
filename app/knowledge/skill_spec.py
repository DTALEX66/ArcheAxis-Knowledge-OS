"""SKILL.md specification — absorbed from colleague-skill (titanwings).

Skills are portable markdown documents with YAML frontmatter and a structured
body (report §3.8, A4 teardown). This module parses/validates SKILL.md and
generates a skill doc from an expert rule + optional persona, so distilled
human knowledge becomes a portable, reviewable capability.

Format (colleague-skill style, adapted to local-first governance):

    ---
    name: <skill-name>
    description: <one-line>
    version: <semver>
    source: <distillation://rule-id | corpus://...>
    risk_level: low|medium|high
    license: MIT
    ---
    ## Trigger
    ...
    ## Process
    ...
    ## Rules
    ...
    ## Examples
    ...
    ## Persona (optional)
    ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.knowledge.distillation import ExpertRule


class SkillSpecError(ValueError):
    """Raised when a SKILL.md document is invalid."""


@dataclass(frozen=True)
class SkillDoc:
    name: str
    description: str
    version: str
    source: str
    risk_level: str
    license: str
    sections: dict[str, list[str]] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "---",
            f"name: {self.name}",
            f"description: {self.description}",
            f"version: {self.version}",
            f"source: {self.source}",
            f"risk_level: {self.risk_level}",
            f"license: {self.license}",
            "---",
            "",
        ]
        for title, items in self.sections.items():
            lines.append(f"## {title}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_skill_doc(markdown: str) -> SkillDoc:
    """Parse a SKILL.md document (frontmatter + body sections)."""
    match = _FRONTMATTER_RE.match(markdown.strip())
    if not match:
        raise SkillSpecError("SKILL.md requires YAML frontmatter between --- markers")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    required = {"name", "description", "version", "source", "risk_level"}
    missing = required - set(meta)
    if missing:
        raise SkillSpecError(f"frontmatter missing: {sorted(missing)}")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in match.group(2).splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        elif current and line.strip().startswith("- "):
            sections[current].append(line.strip()[2:].strip())
    return SkillDoc(
        name=meta["name"], description=meta["description"], version=meta["version"],
        source=meta["source"], risk_level=meta.get("risk_level", "low"),
        license=meta.get("license", "MIT"), sections=sections,
    )


def from_expert_rule(rule: ExpertRule, *, skill_name: str, version: str,
                     allowed_tasks: list[str] | None = None,
                     persona: str | None = None) -> SkillDoc:
    """Generate a SKILL.md doc from a verified expert rule (+ optional persona)."""
    if not skill_name.strip():
        raise SkillSpecError("skill name is required")
    sections: dict[str, list[str]] = {
        "Trigger": [f"适用于：{c}" for c in rule.conditions] or ["通用"],
        "Process": [f"{k}: {v}" for k, v in rule.action.items()] or ["按规则执行"],
        "Rules": [f"规则 {i+1}: 来自 {p}" for i, p in enumerate(rule.principle_ids)],
        "Examples": allowed_tasks and [f"任务：{t}" for t in allowed_tasks] or [],
    }
    if persona:
        sections["Persona"] = [persona]
    return SkillDoc(name=skill_name.strip(), description=rule.title, version=version,
                    source=f"distillation://{rule.rule_id}", risk_level="low",
                    license="MIT", sections=sections)
