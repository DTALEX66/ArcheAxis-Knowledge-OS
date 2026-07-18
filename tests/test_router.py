"""Tests for attention router."""
from app.core.router import route
from app.schemas import CoreObject


def make_doc(content: str, source: str = "test") -> CoreObject:
    return CoreObject(content=content, source=source)


class TestRoute:
    def test_empty_content_dropped(self):
        result = route(make_doc(""))
        assert result.route == "DROP"

    def test_low_value_dropped(self):
        for text in ["ok", "hi", "test", "ping"]:
            result = route(make_doc(text))
            assert result.route == "DROP", f"'{text}' should be DROP"

    def test_high_risk_review(self):
        result = route(make_doc("请执行 rm -rf 删除系统目录"))
        assert result.route == "REVIEW"
        assert result.risk_level == "high"

    def test_sensitive_keywords_review(self):
        for text in ["private key", "api key", "token", "password", "credential"]:
            result = route(make_doc(f"use {text} to access"))
            assert result.route == "REVIEW", f"'{text}' should be REVIEW"

    def test_task_routing(self):
        result = route(make_doc("请帮我执行这个任务并生成报告"))
        assert result.route == "TASK"

    def test_ir_routing(self):
        result = route(make_doc("调研对比开源RAG框架方案"))
        assert result.route == "IR"

    def test_kb_routing(self):
        result = route(make_doc("学习知识卡片复习笔记总结"))
        assert result.route == "KB"

    def test_task_with_command_marker_prioritized(self):
        result = route(make_doc("请帮我把这个学习资料整理成卡片并生成执行计划"))
        assert result.route == "TASK"  # command marker wins over KB keywords
