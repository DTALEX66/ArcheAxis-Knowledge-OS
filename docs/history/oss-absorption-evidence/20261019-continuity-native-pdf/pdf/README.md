# PDF 实际依赖观察、运行准入与版本回执候选

状态：FROZEN_PROPOSAL_NOT_APPLIED。公共产品树由 root 独占写入，本目录只保存隔离候选和验证；`CURRENT.json` 是机器入口。`MANIFEST.json` 的 18 项含 17 个 APPLY_EXACT_BYTES 和 1 个 REGENERATE_AFTER_SCHEMA_MERGE。完整前后原字节 SHA 在 manifest，原件在 preimages/，候选在 proposal/，验证镜像在 mirror/。

实际问题与修复：原 PDF hello 没有实际导入引擎，缺依赖也会声称可握手；worker 与 Core ENGINE_PROFILES 同时把 `pymupdf` 当作版本。候选复用现有 worker/NDJSON/Core attempts 和质量回执，不建立第二注册器，不使用 capability-package manifest 的许可证登记阻断已有 PDF 必需路径。

- PDF hello 只导入加载中的 `pymupdf`（兼容 `fitz` 别名），验证 callable open 与模块实际版本，明确 AVAILABLE / MISSING / IMPORT_FAILED / VERSION_UNKNOWN。不会打开 PDF、执行模型或宣称完整引擎资格。
- Core 在发送任务正文前要求当前 PDF hello 的实际依赖观察。逐文件产物版本、依赖观察必须与同一进程 hello 完全一致，错配拒绝且不提交产物。
- Core 对新 PDF 回执使用真实版本格式，不能继续接收恒字符串版本。历史 `pymupdf` 假版本回执的提取/预览资格降为 UNVERIFIED，但不修改历史行、原回执、成功执行状态、原件引用或原件导出。
- 静态 operation_readiness 保持不 spawn、不探测模型；PDF 文件存在只说明可进一步观察，dependencies 明确 UNKNOWN。显式 admission 可以进行当前受限 hello，再由实际 executor 再次核验。权限禁用仍先拒绝。实际 React DOM 与 API 正向回归证明静态 UNKNOWN 不切断既有入口和 PDF 执行。
- Schema、Rust 与 Python 同时拒绝版本末换行与 64 字符加换行（maxLength64、绝对结尾），未放宽 Rust 标准。

最终证据（FINAL-VERIFICATION.json）：协议 Rust 6 PASS；应用 Rust 14 PASS；API Rust 5 PASS；新 Python 7 PASS；既有 PDF/共享 transport Python 42 PASS 与 47 子测试 PASS；真实 React 组件 DOM 3 PASS；TypeScript noEmit PASS。受控原生 PDF 引擎实际执行使用项目已有 PyMuPDF 1.28.2；没有安装、升级、模型调用、服务、浏览器、宿主/已安装应用、发布或 Owner 验收。public source_consistent=true 只覆盖本次精确候选与 BE10 14 个当前基线，不是整仓完整 canonical wrapper。

原实现 RED：保存的 baseline 原 worker/transport/schema 和原六项行为用例，5 FAIL + 1 ERROR，完整 stdout/stderr 见 verification.json 的 red 路径。第七用例是交叉审阅后加入的 schema/Rust/Python 共同边界回归。原始应用集成失败揭示 Core 固定版本兼容问题；该早期 raw log 在封存前被覆盖，仅保留明确标注的工具读回片段，未把片段称完整日志。早期 API 编译失败、补丁新文件头失败也保留，最终均已修正。后续日志均带唯一时点，不覆盖。

复现命令（在仓库根目录使用现有 .venv，不装任何包）：

```powershell
.venv\Scripts\python.exe .project-local/audits/pdf-readiness-runtime-20261019/run_checks.py red
# 上条预期退出 1，原实现确实错误
.venv\Scripts\python.exe .project-local/audits/pdf-readiness-runtime-20261019/final_checks.py
# 上条预期退出 0；只使用隔离镜像/自有 target 和现有项目依赖
```

注意：runner 复现会新增本目录日志与重写运行回执；封存的 CURRENT / MANIFEST / patch / verification 不应再次发布或重写。已有 FINAL-VERIFICATION 是本次固定候选的通过证据，复现请复制 runner/回执到后继隔离目录保留本轮封存结果。

串行应用：先验证 CURRENT→MANIFEST→17 个精确 preimage，再应用 proposed-core.patch 或精确候选字节。`git apply --check --ignore-space-change` 已通过。root 应跳过 core-contract.ts 的旧直接复制，合并当前 core-command.schema.json（含 BE10 project_handoff_preview）与本候选 core-document.schema.json 后，用原 generate_core_document.py 再生；本目录 generated-core-contract.advisory.patch 仅作预期 delta。镜像生成物已含当前 BE10 新 op。最终 root 统一 rustfmt、重生与源绑定后，哈希可合法变化，应另记录，不修改本轮 manifest。

公共生成链后续：core-contract.ts 的新 raw identity 会使 current qualification/resource-catalog 的当前来源绑定待更新；应由 root 在合并后的真实源生成链上刷新绑定，不更改历史冻结资格、许可、安装或执行状态来追绿。HUB004 通用包安装/更新/回退仍未由本候选实现；已有 PDF 的实际依赖准入闭环不等于通用安装器或整个能力中心完成。
