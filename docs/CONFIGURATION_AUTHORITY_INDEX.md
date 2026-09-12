# Configuration Authority Index (AXC-010)

> 唯一机器可读/人类可读的项目配置权威索引。一条规则只允许一个 canonical
> source；其余引用或标记 SUPERSEDED。新增会话默认权威 = 本表，不取
> Handoff/intake/旧 taskpack。
> 建立：2026-08-13（AXC-010，Project Config CI DeDup TaskPack v1.1）

| Concern | Authority | 说明 |
|---|---|---|
| 项目 agent 边界 | `AGENTS.md` | 使命、目录边界、隐私/数据边界、工作规则 |
| 当前执行与架构决策 | `PROJECT_CONTRACT.yaml`、`DECISION_SUPERSESSION_LEDGER.yaml`、`docs/current/R5-EXECUTION.md` | 唯一活动包 `docs/authority/taskpack-0912-r5/`（AAK-FOLLOWUP-20260908-R3 / R5，SUP-019）；进度侧车 `docs/current/R5-STATE.json`。0910 R3.1及0908/0907/0906保留原任务正文与各自SHA收据，历史基线不是当前完成状态；独立Q00/Q01不由执行者自签 |
| 本机共享库、绿色软件与资料根路径 | [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) | 用户 2026-09-07 指定的五个资源根；每次定位工具/模型/测试资料先查此表，不猜目录；真实资料库与测试库严格分离，不等于修改产品设置 |
| 开发运行根 | `scripts/runtime/dev.py` | `.project-local` 下 worktree/run 隔离；Bash/PowerShell 共用；不是产品 workspace |
| 正式桌面worker路径载荷 | `apps/ArcheAxis.Desktop/WorkerProfile.cs` | `archeaxis.worker-profile/v1`：应用旁worker-profile.json，显式ARCHAXIS_WORKER_PROFILE覆盖；只含schema/python/script/staging，严格拒绝未知/重复字段及受保护/链接路径。开发由scripts/launch/desktop_launch.py经dev.py生成隔离配置；不改变legacy defaults数据库或读取私有代理配置 |
| 桌面启动身份 | `packages/contracts/bootstrap/v2/launch.schema.json`、`docs/current/R5-DESKTOP-IDENTITY-V2.md` | 显式v2 stdin双令牌、单Core写者；Core作跨字段及路径语义校验，不能把Schema验证当作权限验收 |
| Core持久复习状态 | `packages/contracts/learning/v1/review.schema.json`、`docs/current/R5-LEARNING-STATE.md` | `/api/v1/learning/reviews`从Core事件恢复完整FSRS状态，独立于旧/events收据契约；只有human可写，状态由Core与worker产生，默认UI接线仍需验收 |
| 跨语言词汇与损失回执 | `packages/contracts/v1/`、`scripts/contracts/generate_vocabulary.py` | Schema 为单源；Rust/C#/Python 词汇生成后须 `--check`；loss receipt 另有跨字段运行时校验，完整 DTO/权限协议仍在推进 |
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
