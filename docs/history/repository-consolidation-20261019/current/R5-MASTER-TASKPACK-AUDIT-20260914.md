# R5 / Deep Adaptation Master TaskPack 审计（2026-09-14）

## 结论

用户提供的 2026-09-13 文本是对 R5 的方向性补充和 Wave 规划，不能替代当前活动包 `docs/authority/taskpack-0912-r5/`、`docs/current/R5-STATE.json` 或独立审计要求。它包含若干已经过时的现场数值，也包含尚未验证的外部项目版本/能力描述。当前实现仍以 R5 状态和真实命令证据为准。

## 与当前证据一致的内容

- 产品身份、Rust Core + SQLite 单写者 + Python 隔离 worker + C#/Avalonia 壳层的方向与 `AGENTS.md` 和 R5 当前架构一致。
- R5 的主线状态（R00–R09/R11 待审计、R10/R12/R13/R15 未闭合、R14/R16 独立审计未完成）与当前 `R5-STATE.json` 的未完成事实一致；当前状态字段更细，不能用文本中的简写覆盖它。
- “格式 COMPLETE 必须覆盖 detect→parse→structure→anchor→evidence→search→知识候选→回跳来源→新机器回归”与现有格式矩阵的治理方向一致。
- “内部模型保持 ArcheAxis schema、对外做标准投影”“LLM 输出不能直接写 mastery truth”“WORK-LAB/Agent Memory 不能成为 ArcheAxis Truth”等边界与现行项目契约一致。
- R12 必须 inventory→ownership→manifest/hash→逐路径授权→删除→复核；本轮实际已删除 453 项，125 项仍因 ACL 拒绝未处理，不能把文本写成全部完成。

## 已过时或必须改写的内容

| 文本中的说法 | 当前核对 | 处理 |
| --- | --- | --- |
| Cloud main 为 `1e9813e...` | 这是本地 `main`/缓存 ref 的已知 SHA；本轮未 fetch，不能证明实时云端一致 | 保留为“本地基线”，加上未 fetch 限定 |
| `.hermes` 约 42.9 GiB / 718k files，尚未授权删除 | 这是清理前历史快照；当前可读 `.hermes` 约 0.463 GiB，历史材料已迁移，不能据此描述当前体积；ACL-deny 内容仍未知 | 改成“历史基线；当前可读值以最新盘点为准；未知内容不归因” |
| R12 尚未授权删除 | 用户已授权逐路径清理；实际完成 453 删除，125 ACL 阻塞 | 改成分项状态 |
| “DeepTutor v1.6.7 已形成完整生态” | 当前仓库仅有宿主接线/合成保存等局部证据；版本与完整生态未做本轮外部核验 | 标为外部事实待核，不作为完成依据 |
| Docling/MinerU/FSRS/FoundationalASSIST/TutorBench/MMTutorBench 等版本、数量、许可证与能力 | 本仓库当前证据未逐项绑定来源、版本和复现实验 | 只能作为候选研究输入；进入实施前需许可证、版本和 benchmark 收据 |
| “第一阶段 Done When” | 这是新方向的验收愿景，不是当前 R5 已接受的 Gate；R14/R16 仍要求独立审计 | 作为后续验收草案保留，不提升当前状态 |

## 当前缺口（按可执行顺序）

1. X00/X01：完成 HL01 导入与路径/产物治理的定向回归，继续保留未知私有状态。
2. X02：完成供体语义核查和 M0/M1 吸收资格记录，不把候选列表当已吸收。
3. X03/X08：补齐桌面学习题目渲染、复习提交、学习事件/来源修订可见性和恢复证据；DeepTutor 只走冻结的 host adapter 决策。
4. X06/X09/X10：补齐真实格式、MCP、迁移附件/关系的证据，区分 probe、execution、质量和回跳。
5. X11/X13：完成候选包、安装器、卸载、依赖诊断、干净 Windows 启动和回滚证据。
6. X12/X14：逐路径处理剩余清理候选；ACL 拒绝项需管理员/外部状态变化，不能由普通权限强行绕过。
7. R14/R16：待前置条件满足后，由未参与实现的独立审计者按 G01–G14 逐项 PASS/FAIL/BLOCKED；执行者不得自签。

## 证据边界

- 本审计读取了用户提供的附件文本，并与当前仓库的 `AGENTS.md`、`docs/current/R5-STATE.json`、`docs/current/R5-EXECUTION.md` 和本轮路径盘点结果对照。
- 未读取 `.hermes`、`.zcode`、`.codex`、凭据、E 盘或外置资料库；未 fetch 远端、未运行安装器、未运行可见桌面窗口、未运行 Rust/C# 编译（当前环境无对应工具链）。
- 本文是差分审计与执行排序，不是产品通过声明，也不是 R14/R16 独立签字。

## 本轮推进

- AA-P0-005 的仓库同步依赖文档已完成最小 SSOT 修正：正式桌面明确为 C#/Avalonia，Tauri/Node/Rust 桌面条目降级为 legacy 恢复/兼容用途；相关 41 项治理测试通过。
