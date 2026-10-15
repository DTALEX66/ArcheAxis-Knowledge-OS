# 本地与云端仓库规范化及体积审计

Owner 已将规范化与审计后清理加入执行范围。状态 RUNNING_BY_OWNER / PARTIAL；2026-10-15 首批精确迁移与空目录移除已执行，见文末最新记录。历史测量保留原观察日期；Git 历史和 Green 未改。

## 当前证据

已核实 remote main `be79ff90e7394247171afc311b002eb96ff0581e`。该树 3663 blobs，共 89,507,138 bytes，约 85.36 MiB；docs 39,015,333 bytes/1380 files，apps 14,199,113，verified-knowledge 5,562,353，frontend 5,326,187。最大历史任务 ZIP 10,988,693 bytes、ceshi_sweep_receipt.json 5,264,396 bytes、历史 UI ZIP 4,981,248 bytes；均先保全，体积不构成删除理由。Magika 3,163,428 bytes 有消费者，保留离线功能。

本地 canonical runs 元数据报告 `.project-local/runs/7d522a2a69/storage-audit-20261013/artifacts/storage-report.json`：6543 行，可读大小下界 35,523,740,195 bytes（约 33.08 GiB），1076 个测量错误、222 个排除，measurement PARTIAL，deletion_qualified=false。拒绝访问不绕过；UNKNOWN 不计零。

`be268a2d33` 3609 runs 共可读 25,450,640,056 bytes，其中 31 runs 超过 500 MB，共 19,927,498,562 bytes/605331 files。相同尺寸尚不证明相同内容。`469fb0c2e66a` 已有真实 4B 旅程消费者；`ui-teaching-stage-20261010` 与 `formal-portable-candidate3-20261009` 有明确消费者，保全。

## 已实施

1. `.project-local/archives/` 同步登记到目录 Authority 与 storage_report allowlist，符合 AGENTS 的源资料原始字节保全位置，避免误报成迁移目标。
2. AX-DIR-010 的旧 Avalonia 正式宿主说明改为当前 SUP-022 路由；历史表仍作为历史上下文保留，不赋予迁移/删除授权。
3. UI 源对话和 ZIP 已保全到 ignored archives；公开摘要与哈希回执独立交付。

## 接续队列

- NORM01：完整分区测量，保留测量错误与链接排除；当前 PARTIAL。
- NORM02：消费者索引、逐文件哈希与字节去重方案，先处理可再生构建副本；已完成下述精确白名单透明压缩，其他范围未压缩/删除。
- NORM03：原13个精确目录已处理，11个无损迁移、2个空目录移除，见2026-10-15三批回执；严格布局检查6/6 PASS。其他范围不据此推定已清理。
- NORM04：云端 tracked 当前树与历史对象区别、普通提交去重方案；不重写历史或 force-push。
- NORM05：执行被审阅的具体清理范围，读回空间节约、哈希与仍有效消费者；尚无可审核的批量删除清单。

回退：本轮规范修正可单提交 revert；源文件、历史证据和用户数据均保留。

## 2026-10-15 NORM03 精确目录与消费者审计

针对标准 quick 所报12个新浅层目录名，限定登记为项目-owned 的检出与这些精确路径进行只读元数据核查；同名 `declared-routes` 位于两处，共13个实际目录。9372个可测文件、255199890可读字节，测量错误0；`ui-polish-20261013` 排除1个重解析链接，不进入其目标。1个私有检出在探测前排除。公开tracked源码消费者按文件、行号、检出登记，审计不读取日志／私有正文，不把名称或公开引用当作生成所有权。

逐项来源、拟议标准目标、反向回退与公开消费者见 [迁移审计草案](receipts/AAOS-LEGACY-RUN-MIGRATION-PLAN-20261015.json)。该清单仍是 PARTIAL 草案：生成命令／活跃进程未确认，ignored消费者覆盖不完整，逐文件SHA与移动readback未执行。所有13目录保留，未移动、未删除、未改布局基线；原布局门禁仍 FAIL。先补齐这些事实并处理引用，再确定可执行的精确迁移集合，不能以没有公开引用推导可清理。

## 首批透明压缩实际回执

仅 `runs/be268a2d33/341d928bd8d1/tmp/backend` 的已审计、独立文件二进制白名单操作，217 文件 SHA 全部保持原值、路径原样。首个 libssl 单文件试验节约 815,616 bytes，随后批次新增节约 93,470,856 bytes，合计 94,286,472 bytes（约 89.92 MiB）。不改 Core executable；没有删除或移动，不把另外 31 个大 run 视作相同内容。

证据 `.project-local/runs/7d522a2a69/storage-audit-20261013/artifacts/compression-single-file.json` 与 `compression-reviewed-build.json`；逐文件记录压缩前属性、实际 allocated bytes 和 SHA 读回。回退对 before_compressed=false 的精确路径执行 `compact /U /Q`，已压缩文件保留先前属性。该回执只资格此批清理，不代表全部仓库治理完成。

## 2026-10-15 已授权首批迁移与空目录清理

Owner 明确要求执行中直接处理已审计的过时、冗余内容，包括归档、迁移和删除。对当前13个已登记目录复核后，三份历史源码交付材料已迁入各自 worktree identity 下：`job-journal-helper-fix-20261011`、`capability-onsite-delivery-20261011`、`capability-refusal-delivery-20261011`。9文件、144737字节逐一核对尺寸与SHA，全部保留；两个确认为空的 `declared-routes` 目录已用非递归删除移除。

精确旧→新映射、9文件摘要和反向回退见 [执行回执](receipts/AAOS-LEGACY-RUN-MIGRATION-EXECUTED-20261015.json)。没有删除非空文件，本批不计文件字节节约。其余目录、重解析目标和原始任务正文仍保留；当前批次不代表标准quick已经全通过，也不声称完成全系统句柄或ignored消费者审计。

第二批已迁移 `authority-repair`、`bounded-journal-guard`、`job-journal-delivery`、`upload-sync` 四个历史目录。533文件、10237979字节及241个子目录完整保留，移动前后文件树SHA一致；当前4份公开消费者的7处引用已更新。历史目录内部的原路径不改原字节，由 [第二批回执](receipts/AAOS-LEGACY-RUN-MIGRATION-BATCH2-20261015.json) 的prefix映射解析。精确源路径的当前进程匹配为0，没有终止进程或删除非空文件。首批后的布局检查仍有8项新浅层名称，第二批后已实测剩余4项，5项检查PASS、1项布局检查FAIL；不修改既有基线豁免。

第三批已完成剩余 `record-archive`、`restored-grant-refusal-delivery`、`frontend-taskpack-audit`、`ui-polish` 四个目录迁移，8,830文件、244,817,174字节和1,108普通子目录全部保留。唯一内部Junction仅移除链接对象并重建到新父目录内的原实体依赖，未递归删除或删除链接目标；完整文件树SHA、普通目录清单和链接目标读回PASS。当前2份公开消费者的3处引用同步更新，内部历史正文不改。详见 [第三批回执](receipts/AAOS-LEGACY-RUN-MIGRATION-BATCH3-20261015.json)。

三批合计9,372文件、255,199,890字节完整保留，11个目录归位、2个空目录移除；迁移不计文件字节节约。实际严格布局门禁 `legacy-layout-final` 6/6 PASS，旧基线未放宽。该结论只覆盖本次13个目录，NORM01/02/04/05其余体积审计与去重仍PARTIAL。
