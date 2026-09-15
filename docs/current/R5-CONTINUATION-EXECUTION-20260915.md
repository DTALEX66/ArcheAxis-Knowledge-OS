# R5 连续执行收据：Task 0 基线与候选修复裁决（2026-09-15）

## 基线

- 项目：ArcheAxis-Knowledge-OS
- 分支：`codex/full-loop-0906`
- HEAD：`0dd8ff37b670ae98fac4be35720194434e82191e`
- 远端基线：`0dd8ff37b670ae98fac4be35720194434e82191e`
- 工作树既有未跟踪路径：`docs/current/SESSION-RESTART-2026-09-12.md`、`docs/history/` 迁移资产；本任务不纳入。
- 候选补丁：`ArcheAxis-first-use-fixes.patch`
- 候选补丁 SHA-256：`f20a8616de14b6a08f2d25b009c460ed734d4d771b83c20335d1365b2cd111d7`
- `git apply --check`：PASS（未修改当前树）。
- 执行预检：PASS；使用项目缓存解释器 3.13.14，542 个 Markdown 链接无断链，2 个夹具预期缺失。

## 逐文件裁决

| 文件 | 裁决 | 理由 |
| --- | --- | --- |
| `.github/workflows/ci.yml` | ADOPT | 补全历史 checkout；与 R5 CI 止错一致，需远端同 SHA 验证 |
| `AGENTS.md` | ADOPT | 修正当前入口与首次闭环边界；保留安全边界 |
| `Cargo.toml` | ADOPT | 明确 legacy Tauri 排除，保持 Avalonia/Rust 正式链 |
| `LESSONS_LEARNED.md` | ADOPT | 记录可复现的首次使用失败边界 |
| `docs/current/R5-DESKTOP-START.md` | ADOPT | 补充稳定 TEST 启动说明 |
| `docs/current/R5-EXECUTION.md` | ADOPT | 追加本轮证据索引；不替代冻结任务包 |
| `docs/current/R5-FIRST-USE-REPAIR-20260915.md` | ADOPT | 新增修复说明与限制 |
| `docs/current/R5-STATE.json` | ADOPT-WITH-REVIEW | 仅接受与实际测试一致的状态变更，逐项复核后保留 |
| `scripts/launch/desktop_launch.py` | ADOPT | 稳定 TEST workspace 与显式 fresh 隔离 |
| `scripts/maintenance/bulk_fixture_factory.py` | ADOPT | 根内绝对路径和完整输出路径安全校验 |
| `scripts/probes/r10_host_panel_smoke.py` | ADOPT | 移除空库自动学习假成功 |
| `shared/core_client.py` | ADOPT | 空结果不再写入学习/引用或自动答对 |
| `tests/maintenance/test_bulk_fixture_factory.py` | ADOPT | 覆盖越界与目录链接回归 |
| `tests/test_core_client.py` | ADOPT | 覆盖 adapter probe 与闭环标记 |
| `tests/test_desktop_launch.py` | ADOPT | 覆盖稳定 workspace / fresh workspace |

## 执行边界

本收据先记录裁决和基线；后续应用补丁必须逐文件检查 diff，运行 Task 1–3 的定向测试。若测试显示候选与当前正式架构冲突，使用单文件回退或 `git revert`，不覆盖用户数据、不删除 TEST 库。

包内 68c81a39 的测试只对其原环境和 SHA 有效；本次会重新绑定当前提交和实际命令。远端 CI、Windows GUI、Green、真实资料和 Q00/Q01 仍未通过。

## Task 1–2 本地复核

- `tests/test_core_client.py`、`tests/test_desktop_launch.py`、`tests/maintenance/test_bulk_fixture_factory.py`：26 passed、2 skipped。
- CI/发布/预检相关测试：104 passed。
- Core/桌面运行时/fixture 组合：50 passed、2 skipped。
- `scripts/check_repository_conventions.py --source worktree`：PASS。
- `scripts/check_path_conventions.py`：2019/2019 tracked paths owned，0 unowned，0 ambiguous。
- 本机未发现 `cargo`、`dotnet`、`rustc`；Rust/C# 构建和 Windows GUI 验证为 NOT RUN，需 Windows/CI runner。
- 当前实现提交：`19f9ac1a28917fd670ada214ca6260013f2ecf98`；远端同名分支已回读同 SHA。

## Task 8 模型外置接线

