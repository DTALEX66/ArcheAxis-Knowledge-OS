# ArcheAxis Historical Planning Sources (2026-07-14 to 2026-08-08)

> **状态：历史来源归档，不是当前实现、运行时依赖、自动执行授权或完成证明。**

本目录收敛项目本地 `.hermes` 边界内遗留、但此前未进入 Git 的蓝图、规划、任务包、验收材料和机器可读清单。当前执行权威仍由 `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`、批准增补包和 `docs/truth/EXECUTION_STATUS_LOG.md` 共同定义。

## 归档范围

| 路径 | 内容 | 数量 |
| --- | --- | ---: |
| `source-documents/` | 用户交付的审计/蓝图/测试 DOCX，以及去重后的 2026-08-06 至 2026-08-08 任务包与兼容性审计 | 7 |
| `plans/` | 2026-07-14 至 2026-08-09 的 Hermes 项目计划与交接规划 | 7 |
| `pack-extracts/desktop-cloud-reaudit-v1.0/` | Desktop/Cloud 复审包中的审计、前端融合规划、A1/A2/A3 任务包、发布计划、验收/回滚与 manifests | 20 |
| `pack-extracts/today-archive-v1.0/` | 2026-07-28 归档包中的项目定位、系统蓝图、执行路线、任务包和 manifests；不含对话时间线与 prompts | 21 |
| `pack-extracts/apple-desktop-ui-v1.0/` | 嵌套 UI TaskPack 中的产品/UI 规范、技术计划、页面说明和任务 manifests；不含 prompts、原型与截图 | 29 |
| `pack-extracts/open-source-absorption-2026-07-25/` | 开源能力吸收包的完整项目资料，包括路线、任务包、验收、许可证、注册表和能力矩阵 | 15 |

去重后共有 99 个项目文件。目录另含 3 份完整性清单。

## 去重与隐私边界

- 3 份 `ArcheAxis_Desktop_Cloud_Reaudit_Modification_Pack_v1.0*.zip` 内容完全相同，SHA-256 均为 `6c60bde6405a0d54e0516525ceecbaf3fb3f186cc548475fd15804f460433e76`。
- 2 份 `ArcheAxis_Today_Conversation_Archive_HERMES_TaskPack_2026-07-28_v1.0*.zip` 内容完全相同，SHA-256 均为 `65bd1b3359d4d2e7ba5ef9c43cd4f3156fdf4119cf5d357ebcd255991f9100f3`。
- 3 份 CI Acceleration TaskPack 内容完全相同，SHA-256 均为 `ea2966d6153b2759bdcf4b80f95b764556f2b06df77e8bca86ea75c1a5d86bdb`；仓库只保留无数字后缀的规范文件名。
- 含 prompts、对话时间线、截图、HTML 原型或执行脚本的原压缩包没有整体提交。只抽取蓝图、规划、任务包、验收材料和 manifests，避免把提示词/对话正文及大体积重复缓存带入 Git。
- 文本仓库副本统一为 LF、移除行尾空白，并将两个机器绝对路径替换为 `<repository-root>` / `<external-project-root>`；DOCX/XLSX 保持原始字节。

## 完整性文件

- `ORIGINAL_SOURCE_MANIFEST.sha256`：22 个本地物理源文件的原始 SHA-256；包括未整体提交的压缩包及其重复别名。
- `SELECTED_ARCHIVE_ENTRY_MANIFEST.sha256`：85 个被抽取压缩包条目的原始字节 SHA-256。
- `REPOSITORY_COPY_MANIFEST.sha256`：99 个去重、筛选和规范化后仓库副本的 SHA-256。

以上清单只证明来源和仓库副本完整性，不证明任务已实现、CI 已通过、主分支已合并或安装态可用。
