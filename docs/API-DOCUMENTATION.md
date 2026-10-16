# ArcheAxis Knowledge OS - API文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1
- **认证**: 暂无（开发中）

## 端点概览

### 系统 API

#### GET /api/v1/system/handshake
系统握手，获取版本信息

**响应示例**:
```json
{
  "product_id": "archeaxis-workspace",
  "product_name": "ArcheAxis Knowledge",
  "api_contract": "1.x",
  "backend_version": "0.6.14",
  "source_commit": "6d78de83",
  "workspace_id": "xxx"
}
```

---

### 文件上传 API

#### POST /api/v1/upload/document
上传文档（PDF、EPUB、文本）

**请求**:
- Content-Type: `multipart/form-data`
- 字段: `file` (文件)

**响应示例**:
```json
{
  "success": true,
  "file_id": "abc123...",
  "filename": "document.pdf",
  "size": 102400,
  "type": "pdf",
  "content_type": "application/pdf"
}
```

#### POST /api/v1/upload/media
上传媒体文件（音频、视频）

**支持格式**:
- 音频: MP3, WAV, M4A, OGG
- 视频: MP4, WebM, OGG

#### POST /api/v1/upload/batch
批量上传文件

#### GET /api/v1/upload/status/{file_id}
检查文件上传状态

---

### 学习系统 API

#### POST /api/v1/learning/cards?card_id={id}
创建新学习卡片

**响应**:
```json
{
  "card_id": "card-001",
  "stability": 0.4,
  "difficulty": 7.19,
  "reps": 0,
  "lapses": 0
}
```

#### POST /api/v1/learning/cards/{card_id}/review
复习卡片

**请求体**:
```json
{
  "card_id": "card-001",
  "rating": 3  // 1=again, 2=hard, 3=good, 4=easy
}
```

**响应**:
```json
{
  "card_id": "card-001",
  "next_interval_days": 10,
  "next_due": "2026-10-27T00:00:00",
  "stability": 8.5,
  "difficulty": 6.8
}
```

#### GET /api/v1/learning/cards/{card_id}
获取卡片状态

#### GET /api/v1/learning/cards/due?limit=20
获取到期卡片列表

#### GET /api/v1/learning/stats
获取学习统计

**响应**:
```json
{
  "total_cards": 100,
  "due_today": 15,
  "reviewed_cards": 80,
  "new_cards": 20
}
```

---

### AI 对话 API

#### POST /api/v1/ai/chat
与小栖AI对话

**请求体**:
```json
{
  "message": "你好，小栖",
  "context": "当前文档标题",
  "history": [
    {"role": "user", "content": "之前的消息"},
    {"role": "assistant", "content": "之前的回复"}
  ]
}
```

**响应**:
```json
{
  "response": "你好！我是小栖，有什么可以帮助你的吗？",
  "state": "idle"
}
```

#### GET /api/v1/ai/status
获取AI服务状态

**响应**:
```json
{
  "status": "online",
  "model": "simulated",
  "capabilities": ["chat", "knowledge", "learning"]
}
```

---

## FSRS算法说明

### 评分系统
- **1 (Again)**: 完全忘记，需要重新学习
- **2 (Hard)**: 困难，勉强记起
- **3 (Good)**: 良好，正确回忆
- **4 (Easy)**: 简单，轻松回忆

### 间隔计算
基于FSRS-5算法：
- 记忆稳定性 (Stability)
- 难度 (Difficulty)
- 可提取性 (Retrievability)

### 默认参数
- 目标保持率: 90%
- 最大间隔: 100年
- 启用随机化: 是

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求错误 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 开发计划

### 即将推出
- [ ] 用户认证
- [ ] 真实LLM集成
- [ ] WebSocket实时通信
- [ ] 批量操作API
- [ ] 导出功能API

---

更新时间: 2026-10-17
版本: 0.6.14