- `shared/file_detection.py` 现优先读取 `ARCHEAXIS_MAGIKA_MODEL_DIR` 中同时存在的 `model.onnx` 与 `config.min.json`；外置目录不可用时回退仓库副本，保留离线能力。
- `config/environment/capability-requirements.yaml` 与 `docs/environment/EXTERNAL_DEPENDENCIES.md` 已同步声明该优先级。
- `tests/test_file_detection.py`、`tests/test_capabilities.py`、`tests/test_mfx010_honest_capability.py` 与环境注册测试：21 passed（1 个既有警告）。
- 本次未读取或修改 `D:\\All projects\\Model library`；外置消费者和实际 Windows profile 仍需在 Task 7/8 的 Windows 验收中核实，故未删除仓库副本。

## 外置工具链与 Rust/桌面实测

- `D:\\All projects\\Model library` 顶层存在 `ComfyUI`、`ollama`、`sherpa-onnx`、`whisper` 四类模型/软件目录；未递归读取内容。
- `OS External Configuration\\10-toolchains` 实体版本探测：Cargo/Rust `1.97.1`、.NET `10.0.400`、Tesseract `5.5.0` + Leptonica `1.85.0`、FFmpeg `8.1.2`；MSVC linker 与 `vcvars64.bat` 存在。
- 使用外置 .NET 构建 `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj`：0 errors，2 warnings（NuGet vulnerability feed unavailable、Avalonia Watermark obsolete）。
- 通过 `scripts/runtime/dev.py` 注入项目 run root、Python、Rust 与 MSVC 环境后，`cargo test -p archeaxis-api --tests` 全部通过；包含 API、学习状态、机器纠错、运行时作业和 v0.1 journey 用例。编译警告保留，未修改为静默。
- 当前 registry 的 PATH 探测仍会把未加入 PATH 的 Rust/.NET/MSVC 记为 missing；这是探测器局限，不代表外置实体不存在。正式 Windows profile 仍需把绝对路径绑定并做安装包验收。

## 增量复核：外置库对应关系与完整 Rust 验证

- 只读复核确认 `D:\All projects\Model library` 存在 `ollama`、`sherpa-onnx`、`whisper`、`ComfyUI`；`D:\All projects\OS External Configuration\10-toolchains` 存在 DeepTutor 1.5.17、.NET 10.0.400、Cargo/Rust 1.97.1、MSVC、Tesseract 5.5.0、FFmpeg 8.1.2 及其共享工具目录。五个外置根均为普通目录且未发现 reparse point。
- 已核对的旧 `project-tool-index.yaml` 可用，但仍漏登正式 .NET、DeepTutor、Ollama、Sherpa-ONNX、Whisper 与共享 Magika 模型；项目文档已补充当前对应关系。该索引差异是规范化待办，不代表外置软件缺失。
- 使用外置 MSVC、Rust、Tesseract 路径并通过 `scripts/runtime/dev.py` 路由运行目录，`cargo test --workspace` 全部测试组及 doc-tests 通过。首次失败原因为会话 PATH 未注入 Tesseract/MSVC，补齐外置路径后重跑通过；该事实已单独记录，未将环境缺失误报为产品回归。
- 使用外置 .NET 构建 `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --no-restore`：0 errors，2 warnings（NuGet vulnerability feed unavailable、Avalonia `TextBox.Watermark` obsolete）。
- 本节只记录仓库内文档与本地验证；未修改共享外置库、模型库、Green 目录或真实资料库。DeepTutor 宿主挂载、Ollama/Sherpa/Whisper 实链、安装器/签名/干净机和 Q00/Q01 仍未闭环。

## DeepTutor 外置宿主复核

- 使用共享库 `10-toolchains/deeptutor/1.5.17/venv/Scripts/python.exe` 执行
  `scripts/ci/check_deeptutor_notebook.py`；结果为 `UPSTREAM_SERVICE_CUSTODY_PASS`。
- 合成数据覆盖创建笔记、记录写入、导出、进程重启后读取、custody 打包/解包，以及损坏派生索引后的重建；所有写入均路由到项目 `.project-local/runs/.../artifacts/deeptutor-notebook/`。
- 该证据只证明 DeepTutor 外置服务的离线 custody 能力，不能提升为 GUI 可用、Core 权威桥接、模型调用或真实资料学习闭环；R10/R13 仍保持未闭合。

## Windows 外置工具链 Doctor

