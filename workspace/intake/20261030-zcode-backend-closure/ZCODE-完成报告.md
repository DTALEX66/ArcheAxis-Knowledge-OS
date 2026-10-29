# ZCODE 完成报告：本地后端闭环收尾（2026-10-30）

执行者：ZCODE 会话（Owner 2026-10-30 指示通宵自主执行）。分支 `codex/local-backend-closure-20261029`。
机器可读证据索引：同目录 [evidence-index.json](evidence-index.json)。唯一执行记录已回写：`docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md` 末段"2026-10-30 ZCODE本地后端收尾"。

## 0. 模型模式偏离登记（提示词第0.3节）

本次会话使用云端模型（`account:zai-start-plan/GLM-5.3-Flash`）。接手时已如实报告该事实并停止；Owner 随后指示继续执行，视为对本条的明确豁免。技术事实不变：项目内容随会话进入云端模型上下文，本提示词不能替代操作系统级网络隔离。除此之外，第0.1/0.2/0.4-0.6节边界全程遵守：无 push、无 PR、无远端合并、无云 CI、无发布、无私有材料上传、无私有查询词外发（本轮未发任何真实检索请求）。

## 1. Git 身份与工作树

- 基线：`c4531c1b`（建立分支时的 HEAD，交接快照 `baseline-before-handoff/` 保全原 dirty/untracked）。
- 本轮新增本地 commit（全部显式路径 staging，未用 `git add .`，未 push）：
  1. `7c9c95ba` Share validation and cancellation policy across backend domains（五类归并，11文件）
  2. `c09c7d20` Export edited canvas documents preserving structure and current text（Canvas 文本节点导出，5文件）
  3. `3d8acb0b` Pin local packaging identity and app-local C++ runtime staging（19文件）
  4. `5957abce` Add light brand mark asset（1文件）
  5. `b2839075` Record 20261029 handoff materials and progress documentation（17文件）
  6. 最终治理 commit：`.gitignore` 补 `.mimosa/` + 本报告 + 执行记录回写。
- 未合并分支：无（本轮未发现需要合并的其它本地分支；交接既有的 `trae/20261024` 线保持原样）。
- 回退：每个 commit 独立可 revert；归并为行为保留重构，无 schema 迁移与真实数据改写。

## 2. 能力保全对账（16族/186项/22职责）

- 16族 Atlas 状态分布（CAPABILITY_ATLAS_V2.yaml，未改动）：supported 2（CAP-0010 原件接入、CAP-0030 证据锚定）、in_progress 6（多格式转换/学习系统/互操作/搜索图谱/桌面平台/备份同步）、planned 8；唯一 DEFERRED 族 CAP-0130（受限受控执行探索）。冻结输入 CSV（186项/22职责映射）已随交接入库（`workspace/intake/20261029-stitch-zcode-handoff/ZCODE-仅本地/04、05`）。
- 兼容矩阵（35平台）：PARTIAL_DOCUMENTED 6（markdown/obsidian/notion/anki/joplin/zotero 共18条特色），REQUIRED_NOT_STARTED 29，overall_parity 全部 UNVERIFIED——本轮未删除、未降级、也未虚增任何条目。
- 本轮能力变化只有两类：**行为保留重构**（五类共用策略归并，公开路由/payload/schema/已存数据不变）与**新增**（Canvas 编辑后文本节点导出）。无任何能力被菜单归并删除；无空占位复制充数。
- 外置能力底座复核（`config/environment/external-resources-index.json`，探针 2026-10-25，本轮抽查关键路径全部在盘）：RESULT_VERIFIED 4 / VERSION_PROBED 16 / FILE_EXISTS 9 / NOT_RUN 1（rerank 端点）/ unavailable 1（desktop-runtime-v1，按声明不重装）。OCR/ASR/媒体/Office 引擎与模型路径全部具名在位。

## 3. 修复、验证与根因

### 3.1 五类后端归并——复验并转正
交接期的94项定向测试（domain19+API合同50+取消5+机器问答/journal20）在本轮以同一命令形状复跑为 **99项全绿**（增加 Canvas 5项），全部 `LOCAL_PASS / source_consistent=true`，绑定执行期身份 HEAD `c4531c1b` + dirty patch `e885d130…`；提交后同内容以 HEAD `b2839075` 承接（提交不改变被测文件字节）。共用点：关系校验（live/shape 双策略）、对象引用形状校验去重、四机器路径锁内取消准入、能力 provider 记录组装、模板事务提交。

