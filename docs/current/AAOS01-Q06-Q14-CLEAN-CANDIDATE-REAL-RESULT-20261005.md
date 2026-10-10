# AAOS-01 Q06/Q14：权威流水线产出的干净候选可用（2026-10-05）

用修复后的 `scripts/release/stage_backend_runtime.py` 在短无空格根产出干净候选，并在其中跑通 PDF 流程。
**这不是手补的探针树**，是权威暂存器的产物。

## 候选身份

| 项 | 值 |
| --- | --- |
| 根 | `C:\Windows\Temp\aaos-cand1`（短、无空格、当前用户所有） |
| 文件数 | 8552 |
| manifest sha256 | `c2a18537430bb09abd06092ffbc100f9cbaeb3913d8ed44c2cb8063747eee845` |
| 声明依赖 | 26 条（requirements.txt 解析） |
| 工具链 | 登记 MSVC / `x86_64-pc-windows-msvc`（Core 由当前源码构建） |

## 真实结果

| 步骤 | 结果 |
| --- | --- |
| Core 启动 | `archeaxis-api ready on http://127.0.0.1:8891` |
| 能力注册 | **14**（默认 text.extract + 13 条声明路由） |
| import | 202，sha256 `0f0ffc50c79d9d97…` 与 golden fixture 逐位相同 |
| enqueue | 202 `{"job_id":"pdf-clean-1","state":"queued"}` |
| execute | 202 `{"state":"running","replayed":false}` |
| 终态 | **succeeded**，`attempt:1`、`error:null` |
| outputs/text | 200，正文 `Golden Journey Evidence … PASS`，与 fixture 内嵌文本逐字相符 |

## 发现一个真实的集成缺陷（阻塞第一验收）

权威暂存器产出的布局与正式壳的解析器**不一致**：

| | 暂存器产出 | 正式壳解析器要求 |
| --- | --- | --- |
| 解释器 | **`runtime/python.exe`（平铺）** | **`runtime/python/python.exe`（嵌套）**（`desktop/src-tauri/src/runtime.rs:119`） |
| `worker-profile.json` | `"python": "runtime/python.exe"` | — |

**后果**：用权威流水线产出的候选，正式壳**找不到其解释器**，第一验收会在启动阶段失败。
**因此 `CoreSpec::beside_runtime` 里「`python` 上溯三层得根」的推导，对暂存器产物不成立** ——
它假设的是嵌套布局。这一条我标为**已发现、未修**。

## 按指令口径分项

| 判据 | 状态 |
| --- | --- |
| 正确原件 | ✅ |
| succeeded | ✅ |
| 可读且匹配样本的正文 | ✅ |
| 真实引擎身份 | **未采集** |
| 有效定位与损失记录 | **未查** |
| 退出重启后同一结果可读 | **未验** |

**结论**：**PDF 提取切片在权威候选内通过**；不记完整产品或全部 PDF 能力通过。

## 本轮不声称

未做窗口级验收（真实 Tauri 进程驱动 Core 生命周期）；布局不一致未修；引擎身份/定位损失/重启读回未采集。
