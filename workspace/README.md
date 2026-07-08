# Cognitive-Loop-OS Workspace

本工作区保存项目设计过程中的进口知识包（intake）和会议记录。

## 目录

```text
workspace/
├── README.md           # 本文档
├── intake/             # 进口知识包 — 功能设计和实现记录
├── imports/            # 已清空 — 原参考材料已移至 docs/architecture/imported-designs/
└── configuration/      # 配置说明 (CODEX, README)
```

## 已吸收的外部参考

原 `workspace/imports/` 中的 262 个文件已处理：

- **保留** (63 个设计文档)：移至 `docs/architecture/imported-designs/`
  - AB双系统架构设计 (A-line, B-line)
  - 双系统融合方案 (dual-system-integration)
  - 关键参考文档 (reference-key-docs)
  - 项目声明/铁律 (inspiration-research-root)
- **已吸收** (86 个 Python 参考代码)：逻辑已改编到 `shared/`、`app/`、`Knowledge-Base/`
- **已清理** (113 个)：其他项目元数据、重复文档、前端配置

## 规则

- Intake 记录 (`intake/`): 每次框架方向性变更必须留存
- 配置说明 (`configuration/`): 公共人与代理配置目录
- 不提交日志、数据库、缓存、venv
