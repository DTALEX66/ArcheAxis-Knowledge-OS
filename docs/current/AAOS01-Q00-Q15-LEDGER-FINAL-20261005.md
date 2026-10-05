# AAOS-01 Q00–Q15 当前执行台账（2026-10-05）

任务编号和完成条件以 `docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md` 为准。本文件维护既有 AAOS-01 切片当前状态；不可变任务包仍是执行规格，不是完成证据。历史回执保留原始候选、SHA 和能力范围，不自动提升为本轮或安装态验收。

本轮起始 HEAD：`37bfe872ccbaed88a4825b8ff939ccf94aef8b92`，开工工作树 clean。最终提交 SHA 和精确 SHA CI 结果须在提交、运行及读回之后登记；当前 **CI NOT_EXECUTED**，不得由旧 cancelled/skipped 运行推导通过。

## 当前状态与剩余缺口

| ID / 权威任务 | 当前状态 | 已有证据与实际剩余缺口 |
| --- | --- | --- |
| Q00 现场保护与最小对账 | PARTIAL | 已复核起始 SHA、工作树与工具路径；本轮使用独立候选及全新 Core 数据根。未知用户资产、旧库与历史回执保留；完整资产/schema/writer 身份不因本轮格式测试自动完成。 |
| Q01 重构决定与目录登记 | PARTIAL | 已有 SUP-022 重构登记；本轮统一使用权威 `stage_backend_runtime.py` 产出候选，desktop-fast/build 使用相同准备步骤。此项不是旧编号中的“打包完成”；Authority 与目录完整验收仍按任务书核对。 |
| Q02 Tauri 启动与只读桥接 | TESTED_LOCAL / PARTIAL | `aaos01-final-fmt-verified` 的 src-tauri fmt exit 0；`aaos01-final-worker-cargo` 的 cargo test 56 PASS（无忽略测试），包含真实 resolver/supervisor 验证。历史 Core 生命周期与读回仅按原回执采纳；独立安装态完整桥接与正式接管仍未验收。 |
| Q03 类型合同与权限 | PARTIAL | 既有启动契约、前缀隔离与权限测试保留；本轮未将单元测试提升为全部 DTO、对象权限与版本错误验收。生成合同、有限命令与对象范围需按任务书逐项读回。 |
| Q04 原件与文档保存 | NOT_RUN / UNVERIFIED | 历史候选能力调用不能证明本项完成。版本化 Document/Block、CAS 原件、草稿保存/恢复与同版本内容投影一致性仍待实现或验收；撤销旧 done 声明。 |
| Q05 阅读与证据样板 | UNVERIFIED | 真实 Tauri PDF.js/Tiptap 阅读、中文 IME、引用回跳、焦点与缩放验收缺口保留；不能以浏览器或后端测试代替真实桌面。 |
| Q06 A 波次多格式吸收 | TESTED_LOCAL / PARTIAL | 本轮 XLSX/PPTX 经真实 Core/worker/持久化/重启链路通过，损坏两格式按预期 failed；详细回执见下。代表性文本、DOCX、HTML、PDF、Canvas、ZIP、SRT 仅保留历史 Reported 结果，未宣称本轮重验。音频/视频仅 media.probe 元数据头探测，不计解码、ASR 或时间段内容闭环。OCR 与安装态逐格式资格仍待验收。 |
| Q07 候选审核与纠正 | NOT_RUN（真实用户审核） | 真实候选接受/拒绝/待补证、版本冲突与撤回仍待真人会话。actor="human" 字符串或工程自签不能满足真人审核。 |
| Q08 学习与 AI 资产闭环 | UNVERIFIED | 代表资料上的学习事件、复习计划、AI 使用/纠正候选、幂等计数与冷启动读回仍需完整旅程；历史或合成夹具不替代本项真实验收。 |
| Q09 搜索与完整能力目录 | UNVERIFIED | 真实检索、能力差集、已实现可调用与未来可浏览需在当前 Tauri 产品核验，不从代码存在推导完成。 |
| Q10 导出与首个互通 profile | UNVERIFIED | 限定 Markdown/Obsidian 交换、独立外部软件回读与可见损失尚无本轮闭合证据。 |
| Q11 备份与副本恢复 | UNVERIFIED | 一致快照、CAS 引用清单、独立副本恢复及继续阅读/学习尚需真实演练；重启读回不等于备份恢复。 |
| Q12 B 波次轻量扩展 | NOT_RUN | CSV/TSV、JSON/JSONL、YAML/TOML/XML、EPUB、EML 按各自样本验证结构、定位、损失与冷启动；EPUB 需章节/资产/段落，EML 需邮件头/正文/附件/来源。不得以“同 Q06”替代，未增加 verified_extension_count。 |
| Q13 性能与故障验证 | UNVERIFIED | 本轮损坏 Office 与 Windows 长路径回归已验证局部失败/恢复行为；全进程树、取消、崩溃、断网、恢复及事先定义预算尚未完整验收。 |
| Q14 Windows 安装态资格化 | NOT_RUN | 本地构建、候选完整、Rust/Python 测试和 CI 均不能替代独立安装包的真实桌面旅程；尚无 Installed Qualified。 |
| Q15 第一包收口与第二包交接 | PARTIAL | 本表统一当前状态，47 份现场枚举的旧 Q02 逐轮记录已加历史指向、正文证据保留。Q14、核心完整旅程和 Owner Accepted 未完成，不能宣布第一包收口或冻结旧入口。 |

