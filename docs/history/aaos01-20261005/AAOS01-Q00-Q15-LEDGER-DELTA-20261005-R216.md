# AAOS-01 Q00–Q15 台账 · 增量更新（2026-10-05，第 216 轮）

基线见 `AAOS01-Q00-Q15-LEDGER-20261005.md` 与第 195 轮增量。**只写变化过的行。**

| Q | 变化 |
| --- | --- |
| **Q02** | **宿主→Core 生命周期已可复现通过**：Core 启动、存活 54–79s、干净退出、同一数据根二次启动成功；`EBWebView` 渲染、Core 建库并写入。**缺口仅剩**：**Core 无法打开旧 Python 库**（见下）。**canonical 接管相应推进一大步，但旧数据兼容未完成** |
| **Q02 缺陷（已修）** | **`\\?\` 扩展长度前缀穿透进启动契约** ⇒ Core 一律 `invalid worker profile path`。已修（`contract_path`）+ 回归测试；错误已前移 |
| **Q02 诊断（新增）** | **Core 启动失败时把失败输出与（令牌脱敏的）启动文档落盘** —— 该诊断是定位 `\\?\` 缺陷的唯一手段 |
| **Q01 / Q14** | **包产物现已携带全部 7 项资源**（`core`/`runtime`/`workers`/`shared` + 候选四个根层文件）；资源表仅在**流水线被证实产出**后才扩展 |
| **迁移缺口** | **已定位到表**：Core 读 `workspace_meta.schema_version`，旧库（98 表 Python schema）无此表、`journal_mode=delete`、`user_version=0`。**两条路径（迁移 / 只读接入）待产品选择** |
| **Q06** | PDF 提取切片在权威候选内通过（`83800da9`）；**引擎身份 / 定位与损失 / 重启读回**仍未采集 |
| **Q14 安装旅程** | **NOT_RUN** |
| **§六 合并** | 三暂存器形态分歧已确证（`stage_backend_runtime.py` / `assemble_green_candidate.py` / `desktop/scripts/stage_runtime.py`）；**等产品决定正典形态** |

## 窗口级第一次验收（本轮）

| 判据 | 结果 | 证据 |
| --- | --- | --- |
| Core 生命周期 | ✅ | 存活 54–79s，多轮复现 |
| 真实资料列表 | ✅（代理） | Core 建库并写入；`EBWebView` 渲染；无失败记录 |
| 退出清理 | ✅ | `leftover core = False` |
| 重启读回 | ✅ | 同一数据根第二次启动成功 |
| **视觉确认** | **未做** | **无法查看像素** |

## 复现命令（本机）
```
# 干净重建（务必先删 target 中的资源目录，否则残留会静默胜出）
# cargo tauri build --no-bundle --config {"build":{"beforeBuildCommand":""}}
# 以 portable.flag 指向全新数据根后运行 ArcheAxis.exe
```
