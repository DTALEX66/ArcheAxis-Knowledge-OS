# BE10 native preview 正式门禁修订：冻结接续

状态：**ISOLATED_REVISION_PASS_NOT_APPLIED / NOT_APPLIED / BE10整体PARTIAL**。本目录新15候选（6改9新），旧12文件提案/patch/manifest原字节完整不动，root唯一公共产品writer。

- 补丁 `be10-native-preview-revision.patch` SHA-256 `aa0c154d2725a3b746a6812286c65d55dd281574de3f041d2a1b7ce669260551`；`git apply --check` exit0。
- 准确before/after：`code-manifest.json`、`preimages/`、`proposal/`；不能沿用旧manifest资格。
- 最终canonical `be10-native-preview-revision-final-1019` child/outer均0、source_consistent=true；固定公共基线119份无漂移。精确命令/时间/退出码/日志hash/逐步15源码hash见`validation.json`、`validation-summary.json`。
- 实际edition：API与contracts=2024，native=2021，来自各自实时Cargo.toml。`rustfmt-actual-editions.json`+最终两组check，7个相关Rust均实际格式化和check0。最终API lib相对正式preimage仅module和固定route两处；`edition-format-only.diff`保留曾错误统一2021的修正差异。
- 最终：CI wiring6、schema1×16cases、Rust1×16cases、真实Core25、native bridge29、Ruff、canonical生成客户端逐字节与候选一致、实际PowerShell owned artifact绑定正控均PASS。缺产物exit1、缺owned env native test exit101为明确拒绝负控，不skip。
- 真实红例：owned镜像移除workspace/epoch守卫→HTTP200与应409不符，子101；owned镜像恢复旧CI无绑定→pytest1失败。都finally恢复原字节并最终重编译绿，正式产品与候选从未注入缺陷。

修订只扩展既有desktop-fast的Core release构建成功后绑定：固定release/archeaxis-api.exe、Leaf校验、Resolve-Path、写GITHUB_ENV；两个后继src-tauri cargo test都继承自有构建产物，不使用用户服务、任意URL或skip。local若单独运行新增native test，仍须显式BE10_PREVIEW_CORE指向本次构建Core。

本地实执行的是同一CI绑定片段，并用刚构建debug Core的受控release命名fixture验证路径，再将实际导出且hash相同的产物交给真实native consumer。只证明路径/进程接线；不能冒充release优化、云CI、完整Tauri或安装已过。

**生成物合并注意**：本提案core-contract的after SHA只属于独立schema预览。root待PDF core-document/readiness schema合入后必须用正式generator统一再生，以合并后新SHA重新验证，不能直接复制或继承本镜像生成物身份。

**必须串行完成的来源链**：以合并后的schema统一再生core-contract；root对qualification overlay现2处精确来源引用进行有依据的绑定/再资格判断（`generation-chain.json`列JSON pointer、before/after SHA），随后运行资源目录generator/只读guard与相关回归。`qualification-inherited-state-baseline.json`保留68项五类evidence的state/value摘要；本提案未改或提升它们。不能替换来源SHA后就把旧68项都说成当前资格。

正式应用前root复核6份preimage及9新目标，串行apply15并处理上述资格链。现行全仓cargo fmt基线另有既有FAIL（root记录），本轮不越界修全仓；不能把本轮相关7文件check0说成全仓fmt通过。回退仅6份before和9新文件，保留其他writer修改。

原生preview无正文/投递/执行/接纳写入、无新DB/registry；source/选区UNVERIFIED、navigation UNAVAILABLE。到PinnedReferencePanel的确切NEXT见`proposal/docs/contracts/project-handoff-preview-v1.md`：同事务workspace/restore_epoch+冻结引用正文snapshot、本机只读panel与保留草稿/焦点/布局返回，再做各自外部UI/native/OS URI。metadata preview不是BE10完整旅程验收。
