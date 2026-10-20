# AAOS-01 交接与执行提示词（交给本地 Codex）

> 本文件同时是**交接说明**和**可直接粘贴给 Codex 的执行提示词**。
> 所有路径为 Windows 绝对路径。**凡标注「已验证」的都有命令输出；标注「未验证/推断」的不得当作事实使用。**

---

## 1 身份与起始状态（已验证）

```
仓库根     D:\All projects\ArcheAxis-Knowledge-OS
工作树     D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dsh-backend-loop-20261001
分支       codex/dsh-aaos-real-multiformat-loop-20261001
HEAD       e8b60f73721045116f3f37956d4b1093611bb54f
工作树     CLEAN
远端       https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git
PR 基线    origin/codex/Audit（不是 main）
```

**所有工作在工作树内进行**，不要在仓库根直接改。开工先 `git rev-parse HEAD` 与 `git status --porcelain` 复核。

---

## 2 授权范围与重构方向

**方向已确定，不要再交回用户决定：**

- **Tauri 2 + Rust** 为正式桌面宿主；**React/TypeScript/Vite** 为产品界面。
- **Rust Core 是正典数据的唯一写者**（SQLite + SHA-256 CAS + 契约）。
- **Python 是隔离的格式/模型 worker**，不是权威后台。
- **复用**既有实现与成熟开源库；**不得**新建第三套壳、平行后端或第二套数据模型。

**用户已明确交回给你的权限**：
- 暂存目录布局、普通实现选择 —— **自行决定，不要再问**。
- 合并/清理/冻结按授权推进；**删除前须有精确清单 + 引用检查 + 可恢复方式**。

**只有三类事才提交给用户**：旧库数据语义取舍 · 真实数据不可逆切换 · 必须真人的审核。

---

## 3 权威任务文档（编号以此为准）

```
docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md          ← 权威任务书（141 行）
docs/authority/taskpack-1004-aaos01/00_两包共同架构与交接规则.md
docs/authority/taskpack-1004-aaos01/README.md
docs/authority/taskpack-1004-aaos01/SHA256SUMS.txt
```

**编号定义（现行任务书，禁止用旧 E0 同名编号替代）：**

| 编号 | 现行定义 |
| --- | --- |
| **Q04** | **原件、Document/Block、CAS、草稿保存与恢复一致性**（任务书 §5） |
| **Q12** | **B 波次轻量格式扩展**：CSV/TSV、JSON/JSONL、YAML/TOML/XML、EPUB、EML（任务书 §6） |
| **Q14** | **Windows 安装态资格化** |

**任务书里对本交接最关键的两条硬约束：**
1. **「优先复用权威暂存器，统一运行时产物与启动契约」** —— 不要另写平行暂存脚本。
2. **音视频：「probe 成功不计作 ASR 成功」**；**A 波次不代表扩展名已通过**；
   **`verified_extension_count` 只在各自样本通过后才计入**。

其它仍有效的旧包：`docs/authority/taskpack-0919-r6/`（R6，不可变）+ `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`。

---

## 4 环境与工具链（**已实测**，注意与直觉不符处）

```
外部共享库  D:\All projects\OS External Configuration        （下称 <EXT>）

# Rust —— 注意：不在 10-toolchains 下，而在 <EXT>\toolchains\
<EXT>\toolchains\rust\cargo\bin\cargo.exe            True
<EXT>\toolchains\rust\cargo\bin\cargo-tauri.exe      True
<EXT>\toolchains\rust\cargo\bin\rustc.exe            True
<EXT>\toolchains\rust\rustup\toolchains\            包含：
    1.88.0-x86_64-pc-windows-msvc / stable-x86_64-pc-windows-msvc / stable-x86_64-pc-windows-gnu
<EXT>\toolchains\ 另有：mingw · playwright · scoop · rustup

# MSVC（Windows 安装态资格的权威口径）
<EXT>\10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat   True

# Node（Tauri beforeBuildCommand 需要它在 PATH 上）
<EXT>\10-toolchains\scoop\apps\nodejs-lts\                  True

# Tesseract（OCR 引擎与语言数据，均已在共享库）
<EXT>\10-toolchains\scoop\apps\tesseract\5.5.0.20241111\tesseract.exe
<EXT>\10-toolchains\scoop\apps\tesseract-languages\4.1.0\*.traineddata
# ⚠️ tesseract 当前 NOT on PATH —— 这是 OCR 失败的唯一原因

# CI 用的 Python（依赖齐全，可直接跑测试与探针）
<EXT>\ArcheAxis-Knowledge-OS-ci-venv\Scripts\python.exe       True

# uv —— ❌ 本机不存在（已递归搜索 <EXT> 与 C:\Users\ALEX，只匹配到 uvicorn.exe）
#    ⇒ 不能在本机跑 `uv lock` / `uv export` / prepare_bundle 的全新暂存
#    ⇒ 依赖 CI 的受控构建链，不要擅自全局安装
<EXT>\uv-cache\   （缓存目录存在，二进制不存在）
```

