# ArcheAxis Workspace Planning Sources — 2026-08-09

> **状态：用户提供的原始规划、蓝图、任务包与交接参考。**
>
> 本目录用于保存来源和防止上下文丢失，不是当前实现证明，也不覆盖仓库的冻结执行权威。

## 权威边界

当前执行仍按以下文件裁决：

- [`AUTHORITY_CONTRACT.md`](../../../../../truth/AUTHORITY_CONTRACT.md)
- [`FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`](../../../../../truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md)
- [`DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md`](../../../../../taskpacks/DEEPSEEK_FULL_EXECUTION_TASKPACK_v1_2026-08-09.md)
- [`MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md`](../../../../../taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md)
- [`MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md`](../../../../../taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md)
- [`EXECUTION_STATUS_LOG.md`](../../../../../truth/EXECUTION_STATUS_LOG.md)

## 归档文件

| 文件 | 原件 SHA-256 | 仓库可读副本 SHA-256 | 角色 |
| --- | --- | --- | --- |
| `ArcheAxis_Workspace_v0.5_Multiformat_Full_Audit_and_Recovery_TaskPack_2026-08-09.md` | `48212d25e60e4447e4fedb3022c267403b6e0e4ec32e00b16b3e99601a293f89` | `d8e9cf99a145650fec7b1afc4cd1ad24600ea05b8d5ddf962299e4632868d7fc` | v0.5 多格式审计与恢复输入 |
| `ArcheAxis_Workspace_Future_Master_Blueprint_v1_2026-08-09.md` | `4f8660a0591d52f8b13ff0122aea87db6b6d28be9a59eabbfbf4f5a7cc90851b` | `bab757afd90c541cc1288ed024dd9352f19e0946192f42e5d08f4ff3ca701d7e` | 未来产品与技术蓝图输入 |
| `ArcheAxis_Workspace_CODEX_Final_Master_TaskPack_v3_2026-08-09.md` | `75f3e97de6a483f7a3a71a1b660ad307081e8f65ab6df0e9fa6d50fd3340a756` | `ea09069818d918a6a10bf12480de411288905b1a306b517561e3d485edf2163f` | 被 v4 取代的历史主任务包 |
| `ArcheAxis_Workspace_Final_Master_TaskPack_v4_2026-08-09.md` | `33b81a111204000318238001a28bc5d7cc024d153e119c8463aa109be424a241` | `e52a520be4417628c153aaa0f4162d855dbfae48cb44ec0c08bf89e905d82fd4` | 冻结基线形成前的最终迁移决策源 |
| `ArcheAxis_Workspace_Context_Handoff_2026-08-10.md` | `027ac14b6d20850911a6bb707101725dd68bc90aabdc551e81dcdcae2f7a0d71` | `5999cf7f1674dd15264f1d471e3430318b4cd276cd66a779a8298ba057f0d213` | 新对话交接摘要；云端事实需重新核验 |

逐字节原件保存在 `ArcheAxis_Workspace_Planning_Sources_original_2026-08-09.zip`，ZIP SHA-256 为 `a2838ecc32ff1d0a0b502a4500596e3f8e26bbc48812b4ee525d78315edf6a5f`。原件条目校验见 [`ORIGINAL_SOURCE_MANIFEST.sha256`](ORIGINAL_SOURCE_MANIFEST.sha256)，规范化可读副本校验见 [`REPOSITORY_COPY_MANIFEST.sha256`](REPOSITORY_COPY_MANIFEST.sha256)，来源演变和当前执行关系见 [`PLANNING_SOURCE_LINEAGE_2026-08-10.md`](PLANNING_SOURCE_LINEAGE_2026-08-10.md)。

## 保存规则

- ZIP 内五份文件按用户提供内容逐字节保存；交接文件仅移除了桌面重复下载后缀 `(1)`，内容哈希未变。
- 仓库中的五份 Markdown 可读副本只移除行尾空格并统一最终 LF，以通过仓库文本约定；未修改文字、章节或任务内容。
- 不把旧文档中的分支、SHA、PR、CI、Release、测试数量或“已完成”声明当成当前事实。
- 不从这些历史文件直接启动任务；先映射到冻结基线或批准增补中的具体任务 ID。
- Codex 对话附件、会话正文和私有运行状态不进入仓库。