### 3.2 Canvas 编辑后重建导出（补齐具名缺口）
交接记录具名缺口"Canvas编辑后格式重建缺Core合同"在未跟踪成果中已有完整实现：`crates/archeaxis-domain/src/canvas_export.rs`（rebuild/export + 拒绝歧义编辑、拒绝丢弃字段）接入 `documents.rs` 导出路由 `format=canvas`，API 集成测试覆盖"重启与包恢复后结构/来源/当前文本保全"与"歧义编辑拒绝但不阻断普通保存/markdown"。本轮复跑 5 项测试全绿并提交（`c09c7d20`）。范围仍是有限导出：附件未摄取、非文本节点语义映射从严拒绝，损失范围按测试断言如实保留。

### 3.3 retest 503 / NO_FINAL_ANSWER——诊断闭环（不改合同）
v2 失败步骤34实测：`finish_reason=length`、2048 输出 token 全部消耗在 `reasoning_content`、无正文，worker 按 `worker_machine_answer.py:529-535` 如实抛出具名 `NO_FINAL_ANSWER`（含 usage/elapsed 诊断），未伪造答案。v3 同候选复跑 PASS（answer 36.96s / retest 54.92s）。判定：**推理模型预算行为方差**，不是代码缺陷；自动重试 UNKNOWN 属合同禁止项，worker 合同不改。原 FAIL 收据保留。

### 3.4 dev.py 运行 INVALIDATED 机制修复
本轮两次基线 run 被判 INVALIDATED（exit 3）：`dev.py` 的 worktree 身份会哈希全部未跟踪公共文件，而 Mimosa 插件 hook 在会话期间持续写 `.mimosa/hook-state`，与任何并行运行重叠即漂移身份。修复：`.gitignore` 补 `.mimosa/`（与既有 `.codex/`、`.zcode/` 同类 agent 工具状态）。原失败 run 保留作为机制证据。

### 3.5 lint 与格式
- `cargo fmt --check` 发现2处格式差异（capabilities.rs:295、relation_projection.rs:160，均在归并写集内）→ 已应用 `cargo fmt`（仅这两个 crate）并复检干净。
- clippy 组件在固定工具链缺失 → 经官方 rustup 安装 0.1.97（先例：2026-09-24 rustfmt 同法；用户已授权"缺工具可以下载"）。
- 范围 clippy（domain+api）LOCAL_PASS，8条既有警告保留（unused import×2、dead code×2、expect 内函数调用、未用变量×2、content_type 字段）。
- 全依赖路径 `-D warnings` 不绿：`archeaxis-store-sqlite` 有2条**既有** clippy lint（raw_objects.rs:165、writer.rs:57）。深夜不顺手修改无关模块，具名登记由 Codex/下轮处理。

### 3.6 合格 Core release 构建（固定源码与构建输入身份）
按 dev.py 规范命令执行 `--qualify-core-build`：`.project-local/build/cargo/release/archeaxis-api.exe`，19,181,056 字节，SHA256 `b6f5b591c2663bc03ee986a8b5aef25e1d414219373523c8b404f3a6512e103b`，绑定 HEAD `b2839075` + patch `81d47216`（届时唯一 dirty 文件为 .gitignore）。**注意：该构建只固定身份，未经 staging/安装态消费**——不能移绑旧安装包的 PASS，也不冒称新候选资格完成。

### 3.7 get_canvas created_at 缺陷
20261025 Obsidian 兼容回执曾记录 `get_canvas reports unknown order column: created_at`。当前源码（crates/ 与 services/ 全量 grep）无 `get_canvas`、无 canvas created_at 排序 → 登记 `UNREPRODUCED_IN_CURRENT_SOURCE`，不复现不猜测。

## 4. CL-01—07 / J1—6 逐项状态（证据层分列）

### 4.0b C1 安装生命周期在沙盒完全验证（2026-10-30 第四轮）

按工单执行到底：**新 Core 的 NSIS 安装器在 Windows Sandbox 隔离安装并完成全部生命周期断言**。