**Rust 构建的必需姿势**（否则报 `Missing manifest in toolchain 'stable-x86_64-pc-windows-msvc'`）：

```bat
set "RUSTUP_HOME=<EXT>\toolchains\rust\rustup"
set "CARGO_HOME=<EXT>\toolchains\rust\cargo"
set "CARGO_TARGET_DIR=C:\Windows\Temp\aaos-msvc-target"
set "PATH=<EXT>\10-toolchains\scoop\apps\nodejs-lts;<EXT>\toolchains\rust\cargo\bin;%PATH%"
call "<EXT>\10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat"
```

注意 `RUSTUP_HOME` **必须显式设为 `<EXT>\toolchains\rust\rustup`**；同级的 `<EXT>\toolchains\rustup` 只有 gnu 工具链。

---

## 5 🔴 当前唯一阻断项：资源表与构建流水线不一致（**已定位到根因**）

### 现象

`desktop-fast` 的 `Test the canonical Windows desktop shell` 失败，**真实日志**（run `37262959180`）：

```
error: failed to run custom build command for `archeaxis-desktop v0.6.14 (…\src-tauri)`
##[error]Process completed with exit code 1.
```

### 根因

`src-tauri` 的 `tauri-build` **在编译期校验 `tauri.conf.json` 的 `resources` 声明路径是否存在**。
资源表现声明 7 项（见下），而 **`desktop-fast` 只跑 `prepare_bundle`，它只产出 Python runtime**，
**从不构建 Core、也不落位其余 6 项** ⇒ `tauri-build` 失败。

### 证据链

**资源表** `src-tauri/tauri.conf.json`（`bundle.resources`）声明：
```
../.project-local/rt/runtime                    → runtime
../.project-local/rt/core                       → core
../.project-local/rt/workers                    → workers
../.project-local/rt/shared                     → shared
../.project-local/rt/worker-profile.json        → worker-profile.json
../.project-local/rt/start-backend.py           → start-backend.py
../.project-local/rt/start-backend.cmd          → start-backend.cmd
../.project-local/rt/backend-runtime-manifest.json → backend-runtime-manifest.json
```

**`desktop-fast`**（`.github/workflows/ci.yml` 约 881–935 行）步骤只有：
checkout → dev paths → python3.12 → uv → cache → `uv sync --frozen` →
**`prepare_bundle --destination .project-local/rt`** → `cargo fmt --check` + `cargo test`（**在此失败**）→ `cargo test`

**`desktop-build`**（同文件约 937 行起）在我加的步骤后有 `Build the canonical Core` /
`Place the canonical Core beside the runtime` / `Assert the bundle carries the Core and its workers` /
`Assert the staged runtime carries the format engines` —— **但它同样不产出那四个根层文件**。

**`desktop/scripts/prepare_bundle.py`**（111+ 行）只做：`stage_runtime` → 导出锁定依赖 → 下 wheel →
构建 archeaxis wheel → 装入 staged python → 校验 `import app.runtime_entrypoint, fastapi, uvicorn`。
**它不产出 `worker-profile.json` / `start-backend.py` / `.cmd` / `backend-runtime-manifest.json`。**

**只有权威暂存器产出这四个文件**：`scripts/release/stage_backend_runtime.py`
（`worker-profile.json` 在约 480 行写出；`start-backend.py` 约 486；`.cmd` 模板约 360–380；manifest 全文）。

### 修复方向（任务书已给定）

> **「优先复用权威暂存器，统一运行时产物与启动契约」**

