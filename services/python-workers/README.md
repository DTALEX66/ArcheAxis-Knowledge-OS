# services/python-workers（隔离 capability worker）

> **2026-10-12 当前路由与状态**：2026-10-11 Owner 已恢复完整框架、常见格式与最短闭环实施，RUNNING_BY_OWNER / PARTIAL，读 [活动指针](../../docs/current/AAOS-ACTIVE-EXECUTION.json) 与 [文档身份路由](../../docs/current/AAOS-AUTHORITY-ROUTES.json)。2026-10-10 暂停为历史时点。六项核心能力增量 FROZEN_BY_OWNER；V01 暂停、FT01–04 冻结；发布、Green 替换和真实资料覆盖未授权。

本地回答与复测可在正式请求中显式携带 `model`。Core 将其绑定到请求、拒绝摘要和缓存；Executor 在固定本机 lane 的清单验证后传 `--model`，并核对 worker 返回的 `model/requested_model`。选模回答必须提供冻结 `client_request_id`；模型绑定的原回答复测不能省略模型。显式模型复测同时冻结 timeout；未指定模型的旧请求与历史缓存形状保留。清单列出仅证明身份存在，未证明加载或推理；所选模型不存在时拒绝，不替换默认模型或转云。解析、OCR、ASR 仍调用各自专用 worker，云检索仍遵守独立外发授权。前端当前冻结请求为内存状态；未确认请求跨退出持久恢复尚未完成，不能宣称该能力已验收。

> DIRECTORY_AUTHORITY：`services/python-workers/**` 为 worker 执行域，**无主库权限**
> （may_open_main_database=false）。语言边界：正式 worker 经 Core 管理的 NDJSON
> 子进程通道交互；旧 HTTP receipt 是兼容入口，不是完整 worker 协议。
> 禁止：直连 SQLite、写库、sys.path 修改后 import app 包、双写。

## 公开资料检索的网络线路

百科、社区和科研的三个固定 HTTPS GET 接口使用独立线路选择，不改变模型服务商、鉴权或模型端点。`ARCHEAXIS_PUBLIC_RESEARCH_PROXY` 是仅对当前启动进程及其公开检索子进程生效的专用设置；不修改系统环境或 Windows 配置：

- 未设置时，Windows 仅只读当前用户 Internet Settings 中的 `ProxyEnable`、`ProxyServer`，复用已启用且明确登记的无鉴权、数字 loopback HTTP 代理。只支持单一代理或明确的 HTTPS 映射；不执行 PAC、不猜端口，不使用远程代理、凭证或通用 `HTTP(S)_PROXY`。不支持的系统设置及其他平台保持原直连。
- 显式 `http://127.0.0.1:<port>`（或 `[::1]`）优先于上述登记。显式 `direct` 强制直连并关闭自动复用。显式空值、拼写错误、远程或有鉴权地址均返回 `proxy_config_invalid`，不会偷偷改用其他线路。
- 复用线路仍校验目标站 TLS 证书、固定域名与接口、响应类型、总时限及大小；代理失败不降级为成功，也不自动重试。回读请求仅取回原回执；网络恢复后须显式检索产生新请求，原部分结果保留。

