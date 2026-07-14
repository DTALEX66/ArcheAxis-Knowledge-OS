# 006 Agent Configuration Pack

> Status: superseded. This intake is historical evidence; active policy moved to `AGENTS.md` and `docs/VERIFICATION_POLICY.md`, and the former machine profile was retired because no runtime consumed it.

## 目标

把当前 Codex/Agent 的工作方式沉淀到仓库里，但只上传公开脱敏版本。真实本机配置、凭据、私钥、Token、`.codex` 会保留在本地，不进入 Git。

## 新增配置分类

| 分类 | 文件 | 用途 |
| --- | --- | --- |
| Agent 操作规则 | `AGENTS.md` | 给人和未来 Agent 读的工作边界、Git 规则、安全规则 |
| 机器可读配置 | `config/agent_profile.yaml` | 把项目角色、安全策略、路由、摄取和上传策略结构化 |
| 配置索引 | `workspace/configuration/README.md` | 标明哪些配置能上传，哪些必须留在本地 |
| Intake 记录 | `workspace/intake/006_agent_configuration_pack.md` | 记录这一轮配置沉淀 |

## 分类原则

- 可公开、无密钥、无个人敏感路径的配置可以进仓库。
- 本机 Codex 会话状态、SSH 私钥、GitHub Token、API Key、`.env` 不进仓库。
- 配置分成人读文档和机器读 YAML 两层，方便未来自动化和多 Agent 协作。

## 对当前项目的作用

这份配置让 Cognitive-OS 成为两个主项目的前置运行层时，有稳定的操作协议：先路由、再摄取、再记忆/执行/反馈；同时保留对 KB、IR、Obsidian 三者关系的明确边界。
