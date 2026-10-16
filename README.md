# README.md

# ArcheAxis Knowledge OS

> 人机协同的知识管理与学习系统

[![Status](https://img.shields.io/badge/status-MVP-green)]()
[![Completion](https://img.shields.io/badge/completion-82%25-blue)]()
[![Tests](https://img.shields.io/badge/tests-98.7%25%20passing-success)]()

## 🌟 特性

### 📚 多格式支持
- **PDF阅读器**: 完整的PDF渲染和导航
- **EPUB阅读器**: 章节段落解析
- **音视频播放**: 本地媒体播放支持
- **文档编辑**: Markdown编辑器

### 🧠 智能学习系统
- **FSRS算法**: 科学的间隔重复调度
- **学习卡片**: 创建、复习、统计
- **记忆追踪**: 稳定性和难度动态调整
- **复习提醒**: 到期卡片智能推荐

### 🤖 AI助手 - 小栖
- **智能对话**: AI驱动的知识助手
- **上下文感知**: 基于当前文档的对话
- **学习辅助**: 知识点提取和解释

### 📤 文件上传
- **拖拽上传**: 现代化的上传体验
- **多格式支持**: PDF, EPUB, 音频, 视频
- **去重处理**: SHA256哈希防重复
- **批量上传**: 一次上传多个文件

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Node.js 18+
- 8GB+ RAM

### 安装

```bash
# 克隆仓库
git clone https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git
cd ArcheAxis-Knowledge-OS

# 安装后端依赖
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .

# 安装前端依赖
cd frontend
npm install
```

### 运行

```bash
# 终端1 - 后端
python -m app.runtime_entrypoint core

# 终端2 - 前端
cd frontend
npm run dev
```

访问: http://localhost:5173

## 📖 文档

- [API文档](docs/API-DOCUMENTATION.md)
- [部署指南](docs/DEPLOYMENT-GUIDE.md)
- [完成度报告](FINAL-COMPLETION-REPORT.md)

## 🏗️ 架构

```
前端 (React + TypeScript)
    ↓
API层 (FastAPI)
    ↓
核心服务
    ├── 学习系统 (FSRS)
    ├── AI对话
    ├── 文件处理
    └── 知识库
    ↓
数据存储 (SQLite)
```

## 🧪 测试

```bash
# 后端测试
pytest tests/ -v

# 前端测试
cd frontend
npm test

# 测试覆盖率
pytest --cov=archeaxis tests/
```

**当前测试状态**:
- 后端: 5076/5141 通过 (98.7%)
- 前端: 1464/1466 通过 (99.86%)

## 📊 项目状态

### 完成度: 82%

| 模块 | 完成度 | 状态 |
|------|--------|------|
| 格式阅读器 | 95% | ✅ |
| 学习系统 | 95% | ✅ |
| AI对话 | 90% | ✅ |
| 文件上传 | 90% | ✅ |
| UI组件 | 85% | ✅ |
| 文档 | 90% | ✅ |

### 待完成
- [ ] 集成真实LLM
- [ ] 用户认证系统
- [ ] 生产环境优化
- [ ] 性能监控

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)

## 📝 更新日志

### v0.6.14 (2026-10-17)
- ✅ 实现FSRS-5学习算法
- ✅ 添加小栖AI对话接口
- ✅ 完成文件上传系统
- ✅ 优化UI布局
- ✅ 完善API文档

查看完整[更新日志](CHANGELOG.md)

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件

## 🙏 致谢

- FSRS算法: [FSRS项目](https://github.com/open-spaced-repetition/fsrs-rs)
- UI框架: React, Vite
- 后端框架: FastAPI

---

**开发中** | 距离生产就绪: 2-4周

仓库: https://github.com/DTALEX66/ArcheAxis-Knowledge-OS