1. **让 CI 的候选由 `stage_backend_runtime.py` 统一产出**，而不是我在 `desktop-build` 里手写的
   `--core-only` 拼装。其 CLI（已验证）：
   ```
   --core <要用的 archeaxis-api.exe>        （required）
   --runtime <staged Python runtime 目录>   （required）
   --workers <services/python-workers>      （required）
   --shared <shared 目录>                   （可选）
   --dep-source / --dep（可重复）           依赖闭包
   --out <候选根目录>                        （required）
   --version --source-commit --source-tree   （required）
   --runtime-commit --runtime-tree --packager-commit
   --archive（可选，另写 zip）
   ```
2. **`desktop-fast` 与 `desktop-build` 必须使用同一套准备步骤**（现在只有后者有，且不完整）。
3. **⚠️ 已实测的坑**：`stage_backend_runtime.py` **会拒绝它的输入。**
   我用 `aaos-cand1\runtime` 作 `--runtime` 跑它，得到：
   ```
   ValueError: protected staging path
     at validate_tree → reject_reparse（约 128 / 117 行）
   ```
   ⇒ **它要求一份干净的、通过私有名与 reparse 校验的 staged runtime**。
   ⇒ **先确认 `prepare_bundle` 产出的 runtime 能被它接受**，再接进 CI。

---

## 6 关键源码位置（均已确认存在）

```
宿主（正式壳，Tauri）
  src-tauri/tauri.conf.json            ← bundle.resources（§5）；productName/identifier/frontendDist
  src-tauri/src/main.rs                ← 选择 CoreSpec::beside_runtime 还是 BackendProcess::launch
  src-tauri/Cargo.toml                 ← bin 名是 ArcheAxis，crate 名 archeaxis-desktop

恢复壳（独立 workspace，被正式壳用 #[path] 复用模块）
  desktop/src-tauri/src/backend.rs     ← launch_core / contract_path / text_worker_for / probe_readiness
  desktop/src-tauri/src/runtime.rs     ← resolve_runtime_for_profile（:126 nested 优先，:127 flat）
  desktop/src-tauri/src/job.rs         ← Windows Job Object（只用 KILL_ON_JOB_CLOSE）
  desktop/src-tauri/src/protocol.rs    ← readiness_payload_valid

打包/暂存（三个实现，形态不一致 —— 这是 §六 合并的靶子）
  desktop/scripts/prepare_bundle.py        ← CI 用的，只产 runtime（+ 我加的 --core-only/--candidate-root）
  desktop/scripts/stage_runtime.py         ← 被 prepare_bundle 调用；拒绝已存在的目标目录
  scripts/release/stage_backend_runtime.py ← ★ 权威暂存器，产出完整候选（含四个根层文件）
  scripts/release/assemble_green_candidate.py ← 组装器，写 worker-profile.json（:231-237）
  scripts/release/backend_launcher.py      ← :7 说明「调度器解释器来自 worker-profile.json，Core 读它」

Rust Core
  crates/archeaxis-api/src/main.rs         ← :213-246 挂载条件 + 两句错误（见 §8）
  crates/archeaxis-api/src/lib.rs          ← :55-97 projections 路由（18 条）
  crates/archeaxis-api/src/runtime/mod.rs  ← :36-81 runtime 路由（18 条）；:676 output 处理器
  crates/archeaxis-store-sqlite/src/lib.rs ← :249/281/393 读 workspace_meta.schema_version
  crates/archeaxis-store-sqlite/src/writer.rs ← :68 Store::open

worker 与契约
  services/python-workers/routes.json      ← 13 个路由键的单一映射（任务书 §1 明确：不要重做收敛）

测试与夹具
  tests/test_multiformat_extraction.py     ← 我加的：canvas/archive/subtitles，6 项，走 convert_file
  tests/test_pdf_extraction.py             ← PDF 抽取测试范式（不要重写）
  tests/golden_pdf_fixture.py              ← 金样本模块
  tests/fixtures/golden/                   ← 金样本集（含我加的 canvas/zip/srt）

依赖声明
  pyproject.toml  ·  uv.lock               ← uv.lock 已含 openpyxl / python-pptx（带 wheel URL）
```

---

## 7 CI 与门禁（本轮实测的关键约束）

