# 本地固定构建包装合同补充

本记录解释已有 Tauri/React Host 与 Rust Core 的本地安装验证工具方向，不建立第二执行队列。实际状态仍读取活动指针与唯一执行记录。Owner 当前要求后端可靠性继续，UI 构建暂停；因此优先复用已有程序字节，不重新编译前端或改变产品。

`scripts/release/local_pinned_packaging.py` 的 `local-pinned-packaging/v1` 用于未发布的本地包装。它分别记录原构建来源、新包装工具来源及逐成员身份；不改变 CI candidate schema、`app.release`、原候选或通用发布资格器。真实 CI、安装业务、升级回退、Green 更新和 Owner 接受仍各自验收，不因本地打包成功合并为通过。

源码依据包括原 Host/Core 构建回执、源码逐文件快照，以及需要时的完整工作树摘要重建证据。旧快照遗漏的未跟踪文件，只有在隔离临时索引／对象目录中重新得到原构建的完整摘要，并核当前原字节与该证据一致后，才可形成明示的逻辑补充；不补写历史文件或默许任意新增产品输入。文档、当前工具和本合同的变化逐项列明，产品输入变更继续拒绝。

纯包装仅执行已有 Tauri CLI 的 `bundle --no-sign --no-binary-patching --bundles nsis`，禁止隐式前端／Rust 构建钩子。前端已经嵌入被固定的 Host；`frontendDist` 是此步骤的配置路径，不冒称已证明历史 dist 独立保全。实际配置、图标、Host/Core、完整资源清单、Node/CLI/native binding、NSIS 工具均绑定摘要，运行前后复核。旧资源映射必须明确移除，不能同时读取可变的旧 runtime staging。

输出是全新的、项目内 ignored 运行目录；拒绝链接／重解析、输出覆盖和越界。工具缓存限定在该目录，复用工具按文件清单复制并验证，不改全局配置或新写用户目录。源文件名允许合法隐藏文件与 Unicode；分发成员复用正式 portable 资源路径规则，允许已在完整清单中验证的依赖隐藏文件，不套用旧 Core-only 包对点目录的不同限制。

本地身份必须明确 `unreleased`、非 CI、尚未安装验收，不能虚构 CI run/URL 或称为公开合格发行。后续隔离安装验证须显式接收此独立身份及预期摘要，并保留原 CI 默认验证分支；未实现该接收路径前，不降低现有 `RequireCandidateIdentity` 门。本记录不授权在 Owner 当前账户安装，不替换 Green，不发布或覆盖真实用户资料。

安装消费者使用独立的 `RequireLocalPinnedIdentity` 模式，固定包装收据、安装器、Host、Core和运行时清单五个摘要；重新安装的每个阶段仍核完整成员、大小、哈希和链接状态。本地模式记录同安装器同版本重装与数据保留，跨版本升级和回滚另验。原运行时发行摘要按原manifest核对，不补造CI身份或重新盖源码戳。固定工具增量名单明确增加该验证脚本及其三个关联测试文件；每次仍须声明逐文件before/after摘要，不扩成目录或通配规则，产品源码变化继续拒绝。实际验收结果仍只进入唯一执行记录。

依据为本机固定 CLI 帮助及对应官方实现：[bundle 入口](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.3/crates/tauri-cli/src/bundle.rs)、[NSIS 输入](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.3/crates/tauri-bundler/src/bundle/windows/nsis/mod.rs)、[编译期嵌入](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.3/crates/tauri-codegen/src/context.rs)。本合同的合成测试与实际包装、安装验收分层记录；原始失败保留。
