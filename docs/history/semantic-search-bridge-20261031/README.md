# semantic_search 有限后端桥接合同

本历史只记录正式 Tauri CoreOperation/API 边界的接通与无界面合同验证。当前状态仍导航[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。UI 实施暂停没有解除；无组件、页面、布局或自动调用触发变更。

## 行为与权限

新增唯一 `semantic_search` operation，固定 POST `/api/v1/search/semantic`；严格接收 `payload.body.q`（非空、最多 2048 Unicode scalar），拒绝 model、endpoint、corpus、token、method 等额外字段。沿既有 host 保管凭据、loopback、禁代理/重定向机制；不授予新模型配置或数据外发权限。Core 90 秒整体时限之外，桥接等待上限 135 秒；不自动重试，FTS search 保持原行为。

响应保持 AVAILABLE / PARTIAL / UNAVAILABLE / EMPTY；HTTP 200 不等于完整排名。DTO/API 边界核查询回显、候选数量、知识/版本/来源身份、排名重复/有限分数、完整状态及批次覆盖，保留 index_persisted=false。HTTP 拒绝保留状态码和安全提示，不向用户展示原始 worker/private 诊断。没有新 DB、Runtime、API 路由或向量索引。

三个 vault operation 均未开放。此前 vault 反斜杠分类问题另有独立修复/验证分支，不由本记录宣称安全；vault links record 外部 Markdown 替换图的权利也未授予。

## 当前源码实际验证

HEAD `e792dadc062033a93914b433278cd1a41b6d368b`，稳定 dirty=true；完整未提交 patch SHA-256 `6ee00f37206a138433014e683efa4bed72c2ade0c3c48b54dc175897d970bf55`。本 patch 含 root 协调的其他独立改动，本记录仅认领 manifest 列出的 semantic 文件与配套 live 合同引用同步。正式 bridge SHA-256 `58ade206feb1bb7c184d12dbfe4450065ebd448d618374fc1316d1a258d6caf7`。

- `bkr-semhead2`：实际 rustc 1.97.1 (8bab26f4f 2026-07-14)，直接 `--test` 编译正式 `src-tauri/src/core_bridge.rs`；compile exit 0。两个 `tests::semantic_search_*` 精确过滤各 1 passed，其他 34 项过滤，不执行模块内 HTTP 测试。
- `bkr-semrepo2`：实际仓库 Schema 3 + capability contracts 127 = 130 passed；正常 Vite 配置及 manifest 门禁下 CoreBridge 62 passed；scoped TypeScript noEmit 0 diagnostics（290 个依赖源码）。无源码 overlay，不替代全前端类型/构建资格。
- 上述两 run actual/wrapper 均 0、source_consistent=true、dirty=true，绑定同一 patch；不是 clean commit 资格。

headless 复用 Host release 的 serde 1.0.228 / serde_json 1.0.149 / reqwest 0.13.4 / url 2.5.8 / getrandom 0.3.4，以及 root 明确授权的 Core debug tempfile 3.27.0（仅测试编译）。六个 rlib 的路径、feature、SHA 及前后相等证据见 MANIFEST 与 headless-result。**正式 Host 仍锁 tempfile 3.26.0；没有验证 Host 原 Cargo 依赖图或构建 Tauri/bin。** 没有 Cargo fallback、依赖下载、升级或全局设置变化。

测试 exe 3,601,408 B，SHA `8af3c134c08a81c931b82c81249c2eae21663547d8839dcd8058353f785d2996`；PDB 5,017,600 B；四份日志 578 B；这组输出共 8,619,586 logical B。未复制输入载荷；六个直接 rlib 前后 SHA 相同。物理分配未测，共享 cache 全量增量未测（同期 root 另有 Core 合同编译），不得推成共享 cache 总变化为零。

## 保留失败与修正

- `bkr-semseal1`：新增 TypeScript 测试访问 unknown error.message，类型检查失败；后继加 ApiError 类型守卫，原失败保留。
- `bkr-semhead1`：首次直接编译遗漏 getrandom，且 Host tempfile 3.26 缓存的传递依赖不可解析；compile exit 1，无测试执行。后继补精确 Host getrandom，并经 root 授权只在测试程序使用现存 Core tempfile 3.27；没有删除旧测试或 stub 替代。
- `bkr-semrepo1`：Schema 3 passed 和 scoped noEmit 通过，但正常 Vite 因 live pdf-extract manifest 三处旧 schema SHA 而在测试前失败。root 同步三个引用及 capability cases 中 153 个同路径 SHA，并再生现有 projection 后，`bkr-semrepo2` 正常门禁及全部上述检查通过。历史冻结快照不重签。

## 未验证

全部资料为合成合同输入/模拟 native 响应。真实 Core HTTP 调用 0、模型调用 0、VM 0；没有 Tauri 应用构建、UI 渲染或安装。未验证 semantic 模型可用性、检索质量、多语言/大库表现、用户实际旅程或同安装候选闭环。候选合同通过不能替代真实 semantic 效果，CL/F05 整体未因此完成。