```
.github/workflows/ci.yml
  gateplan      ← 决定哪些门禁必需（按改动路径）
  desktop-fast  约 881 行  ← Test the canonical Windows desktop shell（当前红）
  desktop-build 约 937 行  ← 含我加的 Core 构建/落位/两条断言
  a0-gates      ← ci-verdict，汇总必需门禁
```

**⚠️ 只有改动以下路径的提交才会触发 `desktop-build` / `desktop-fast`**：
`.github/workflows/` · `src-tauri/` · `desktop/` · `crates/`。
**只改 `tests/` 或 `docs/` 的提交会让这两个 job `skipped`** —— **从这类运行里读桌面结论是徒劳的。**

**该分支设了 `cancel-in-progress: true`** ⇒ **等待运行期间推送会取消它**。
**已有 `workflow_dispatch(force_full)`** ⇒ 固定提交后用它跑完整门禁。

**已登记的既有运行结果（审计核验，请采纳）**：

| 运行 | 目标 | 结果 |
| --- | --- | --- |
| `37262959180` / `desktop-fast` | Test the canonical Windows desktop shell | **failure**（根因见 §5） |
| `37262959180` / `desktop-build` | 引擎断言 | **cancelled**；准备运行时被取消；断言 skipped |
| `37262727101` / `desktop-build` | — | **skipped** |
| `37262571828` | — | **cancelled**，`run_attempt=2` |

**引擎断言的精确登记：五次均未取得结论 —— 三次取消、一次拒绝重跑、一次目标任务跳过。**

---

## 8 硬获得的事实（照做，否则会重复本会话的弯路）

**Core 启动契约**（`desktop/src-tauri/src/backend.rs`）
- Core 从 **stdin 读一份 JSON 文档**，读完后才校验；参数是 `<workspace_db_path> [port]`。
- `protocol` 必须恰好等于 `archeaxis.desktop-launch/v2`；`actor` 必须恰好 `human`。
- `launch_token` 64 hex；`machine_token` 64 hex 且**必须与 launch token 不同**；`session_id` 32 hex。
- **`text_worker` 块**接受 `{python, script, staging, routes:[{capability,script}]}`，**绝对路径、不要 `schema` 字段**。
  加了 `schema` 会被判 `invalid launch input`。

