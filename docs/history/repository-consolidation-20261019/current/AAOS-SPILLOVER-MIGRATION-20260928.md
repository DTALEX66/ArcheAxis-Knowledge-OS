> Historical snapshot: 2026-09-27 至 2026-09-29 的过程记录，非当前状态或执行权威。
> 当前清理、交付、验证与阻塞请读 [2026-10-01 交接](STORAGE-CLEANUP-HANDOFF-20261001.md)。

## 现行解释（2026-10-01）

- B10 最终可部署母版是最高视觉依据；Aurora/黑白共用布局、状态及缩放规则。正文中此前 B03 最高或 B10 仅作风格参考的判断已被取代。
- r97/r38/r30、旧截图数、PID、HEAD、测试/构建及上传结果仅证明对应历史快照；不能推断今天界面、完整原生交互/DPI/动画或安装态已经验收。
- “49 项失败全为旧标题”是当时判断，后续发现并修复真实交互行为问题，不能沿用为全部豁免理由。
- 旧76项保留/未授权、原位展开仍在、未上传及换连接器建议都是早期阶段记录，今天以最新交接和删除回读为准；不再要求沿用旧认证建议。
- SHM PARTIAL、wheel UNVERIFIED、未知归属与历史拒绝如实保留；当前整体仍 PARTIAL，静态/编译通过不等于用户数据库或完整产品健康。

原快照源 SHA-256：`83ad5384e7a03b192affd3931e48423a2ea37e7a048511b5b3b8823c9570250e`。以下保留历史正文，只统一文本格式，不将旧叙述重新认定为当前真值。

---

# AAOS 外溢目录迁移与清理回执（2026-09-28）

## 结果

上轮回执记录为已清理；本轮只确认三处源目录均不存在，无法独立追溯实际清理动作。保留数据和可恢复材料集中在正式仓库的 `.project-local/mig/`，不复制到 Green 可执行版目录或远端，以免重复占用空间。所有报告尺寸均是逻辑文件大小，未声称对应物理磁盘块回收量。

| 原始目录 | `.project-local/mig` 归档 | 结果与验证 | 源目录 |
|---|---|---|---|
| `D:\All projects\AAOS candidate run` | `candidate-run-20260928/` | 4 组 SQLite 主库/WAL/SHM/锁文件原样保存在 `sources/`；4 份 WAL 恢复结果 SHA-256 相同，合成去重后 canonical DB SHA-256 `bed7bdc510a3f84af8c43bcc17e7ecf626e5d0a854b163b8bfa3c7422e92f80e`，SQLite `integrity_check=ok`。合并库只有 1 行 workspace metadata，无业务内容。 | 不存在（本轮检查） |
| `D:\All projects\AAOS-DSH-BACKEND-RUNTIME` | `dsh-backend-runtime-20260928/` | 7 个 runtime 包、19,979 个文件条目经 SHA-256 校验后重建到内容寻址存储；3,112 个唯一对象、71,879,804 B，相比来源 437,264,634 B 的逻辑展开文件。`archive-manifest.json` 记录包路径与哈希；`README.txt` 和 `restore_runtime_archive.py` 说明恢复。未执行其中 runtime。 | 不存在（本轮检查） |
| `D:\All projects\AAOS-DSH-WHEEL-QUAL` | `dsh-wheel-qual-20260928/` | 保留完整 ZIP `AAOS-DSH-WHEEL-QUAL-ee015075.zip`，1,608 文件；ZIP SHA-256 `031304de1477297e5bdd182258de438fb46892bb867488a046889d3b1370e597`。逐项路径集合、长度、SHA-256 与 ZIP CRC 校验通过；归档约 7.76 MB，来源逻辑文件约 22.61 MB。此项只证明打包完整，wheel qualification 本身 `UNVERIFIED`。 | 不存在（本轮检查） |

## 恢复路径

- Candidate run：以 `candidate-run-20260928/merge-manifest.json`、`migration-manifest.json`、`recovery-report.json` 和 `sources/` 恢复/复查原始输入；合并数据库位于 `merged/synthetic-workspace.sqlite`。
- DSH runtime：按 `dsh-backend-runtime-20260928/README.txt` 指定方式运行归档内 `restore_runtime_archive.py`，并提供一个新的绝对目标路径。
- DSH wheel qualification：完整归档为 `dsh-wheel-qual-20260928/AAOS-DSH-WHEEL-QUAL-ee015075.zip`；manifest 位于同目录。

## 边界

- 这些归档属于正式仓库 `.project-local`，是本机数据，不是 Git 版本内容。Green 主线保留本回执副本，不再复制这些归档负载。
- 外部三个源目录是否曾含未被迁移清单扫描到的被拒绝/访问受限条目，以归档清单和 recovery report 的 errors/exclusions 字段为准；不得把该类状态推断成空数据。
- 未提交、推送或发布这批本地数据；没有据此宣称两个 Git 仓库已合并。

## 2026-09-30 跨项目归属复核与交接

用户授权将可确认为其他项目所有的数据迁至对应归属地，并要求附迁移文档/交接。本节只记录本轮实际核实的对象；E:、F: 未访问。

### 结果摘要