## 本轮工程与样本证据

最终候选：工作树 `.project-local/rt`（Office 回执执行时为 `.project-local/a4`，随后迁入最终位置，旧 rt 保留）；解释器：最终候选 `runtime/python.exe`，Python 3.12.13。依赖沿既有 `uv.lock` 导出并安装到 staged Python，再由权威暂存器进入候选；未重复增加 openpyxl/python-pptx 声明。锁文件 SHA-256：`0F73EA804B0ECA61A251013D199F75D88F35E6322BB155EB2581B8D10F69CE52`。

引擎断言由产品候选解释器执行真实 import，输出模块路径与版本，检查模块来自 runtime 内部，并核对 profile 与宿主 nested/flat 选择规则；失败非零。四模块为 openpyxl、pptx、markitdown、pytesseract。引擎负向测试失败非零，原文件字节已恢复；这不是 OCR 样本资格。

最终 Office 回执：工作树 `.project-local/task-runtime/aaos01-office/93fd87f7648840e1940021ca99f1db95/receipt.json`，`ok: true`，证据级别 `REAL_CORE_WORKER_INTEGRATION_AUTHORED_FIXTURES`。这是项目自制样本在真实产品 Core/worker 中执行，不能称为私人真实资料或安装态验收。

- 有效 XLSX/PPTX：导入 → job → worker → Core 持久化 → 完全重启读回；已知工作表/单元格、页/文本、native 位置、canonical 锚点、损失与三类输出 SHA 校验通过。
- 损坏 XLSX/PPTX：均 failed，错误 `AAK-WORKER-003`；这是预期失败行为通过，不是格式内容提取成功。
- 四项作业重启后状态、质量与输出快照一致；默认 UUID32 长数据根已通过，此前长路径失败不再作为当前候选结果。

组合回归 `fda7d77ffa15`：89 PASS，覆盖暂存安全、两桌面门禁同准备、Desktop staging 与 Windows 真实 worker 长路径；变更 Python 文件 Ruff PASS。架构门禁与 source=worktree 仓库规范最终再次 PASS。以上为本地结果。src-tauri 的最终 fmt 与 56 项测试见上表 Q02。

## CI 与不可自签边界

固定提交后的 `workflow_dispatch(force_full)`：**NOT_EXECUTED，等待固定 SHA**。需登记完整 SHA、workflow、run ID、attempt、headSha 及目标步骤实际执行结果；等待期间不推送，重跑使用 run ID。旧 `37262959180` 的 desktop-fast failure、desktop-build cancelled，其他 skipped/cancelled 运行仍按原始结论保留，不能计 PASS。

旧 98 表 Python 库与 Core `workspace_meta.schema_version` 不兼容。迁移与只读接入的数据语义仍须明确；保留原库与独立新数据根，不以泛化修复授权推断具体内容舍弃或映射。普通暂存布局与实现合并已授权自主处理，不再列为待用户决定。

历史纠偏出处保留在 `AAOS01-AUDIT-CORRECTIONS-20261005.md`、交接文件与 Git 历史；不在本表保留互相矛盾的 done/撤回当前状态。回退使用本次提交前代码与已保留旧候选/旧数据副本，不让旧程序打开新 schema；本轮未发布、未安装资格化、未声称 Owner Accepted。