配置读取依据：[Microsoft WinINet](https://learn.microsoft.com/en-us/windows/win32/wininet/enabling-internet-functionality) 与 [Python winreg](https://docs.python.org/3/library/winreg.html)。这只是已登记本机 HTTP 线路的受限复用，并非完整 Windows/PAC 代理栈。

## Worker 能力矩阵（2026-09-05 实测状态）

| worker | 格式/能力 | 引擎 | 状态 | 收据 |
|---|---|---|---|---|
| worker_extract.py | 纯文本 envelope 样例 | stdlib | ✅ gate | T02s1 |
| document/worker_text.py | TXT/MD/CSV/TSV/JSON/XML(F01) | stdlib | ✅ | T05s1 |
| document/worker_canvas.py | JSON Canvas(F12) | stdlib | ✅ | T05s1 |
| document/worker_subtitles.py | SRT/VTT(F12) | stdlib | ✅ | T05s1 |
| document/worker_office.py | DOCX/PPTX/XLSX/PDF(F05/F07/F08/F09) | stdlib+pptx+openpyxl+pymupdf | ✅(docx CI 全跑; 其余本地实测) | T05s2b |
| web/worker_html.py | 静态 HTML 快照(F02 正文段) | stdlib | ✅ | T05s2a |
| web/worker_webpage.py | 有界抓取+快照(F02 网络) | urllib | ✅ 本地实测 | T05s2c |
| media/worker_transcribe.py | WAV/MP3/M4A/FLAC ASR(F10) | faster-whisper-large-v3-turbo | ✅ 本地实测 | T06s1 |
| media/worker_video.py | 视频音轨+关键帧(F11 部分) | ffmpeg | ✅ 本地实测 | T06s2a |
| vision/worker_ocr.py | 图像 OCR 文本+框(F04 部分) | tesseract 5.5；无 Tesseract 时 RapidOCR PP-OCRv4 回退（中英） | ✅ 本地实测 | T06s2b |
| vision/worker_caption.py | 图示/场景描述(F04 层2) | ollama qwen2.5vl:7b | ✅ 本地实测 | T06s2c |
| evaluation/worker_quality.py | CER/WER 评测(T07) | stdlib | ✅ | T07s1 |

通用契约：成功=单行 JSON envelope（engine/engine_version/text 或格式专属字段 + loss_receipt）；
失败=非零退出 + `{"error": ...}`，绝不伪造成功。CI 门禁：`workers-vnext`
（scripts/ci/check_vnext_workers.py：编译+正反例+探针+失败契约）。

## 明确边界（不冒充已完成）

- F03 动态网页渲染/截图：需 playwright+chromium 运行器，当前标 BLOCKED-RUNTIME（记录于模型 profile）。
- F06 扫描 PDF/混合 OCR 页：逐页渲染与 `image.ocr` 路由已接线；Tesseract 缺失时 RapidOCR 仅承担中英，其他语言仍具名失败。嵌入图/幻灯片图像 OCR、字幕对齐、画面事件语义（VL）仍属独立 lane。
- 广告/正文分离（trafilatura 级）与多栏阅读序：后续 slice。

## worker-protocol（contract: packages/contracts/v1/worker-protocol.schema.json）

2026-09-06 新增文本协议入口：`transport/text_ndjson.py --staging-root <attempt-dir>`。
此入口发出 hello，读取一个 request，写入哈希寻址输出，再返回一个 result；
不打开主库。Rust `archeaxis-sidecar-protocol::worker` 检查报文身份和输出元数据。
路径、字节校验与进程正常退出还必须由 Core 执行器独立验证，不能信任 worker 自报。
现有格式脚本和上表历史探测结果不等于全格式端到端资格。

旧 worker 调用流（保留为解析能力入口，并非正式 NDJSON）：

1. 输入：文件路径 / 原始字节 + source_name（owner 通过 Core 导入后调用）
2. 处理：调用本仓可替换能力（解析/OCR/ASR 由包 C 引擎：pymupdf/RapidOCR/SenseVoice —— 复用现有 legacy 引擎代码作为行为来源）
3. 输出：`text` + `loss_receipt`（engine/version/params/loss_note）→ POST 给 Core（Rust 持久化 transform）
4. 失败：显式错误回执；绝不假装成功

文本切片已经由 `archeaxis-application::executor::Executor` 执行：领取 attempt、
独立校验三份输出、原子落库、直接子进程超时/取消及重启恢复。尚未接入完整
HTTP/UI 调度、多格式子进程树隔离和自动重试；不能据此声称全格式闭环完成。
envelope 契约与通道映射见 `packages/contracts/v1/protocol-mapping.md`。

### Document check independent search query (2026-10-11)

Document-check engine receipts preserve missing provider `total_tokens` as JSON `null` (unknown), independently of execution success. A provider-reported integer zero remains zero. Boolean, negative, fractional and string token counts are invalid; missing usage must never be coerced into zero. Core persists the unknown value and the UI accepts it without treating it as a known cost. Actual fee accounting remains unqualified.

`document_check.py` accepts an optional `search_query` in its version-bound worker request. The query must contain non-whitespace text, at most 1000 characters and 4000 UTF-8 bytes; the worker rejects invalid queries before loading the search transport and never truncates or substitutes document text. Recognition fidelity does not search by default. Professional-basis checks require this independent query and otherwise return `search_query_required` without calling search or model transport. This worker boundary is not user egress approval. Core/UI now preview and confirm the actual material/destination/configuration plan, retain immutable per-request local_only, and append durable withdrawal events in the existing document_checks store. Admission rechecks the original request and full plan after waiting for a worker slot. Confirmation fingerprints include the existing authorization restore epoch; restore requires a fresh preview and confirmation. Core-only admission fingerprints are removed from worker wire requests, so they do not alter the worker protocol or prompt. Withdrawal blocks subsequent starts/retries and cannot recall materials already sent; Core now revalidates while waiting for worker stdin, response and exit, terminating its owned child after withdrawal; this has a synthetic no-network worker regression. Terminal receipt admission checks withdrawal in the same SQLite writer transaction: a prior withdrawal prevents a successful terminal outcome while preserving the returned verdict and engine evidence. Complete active-network cancellation, child-tree isolation and the final recheck-to-first-network race remain unqualified. Core/UI now register, persist and forward an independent query; requests without it remain unavailable instead of silently searching document contents. Query registration is not complete egress approval. Ordinary content saving and human knowledge selection remain independent.

### Machine-call failure diagnostics (2026-10-12)

The CLI machine worker emits only `archeaxis.machine-worker-failure/v1` plus an allowlisted `reason_code` on failure, then exits nonzero. Known classifications are `MODEL_CALL_FAILED`, `NO_FINAL_ANSWER`, `EMPTY_ANSWER`; unknown exceptions become `WORKER_FAILED`. Exception strings, stderr, prompts and model text are excluded. Executor drains bounded stdout/stderr after terminal exit for at most one second, still within the existing overall deadline and owned-child cleanup; a nonzero worker never supplies a successful answer even if stdout includes one. Core rebuilds HTTP503 `archeaxis.machine-call-failure/v1` with operation `answer`/`retest`, reason code, `execution_state=UNVERIFIED`, `answer_published=false`. Additional executor reasons are `WORKER_TIMEOUT`, `OUTPUT_LIMIT`, `INVALID_OUTPUT`, `PIPE_DRAIN_FAILED`; unknown errors remain `WORKER_FAILED`. Frontend displays only these classifications, retains the original request, and never treats a 503 as proof of non-execution. Existing historical generic503 failures cannot be retroactively classified. The worker's own HTTP timeout and Core's stricter process budget remain distinct; this change does not alter endpoints, models or budgets.

Machine answer --probe reads model inventory only. Legacy capability=true means the selected model ID is listed; it does not prove loaded state or successful inference. Consumers must use evidence_scope=MODEL_INVENTORY_ONLY, availability=MODEL_LISTED_INFERENCE_UNVERIFIED, inference_status=NOT_EXECUTED and loaded_status=UNKNOWN; inventory failure remains UNVERIFIED, and a missing selected ID is MODEL_NOT_LISTED. No prompt is sent by this probe.

Local answer receipts preserve only provider-reported nonnegative integer token counts: OpenAI usage prompt/completion/total tokens, or Ollama prompt_eval_count/eval_count. Missing/invalid fields remain absent, never synthesized as zero or total. usage_status is REPORTED or UNKNOWN; cost remains null/UNKNOWN without verifiable pricing. Inventory probes do not return inference usage.

The local answer/discovery transport accepts HTTP numeric loopback only; localhost is normalized to 127.0.0.1 without DNS discovery. Inherited proxies are disabled, redirects are refused, URL userinfo/fragments and remote/unspecified destinations are rejected before open. This lane has no remote fallback. Inventory listing still does not establish loaded or inference status.


Core 在回答与复测的 worker 调用前，将请求摘要与 IN_FLIGHT 执行记录持久化到 canonical workspace_meta。既有 positive/withheld 回执优先重放；无终态的旧执行记录阻止同身份再次推理，并将历史执行标为 UNVERIFIED。只有已返回的 worker 失败且 KNOWN_FAILURE 写入确认后，才允许显式同请求重试。记录不存材料正文。此机制不是完整 exactly-once：没有 client_request_id 的 legacy 回答缺少跨请求稳定键，UI pending_machine 已由 Core 持久化冻结请求，并等待写入 ACK 才执行；恢复只读核对，尚未进行真实模型执行中杀进程恢复验收。

复测 claim 身份绑定有限 normalized 请求，实际材料摘要保留在执行记录中；材料变化不能用新的派生身份绕过未完成屏障。扣留审计同时保存 admission_request_sha256（冻结 transport 输入）与 request_sha256（实际执行 envelope），二者不混用。只有精确匹配的 RECORDED 终态可由 human clear-machine 明确清理 pending_machine；该操作不删除审计、执行 claim 或更新模型/授权。FAILED 和旧无输入指纹的审计不能作为清理凭据。复测 journal owner、问题绑定既有 runtime.evaluation.failed 旅程；历史核对不消费当前授权。