- Formal `docs/history/` 中曾由旧扫描列为混合/外溢的少量交接、看板、task-runtime 文件，当前权威处置表 `docs/current/AAOS-HISTORY-PATH-DISPOSITION-20260926.json` 仍将相应对象标为 `owner=UNRESOLVED`、`data_class=LEGACY_MIXED_PRESERVE`、`target_path=RETAIN`、`move_status=BLOCKED_UNRESOLVED_OWNERSHIP`、`deletion_authorization=NOT_REQUESTED`。本轮只读重新核对了文件名/内容归属线索、SHA-256 与部分精确消费者；没有推翻 owner 未确认状态。
- 9 个 `docs/history/worktree-preserved-diffs/hermes__task-runtime__*.patch` 的 patch header 指向本仓 `tests/`、`src-tauri/`、`desktop/src-tauri/` 等路径，不能据文件名前缀认定属于 WORK-LAB。与 WORK-LAB 指定归档子树中 539 个小于等于 5 MiB 文件比对，未找到同 SHA 副本。暂保留在原路径；禁止直接迁往 WORK-LAB。
- `docs/history/task-runtime-scattered/worker-quality-0906-unique-20260918.md` 明确关联本仓 `.project-local/worktrees/worker-quality-0906`，并被 `docs/current/DSH-COMPLETION-REPORT-20260918.md`、`docs/current/R5-LOCAL-BRANCH-DISPOSITION-20260918.md`、`docs/current/HERMES-FULL-AUDIT-PROMPT-20260918.md` 引用；属于 AAOS 历史恢复/交接材料，保留。
- `Cognitive-Loop-OS` 标题材料（`task-runtime-scattered/ms00-b-handoff.md`、`project-pipelines-inventory.md`）及 `kanban/boards/cognitive-loop-os/board.json` 暗示旧项目身份，但旧归属目录/当前 Authority 未找到，且现行 AAOS 路径处置表仍标 owner 未解决。不得仅凭旧项目名迁往 WORK-LAB、DSH 或删除；等待确认归属仓后按 SHA 做保留式迁移并更新双方恢复映射。
- Formal 下 DSH 三个既有归档仍属于 AAOS 接管/追溯材料：`candidate-run-20260928/`（含 SQLite/WAL/SHM，仅保留未读库体）、`dsh-backend-runtime-20260928/`、`dsh-wheel-qual-20260928/`。其原始外溢目录当前均不存在。D: 顶层 `DSH` 是独立桌面分发/用户状态目录，不是已验证的 DSH 源码仓；不得迁入 ArcheAxis。
- Formal 中 2026-09-29 三份规划材料已有本仓副本，`planning-blueprint-absorption/2026-09-29/ARCHIVE_MANIFEST.json` 记录 3 个源文件与归档文件逐字节一致；D:\All projects\Record 中的原件保留为外部恢复副本。Record 中 DESIGN-LAB、WORK-LAB、混合 Other 档案没有足够依据确定是否已有各自权威归档，故不移动、不删除。
- Green 根大体积审计没有证明可安全删除的纯生成对象：注册 linked worktree 各有独有 dirty/untracked 内容；`backups` 存在不同哈希可恢复版本及用户/数据库状态；`runtime/python` 被候选/验收链引用；`AAOS-Frontend-Acceptance-v4` 被 UI 验收报告引用。以上保留。

### 给归属负责人/后续接手者

1. 先为 `Cognitive-Loop-OS` 旧身份确认当前正式项目归属与目标归档路径；若它是 ArcheAxis 的历史别名，保留在本仓 `docs/history/` 并补一个从当前权威入口可达的索引即可。
2. 若明确迁往另一个仓库，先在目标仓按其 Authority 接收逐字节副本，回读源/目标 SHA-256 与文件数；保留源端可恢复归档，完成当前消费者和 basename 引用复核，再更新两端所有权/恢复记录。不得改写旧处置表的历史结论，应新增带日期的处置记录。
3. WORK-LAB、DSH、DESIGN-LAB、Record 及共享工具链是不同归属面。涉及其他仓库写入时，按各自 Authority 建独立任务与分支；本轮没有在其他仓库写入、改分支、提交或推送。

### 本轮状态

| 项目 | 状态 | 说明 |
|---|---|---|
| 原 DSH 三个外溢源路径 | `NOT_FOUND` | Formal `.project-local/mig/` 中的保留归档继续可读；本轮无源数据可迁 |
| Formal 跨项目历史候选 | `RETAIN / OWNER_UNRESOLVED` | 归属未确认，工作树脏；无移动或删除 |
| WORK-LAB 同哈希替代物 | `NONE_FOUND` | 指定归档扫描范围内未发现补丁字节副本 |
| Record 中非 AAOS 内容 | `UNKNOWN / RETAIN` | 当前无法证明归档重复及准确 owner |
| Green 大体积候选 | `KEEP` | 未证明可以安全清理 |
| 本轮文件迁移/删除/建分支 | `NOT_EXECUTED` | 只读归属审计与交接补充，不覆盖其他项目未提交状态 |

## 2026-09-30 Green 旧 UI 归档源路径复核更正

对旧记录中“76 个 Green acceptance 目录仍保留”的历史状态重新回读后，更正为：

- Formal 本机清单 `.project-local/mig/green-ui-history-20260929/AAOS-UI-HISTORY-76DIRS-20260929.manifest.json` 列出 76 个历史目录、14,713 文件、14,366,893,032 B。按清单对 Green mainline acceptance 根逐路径检查，76/76 个源目录均不存在；该根下另有 10 个不同名称的新候选/验收目录，均不在这份旧清单中，本轮保留。
- 恢复 ZIP 当前位于 `D:\All projects\Record\AAOS-project-archives\2026-09-29\AAOS-UI-HISTORY-76DIRS-20260929.zip`，大小 5,434,623,954 B，SHA-256 `183929BF629BCBD5473C0F41210EC37125F86FB7CAE0BFADA38843AE100151A4`；与历史迁移报告和 manifest 记录值一致。Formal `.project-local/mig` 和 Green mainline `.project-local/mig` 均无该 ZIP 的副本。
- 因而旧 76-dir 批次已按此前归档回执完成源目录移除，历史计算的逻辑净差为 8,932,269,078 B；不把该值冒充当前 D 盘自由空间增量。较早文本中“仍保留/等待精确清理确认”是早期快照，不是本次回读结论。
- 本次未再次移动或删除文件。10 个现存 acceptance 子目录尚未完成独立逐项审计，不将其归入这 76 项，也不据此声称 Green 目录已无可清理内容。

## 2026-09-29 只读体积与残留盘点

以下为逻辑文件长度，不等同于 NTFS 实际已分配空间或物理回收量。扫描没有删除或移动任何文件。

| 范围 | 当前读数 | 说明 |
|---|---:|---|
| Formal 仓可读取部分 | 136,312,816,211 B / 1,213,855 files | 排除 `.hermes`、`data`；遍历有 1,298 项错误，因此不是完整 root 总量。 |
| Formal `.project-local/build` | 74,193,283,322 B / 465,285 files | 最大单项开发输出；候选包和发布记录有路径引用，不能按相似体积清理。 |
| Formal `.project-local/staging` | 23,628,814,069 B / 378,683 files | 候选 staging；当前没有已证明可删的精确目录。 |
| Formal `.project-local/runs` | 19,838,881,115 B / 249,692 files | 运行记录；消费者尚未逐路径确认。 |
| Formal `.project-local/worktrees` | 9,900,674,727 B / 40,495 files | 7 个 Git 注册 worktree；不得作为普通缓存删除。 |
| Formal `.project-local/cache` | 3,635,009,137 B / 47,719 files | 构建缓存；部分缓存被 CI/项目脚本引用。 |
| Green root | 47,306,113,786 B / 149,133 files | 只读逻辑大小扫描；包括树内开发资料，不能等同于可分发绿色版体积。 |
| Green `.ui-task-tree` | 44,304,578,956 B / 81,972 files | 内有两个活动/注册任务 worktree：约 16.13 GB 与 28.17 GB。 |
| Green root（task tree 以外） | 约 3,001,534,830 B | 包含约 1.35 GB backups、约 0.90 GB acceptance；正在运行的验收 v4 约 245,747,591 B，应保留。 |

