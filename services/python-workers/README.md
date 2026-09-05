# services/python-workers（隔离 capability worker）

> DIRECTORY_AUTHORITY：`services/python-workers/**` 归 worker 执行；**无主库权限**（may_open_main_database=false）。
> 语言边界：Python worker 只能经本地 HTTP API（crates/archeaxis-api，契约 packages/contracts/v1）与 Rust Core 交互；
> 禁止：直连 SQLite、写库、sys.path 修改后直接 import app 包、双写。

## worker-protocol（contract: packages/contracts/v1/worker-protocol.schema.json）

worker 调用流（v0.1 slice 未实现 HTTP job 队列前的最小形态）：

1. 输入：文件路径 / 原始字节 + source_name（owner 通过 Core 导入后调用）
2. 处理：调用本仓可替换能力（解析/OCR/ASR 由包 C 引擎：pymupdf/RapidOCR/SenseVoice —— 复用现有 legacy 引擎代码作为行为来源）
3. 输出：`text` + `loss_receipt`（engine/version/params/loss_note）→ POST 给 Core（Rust 持久化 transform）
4. 失败：显式错误回执；绝不假装成功

## 当前状态
- 骨架就位（本 README + 契约引用）
- 下一步 slice：worker 与 api 之间的 job 契约实现（import 202 → worker 执行 → transform 回执入库）
