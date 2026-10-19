# 应用前阻断补充（不改冻结12候选）

冻结候选的定向隔离验证为PASS；整体正式接入仍BLOCKED，不能仅以git apply --check0视作可完成应用。

- P1：新增src-tauri/tests/project_handoff_preview.rs要求BE10_PREVIEW_CORE。现行.github/workflows/ci.yml:1079、1248在src-tauri直接cargo test而未提供此值，故会导致现行CI失败。1070左右前一步构建了release Core，但随后切换CARGO_TARGET_DIR；不能猜默认debug路径或skip。最小修正可由root选择：把真实native test留为audit-only probe（不新增正式src-tauri测试文件），由显式canonical证据命令运行；或将正式runner/CI显式指向刚构建Core产物，且不使用用户服务。本候选未擅自扩大CI修改范围。
- P2：.github/workflows/ci.yml:1077运行cargo fmt --all -- --check。当前新增Rust存在compact格式，未运行正式rustfmt门禁；root应用前需对切片相关Rust做格式化并以新源码hash复验。不应继承冻结候选的旧after hash为格式化后资格。

本补充写于最终候选封口之后，不修改原12文件/patch/manifest/validation；root仍唯一产品writer。实际外部UI/native/正文snapshot接线与OS URI依然NEXT，不因修复以上门禁宣称BE10完成。