三个已授权外溢源目录当前均不存在；恢复材料分别在 `candidate-run-20260928/`（36 files / 1,821,597 B）、`dsh-backend-runtime-20260928/`（3,117 files / 76,831,790 B）和 `dsh-wheel-qual-20260928/`（4 files / 8,188,484 B）。formal `.project-local/mig/` 共 3,157 files / 86,841,871 B；Green mainline 仅留本回执，没有再复制这些负载。

残留复核：formal 的五个 `legacy-copy` 归档树 SHA 全部不同；跨树存在 14 组同 SHA 文件，额外副本的理论总量 38,743,565 B，但每个原始树包含不同 WAL/SHM/receipt，且最后两个 receipt 对 `every_planned_table_accounted_for` 没有完整 PASS（一个为 false），全部保留。Green `green-preview-duplicate-cleanup-20260928/predelete-verification.json` 记录十个旧 build 副本合计 2,218,209,306 B；本次 readback 发现十个 source 目录均已不存在、同名 acceptance 目录仍在。历史 pre-delete receipt 不足以判断这些路径由哪个回合移除，本次不重复清理。

目前 `exact cleanup candidates = NONE_PROVEN`。后续候选必须逐路径证实文件 SHA/恢复副本、文档或脚本消费者、Git worktree 注册及活动进程引用；不得从文件名相似、体积相近或旧 pre-delete 回执推断可删。此状态表示保留并继续追踪，不表示空间清理已全部完成。

## 2026-09-29 重新读取仓库体积

用户追问后由两次只读递归扫描交叉复核；报告逻辑文件长度，不等于资源管理器显示的 NTFS 实际占用。Formal 仓存在拒绝访问目录，数值是已读到的下界。Green 根包含 `.ui-task-tree`，不可把子树再加一次。

| 范围 | 最新读数 | 解释 |
|---|---:|---|
| Formal 仓可读取文件 | 137,454,607,622 B / 1,268,088 files / 128.015 GiB | 有拒绝访问项；不是完整总量。 |
| Green 产品根 | 47,322,257,352 B / 149,666 files / 44.072 GiB | 包含开发树、备份、验收与运行时数据；不等于可分发包。 |
| Green `.ui-task-tree` | 44,320,722,522 B / 82,505 files / 41.274 GiB | 已含在 Green 根；其注册任务树需保留。 |
| Green `runtime` | 654,538,073 B / 21,162 files / 0.610 GiB | 只是运行时子目录，不能代表完整产品。 |
| Green `output` | 0 B / 0 files | 当前空目录。 |

可分发绿色版安装目录/Release payload 的独立体积本次没有核定（`NOT_EXECUTED/UNKNOWN`）。三处已授权外溢源的当前回读仍均不存在；迁移留档合计 86,841,871 B / 3,157 files。本次没有删除或移动外溢数据，残留清理候选仍为 `NONE_PROVEN`。

## 2026-09-29 审计更正：迁移清单与体积

本节更正上文旧回执中的两处遗漏；原始清单保持不变以保留当时记录。

- 当前 `.project-local/mig/` 实测为 **3,275 files / 135,499,757 B**。此前写的 3,157 files / 86,841,871 B 只统计 2026-09-28 三个归档目录，漏掉了已存在的五个 hash 命名 SQLite 快照目录（342f16e3、345df936、3c605b9b、85832da5、f985e566）。
- `candidate-run-20260928/migration-manifest.json` 的 16 项中，12 项与当前归档 SHA-256 一致，4 个 `sources/*/workspace.sqlite-shm` 不一致。大小都仍为 32,768 B；每组源目录当前值：
  - `data`: manifest `870851AB8494134C9F5BDC3F90A167CAEB580E8A2E6439BD4C274DFCA11D0DBD`; actual `24D92322693206AD04655F08620060E00DE582BC8EEB25B40C3228364390FDB8`。
  - `data2`: manifest `86E4D7BB3DDECAC6F7D745496251E22449C8D172AC3AE74139266BFFF1A8EF8C`; actual `9E9A57B465390C6C9D44AF03EB8D25771F7F1ECF78F7DEEC38985226FAEBB926`。
  - `data3`: manifest `482A275201458A876F69EE088D35F1B4688E14022DE6B2BE96FA17E8898F01AA`; actual `9A8CB471560D71AED3D0795C71313857E26AAA2733B0799B6A744DDA2CF0968B`。
  - `final`: manifest `0299D281B6ED28C81AE921AAC2A027ABCCE5343C3B09A09BF2D3876E810183FA`; actual `B284B5940EFE232F23FD05A72191F0E582AC8C2DC6AB871665FEE113E93843C2`。
- 三个原始源目录当前均 `NOT FOUND`，因此无法判断 SHM 差异发生在归档前、归档后或清单生成时。保留所有 SHM 和其他候选输入；源文件级归档校验记为 `PARTIAL / 4 SHM HASH MISMATCHES`。合并 synthetic DB 的 SQLite integrity check 为 `ok`，只证明该合并数据库可读，不覆盖原始 sidecar 的 SHA 差异。
- 并行复核确认 DSH runtime 的 3,112/3,112 个内容寻址对象 SHA-256 均匹配；wheel ZIP SHA-256 匹配，展开的 1,608/1,608 条路径、尺寸与 SHA-256 均匹配。未执行 runtime 或 wheel qualification 本身，资格结论仍为 `UNVERIFIED`。
- 以上均为逻辑文件长度；本次没有删除或移动文件，安全可确认的释放空间仍为 `0 B`。
## 2026-09-29 Green 根启动与体积复核

Green 根只读快照（逻辑文件长度；不是 NTFS 实际占用）：`D:\All projects\ArcheAxis.Knowledge.Green-x64` 为 **47,333,424,179 B / 149,743 files / 44.083 GiB**；其中 `.ui-task-tree` 为 **44,331,889,349 B / 82,582 files / 41.287 GiB**，已包含在根总量中。已登记 worktree `ArcheAxis-Knowledge-OS` 为 16,133,481,904 B / 45,493 files；dirty UI 主线 `ArcheAxis-Knowledge-OS-mainline` 为 27,726,131,611 B / 36,826 files，分支 `codex/aaos-ui-mainline-20260927`、HEAD `d8f99a6357405054f1f9ee66eb2f88d36f7f5143`。主线含大量未提交改动，禁止当作临时目录清理。

