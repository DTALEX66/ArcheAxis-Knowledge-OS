# Configuration Authority Index (AXC-010)

> 唯一机器可读/人类可读的项目配置权威索引。一条规则只允许一个 canonical
> source；其余引用或标记 SUPERSEDED。新增会话默认权威 = 本表，不取
> Handoff/intake/旧 taskpack。
> 建立：2026-08-13（AXC-010，Project Config CI DeDup TaskPack v1.1）

| Concern | Authority | 说明 |
|---|---|---|
| 项目 agent 边界 | `AGENTS.md` | 使命、目录边界、隐私/数据边界、工作规则 |
| 验证节奏 | `docs/VERIFICATION_POLICY.md` | 风险类型与验证节奏、审计/审查触发 |
| path risk | `.worklab/project-validation.v1.yaml` | 变更路径 → 风险类 → Gate 映射 |
| gate vocabulary | `.worklab/gate-registry.v1.yaml` | 本项目可被调用的稳定 Gate ID |
| fast CI implementation | `.github/workflows/ci.yml` | push/PR 的路径风险选择与快速门禁；不是全量资格证据 |
| full qualification implementation | `.github/workflows/nightly.yml` | schedule/manual 的兼容矩阵、全量 Python、浏览器与 Windows 运行时门禁；结果必须按精确 SHA 回读 |
| release implementation | `.github/workflows/release.yml` | 精确 SHA 候选产物的发布流程；发布不替代资格门禁 |
| runtime defaults | `config/defaults.yaml` | 产品运行时默认真值（唯一） |
| runtime profiles | `config/profiles/*.yaml` | 按环境差异（不复制整树） |
| runtime legacy shim | `config/settings.yaml` | 兼容入口（保持空映射） |
| naming | `docs/truth/NAMING_CONTRACT_V2.md` | 命名体系 V2（binding） |
| current capability | `docs/truth/CURRENT_STATE_TRUTH.md` | 当前能力/状态真值 |
| future blueprint | `docs/truth/CAPABILITY_ATLAS_V2.yaml` | 未来蓝图（DEFERRED/PARKED 保留） |
| language ownership and migration | `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` | 语言边界、兼容命名与迁移门禁 |
| directory topology and cleanup | `docs/DIRECTORY_AUTHORITY_INDEX.md` | 路径分类、归档/移动/删除前置条件 |

## 优先级（项目独立执行时）

```text
官方客户端规则
  ↓
本项目 AGENTS + 项目 profile（项目工作）
  ↓
TaskPack（当前任务）
```

## 优先级（可选外部协调时）

```text
WORK-LAB USER_OVERLAY（仅全局协调，不进入产品运行时）
  ↓ 版本化协议读取
本项目 AGENTS + 项目 profile（权威仍在本仓库）
```

## 产品运行时配置优先级

```text
defaults.yaml
  ↓
profile/{development,test,desktop,production}.yaml
  ↓
local ignored config（不提交）
  ↓
ARCHEAXIS_* environment（COGNITIVE_* 仅限期兼容）
  ↓
CLI explicit override
```

工作配置与产品运行配置绝对分开。