- 通过 PowerShell 7.6.3、项目 Python 3.13.14，并显式绑定共享 Rust 工具链运行 `scripts/doctor_windows.ps1`：`healthy=true`，Python/Node/Rust/PowerShell 均可见，5 个探测端口可用，项目根与 `.project-local/task-runtime` 可写，访问阻塞项为空。
- 该 Doctor 证明当前开发机的基础工具链和路径布局可用；它不替代安装器、签名、卸载、干净机器或 GUI 验收。
- 对 `Model library/ollama` 进一步检查只发现模型 blob 存储，未发现可执行的 `ollama.exe`，因此 Ollama 服务连通性保持 `NOT RUN`；不能把模型文件存在等同于本地推理服务可用。
- `Model library` 中发现的 `model.onnx` 属于 Sherpa‑ONNX 目录；未发现同时具备 `model.onnx` 与 `config.min.json` 的共享 Magika 目录。Magika 当前实际使用仓库离线副本，避免错误复用音频模型。

## 云端精确 SHA 回读

- `git fetch origin` 后，当前分支 `codex/full-loop-0906` HEAD 与远端分支均为 `ae7796020aaa2d0f24de329e0932a17c36fa4781`；`origin/main` 仍为 `1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`，两者不混称。
- GitHub Actions CI run `34970004760`（head SHA `ae779602...`）为 `completed/success`。该提交仅含文档变更，实际执行 gateplan、lint、a0-gates；产品构建、Rust、Windows、格式、安装器等 job 按路径分类为 skipped，因此不能把该 run 解释为产品全门禁通过。
- 后续收据提交 `f6762ef5...` 的 CI run `34970160009` 同样为 `completed/success`；执行 gateplan、lint、a0-gates，其余产品 job 因文档路径变更 skipped。该状态已绑定到精确 head SHA，不能替代产品门禁。

## 外置引擎格式定向实跑

- 通过共享 Tesseract 5.5.0、语言包、FFmpeg 8.1.2 和项目外部 CI venv，运行 OCR/PDF/Office/DOCX/HTML/媒体/ASR/VAD 及 worker 路由测试：`164 passed, 2 warnings`，退出码 0。
- 运行命令和日志保存在 `.project-local/runs/format-targeted-20260915.log`；未下载或安装依赖，未修改外置库、模型库、Green 或真实资料。
- 该结果证明适配器与 worker 的局部真实执行；不等于完整格式矩阵、真实 Vault 往返、长音频质量、全链路学习或新机器验收完成。

## 外置能力注册器路径修复

- 能力清单新增 `external_paths` 相对路径字段，并登记正式 .NET、Rust、MSVC、Tesseract、Tesseract 语言目录与 FFmpeg 的共享位置。
- 注册器在显式 `ARCHEAXIS_EXTERNAL_ROOT`/`OS_EXTERNAL_CONFIG` 下探测这些路径；支持文件和模型目录，报告仅输出脱敏标签。回归与能力测试 `10 passed`，ruff 通过；实机注册器从原 18 项扩展为 19 项，其中 12 项可见。
- 该修复解决“共享工具已存在但 PATH 探测误报 missing”问题；模型服务、浏览器运行时、真实模型文件和 GUI 仍按各自验收项独立判断。

## 安装/桌面合同定向复核

- 运行桌面 staging、桌面启动、release SBOM/manifest/identity/evidence/architecture 及生命周期合同测试：`61 passed, 2 warnings`，退出码 0。
- 这些测试验证项目内 staging、发布身份和生命周期逻辑；当前仓库的 `scripts/release/candidate.py` 明确生成候选目录/ZIP，不包含安装器、运行时、worker 或卸载器。因此 R13 的真实 NSIS 安装、签名、升级、卸载和干净机验收仍保持未完成。
- `4cf90c54...` 的 GitHub Actions run `34971284974` 已终态 `completed/success`；本次为文档收据变更，lint/gateplan/a0-gates 执行，其余产品 job 按路径规则 skipped。

## 桌面复习来源投影修复

- `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` 的复习队列加载现在同时显示 `next_review` 与 Core `/state` 返回的权威 `knowledge_id` 引用；来源缺失时明确显示“未记录”，不伪造题目正文。
- `tests/test_project_output_routing_contract.py tests/test_desktop_launch.py`：`18 passed`；外置 .NET 10 Avalonia 构建：0 errors、2 warnings（NuGet feed、Watermark 弃用）。
- 该修复补足来源可见性，但题目正文、先修路线、讲回和完整 DeepTutor 默认入口仍未完成，不能提升 G05 为 PASS。

## 首次导入与学习/迁移定向实跑