Green 根当前 `release-identity.json` 与 `ArcheAxis.exe` 均为 stable **v0.6.14**；根启动脚本指向根 `ArcheAxis.exe`。正在运行的 PID 21556 窗口来自 `AAOS-Frontend-Acceptance-v4\ArcheAxis.Desktop.exe`（该验收目录约 245,747,591 B），不是根发行版。因此 UI 主线尚未集成进 Green 根启动链。此处为文件/进程路径 readback，不代表根发行版启动或 UI 集成已验证。

目录快照：`backups` 1,351,203,798 B；`runtime` 654,538,073 B；`data` 41,080,145 B；`AAOS-Frontend-Acceptance-v1..v4` 分别为 217,597,126 / 217,626,107 / 219,603,930 / 245,747,591 B。正式发布目录/Release payload 的独立规范体积尚未单独核定；不要将完整 Green 根大小当作绿色版安装包大小。

## 2026-09-29 04:26 上海时间：双仓体积与清理状态更新

Formal B10 主 rail parity Release build 后的只读扫描为 **136,732,865,220 B / 127.342 GiB / 1,248,667 readable files**；Formal `.project-local` 为 **133,218,870,489 B / 124.070 GiB / 1,213,048 readable files**。排除 `.git`、`.agents`、`.codex`、`.hermes`；1,220 个 `.project-local` 内路径及 `p-w7n3ehdf` 拒绝访问，合计 1,221 个错误，所以这是逻辑大小下限。Formal build 74,444,624,277 B；staging 23,628,814,069 B；runs 19,846,935,363 B；worktrees 9,900,674,727 B；cache 3,635,009,137 B。相比 03:58 快照，主仓可读内容增加约 259,393,020 B，主要是刚生成 Release 构建与运行回执。

Green B10 rail Release build 后最新完整根目录为 **53,646,882,150 B / 49.963 GiB**，其中 `.ui-task-tree` **50,645,347,320 B / 47.167 GiB**；根扣除该树后为 **3,001,534,830 B / 2.795 GiB**。当前没有独立正式 publish/release 包可单独量体积。Formal 三份指定外溢迁移负载为 **3,157 files / 86,841,871 B**；`.project-local/mig` 总计 **3,275 files / 135,499,757 B**。三个源目录均不存在。

所有大小均为逻辑文件长度而非 NTFS 分配/物理回收量。Formal 已证明可安全回收量仍为 **0 B**。Green 历史 UI 候选 ZIP 已逐文件验证，原 76 个源目录仍保留；其 exact removal review list 与 manifest 76/76 一致。清单有 24 个目录被限定范围的历史文档引用，52 个未命中；未命中不是删除证明。此前进程扫描发现 UI 进程运行于 Green v4，无法排除所有其他消费者。没有删除、提交或推送。

## 2026-09-29 当前回合体积、外溢与精确清理复核

本节为当前快照；所有数值是逻辑文件长度，不是 NTFS 分配空间或实际可回收空间。

| 范围 | 文件数 | 逻辑字节 | GiB | 状态 |
|---|---:|---:|---:|---|
| Formal 仓根（只读递归所得） | 1,268,413 | 137,714,394,292 | 128.260 | 含 `.project-local`；部分子目录 ACL 拒绝，读数不是保证完整的上界。 |
| Green 产品根 | 约149,743 | 约53,646,886,307 | 约49.963 | 含内嵌 `.ui-task-tree`，不可重复相加。 |
| Green `.ui-task-tree` | 约82,582 | 约50,645,351,477 | 约47.167 | 两个注册/活动任务 worktree；保留。 |
| Green mainline `.project-local` | 约46,233 | 32,571,651,046 | 30.335 | acceptance、build、archives、cache、tmp；不得整体清理。 |
| Green 根扣除 `.ui-task-tree` | — | 约3,001,534,830 | 约2.795 | 含 backups/runtime/验收包；末次进程读回确认 v4 应用 PID 21556 仍在运行。 |

### 三处已指定外溢数据

`D:\All projects\AAOS candidate run`、`D:\All projects\AAOS-DSH-BACKEND-RUNTIME`、`D:\All projects\AAOS-DSH-WHEEL-QUAL` 当前均不存在；迁移档案位于 Formal `.project-local/mig/`。三个迁移目录共 3,157 files / 86,841,871 B；整个 `mig/` 含先前五个快照为 3,275 files / 135,499,757 B。DSH runtime CAS 为 3,112/3,112 对象 SHA 匹配，wheel ZIP 的完整清单哈希匹配且 qualification 仍 `UNVERIFIED`。candidate-run 的四个 32 KiB `workspace.sqlite-shm` 与迁移 manifest 哈希不符，源目录已不存在；所有输入均保留，源文件级完整性是 `PARTIAL`。没有新发现这些外溢数据的第二份可安全删除副本。

### 当前可证明的清理空间

