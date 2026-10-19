# 星环知识系统（ArcheAxis Knowledge）

本地优先、原件保全、证据可追溯的人机双向学习与可信知识工作台。

**当前状态：PARTIAL。** Owner 于2026-10-18恢复项目内实施；当前范围读[活动指针](docs/current/AAOS-ACTIVE-EXECUTION.json)，实际进度读[执行记录](docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。[接手入口](docs/current/AAOS-AGENT-HANDOFF-CURRENT.md)与[会话整合](docs/current/AAOS-SESSION-RECONCILIATION-20261018.md)记录本轮证据和未完成项。测试、构建、CI、安装运行和Owner验收分别判断，当前没有可靠的整体完成率。

正式宿主是 `frontend/`（React/TypeScript/Vite）和 `src-tauri/`（Tauri 2）。Rust Core 是 SQLite/CAS 唯一写者，Python workers 隔离运行。普通文档保存不以模型或云核验为前置；候选知识的人工接受另行执行。详见[合同](PROJECT_CONTRACT.yaml)及[当前架构](docs/architecture/CURRENT_ARCHITECTURE.md)。

六项核心能力对话增量、V01、FT01–04仍按活动指针冻结或暂停；Owner 已要求小栖/ASTRYN直接并入本项目，见[整合决定](workspace/intake/20261018-xiaoqi-in-project.md)。发布、Green替换和真实数据覆盖未授权。

[项目资料与实施收敛](docs/current/AAOS-PROJECT-CLOSURE-20261018.md)汇集历史保全、权威任务包、会话索引、88个跟踪ID及开源吸收/延期/拒绝依据；原始资料与恢复包保全在项目内部忽略区，公开结论与源码单独审查。

## 能力范围与验证

以下为能力方向与已有组件概览，各格式的实际摄入、编辑、往返、学习效果和安装资格需按执行记录分别验收；组件存在不代表整个流程已完成。

### 📚 多格式支持
- **PDF阅读器**: PDF渲染和导航组件
- **EPUB阅读器**: 章节段落解析
- **音视频播放**: 本地媒体播放支持
- **文档编辑**: Markdown编辑器

### 🧠 智能学习系统
- **FSRS算法**: 间隔重复调度组件；实际学习效果单独评估
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

## 开发入口

先读[共享资源与工具链索引](docs/SHARED_RESOURCE_PATH_INDEX.md)、[运行交付索引](docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md)和[验证规则](docs/VERIFICATION_POLICY.md)，优先使用项目现有环境及lockfile。Python-era FastAPI入口属于兼容/供体路径，不能替代正式Tauri宿主启动与验证。

在已准备依赖的项目根目录构建正式前端：

```powershell
node scripts/runtime/frontend.mjs build
```

构建输出由项目运行路由保存到 `.project-local/`。构建通过不证明安装版、真实模型或原生完整旅程通过。

## 📖 文档

- [API文档](docs/API-DOCUMENTATION.md)
- [部署指南](docs/DEPLOYMENT-GUIDE.md)
- [当前任务与证据](docs/current/AAOS-SESSION-RECONCILIATION-20261018.md)
- [原始资料与归档入口](AAOS-资料索引.md)
- [文档权威索引](docs/DOCUMENTATION_AUTHORITY_INDEX.md)
- [文档身份路由](docs/current/AAOS-AUTHORITY-ROUTES.json)

## 🏗️ 架构

```
正式宿主 (Tauri 2 + React + TypeScript)
    ↓
受认证的有限命令桥接
    ↓
Rust Core（SQLite/CAS唯一写者）
    ↓
隔离 Python workers（解析、转换等）
```

## 🧪 测试

```powershell
# 项目根目录；run-id每次使用新的值
.venv/Scripts/python.exe -B scripts/runtime/dev.py --run-id <unique-run-id> -- node frontend/node_modules/vitest/vitest.mjs run --root frontend
```

2026-10-18本轮第二批本地前端回归：158文件、1516用例通过，TypeScript与Vite构建通过，绑定 `fe18fdc3` 加当时未提交前端修改。模型/Core测试使用模拟，不代表真实推理。后端全量、当前exact-SHA CI、原生安装及Owner验收未在本轮完成；具体收据见[统一本地验证记录](docs/current/receipts/AAOS-TAKEOVER-VALIDATION-20261018.json)；浏览器13视口5主题及文档/浏览器工具24项检查通过，Host/Core仍为模拟。Codex主会话及执行/审计子会话已另列[专项索引](docs/current/AAOS-CODEX-SESSION-INDEX-20261018.md)。

## 📊 项目状态

当前为 **PARTIAL**，不以测试数量或候选目录条数计算产品完成率。

### 待完成
- [ ] 性能监控接入实际视图与资源实测
- [ ] 完整键盘、焦点、状态及主题可访问性验证
- [ ] 前后端合同、常用格式和人机学习的剩余整任务验收
- [ ] 同版本原生旅程、重启/恢复及真实交付资产

### 历史材料

- **Historical snapshot: pre-R6 Research implementation**：旧研究与Python-era实现只作为行为供体，参见[历史状态](docs/PROJECT_STATUS.md)；当前职责按正式宿主与活动指针解释。
- **Historical snapshot: pre-R6 program roadmap**：旧阶段与未来规划见[历史蓝图](docs/FUTURE_EXECUTION_BLUEPRINT.md)，不作为今天的完成证据或第二条执行队列。

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)

## 📝 更新日志

`frontend/package.json` 的源码版本为 `0.6.14`；不据此宣称该版本已发布、安装或完成整体验收。

查看完整[更新日志](CHANGELOG.md)

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件

## 🙏 致谢

- FSRS算法: [FSRS项目](https://github.com/open-spaced-repetition/fsrs-rs)
- UI框架: React, Vite
- 正式核心与宿主: Rust Core、Tauri；FastAPI保留兼容/供体用途

---

**开发中 / PARTIAL**；交付时间以剩余任务和实际验收为依据。

仓库: https://github.com/DTALEX66/ArcheAxis-Knowledge-OS