- 通过项目外部 CI venv 运行首次导入、学习复习、目录续跑、HL01 来源导入、迁移 runner、四库 setup/restart、Core handshake 与 supervisor 测试：`116 passed, 2 warnings`，退出码 0。
- 日志保存在 `.project-local/runs/r5-core-loop-20260915.log`；测试使用隔离临时库和合成 fixture，未触碰 `D:\All projects\资料库`、`D:\All projects\ceshi` 或 Green 真实数据。
- 该结果提升项目内首用闭环与合成迁移的本地证据等级；真实资料库一致快照、附件/关系全量回读、激活和回滚仍未验收。

## 2026-09-15 监控审计材料纳入后续任务

- 用户提供的 `01_审计报告与三项目融入建议.md`、`05_附件完整性与工作簿审计.json`、`06_ArcheAxis_工作区接入交接.md` 已只读核对并按 SHA 登记到 [监控审计任务入口](../../workspace/intake/2026-09-15-monitoring-audit-followup.md)。三份材料均标明自身不是新的权威 TaskPack，也不授予安装、付费、生产替换或仓库修改权限。
- 新入口将研究与模型记录分开，保留 43 条原始任务行作为待去重来源；工作簿边界缺陷（非整数次数、除零、负时长）仅转为待回归任务，不修改原始 XLSX。
- ArcheAxis 后续顺序固定为：命名空间/去重 → 工作簿边界回归 → 引用证据回归 → Green TEST 闭环 → 可选 NeoMME POC → DeepTutor/机器纠错回读 → 独立 Q00/Q01。缺真实资源、宿主或独立证据的项保持 BLOCKED/NOT RUN。
- 本次仅新增任务入口和执行记录；未复制桌面原件、未访问 E: 盘、未读取凭据或私有代理状态，也未改变冻结 TaskPack、R5-STATE 或原始工作簿。
- `MON-AX-01` 已结构化为 [monitoring-task-map.json](../../workspace/intake/2026-09-15-monitoring-task-map.json)：保留研究候选 11、模型记录 17、原始任务行 43 的来源计数，并收敛为 7 条执行轨道；映射文件仅是当前任务侧车，不改变冻结包。

- `MON-AX-02` 原始工作簿只读核对：46,283 bytes，SHA-256 `42528b02714eab50a1f31a7e7f6ae4b03132fe560b885b1bd4da4f5f6b9c42c3` 与审计 JSON 一致；读取到 10 个工作表，计价相关表无数据验证且未保护。该结构证据不等于公式边界回归通过，除零、负时长、非整数次数仍保持待修。

- `MON-AX-02` 新增可重复脚本 `scripts/maintenance/audit_monitoring_workbook.py` 与 3 个定向测试；项目外部 CI Python 下测试 `3 passed`、Ruff 通过。真实桌面原件实跑退出码 0，报告写入 `.project-local/runs/monitoring-audit-20260915/artifacts/monitoring-workbook-structural.json`；状态仍为 `STRUCTURAL_AUDIT_ONLY`，不提升为公式回归完成。
- `MON-AX-04` 复用证据/主张分离回归：grounded answer、证据边界、关系冲突与覆盖率测试合计 `26 passed`，退出码 0；证明局部合同可用，真实资料和模型精度仍未验收。
- `MON-AX-02` 审计报告现额外列出 17 个含除法公式的位置，统一标为未求值且需要边界回归；真实报告已刷新到 `.project-local/runs/monitoring-audit-20260915/artifacts/monitoring-workbook-structural.json`。这只是风险定位，尚未声称公式缺陷已修复。
- `MON-AX-03` 只读元数据复核确认五个指定外置根均存在：`ceshi`、`资料库`、Green、Model library、OS External Configuration；未递归读取内容或私有配置，故仍不能证明 profile、资源绑定或真实导入闭环。
- `MON-AX-03` 在批准测试副本 `ceshi\Obsidian知识库` 上完成 source preflight：22,224 文件、835 目录，退出码 0；未打开/修改源文件，报告位于 `.project-local/runs/monitoring-audit-20260915/artifacts/ceshi-source-preflight.json`。这只是输入前置门禁，不是导入或学习闭环。
- `MON-AX-03` 进一步以隔离输出根转换 3 个 Markdown 样本：3 条记录均 `converted`，每条源/输出 SHA-256 一致，退出码 0；manifest 位于 `.project-local/runs/monitoring-audit-20260915/artifacts/ceshi-import/manifest.jsonl`。仍不等于 Green 真实资料库、全量导入或学习重启验收。
- 同一 manifest 第二次运行读回前 3 条为 `resumed`，再处理下一批 3 条，累计 converted=6；续跑未重复覆盖已完成输出。此为小样本可恢复性证据，不提升 Green/全量/学习验收等级。