- Formal：`NONE_PROVEN`，0 B 可安全回收。build 74,444,624,277 B、staging 23,628,814,069 B、runs 19,846,935,363 B、注册 worktrees 9,900,674,727 B、cache 3,635,009,137 B 都有恢复/消费者/注册工作树边界；项目脚本明文禁止移动/删除历史 cache。
- Green：只存在一组可供 Owner 审批的精确候选：74 个已被 ZIP 逐文件归档的非空旧 UI 候选目录，加 2 个空目录，总源逻辑大小 14,366,893,032 B / 14,713 files；归档 ZIP 5,434,623,954 B，manifest 3,872,070 B，若批准移除原件，逻辑净差约 8,928,397,008 B（ZIP+manifest 均保留）。原目录当前仍完整保留。
- 精确列表：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\.project-local\archives\AAOS-UI-HISTORY-76DIRS-20260929-removal-review.txt`；归档与恢复说明：同目录 `README-AAOS-UI-HISTORY-20260929.txt`。该集合排除当前 `AAOS-UI-CANDIDATE-20260928-r97` 与 `AAOS-UI-VERIFY-20260929`。74 个非空目录在来源路径、文件数及逻辑字节上与清单逐项相符；另列 2 个空目录。限定的文档/脚本/测试消费者扫描命中 24 个目录名、52 个未命中；未命中不证明无消费者，文档中的历史路径也不会被归档本身改写。
- 在收到对上述确切清单路径集合的明确批准前，不删这 76 个目录。不会据此清除 build/cache/tmp、Green backups/runtime、用户数据、root 启动程序、最新候选或任务 worktree。

### 集成与体积定义

Green 完整根目录约 49.96 GiB 主要因内嵌 47.17 GiB UI 任务树，不能称为用户绿色版包体积；Green 根 `output/` 为空，正式独立 Release payload 体积 `UNKNOWN`。根启动器仍指向 stable v0.6.14；UI mainline 未集成到该启动链。当前运行 PID 21556 来自 `AAOS-Frontend-Acceptance-v4`。R6 要求新 Green 候选先通过构建、首次使用、重启读回、备份替换/回滚及 owner gate；Release 冻结不变。本轮没有替换根程序、访问 Green `data/`、删除、提交或推送。



## 2026-09-29 final-source UI candidate volume increment

A fresh read-only scan after the final-source publish and screenshot matrix measured Green mainline `.project-local` at **32,818,581,001 B / 46,814 files / 30.565 GiB**. The isolated Release publish contains 225 files / **226,237,466 B**. The final-source capture directory contains 65 files (64 PNG + manifest) / **8,579,906 B**; its previous pre-hero diagnostic matrix remains separately present (65 files / 8,391,676 B). Both matrices are project-local acceptance evidence and are not counted as safe cleanup without exact review. These outputs increased mainline disk use for reproducible visual verification; they are not installed Green payload. Full Green root size was last read at about 49.96 GiB before this increase; do not add tasktree to root total twice. Root user data was not re-scanned in this pass.

## 2026-09-29 post-v2 Green task-tree readback

After the current publish, final-source matrix and source edits, Green mainline `.project-local` measured **32,818,658,581 B / 46,815 files / 30.565 GiB**. The current self-contained publish is 226,237,466 B / 225 files. The final-source capture matrix is 8,656,272 B / 65 files; the first pre-hero diagnostic matrix is 8,391,676 B / 65 files and is retained as superseded evidence. Do not treat this development output as the installed Green payload. The full Green root's latest direct scan remains the earlier 49.963 GiB snapshot; its `data/` subtree was not revisited. No UI tasktree, backup, runtime, user data, or historical archive directory was removed.

## 2026-09-29 refreshed readback after contact sheets

The final-source capture directory now contains **69 files / 11,062,127 B** (64 route/theme/size screenshots, manifest and four contact sheets). The manifest reports **64/64 PASS, 0 failed**; all 64 capture hashes plus four contact-sheet hashes and dimensions were re-read successfully (0 mismatches). Green mainline `.project-local` now measures **32,821,581,656 B / 46,844 files / 30.567 GiB**. This supersedes earlier counts for the same paths; the full Green root is still only known from the preceding ~49.963 GiB scan, with `data/` not re-scanned. The final UI captures and build output remain task-tree evidence, not installed root payload. No cleanup or root replacement was performed.

## 2026-09-29 Green root refreshed size (user data excluded)

A fresh recursive size read excluding the contents of root `data/` measured all other Green root entries at **53,855,759,558 B / 164,048 files / 50.157 GiB**. `.ui-task-tree` accounts for **50,895,304,873 B / 97,234 files / 47.400 GiB** and is included in that root subtotal, not additive. `data/` contents were not enumerated or measured; therefore no complete current total including user data is claimed. Top-level other large owners: `backups` 1,351,203,798 B, `runtime` 654,538,073 B, and acceptance v4 245,747,591 B (v4 process remains live). Root `backups` retained; no deletion performed.

## 2026-09-29 双端外溢归档负载同步回执

依照用户此前“迁到仓库 `.project-local`”及“双端仓库也要一致”的要求，将 Formal `.project-local/mig/` 中三项指定迁移目录复制到 Green UI mainline worktree 的 `.project-local/mig/`。只新增了三个不存在的子目录，没有覆盖 Green 已有的 `green-preview-duplicate-cleanup-20260928/`。

- 目标路径：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\.project-local\mig\`
- `candidate-run-20260928`: 36 files / 1,821,597 B；逐文件相对路径、长度、SHA-256 一致。
- `dsh-backend-runtime-20260928`: 3,117 files / 76,831,790 B；逐文件相对路径、长度、SHA-256 一致。
- `dsh-wheel-qual-20260928`: 4 files / 8,188,484 B；逐文件相对路径、长度、SHA-256 一致。
- 三项合计 3,157 files / 86,841,871 B。两个仓库保留相同归档负载；本地 `.project-local` 数据未提交或推送。
- Candidate run 仍为 `PARTIAL`: 四个 32,768 B `workspace.sqlite-shm` 与 migration manifest 哈希不符，源目录已不存在，无法重建来源级证据。同步只复制现存归档，不将此差异升级为 PASS。
- DSH runtime 包清单验证记录为 PASS，但本次不执行归档中的 runtime；wheel 包归档完整性 PASS，wheel qualification 仍 `UNVERIFIED`。

本次未删除或移动任何原始/归档文件。三处原始源路径在本次复核时均不存在；其移除时间和动作无法从当前证据追溯。
## 2026-09-29 实时并行复核：双仓体积与外溢状态

本节为本轮复核新增快照，字节均为逻辑文件长度，不代表 NTFS 物理占用或可回收量。

| 范围 | 文件数 | 字节 | GiB | 说明 |
|---|---:|---:|---:|---|
| Formal 仓可读扫描 | 1,268,433 | 137,714,558,583 | 128.260 | ACL/IO 部分路径拒绝访问，视为可读下限，不是完整仓库总量。 |
| Green 根（排除 `data/` 内容） | 167,854 | 54,423,366,156 | 50.690 | 包含 `.ui-task-tree`；绿色版独立发行包大小仍 UNKNOWN。 |
| Green `.ui-task-tree` | 101,040 | 51,462,911,471 | 47.934 | 已含在 Green 根总量，不得重复相加。 |
| Green 根扣除 task tree | — | 2,960,454,685 | 2.756 | 由上两项相减。 |
| Green `backups` | 44,256 | 1,351,203,798 | 1.259 | 保留。 |
| Green `runtime` | 21,162 | 654,538,073 | 0.610 | 不是完整绿色版包。 |
| Green acceptance v4 | 366 | 245,747,591 | 0.229 | 验收实例保留；PID 21556 不终止。 |
| Green `output/` | 0 | 0 | 0 | 当前空目录。 |

当前 Green `.ui-task-tree` 相较上一记录增加约 567,606,598 B / 3,806 files，主要是本地任务构建与验收输出的累积；本轮没有将这些输出视为可删缓存。Green `data/` 内容不在本次扫描范围；Formal 数值仍受 ACL 限制。以上根目录大小不是可分发发行版大小。

### 外溢数据复核

- 三条指定源路径 `D:\All projects\AAOS candidate run`、`D:\All projects\AAOS-DSH-BACKEND-RUNTIME`、`D:\All projects\AAOS-DSH-WHEEL-QUAL` 当前均不存在；没有证据追溯其消失动作，不将其归因于本轮删除。
- Formal 和 Green mainline 的 `.project-local/mig/` 中三项指定迁移目录逐文件 SHA-256 一致：candidate-run 36 files / 1,821,597 B；DSH runtime 3,117 / 76,831,790 B；wheel qual 4 / 8,188,484 B；合计 3,157 files / 86,841,871 B。两份回执 SHA-256 相同：`5EEF4FFA42797EC1BBA6F542482ABFD693D3C1D76DD37BBA4086948137AA1B8A`。
- candidate-run 仍是 `PARTIAL`：四个 32,768 B `workspace.sqlite-shm` 与 manifest 哈希不符，源目录缺失后无法恢复来源级验证。DSH runtime CAS 3,112/3,112 哈希匹配；wheel qualification 仍 `UNVERIFIED`。
- Formal 可证明安全回收空间仍为 0 B。Green 另有一组归档完整的旧 UI 验收候选：精确清单 76 个目录、14,713 files / 14,366,893,032 B；ZIP SHA-256 `183929BF629BCBD5473C0F41210EC37125F86FB7CAE0BFADA38843AE100151A4`，保留 ZIP 与 manifest 后逻辑差约 8.93 GB。限定审计发现 24 个目录名被历史 UI 文档引用，另 52 个未命中；未命中不构成无消费者证明。原目录继续保留，自动审批曾拒绝递归删除，当前尚无用户对精确 76-dir 清单的明确选项，故尚未执行删除。
- Green 独立发布 payload 仍为 `UNKNOWN`（`output/` 为空）；根 launcher 仍是 stable v0.6.14。本轮没有替换根运行时、删除目录、提交或推送。
## 2026-09-29 当前回合双仓只读体积刷新与临时产物回收

本次读数均为可读取文件的逻辑字节，不是 NTFS 已分配空间；不同路径口径不可直接互换。

| 范围 | 文件数 | 字节 | GiB | 范围/状态 |
|---|---:|---:|---:|---|
| Formal 仓可读取文件 | 1,252,206 | 137,443,942,213 | 128.005 | 排除 `.git`、`.agents`、`.codex`、`.hermes`；有 1,221 项读取错误，属于可读下界。 |
| Formal `.project-local` | 1,216,585 | 133,929,909,877 | 124.732 | 同样受 1,221 项错误影响；不是完整物理占用。 |
| Green 根（不枚举 `data/`） | 167,973 | 55,053,592,648 | 51.273 | `data/` 未读取；扫描 0 个 I/O 错误。 |
| Green `.ui-task-tree` | 101,159 | 52,093,137,963 | 48.516 | 已包含于 Green 根读数，不重复相加。 |
| Green mainline `.project-local` | 50,760 | 34,017,455,395 | 31.681 | 已移除本轮专用临时构建输出目录后读数；含其余任务资产、验收材料与归档。 |

本轮仅清除两个由本轮创建、用于 B05 截图验证的专用 Release 输出目录：Formal `.project-local/build/aaos-b05-evidence-table`（78 files / 601,856,694 B）和 Green mainline 同名目录（74 files / 602,222,164 B），共 152 files / **1,204,078,858 B**。删除前核实了两个目录的确切文件数/逻辑字节并确认无进程从这些路径运行；删除后读回均不存在。B05 截图、索引和其他 build/run/验收/恢复资产均保留。该数值为目录逻辑大小，不承诺磁盘物理空间等量回收。

外溢源目录和归档校验状态不变：三条原始源路径均不存在；Formal 与 Green mainline `.project-local/mig/` 下三份迁移负载仍逐文件哈希一致（3,157 files / 86,841,871 B）。Candidate-run 的 4 个 SHM 哈希差异仍为 `PARTIAL`；DSH runtime 的内容寻址对象哈希为 3,112/3,112 PASS；wheel qualification 为 `UNVERIFIED`。没有对这三份归档做删除或内容改写。

安全清理边界不变：Formal 其他 build/staging/runs/worktrees/cache 仍没有精确证明可删除对象；Green 精确 76-dir 历史 UI 候选仍未收到针对清单的明确删除确认，不删除。Green 独立可分发 Release payload 仍 `UNKNOWN`；本轮没有扫描 Green `data/`、替换 Green 根启动程序、提交或推送。

## 2026-09-29 双端编译后的体积快照

此快照晚于上一节清除临时 B05 构建目录，也晚于正式编译 `AvaloniaResource` 清单的双端 Release 配置验证。所有数值仍为逻辑文件大小；`.project-local` 属于总量的一部分。

| 范围 | 文件数 | 字节 | GiB | 读数口径 |
|---|---:|---:|---:|---|
| Formal 仓可读文件 | 1,252,206 | 137,414,152,585 | 127.977 | 排除 `.git`、`.agents`、`.codex`、`.hermes`；全仓有 1,221 个读取错误，作为下界。 |
| Formal `.project-local` | 1,216,585 | 133,900,117,905 | 124.704 | 有 1,220 个读取错误；其余一项错误位于仓库根其他路径。 |
| Green 根（排除 `data/` 内容） | 167,973 | 55,017,982,211 | 51.239 | `data/` 未枚举，0 个 I/O 错误。 |
| Green `.ui-task-tree` | 101,159 | 52,057,527,526 | 48.482 | 包含在 Green 根之内；不能重复加总。 |
| Green mainline `.project-local` | 50,760 | 33,981,842,614 | 31.648 | 包含本轮正常 Release 编译输出及其余任务材料。 |
| Green 根减 `.ui-task-tree` | — | 2,960,454,685 | 2.756 | 仍包含 backups、runtime 与各验收候选；不等于独立 release payload。 |

Green 正式启动根的独立安装/发布负载体积仍未核定；根目录、task tree、Acceptance v4、runtime 子目录和独立 Release publish 是不同口径。当前量值不能用于声称 Green 安装包为 51.239 GiB，也不能替代 v0.6.14 根启动链与 UI mainline 的集成验收。

## 2026-09-29 回合末体积 / 清理 / 上传状态复核

本次只读扫描由并行审计完成，文件长度为逻辑字节，扫描跳过目录联接点；不代表 NTFS 已分配空间。Formal 排除 `.git`、`.agents`、`.codex`、`.hermes`；Green 整体跳过 `data/` 内容。

| 范围 | 文件数 | 逻辑字节 | GiB | 说明 |
|---|---:|---:|---:|---|
| Formal 仓可读范围 | 1,248,803 | 137,349,913,121 | 127.917 | 1,221 个读取错误，为下界 |
| Formal `.project-local` | 1,213,182 | 133,835,837,053 | 124.644 | 1,220 个读取错误，为下界 |
| Green 根（不含 `data/` 内容） | 167,978 | 55,018,615,513 | 51.240 | 含 `.ui-task-tree`，不是安装包大小 |
| Green `.ui-task-tree` | 101,164 | 52,058,160,828 | 48.483 | 已计入 Green 根，不重复相加 |

### 清理与外溢

- 新审计未确认除既有候选外的安全可删除对象；Formal 已证明可回收空间仍为 `NONE_PROVEN`。
- Green 有 76 个旧 UI 历史目录（14,713 files / 14,366,893,032 B）已逐文件归档到保留的 ZIP+manifest；保留归档时的逻辑差额约 8,932,269,078 B。24 个目录名仍被限定范围内历史文档/脚本/测试引用，52 个未命中不证明无消费者。自动审批此前拒绝递归删除，因此原目录仍保留；本条不构成删除授权。
- 三个指定外溢源目录当前均不存在。Formal 与 Green mainline 的 `.project-local/mig/` 仍持有逐文件哈希一致的 3,157 files / 86,841,871 B 迁移归档；candidate-run 仍 `PARTIAL`（4 个 SHM 与 manifest 哈希不同），DSH runtime CAS 3,112/3,112 PASS，wheel qualification `UNVERIFIED`。

### Git 上传与双端一致性

- 当前 Formal `codex/Audit` HEAD `43c2cafa`，工作树有未提交变更；Green mainline `codex/aaos-ui-mainline-20260927` HEAD `d8f99a63`，也有未提交变更。两端 UI 文件与测试集合不完全一致，不能记作同一发布提交。
- Green 的 `origin` 指向本机 Formal 仓库路径。Formal 的 GitHub `origin` SSH 只读连通性检查因本机 `known_hosts` 无法读取而失败；没有执行 commit/push，也未读取或更改凭据。故远端上传状态为 `NOT_EXECUTED`，不是 PASS。
- Green 根 stable launcher 仍未替换为 UI mainline；首次启动、真实 Core、回滚及多 DPI 验收仍未完成。独立可分发 Green payload 体积 `UNKNOWN`。

## 2026-09-29 上传阻塞根因复核

用户已明确授权上传。根因为执行通道授权/网络，不是缺少用户口头授权：

- GitHub 连接器身份为 `dtslwx6890`，读取仓库 `DTALEX66/ArcheAxis-Knowledge-OS` 返回权限 `pull=true, push=false`；该连接器不能提交或移动远端 ref。
- Formal 仓库原始 remote 是 HTTPS，但用户级 Git URL rewrite 将 `https://github.com/` 改写为 SSH；SSH 在受限上下文无法读取用户 `known_hosts`。
- 使用仓库内临时空 Git 配置避开全局 rewrite 后，OpenSSL HTTPS 的公开 `ls-remote` 成功读到 refs；但 `push --dry-run` 在 Git Credential Manager/网络路径失败，随后指定 HTTPS 的受控只读复测在沙箱与批准执行上下文均无法连接 `github.com:443`。
- 未修改全局 Git/SSH 配置、ACL 或凭据；未提交或推送。此次隔离测试配置已清除。
- 双仓 UI 写集仍有真实差异，不能用整仓 `git add -A`；在授权通道恢复后，须按显式 UI 文件清单提交，并保留 `.project-local`、历史归档和本地运行数据。