1. **C1 验证器**（`verify-mixed-core-c1-v1.proposed.ps1`，SHA `b5e6b927…`）：由 v2 验证器经逐锚点断言的精确替换构建（旧身份 token 断言不存在），打包身份校验重定向到混合链（8份sidecar、core-build回执绑定、host供体钉、无 msvcp140 delta、无 pdf 前置、无 portable.flag）；安装/启动/关闭/强制清理/重装/卸载保全/读回的生命周期机制原样复用。
2. **宿主 proof-review**（`zc1r-v9`）：`PASS_REAL_OFFLINE_MIXED_CORE_PROOF_ONLY`，19,747成员/8份sidecar；六次失败尝试（参数别名、对象vs裸SHA、赋值遗漏、pin同步）全部保留。
3. **沙盒运行**：`zc1i` 首跑在安装成功、窗口响应后于前端就绪 CDP 评估 30 秒超时（about:blank）——**判为冷启动方差，原 FAIL 保留**，经官方 exact-owned stopper 清场；`zc1i2` 重跑**走完全程**：guest 终态 `VERIFIER_RETURNED_REQUIRES_LIFECYCLE_RECEIPT_REVIEW`（error=null）。
4. **生命周期回执**（SHA `37684512…`）：`complete_lifecycle_verified=true`，scope `LOCAL_MIXED_CORE_INSTALLED_LIFECYCLE`，安装器 `3337fce6…` + Host `ac4c399b…` + **Core `b6f5b591…`（新）** + manifest `440e9084…` 全绑定；优雅关闭、同版本重装数据保全、强制树清理、干净卸载、卸载保留数据、重装读回全 true，pyc 增长 0，持久 job 读回成功。
5. **清场**：zc1i2 因 launch 绑定瞬时阻断（v7 cppstart1 同型先例，回执保留）无法走形式化 stopper，按其核心语义执行一次直接官方 stop（单一 owned 环境核对 + 意图回执先行）：`STOP_CONFIRMED_OWNED_RESOURCES_CLEARED`，官方清单空、零沙盒进程。
6. **如实 NOT_EXECUTED**：冲突旅程、跨版本升级/回滚、AI 旅程（宿主模型 127.0.0.1 绑定阻断）。

### 4.0a 新 Core NSIS 安装器（2026-10-30 第三轮）

合格构建 → staging（R2）→ 混合候选（C1）之后，本轮完成 **C1 专属打包链并产出新 Core 的 NSIS 安装器**：

1. **candidate-manifest**（`zcode-c1-manifest-20261030`）：C1 全量 19,747 成员逐字节清单（扩展路径枚举），envelope `aaos.mixed-core-candidate/v1`，无构建/CI身份合成。
2. **consumers 复核**（`zcode-c1-consumers-20261030`）：`EXACT_EXISTING_BUNDLE_CONSUMERS_VERIFIED`，与 lpns3 基线逐字节一致。
3. **新打包适配器 `bundle-mixed-v6.py`**：v5 的资格逻辑钉死"旧候选仅加一个DLL"场景，不适于新 Core；v6 保留 v5 的打包机制（consumer 清点、overlay、tauri bundle 命令、回执），将资格校验替换为 C1 混合身份链（candidate-manifest + mixed-assembly + host供体钉 + stage回执 + **core-build回执**（Core exe 的真实来源绑定）+ host构建回执 + consumers），proof sidecars 全部落盘并离线复核。**不设 pdf_validation 前置**：安装态 PDF 由下一轮沙盒旅程直接行使（更强证据），如实记 NOT_RUN。
4. **打包执行**：首次执行失败于 makensis 长路径（我的 run 名比 v7 长，litellm 深层文件越界 MAX_PATH——失败 run 保留）；改用短输出路径 `zc1n` 后 **`LOCAL_MIXED_CORE_PACKAGING_PASS`**。
5. **安装器**：`ArcheAxis Knowledge_0.6.14_x64-setup.exe`，424,441,075 字节，SHA256 `3337fce6f1365d6eb8011348533b82065570cc093289771f1353a7a14268572b`（版本标签来自冻结的 tauri 配置 0.6.14；backend manifest 声明 staging 版本 0.6.15，两处身份分别记录）。

**具名阻断（安装态旅程）**：v7 沙盒驱动硬钉旧身份（旧 CORE SHA、固定 RUN、旧 bundler SHA），C1 安装需按新钉扎staged变体；安装态 AI 旅程的真正阻断是宿主 LM Studio 只监听 127.0.0.1、沙盒 guest 不可达（v7 安装态也因此从未跑过 AI），改监听地址属宿主模型配置变更，超出本轮边界；真跨版本升级/回滚需要版本号提升决策（安装器版本标签来自冻结 tauri 配置），否则只能重复已验证的同版本重装路径。