**两条 `\?\` 前缀教训**
- Windows `canonicalize()` 返回 `\\?\C:\...`；**该前缀一旦进入启动文档，Core 一律拒绝**：
  `[core:stderr] invalid worker profile path`。
- 已修：`backend.rs::contract_path()` 去掉前缀 + 回归测试。**任何新写路径的地方都要过滤。**

**Core 的两句不同错误来自两个不同函数**（`crates/archeaxis-api/src/main.rs`）
```
if let Some(profile) = &launch.text_worker {
    Executor::open_routes(db, staging, python, script, extra)  →  失败: "failed to initialize execution workspace"
} else {
    Store::open(db)                                           →  失败: "failed to open workspace"
}
```
**声明 worker ⇒ 挂 36 条路由（projections + runtime）；不声明 ⇒ 只挂 18 条。**
⇒ **`/api/v1/capabilities` 是 runtime 路由，不声明 worker 就是 404（不是路径写错）。**

**查询端点（实测正确）**
- **引擎身份在 `GET /api/v1/jobs/:job_id/quality`** ⇒
  `{coverage, covered, total, engine, engine_version, loss_count, pages, region_count, state}`。
- **不在 `/api/v1/capabilities`** —— 那报的是 worker 握手：`health: handshake_ready`、
  `worker_identity`、`task_executed: false`，且自述「a job has to run to verify engines and output」。
- **输出种类由 worker 写入**（非固定枚举）；实测该 PDF 作业只有 `text`（`location`/`pages`/`loss` 等均 404）。
- **`job kind` = 能力前缀**：`pdf` → `pdf.extract`；`office` → `office.structure`；`canvas` → `canvas.structure`。

**完整作业流程（实测可用）**
```
POST /api/v1/imports          {"name":"x.pdf","content_base64":"<b64>"}   → 202 {source_id, sha256}
POST /api/v1/jobs             {"job_id":"pdf-<run>","kind":"pdf","input_ref":"<source_id>"} → 202 queued
POST /api/v1/jobs/<id>/executions  header: idempotency-key: exec-<run>   body: {"deadline_ms":180000} → 202 running
GET  /api/v1/jobs/<id>        → 轮询到 state ∈ {succeeded,failed,cancelled}
GET  /api/v1/jobs/<id>/outputs/text  → 200 正文
GET  /api/v1/jobs/<id>/quality       → 引擎身份与损失
```
**禁止手工 `UPDATE jobs.state`。** 若遇 409 `AAK-CON-003`，读状态机与既有测试，不要靠改请求字段猜。

**运行环境的三条硬要求**
1. **必须用全新数据根。** Core **打不开旧 Python 库**：它读 `workspace_meta.schema_version`，
   而旧库是 98 表的 Python schema（`user_version=0`、`journal_mode=delete`、**无 `workspace_meta`**）。
2. **构建 target 必须先清资源目录再重建。** `--no-bundle` **不清理** `CARGO_TARGET_DIR/release/`，
   而 `runtime.rs` **优先选 nested** ⇒ **残留的陈旧嵌套解释器会静默胜出**，表现为莫名失败。
3. **`tauri build` 需要 `npm` 在 PATH**（`beforeBuildCommand` 是 `npm --prefix ../frontend run build`）。
   跳过前端可用：`cargo-tauri build --no-bundle --config "{\"build\":{\"beforeBuildCommand\":\"\"}}"`
   （前提是前端已构建）。

**本机可用的验证入口**
```
Rust 单测（恢复壳）  cd desktop/src-tauri && cargo test --lib backend::     （13 项，MSVC）
多格式抽取测试       <EXT>\...\ci-venv\Scripts\python.exe -m pytest tests/test_multiformat_extraction.py -q  （6 项）
仓库规范门禁         python -B scripts/check_repository_conventions.py --source head
架构门禁             python -B scripts/check_architecture.py
```

---

## 9 已确证的实测结果（可直接复用，**但不得扩大范围**）

**通过**（同一权威候选、全新数据根、声明 worker）：

| 格式 | kind | quality.engine | loss | coverage |
| --- | --- | --- | --- | --- |
| 文本 | text | python-worker-text | 0 | 1.0 |
| Word/docx | office | python-worker-office | 1 | 1.0 |
| HTML | html | python-worker-html | 1 | 1.0 |
| 音频 wav | media | python-worker-media | 1 | 1.0 |
| 视频 mp4 | media | python-worker-media | 1 | 1.0 |
| Canvas | canvas | python-worker-canvas | 1 | 1.0 |
| ZIP | archive | python-worker-archive | 0 | 1.0 |
| SRT | subtitles | python-worker-subtitles | 1 | 1.0 |
| **PDF** | pdf | **pymupdf-native-pdf** | **1** | **1.0**（covered 6/6, pages 1） |

**⚠️ 范围限制（审计裁定，必须遵守）**：
- **音频/视频只是 `media.probe` 头信息探测通过**，**不计作解码、转写或时间段证据闭环**；
  `coverage:1.0` 是**事实列表行锚点覆盖**，**不是媒体内容全覆盖**。
- **「worker 与管线正确」这个说法收窄了**：缺依赖报错只证明失败被报告，**不能证明未执行的路径正确**。

**PDF 六项判据全部成立**（sha256 `0f0ffc50c79d9d977efb925351ca1d64a063184e4bdd71507b9ac44992f7adcf` ·
`succeeded` attempt 1 · 正文 `"Golden Journey Evidence\nOriginal SHA and anchored conversion\nCriterion\nVerified\nPage Anchor\nPASS\n"` ·
引擎身份 · 定位与损失 · 重启读回）。

**失败 3 种**（错误码均 `AAK-WORKER-003`）：
```
xlsx → "xlsx engine missing (openpyxl not installed)"
pptx → "pptx engine missing (python-pptx not installed)"
png  → "tesseract binary not found on PATH (OCR engine unavailable)"
```

**已实测的解释器事实**（`-I` 隔离模式）：
```
aaos-cand1\runtime\python.exe                 openpyxl=false  pptx=false  tesseract=null
aaos-msvc-target\release\runtime\python.exe   openpyxl=false  pptx=false  tesseract=null
runtime\Lib\venv\scripts\nt\python.exe        "No pyvenv.cfg file"
```
**⚠️ 审计已撤回我此前两项推断，不要再犯：**
1. **扫描两个解释器失败不足以确认宿主实际选了哪一个** —— 必须从宿主启动路径与契约确定；
2. **实际导入失败不足以推出「搜索同名目录」的断言一定失败**，也不能据此宣布不存在假通过风险；
3. **不得仅凭 `No pyvenv.cfg file` 判定该 venv 启动器损坏** —— 先核对 Python 版本与官方 venv 实现，
   那可能是正常的启动器模板；**只有产品错误地选它作运行解释器，才按真实启动路径缺陷处理**。

**OCR 的定性（已查证）**：引擎 `tesseract.exe` 与语言数据 `*.traineddata` **都已在共享库**；
`services/python-workers/vision/worker_ocr.py` 的 `_usable_tessdata()` **已主动防住**
「环境里 `TESSDATA_PREFIX` 指向别处」的陷阱。⇒ **缺的是「指向」，不是引擎。**
**`tesseract` 必须按外部可执行引擎验证**（解析路径、版本、语言数据、OCR 样本），
**不得用 Python 模块查找结果代替。**

---

## 10 现行任务表中的实际缺口

| 编号/事项 | 状态 |
| --- | --- |
| **§5 阻断项**（资源表 vs 流水线） | **必须最先修**，否则所有 CI 验收必红 |
| **Q04** 原件/Document-Block/CAS/草稿保存与恢复一致性 | **完成状态已撤销**，未做 |
| **Q12** B 波次（CSV/TSV、JSON/JSONL、YAML/TOML/XML、EPUB、EML） | **未开始**（**不得写「同 Q06」代替验收**） |
| **Q14** Windows 安装态资格化 | **NOT_RUN** |
| **XLSX/PPTX 真实闭环** | 未完成（先修依赖安装/运行时选择） |
| **引擎断言强化** | 未完成 —— 须改为**由实际产品运行时执行真实 import**，输出模块路径与版本，**失败返回非零退出码**；不得只搜索目录名或只用 `find_spec` |
| **迁移路径**（旧库 `workspace_meta`） | **待用户拍板**（迁移 vs 只读接入） |
| **§六 合并**（三个暂存器形态不一致） | 已出可审查清单，**待做** |
| **§六 冻结** | 未做（**Tauri 尚未达到可冻结 Avalonia/旧 Python 入口的门槛**） |
| **依赖安装链排查** | 未做 —— **不要重复增加依赖声明**（锁里已有）；沿实际构建链查：依赖是否装上 → 装到哪个解释器 → 该运行时是否进产物 → 宿主是否启动同一解释器 |

---

## 11 执行纪律（这些是本会话用代价换来的）

**CI 操作**
1. **等待运行期间绝不推送** —— 该分支 `cancel-in-progress: true`，**推送即取消**。本会话因此失败五次。
2. **不要为了触发门禁而提交文档或无关文件。** 需要重跑时用 `gh run rerun <id>`（无需推送）；
   已被重跑过的运行会被服务拒绝（`cannot be retried`）。
3. **watcher 必须绑定完整 SHA + workflow + run ID + attempt**；用 `--commit` 定位、**持有 run ID** 持续监视；
   **不要用 `--limit 3` 的最新窗口推断目标**（本会话因此写出两个 0 字节文件）；
   **采集失败必须显式报错；0 字节文件不算证据**；cancelled/skipped/failure/success 分别登记；
   **只有目标断言实际执行且成功，才能登记通过**。
4. **固定提交后用 `workflow_dispatch(force_full)`** 跑完整门禁，并核对运行的 `headSha` 与固定提交一致。

**诊断方式**
5. **让失败者自己说话，再提假设。** 本会话连做六个错误假设（cwd / text_worker 形状 / Job / env / 新数据根 / 陈旧嵌套），
   全错；**加了「失败时把 Core 输出与启动文档落盘」的诊断后，一眼看到 `\\?\` 前缀**。
6. **同一失败最多两次有明确假设变化的尝试**；仍失败就保留原始输出、换排查路径，**不要重复同一命令同一结论**。
7. **路径用工具返回值**，不要在 PowerShell 里切字符串；**搜索限定在相关目录**，不要在仓库根递归 glob
   （会撞 ACL 边界并返回全零）；**结构化输出先写完整文件再解析**，避免截断。
8. **推断必须标注为推断**，不得写成已验证事实。
9. **核查优先**：本会话多次因「从旧状态推断」而错（陈旧嵌套解释器、`--limit 3` 的 watcher、只看跳过的门禁就宣布绿）。

**范围纪律**
10. **不新增审计编号、不建第二份状态真值、不写「关于更正的更正」文档。**
11. **当前主表只能有一个有效状态**；历史证据留在 Git 历史、原始回执或明确标识的历史区。
12. **交付物优先是可观测变化**：查实一个根因、修一处实现、完成一次有效运行、落定一个工程决定。

---

## 12 建议的执行顺序

1. **复核起始状态**（§1），读 `01_完整执行任务书.md` 与 `desktop/scripts/prepare_bundle.py`、
   `scripts/release/stage_backend_runtime.py`。
2. **修 §5 阻断项**：让 `prepare_bundle` 产出的 runtime 能被权威暂存器接受 → 用权威暂存器统一产出候选 →
   **让 `desktop-fast` 与 `desktop-build` 用同一套准备步骤**。
3. **本地验证**：`cargo build`/`cargo test` 在 `src-tauri` 能过（资源路径存在即不再报 `custom build command` 失败）。
4. **强化引擎断言**：改为**由实际产品运行时执行真实 import**，输出模块路径与版本，失败非零退出。
5. **修依赖安装链**（§10），再用 XLSX/PPTX 样本走完整真实链路：
   导入 → job → worker → Core 持久化 → 重启读回；验证已知工作表/单元格与已知页/文本、锚点、损失、错误状态。
6. **诊断 `desktop-fast` 是否还有第二层失败**（当前只看到 `tauri-build` 这一层）。
7. **固定一个提交 SHA** → `workflow_dispatch(force_full)` → **核对 headSha** → **期间停止推送** →
   按 §11.3 登记该 run 的 ID/attempt 与目标步骤结果。
8. **按现行任务表登记真实剩余缺口**，并继续在授权内推进合并/清理/冻结。

---

## 13 最终回报格式（用户要求）

1. **修复了什么**，对应提交 SHA；
2. **使用哪个候选、解释器和锁文件**；
3. **哪些真实样本通过，哪些失败**；
4. **固定 SHA 对应的 CI run ID、attempt 和目标步骤结果**；
5. **现行任务表中的实际剩余缺口**。

---

## 14 本会话产出的记录（如需背景）

均在 `docs/current/`，**自包含**，但**多数是中间过程记录**：
```
AAOS01-AUDIT-CORRECTIONS-20261005.md            ← 审计更正总表（自包含，最值得先读）
AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md         ← 台账（含更正段）
AAOS01-Q06-PDF-SLICE-SIX-CRITERIA-PASS-20261005.md
AAOS01-MULTIFORMAT-ELEVEN-FORMAT-MATRIX-20261005.md
AAOS01-MULTIFORMAT-THE-THREE-FAILURES-ARE-MISSING-ENGINES-20261005.md
AAOS01-OCR-NEEDS-A-POINTER-NOT-AN-ENGINE-20261005.md
AAOS01-THE-CORE-CANNOT-OPEN-THE-LEGACY-DATABASE.md
AAOS01-THE-CI-CANDIDATE-IS-MISSING-ITS-ROOT-FILES.md
AAOS01-Q02-THE-SHELL-CANNOT-REACH-CORE-READINESS.md
AAOS01-MERGE-REVIEW-reject-reparse.md
AAOS01-BLOCKED-ENGINE-ASSERTION-VERDICT-20261005.md
AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md
AAOS01-RECORD-INDEX-AND-THE-SURPLUS-20261005.md
AAOS01-RECORD-CONSOLIDATION-REVIEW-20261005.md
AAOS01-STEP2-INTERPRETER-IMPORT-EVIDENCE-20261005.md
```

**⚠️ 已知记录债务**：`docs/current/` 下有 **173 个 `AAOS01-*` 记录**，其中 **47 个 `AAOS01-Q02-*` 是逐轮叙述且成对矛盾**
（如 `HYPOTHESIS-CONFIRMED` 与 `HYPOTHESIS-REFUTED` 并存）。**读者无法据此判断当前真相。**
**这是纠偏指令禁止的「文档随每轮产生」。** 归并方案见 `AAOS01-RECORD-CONSOLIDATION-REVIEW-20261005.md`；
**最低成本做法：给每份加一行 `superseded-by:` 头**（比删除安全，比现状有用）。**未执行。**