恢复条件：在 Codex 中将 GitHub 连接器切换/重连到对该仓库具备 Contents 写权限的账号（或授予当前连接该权限），并确认批准网络通道可达。然后先统一经审阅的 UI 写集，再创建 feature commit、推送并读回远端 SHA；不直接推 `main`。

## 2026-09-30 外部项目归属与系统残留交接补充

本补充依据用户授权，对本轮实际遇到的跨项目/软件残留做了归属判断；不把 Windows 安装登记误记成 AAOS 源码，也不伪造迁移或分支：

| 发现 | 应归属 | 本轮处理 | 后续 |
|---|---|---|---|
| Visual Studio Build Tools 2022 17.14.36 安装登记指向不存在的 `D:\All projects\Cognitive-Loop-OS\.hermes\toolchains\vs-build-tools` | 旧 Cognitive-Loop-OS 工具链登记，不是当前 AAOS 依赖 | 通过微软官方安装器仅卸载此失效 instance；`vswhere` 和对应注册项已回读为不存在；注册备份在 `D:\All projects\Record\system-software-audit\2026-09-30\visualstudio-buildtools-17.14.36-stale-registration.reg`，SHA-256 见软件复核报告 | 不创建 Git 分支：没有要搬入 AAOS 的源码；备份保留在系统审计 Record |
| LibreOffice 卸载登记指向 Obsidian-Assistance 源路径，但未找到 `soffice.exe`；D 全盘可遍历文件名检索存在失败项 | Obsidian-Assistance / 原软件安装，归属与实际状态未定 | 未改注册表、未迁移目录、未删除程序文件；状态 `UNKNOWN` | 有效源路径和程序所有者明确后，交给该软件归属仓库处理；不得复制入 AAOS `.project-local` |
| C 盘 `EDTemp` 两份同 SHA SQLite DLL | 临时软件/安装源未知，不属于已证明的 AAOS 数据 | 保留原位置，写入 `D:\All projects\Record\system-software-audit\2026-09-30\software-health-review.md` | 获得安装包/创建者证据后再决定迁入所属软件归档或删除 |
| 用户指定的三处 DSH 原始目录 | 对应 DSH 项目 | 2026-09-30 回读仍不存在；已迁移材料及边界仍见本回执上文的 `.project-local/mig` 清单 | 没有源目录可再迁移；若在其归属仓库发现需要接收的文件，另做清单、SHA 验证和 owner handoff |

