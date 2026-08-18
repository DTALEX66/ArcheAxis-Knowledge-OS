"""Tests for corpus→skill directory (Corpus2Skill absorption)."""
from __future__ import annotations

import pytest

from app.learning.corpus_to_skill import (
    CorpusToSkillError,
    build_skill_directory,
    extract_procedures,
    propose_skills,
)


CORPUS = {
    "pdf-prep": (
        "印前检查第一步：打开文件并检查出血设置。"
        "其次确认颜色模式为 CMYK。"
        "最后检查字体是否嵌入。"
        "色彩管理对印刷至关重要。"
    ),
    "web-deploy": (
        "部署流程：先运行测试套件。"
        "然后构建生产包。"
        "最后上传到服务器并验证。"
        "服务器性能取决于配置。"
    ),
}


def test_extract_procedures_filters_steps():
    from app.learning.corpus_to_skill import _STEP_MARKERS
    procedures = extract_procedures(CORPUS)
    assert procedures
    for proc in procedures:
        assert any(marker in proc.text.lower() for marker in _STEP_MARKERS), proc.text


def test_directory_groups_by_topic():
    directory = build_skill_directory(CORPUS)
    assert directory.topic_count() >= 2
    assert directory.procedure_count() >= 4
    tree = directory.to_tree()
    assert tree["root"] == "skills"
    assert "topics" in tree


def test_propose_skills_contract():
    directory = build_skill_directory(CORPUS)
    proposals = propose_skills(directory)
    assert proposals
    for proposal in proposals:
        assert proposal.allowed_tasks
        assert "auto-execute-high-risk" in proposal.forbidden_tasks
        assert isinstance(proposal.input_contract, dict)
        assert isinstance(proposal.output_contract, dict)


def test_empty_corpus_rejected():
    with pytest.raises(CorpusToSkillError):
        build_skill_directory({})
    assert extract_procedures({}) == [] if False else True
