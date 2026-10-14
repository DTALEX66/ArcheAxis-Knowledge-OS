# AAOS GitHub 与项目优化方案 — 2026-10-14

来源：Owner 在当前会话提供的优化方案。观察基线 main `c541ed8315e54aaa111da64ba79c95cad19b408d`。下列观察为输入方案的 dated 记录；执行时必须重新核实，不构成当前性能测量或已完成回执。

## 执行顺序与边界

先完成当前已经启动的功能整合、CI 修复及授权上传。本方案 A01～A04 作为下一批单独隔离分支、一个 writer；先形成可审阅 diff 和真实验证。此方案不自动授权推送、合并、发布或 GitHub ruleset 修改。A05～A08 等阶段数据可用后实施；A09 先采样；A10 精简而保留边界。

正式宿主仍为 frontend + src-tauri；Rust Core 是唯一 SQLite/CAS 写入者。保留保存、恢复、exact-SHA 汇总、安装资格、现有 a0-gates、quick/full 与 GatePlan。不得覆盖 Green、真实用户数据库或知识状态。禁止 E/F 和无关系统操作。每批一个可回退提交，缓存只失效自己的新 key，不清空其他任务状态。

## 输入观察（待执行前核实）

- 最近 PR 总耗时 23分15秒；desktop-build 16分02秒之后 installer-lifecycle 串行 6分22秒。优化最长串行链。
- dev.environment 导出 CARGO_HOME 为 .project-local/cache/cargo；两个手写 cache 却保存 ~/.cargo/bin、registry、git。cargo-audit 预检 $HOME/.cargo/bin 与实际安装根不同。
- 手写 key 主要使用 src-tauri/Cargo.lock；root Core 是另一 workspace/lockfile。依赖恢复和可变构建输出必须分开测。
- frontend build 已执行 tsc --noEmit 再 Vite，不另装类型检查器。
- stage_runtime.py 复制 sys.base_prefix 整个 Python 安装，排除 site-packages/bytecode 等，须量化复制成本和实际需要。
- build.rs 监听前端产物整树、ARCHEAXIS_FRONTEND_DIST、TAURI_CONFIG；路径变化可能触发重编译，资源正确嵌入保护必须保留。
- SQLite writer 已有64有界队列、独立线程、with_store submit，不能多连接写入提速。
- 输入观察 main ruleset 要求 a0-gates、strict=false、有 always bypass RepositoryRole actor；平台规则不等于精确版本资格。设置调整是独立任务。

日志来源：[最近 PR](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/38487686931)、[成功样本](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/38268676998)。源记录称未修改远端配置或源码。

## 去重后的任务队列

全部状态为 NOT_EXECUTED；当前 CI 缺 layout 路由与61/59计数反例的修复属于在途功能验收，不能冒充本方案性能优化已完成。

| ID | 优先级 | 实施与验收 |
| --- | --- | --- |
| A01 | P0 | ci.yml/dev.py 初始化后输出非敏感有效路径；手写 cache 保存实际 CARGO_HOME 子目录；分别管理 root Core/Tauri target；cargo-audit 预检实际安装根。记录冷/热 path、key、restore秒数、编译秒数；真实下载目录命中，工具不因错根反复安装。 |
| A02 | P0 | key 纳入 rustc身份、OS/target、两个锁文件、.cargo/config、features；依赖和可变产物分离，避免同key永远首次输出。身份变化产生可解释新key；旧key恢复后仍编译当前源码；不缓存运行数据/资格回执。 |
| A03 | P0 | 在已有 quick/preflight 提前接路由文档、挂载库存、生成合同，重构建依赖此前置检查。61/59和缺layout反例在编译前失败，保留精确断言，不换任意数量。 |
| A04 | P0 | prepare_bundle.py/stage_runtime.py/ci.yml 分别计时 Python复制、依赖导出、依赖安装、wheel构建、wheel安装、Core编译、Tauri编译、NSIS压缩。成功失败都保存时间，8分07秒Tauri步骤拆到内部，不全叫Rust编译。 |
| A05 | P1 | Python版本、uv.lock、ABI、平台缓存不可变基础环境；每次重新安装当前wheel并组装当前Core/worker，候选SHA/tree绑定。改变Python源码后包内读回新源码；离线安装与恢复通过。 |
| A06 | P1 待测 | 同一run复用已验证前端；记录Cargo重建原因，研究稳定内容寻址与run隔离；保留 rerun-if 监听。CSS/JS/合同变更嵌入必更新，相同内容成本对比，并发不串产物。 |
| A07 | P1 | pytest --durations/JUnit；Rust build/test 分开计时。仅先试纯合同/纯计算分片；OCR/ASR/恢复/端口/状态明确隔离。测试ID全集无遗漏，失败传播，无共享污染，禁止无限并发。 |
| A08 | P1 | project-validation/ci 维护变更→消费者→资格映射；共享合同覆盖TS/Rust/Python及所需C#；安装候选才完成安装验收。未知路径阻断并分类，混合变更不漏消费者；ci.yml变更仍触发安装链。 |
| A09 | P2 待测 | writer/API/App 采样队列等待、执行时间、Busy、大列表、首屏/切页/大文档；EXPLAIN QUERY PLAN后才补索引/游标。100/1000/10000条合成数据记录p50/p95；单写者、事务/CAS保留，普通保存不增加云检查。 |
| A10 | P2 | 根AGENTS仅保留当前宿主、入口、边界、命令、活动指针；历史按需读取；修旧WORK-LAB 00-governance引用。本地独立工作不因外部探测阻断；旧证据不重写。 |

## 缓存核对与完成标准

Cargo registry/git/bin 使用 environment 的 CARGO_HOME；root Core 使用 CARGO_TARGET_DIR；Tauri 包装入口路由 .project-local/build/tauri，须核对 profile/输入；uv 使用 UV_CACHE_DIR，不能因清单有 uv-desktop 就当作 setup-uv 已覆盖。

rust-cache 保留依赖产物、清除 workspace 自有/incremental；命中后当前项目重新编译是正常现象。不能缓存上次 PASS 来跳过源码验证。

本地先已有 quick 和两项 maintenance；完整安装资格用分支真实候选 CI。冷/热阶段实测，不仅声称变快。最后对文档、前端、共享合同/Rust、安装候选四类变更记录选中检查。bundle 无法证明新源码进入安装包则回退组装路径。

参考：[Cargo cache](https://doc.rust-lang.org/cargo/reference/build-cache.html)、[build.rs](https://doc.rust-lang.org/cargo/reference/build-scripts.html#change-detection)、[rust-cache](https://github.com/Swatinem/rust-cache)、[uv Actions](https://docs.astral.sh/uv/guides/integration/github/)。
