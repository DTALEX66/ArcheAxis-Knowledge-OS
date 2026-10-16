"""
End-to-end test suite for complete workflow validation
"""
import pytest
import requests
from pathlib import Path
import tempfile
import hashlib


BASE_URL = "http://127.0.0.1:8000"


class TestEndToEnd:
    """完整工作流程测试"""

    def test_system_handshake(self):
        """测试系统握手"""
        response = requests.get(f"{BASE_URL}/api/v1/system/handshake")
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == "archeaxis-workspace"
        assert "backend_version" in data

    def test_file_upload_workflow(self):
        """测试文件上传工作流"""
        # 创建测试文件
        test_content = b"Test PDF content for upload test"
        test_hash = hashlib.sha256(test_content).hexdigest()

        # 上传文件
        files = {"file": ("test.pdf", test_content, "application/pdf")}
        response = requests.post(f"{BASE_URL}/api/v1/upload/document", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_id"] == test_hash
        assert data["type"] == "pdf"

    def test_learning_card_workflow(self):
        """测试学习卡片工作流"""
        card_id = "test-card-001"

        # 创建卡片
        response = requests.post(f"{BASE_URL}/api/v1/learning/cards?card_id={card_id}")
        assert response.status_code == 200

        # 获取卡片状态
        response = requests.get(f"{BASE_URL}/api/v1/learning/cards/{card_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == card_id
        assert data["reps"] == 0

        # 复习卡片 - Good
        review_data = {"card_id": card_id, "rating": 3}
        response = requests.post(
            f"{BASE_URL}/api/v1/learning/cards/{card_id}/review",
            json=review_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["next_interval_days"] > 0
        assert data["stability"] > 0

    def test_ai_chat_workflow(self):
        """测试AI对话工作流"""
        chat_data = {
            "message": "你好，小栖",
            "context": "测试对话",
            "history": []
        }

        response = requests.post(f"{BASE_URL}/api/v1/ai/chat", json=chat_data)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert data["state"] in ["idle", "thinking"]

    def test_learning_stats(self):
        """测试学习统计"""
        response = requests.get(f"{BASE_URL}/api/v1/learning/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_cards" in data
        assert "due_today" in data

    def test_upload_status_check(self):
        """测试上传状态检查"""
        test_file_id = "abc123"
        response = requests.get(f"{BASE_URL}/api/v1/upload/status/{test_file_id}")
        assert response.status_code == 200
        data = response.json()
        assert "exists" in data

    def test_ai_status(self):
        """测试AI服务状态"""
        response = requests.get(f"{BASE_URL}/api/v1/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "capabilities" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