本轮仅创建本地审计报告与清理回执，无 commit/push，也没有创建 branch。系统维护报告同时记录 C/D Windows servicing PASS 和第三方软件未验证项。

## 2026-09-30 AAOS 候选缓存与跨项目 handoff 状态

- `vcurrent8` 曾被只读审计报告为与同名 ZIP 完全匹配，但 `.project-local` 文档引用检查有 ACL 盲区；本轮未完成独立重校验，保留。
- `vcurrent13` 曾被报告与同名 ZIP 匹配，但比归档多两个空数据目录，且 DSH 回读文档引用展开路径；本轮未建立可验证的恢复指针，保留。
- `vcurrent6` 有 ZIP 未含文件，且被当前候选索引；保留。`va5de4b13` 是正式候选输入；保留。
- R6 三个候选包和展开目录本轮均保留，因本轮逐成员重算未完成。详见 Formal 仓库 `docs/history/storage-cleanup/2026-09-30/r6-green-expanded-candidate-handoff-20260930.md`。
- DSH 原始项目路径现在不存在。现有 DSH CAS/快照归属 DSH，暂存于 AAOS `.project-local/mig/` 的历史接收区，仅作为可审计迁移来源；没有目标 DSH 仓库时，不擅自复制、建分支或声称目标端集成。未来在 owner 项目恢复后，按 machine manifest/hash 迁入归属地并在目标仓库建立 handoff；candidate-run 的 SHM 差异与 wheel `UNVERIFIED` 限制必须随材料保留。
- 本轮没有创建分支或对远端操作；全部说明是本地交接文档，工作树仍有用户已有 UI 修改。