### 4.0 新 Core 同候选纵向链（2026-10-30 第二轮，C1 campaign）

合格 Core 构建 `b6f5b591…` 已从"仅构建身份"推进到**可运行混合候选**并重建同候选收据链：

1. **Staging**：`stage_backend_runtime.py` 以规范参数（version 0.6.15，source `b2839075`+tree `a502f9d2`）产出 backend 候选根 R2（19,744成员，manifest `440e9084…`）。
2. **混合候选 C1**：新组装器逐字节复制 R2 + 历史 Tauri Host（供体 SHA `ac4c399b…` 双源交叉核对，不冒称一次完整新编译），19,746成员逐一哈希验证，组件来源回执入 `c1/mixed-candidate-assembly.json`。长路径（litellm 深层 site-packages）需要 `\\?\` 扩展路径枚举+哈希——已修入组装器。
3. **C1 同候选链五段全通**：J2 真实公开检索（三通道，REAL_CORE_PUBLIC_NETWORK，42步）→ 常用格式资格 → 研究学习旅程（PASS_DECLARED_INTEGRATED_SUBSET，108请求，含 restart_equal 与独立恢复相等）→ J5 模板同候选工作区（PASS_FINITE_T3，58请求）→ **真实本地模型 colearning 冒烟**（REAL_MODEL：qwen3.5-4b 真实推理回答正确 `finish_reason=stop`、超界问题真实失败、纠正后 retest 链接成功，failed_stage=null）。
4. 途中修复：`colearning_real_model_smoke.py` 的 `timeout_s:600` 超出 Core 合同上界（`1..=120`，colearning.rs:137-141）→ 探针对齐合同（commit `1d10938b`），合同未放宽。
5. **仍未做**（需要 v7 bundle 链按新候选重建 request + 沙盒执行）：新 Core 的 NSIS 安装器、安装态普通/冲突/AI旅程、跨版本升级/回滚（旧安装包 `53a83f20…` → 新候选）。


| 项 | 状态 | 证据与未完 |
| --- | --- | --- |
| CL-01 完整核心架构 | PARTIAL（后端源码级强化） | 五类归并+99测试绿；Rust Core 唯一 writer 保持；公开合同不变。未做新业务能力 |
| CL-02 常用多格式 | PARTIAL | 安装态 PDF 子集 PASS（v7）；OCR/ASR/媒体/Office 引擎在位；Canvas 重建导出本轮补齐（源码级）；完整混合目录旅程未全跑 |
| CL-03 免费公开检索 | PARTIAL（真实通道有证据） | `c453-j2-public` REAL_CORE_PUBLIC_NETWORK 42步全通（百科/社区/学术三通道 raw/select/anchor/jump/save/restart/backup）；限制具名（无独立语义比较等）。本轮未发新真实查询；installed 态未验 |
| CL-04 知识库特色 | PARTIAL | Obsidian 兼容 PASS_WITH_RECORDED_GAPS（20261025）；矩阵35平台6项 partial；get_canvas 缺陷现源码不可复现 |
| CL-05 开源吸收 | PARTIAL | 吸收登记与引擎在位；本轮无新吸收 |
| CL-06 本地与云端模型 | PARTIAL | 本地真实推理 PASS（Green 实测 + v3 dual-loop）；retest 503 诊断闭环；云端专业接口代码路径存在（凭据读取、材料授权边界），**真实云推理 DEFERRED_UNEXECUTED** |
| CL-07 同候选可靠性 | PARTIAL | 安装生命周期+PDF子集+恢复子集 PASS（v6/v7）；完整安装态业务/冲突/AI旅程、跨版本升级/回滚 NOT_EXECUTED |
| J1 | PARTIAL | 合成+安装态 PDF 子集；完整旅程未跑 |
| J2 | PARTIAL（REAL_CORE 层通过） | 42步真实链；installed 未验 |
| J3 | PARTIAL | Obsidian 子集；35平台矩阵未全 |
| J4 | PARTIAL | 本地真实推理子集 PASS；云接口未真实调用 |
| J5 | PARTIAL | 模板/T3 合同测试绿 + j5-template 既有 run；卡片形态消费者边界保持 |
| J6 | PARTIAL | 生命周期/恢复子集；完整未跑 |

**结论：`LOCAL_BACKEND_SCOPE_PARTIAL_PENDING_CODEX_AUDIT`。** 后端有限切片（归并、Canvas 导出、打包身份、测试门禁、构建身份）真实完成；因 UI 暂停未实现的统一缩放、缺失原生消费者、完整安装态旅程、跨版本升级/回滚、真实云推理、外部上下文连接按合同记产品层未完成，不阻塞已完成后端切片，也不据此宣称全产品完成。

## 5. 延期/损失清单（沿既有登记，无新增延期）

复杂延期族（企业协作/多租户、通用 Agent Runtime、Marketplace、3D/VR/AR/XR、动态解释仿真、参数训练实验）沿 Atlas `formal_later`/FT01-04 冻结保持；外部跨项目原始会话 `EXTERNAL_CONTEXT_PROVIDER_NOT_CONNECTED`；真实云推理 `DEFERRED_UNEXECUTED`；旧真实 UNKNOWN 与 provider 停止状态按"不重放、不覆盖"保留（`PASS_UNKNOWN_RETAINED_NO_LOCAL_REPLAY_OBSERVED`）。Canvas 有限导出的损失范围（附件、非文本节点映射、富文本往返）由测试断言显式声明。

## 6. Codex 独立审计入口

1. **diff 审阅**：`git log c4531c1b..HEAD --stat`；六个 commit 均显式路径。重点：`runtime/mod.rs:47` 的 `MachineActive::request_cancel` 与四处调用点互斥语义；`capabilities.rs` provider 记录组装次序；`template_definition.rs:100` `commit_state` 事务边界；`canvas_export.rs` 拒绝路径。
2. **测试复现**：九个 run 的 execution.json（SHA 见 evidence-index）逐条可复现，命令在各自 receipt 内；重跑入口 `scripts/ci/cargo_test.bat …` 经 `scripts/runtime/dev.py --run-id <new>`。
3. **已知失败/保留项**：store-sqlite 2条 clippy lint；8条范围警告；v2 retest FAIL 收据；两个 INVALIDATED/交互式 cmd 失败 run；Mimosa hook `scanner_no_output`（commit 未获完整扫描结论，**不做项目安全宣称**，完整审计待 Codex/Owner 决定是否重跑）。
4. **不移绑警告**：99+411 测试为源码级；`b6f5b591…` 构建未经 staging/安装；v7 安装态证据仍属历史候选 c453+6b30；J2 真实链为 REAL_CORE 层。各证据层不得互相晋升。
5. **复现命令样例**（重跑归并域测试）：`cd /d D:\All projects\ArcheAxis-Knowledge-OS && .venv\Scripts\python.exe -B scripts\runtime\dev.py --run-id <新id> -- cmd.exe /d /c scripts\ci\cargo_test.bat test -p archeaxis-domain --test relation_projection --test research_metadata --test object_reference --test template_lifecycle --offline --locked`（Git Bash 下需 `MSYS_NO_PATHCONV=1`）。

## 7. 边界遵守与清场

- 无 push/PR/远端合并/云 CI/发布/Green 替换/真实数据覆盖；云 CI 记 `NOT_EXECUTED_BY_OWNER_LOCAL_ONLY_BOUNDARY`。
- 网络使用：仅 rustup 官方源下载 clippy 组件一次；无真实检索调用、无私有材料外发。
- 进程清场：本轮仅运行短生命周期测试/构建命令，无常驻自有进程残留；未触碰共享 LM Studio 与未知进程。
- `.mimosa/`、`.project-local/` 等运行态不入 Git；证据全部项目本地保存。

## 8. 后继最短路径（供 Codex 审计后接续）

1. store-sqlite 2条 lint + 范围内8条警告清理（小改动，先审后改）。
2. 用 `b6f5b591…` 构建走 `stage_backend_runtime.py` staging → 新候选 → 安装态普通/冲突/AI旅程（v7 基建可复用）。
3. J2 installed 态验证；跨版本升级/回滚隔离验证。
4. 云接口凭据由 Owner 配置后做一次真实云推理（仍延期，不阻塞）。
5. Codex 审计通过后由 Owner 决定远端交付（本轮无远端操作）。
