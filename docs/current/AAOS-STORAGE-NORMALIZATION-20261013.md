# 本地与云端仓库规范化及体积审计

Owner 在本轮明确加入该任务。状态 RUNNING_BY_OWNER / PARTIAL；没有目录迁移、批量删除、Git 历史重写或 Green 替换。

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
- NORM03：精确迁移清单、目标、回退与 readback，保护所有被引用证据；未执行移动。
- NORM04：云端 tracked 当前树与历史对象区别、普通提交去重方案；不重写历史或 force-push。
- NORM05：执行被审阅的具体清理范围，读回空间节约、哈希与仍有效消费者；尚无可审核的批量删除清单。

回退：本轮规范修正可单提交 revert；源文件、历史证据和用户数据均保留。

## 首批透明压缩实际回执

仅 `runs/be268a2d33/341d928bd8d1/tmp/backend` 的已审计、独立文件二进制白名单操作，217 文件 SHA 全部保持原值、路径原样。首个 libssl 单文件试验节约 815,616 bytes，随后批次新增节约 93,470,856 bytes，合计 94,286,472 bytes（约 89.92 MiB）。不改 Core executable；没有删除或移动，不把另外 31 个大 run 视作相同内容。

证据 `.project-local/runs/7d522a2a69/storage-audit-20261013/artifacts/compression-single-file.json` 与 `compression-reviewed-build.json`；逐文件记录压缩前属性、实际 allocated bytes 和 SHA 读回。回退对 before_compressed=false 的精确路径执行 `compact /U /Q`，已压缩文件保留先前属性。该回执只资格此批清理，不代表全部仓库治理完成。