### 2026-09-30 候选审计更正

更新正式 `green-candidates` 状态：`vcurrent8` 不能视为与 sibling ZIP 完全相同；既有 manifest 审计发现 ZIP 多 225 个成员，历史 runs 消费状态也有 UNKNOWN，因此保留。`vcurrent13` 有两个 ZIP 未编码的空目录且被 DSH 回读文档引用，保留；`vcurrent6` 缺失 ZIP 载荷并被当前索引引用，保留。三者均有 setuptools `.lock` 文件。详细审计见 Formal [系统软件与存储续审](../history/storage-cleanup/2026-09-30/system-software-and-storage-continuation-20260930.md)。

同日后续的独立完整回读已验证三个 `green-candidates-r6` 展开包与 ZIP 的成员路径、长度、SHA-256 和 CRC 全部一致，唯一额外项是可重建 `.pyc`。展开副本仍在原位；本轮未删除。恢复路径和当前逐成员 machine receipt 已记录于 Formal `docs/current/R6-EXECUTION.md` 与 `.project-local/mig/r6-green-expanded-dedupe-20260930/verified-recheck.json`。此前“本轮校验未完成”的注记是先前时间点记录，由后续证据更新。


## 2026-09-30 系统报告与归属续审

两条明确指向 ArcheAxis Desktop 的 Windows WER 原件已复制至 D:\All projects\Record\AAOS-project-archives\2026-09-30\windows-wer\，每个 Report.wer 大小/SHA 回读一致，清单 SHA CB64D4B57C25BF73840BD8B0A5368982C49004398527F4E6D1C0C7DB78202985。C: 原件目录仍保留，因为删除命令被执行策略拒绝，未绕过；不计源盘回收。C:\EDTemp 同哈希 SQLite DLL owner 未确认；D:\All SQLite+WAL/SHM 仍 UNKNOWN；D: DSH Desktop 数据归 DSH owner，保留；VS Code 注册项路径失效、LibreOffice登记指向 Obsidian-Assistance 路径均未修改。完整状态与软件健康限制见 docs/history/storage-cleanup/2026-09-30/system-software-and-storage-continuation-20260930.md。


## 2026-10-07 独立回读与更正（只追加，不改写上文任何一句）

本轮用逐文件 `os.walk` + SHA-256 重测，未删除、未移动任何文件、未发布。完整逐条表在忽略根
`.project-local/task-runtime/spillover-readback-20261007.md`；下列数字是同一次回读的复算值。

- **计数更正**：第 47 行写"9 个 `hermes__task-runtime__*.patch`"，今日 `docs/history/worktree-preserved-diffs/`
  下实测 **8 个**，全部未入 Git。第 9 个为 UNVERIFIED。
- **"五个 legacy-copy 归档树 SHA 全部不同"（第 98 行）今日不成立**：`342f16e3 / 345df936 / 3c605b9b /
  85832da5 / f985e566` 五棵树的 `legacy-copy.sqlite` **同为 `b318c99e5a58…`**，其 WAL/SHM 为 0 B，
  差异只在 receipt/manifest。当时的"全部不同 → 全部保留"判断按当时证据成立；今天的重复度评估必须按
  "同一个 SQLite 存了五份"来算，是否去重需另做带可恢复件的处置，本轮不动字节。
- **体积读数已过期**：第 120/141/159 行的 `.project-local/mig/` = `3,275 files / 135,499,757 B`，
  今日实测 **4,394 files / 4,606,843,838 B**。
- **双仓一致性被现盘推翻**：第 223 行记录 Formal 与 Green mainline 三份指定迁移目录逐文件一致、两份回执
  同 SHA `5EEF4FFA…`。今日 Green mainline `.project-local/mig/` 中这三项**全部不存在**，其
  `.project-local/archives/` 为空，未找到任何移除回执。Formal 侧三份完整（candidate-run 36 files /
  1,821,597 B；DSH runtime 3,117 / 76,831,790 B；wheel qual 4 / 8,188,484 B）。在补出移除证据之前，
  Green 侧不得再被当作副本；也不得反向覆盖 Green 的旧文本。
- **同一回执现存两版**：Formal `72d828bb…`（43,490 B）与 Green mainline `94e50f4a…`（31,022 B，缺
  09-30 追加段）。以 **Formal 版为权威**，Green 版记为历史早期版本，二者不再互写。
- **最大宗外溢仍在仓外且被引用，因此本轮不移动**：`D:\All projects\Record\AAOS-project-archives\` 今日
  **15,042,572,388 B**；其中 `2026-09-29\AAOS-UI-HISTORY-76DIRS-20260929.zip` 5,434,623,954 B 是
  **唯一副本**，其 SHA 与记录 `183929BF…` 相符。`git grep` 确认该路径被 **9 份已跟踪文档**按名引用。
  移动会使这 9 处引用失效，且它没有第二份可回退，所以搬迁的正确顺序是：先落一份"归属 + 新路径 + 旧路径映射"
  的处置记录，再按逐文件 SHA 搬迁并在同一批里改引用；本轮只把状态说清，不做前两步。
- **两处断链引用**：本文件引用的 `…-removal-review.txt` 与 `README-AAOS-UI-HISTORY-20260929.txt` 实际位于
  Formal `.project-local/mig/green-ui-history-20260929/`（不在 Green `archives/`）；
  `task-runtime-scattered/worker-quality-0906-unique-20260918.md` 的已跟踪位置是
  `docs/history/worktree-preserved-diffs/`。按现盘路径读，不按旧目录名读。
- **保持"标记不删"**：`C:\EDTemp\20260626_*\sqlite3.dll`（2 × 2,166,784 B，同哈希）归属仍未证，按 AGENTS
  的归属规则保留并标 UNRESOLVED-AMBIGUOUS。
- **两张处置/血缘表今天仍然成立**：处置表 284 条中 1 条盘上缺失，是已记录的
  `REMOVED_EXACT_DUPLICATE_CANONICAL_RETAINED`（规范件哈希一致），不是幻影；血缘表 292 条中 8 条哈希漂移，
  是活跃开发文件相对 09-25 快照的正常变化。
- **Green mainline 工作树归属**：该目录 git 报 dubious ownership（属 `CodexSandboxOnline`），任何搬迁之前
  先解决归属；本轮只读，未改其 ACL 与提权。
