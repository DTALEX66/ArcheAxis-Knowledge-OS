# AAOS 接手、会话与项目漂移审计 · 2026-10-21

审计基线：8d367bac4a85bebfbb523503678ade0838faa73e，tree 629d02d8ce5512e64efd9922aa793dbfcd698b08。主要现场读回时间为北京时间23:00—23:10；具体检查时间见机器记录及本地execution.json。本报告是冻结审计快照，不是新权威、任务队列或第二份实施进度。

**结论：存在可证实的文档传播及归档校验漂移；未在本次范围内证实核心架构反向漂移、TRAE丢失或将不同SHA拼成完整闭环。产品仍为PARTIAL。** 当前主指针已承接后端优先；五项问题见下。源码、现行权威、冻结历史均未在本轮修复，只新增审计派生物和历史导航。

## 1. 范围、来源与读取边界

- 已用Codex线程工具定位并分页读完“接手 AAOS 全链路执行”，thread 01a158e8-ce8c-7921-bdaf-bf83fb6dd901，共12个顶层轮次，最后一页hasMore=false。逐轮决定和交付见[会话梳理](THREAD-MAP.md)。
- 核对根AGENTS/AUTHORITY/PROJECT_CONTRACT、闭环定义、活动指针、最新交接、唯一执行记录近期段、执行覆盖与来源待办；并行核对权威、实现、远端交付。
- 历史覆盖：10/18会话索引与跨客户端对账、10/19的39项来源归档及迁移清单、10/21 Stitch统一归档。没有重读194个原生会话全文，也没有验证全部历史15GB恢复档；Cowork完整正文仍UNVERIFIED。
- 只保留本项目决定的脱敏派生梳理；不复制原始会话、工具payload、凭据或私人记忆。未访问E/F、原生认证数据、真实用户库；未运行模型、产品服务、GUI、安装、删除、远端写入或CI dispatch。
- 当前用户请求是审计与梳理。旧交接中的“继续开发、合并、安装”没有被当成本轮立即执行清单。

## 2. 当前有效规划与权威

| 事项 | 当前依据与结论 |
| --- | --- |
| 权威解析 | 当前明确用户决定→适用AGENTS→批准的规范/替代关系→选中合同→带时点历史证据；AUTHORITY仅导航 |
| 任务来源 | aaos-ui-first-20261009及前后端补充合同继续沿用原ID；文件名含UI-first不等于执行仍前端先行 |
| 最新顺序 | active execution_priority_overlay：现场/失败→BE-P01—15→同候选CL-01—07/J1—6与合格交付→剩余UI-P01—24 |
| 完整闭环 | CLOSED_LOOP_DEFINITION V2七维与六场景；全面非企业特色、三类免费检索、本地和云端均保留 |
| 架构 | 正式Tauri2/React/TS/Vite；Rust Core唯一SQLite/CAS业务writer；Python隔离worker |
| 主题 | 新建/无效偏好回退cosmic，保留有效偏好；五主题共享布局。theme.ts:32—39与指针一致 |
| 冻结及排除 | V01暂停、FT01—04及六项增量冻结；专业PSD/AI/CDR/CAD/3D源格式直接支持排除；长期蓝图保留 |
| Green | 精确目录程序更新已授权但资格未满足；数据保全/回退条件有效，发布及真实数据覆盖未授权 |
| Stitch | 已有只读设计来源和本地保全；不是新产品权威、可用交互或已实现前端 |

## 3. 确认的五项漂移

### D01 · P2 · 归档迁移后，39项来源校验器直接读旧路径而失败

原命令在干净8d367bac上真实执行，exit1/source_consistent=true：
.venv/Scripts/python.exe -X utf8 -B scripts/runtime/dev.py --run-id drift-dialogue-20261021 -- .venv/Scripts/python.exe -X utf8 -B docs/history/owner-dialogue-20261019/verify_archive.py --require-local-attachments

首个错误：现行入口缺失 docs/current/AAOS-XIAOQI-MIGRATION-20261018.md。
decision-coverage.json:265、320、335、349、462共涉及4个已不存在的唯一旧引用（共28个唯一引用）；verify_archive.py:80—82只做直接is_file，未解析迁移清单。
另三项为旧current/receipts中的AAOS-DIAGNOSTIC-CENTER-20261018.json、AAOS-FRONTEND-TEST-CASES-20261018.json、AAOS-NEURAL-GRAPH-ABSORPTION-20261019.json。

四份原件均在repository-consolidation-20261019/MANIFEST.json登记的archive_path存在，逐份大小和SHA全部匹配。**这是验证/路由回归，不是四份原件丢失。** 根权威检查exit0没有检测出此类问题；本轮不宣称全部归档校验通过。原脚本在路由错误处停止，未到附件检查；补充只读readback单独核字节，不替代失败结果。

建议：保留冻结decision-coverage及MANIFEST原字节，在维护中的校验入口安全解析明确迁移映射，或新增受维护的路由包装器；增加“冻结旧引用已迁移”的正负例并接现行检查。不要在旧current位置重建副本，不改历史来掩盖原FAIL。
本地失败证据：.project-local/runs/be268a2d33/drift-dialogue-20261021/artifacts/execution.json及logs/execution.log。

### D02 · P2 · 当前导航及执行覆盖正文残留前端先行

DOCUMENTATION_AUTHORITY_INDEX.md:9仍写“当前前端优先”“Owner后继明确先全量前端、再后端”，与active pointer:494—510的后端优先相反。
FRONTEND-FIRST-EXECUTION-OVERLAY的:3已置后端覆盖说明，但:5、12、52、84、88、93仍以当前语气写旧顺序。完整读取能解析优先级；摘要读取、检索命中和其他客户端仍可能按旧顺序执行。

建议：保留文件身份及24/15/8分片，统一当前导航措辞并将旧顺序标为已替代；不重建第二任务队列。

### D03 · P2 · 根规则、规范合同与实际默认主题相反

PROJECT_CONTRACT.yaml:19及AGENTS.md:88仍写default blueprint；CONFIGURATION_AUTHORITY_INDEX.md:8、DIRECTORY_AUTHORITY_INDEX.md:6、LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md:6也保留该默认。
活动指针:50和实际frontend/src/design-system/theme.ts:39均为cosmic，AUTHORITY.md:64及handoff:77明确旧默认已覆盖。当前代码没有被发现回退；风险是后续按旧合同把正确实现改回。

建议：删除重复默认值或统一引用theme_policy；保留用户有效已存偏好，不改UI或Core数据。

### D04 · P3 · 部分旧日期banner仍写Green未授权

CONFIGURATION_AUTHORITY_INDEX.md:5、DIRECTORY_AUTHORITY_INDEX.md:3、LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md:3、VERIFICATION_POLICY.md:3保留10/11或10/12禁令。
这些是带日期的维护遗留，不能撤销后继精确路径授权；但标题仍称“当前”。active pointer:445起明确GRANTED_NOT_EXECUTED和资格条件，交接也正确保留。

建议：导航声明引用当前授权及资格，将旧禁令明确标历史；不得把修正文档当作安装资格、数据覆盖或公开发布授权。

### D05 · P3 · 已修复的合同Schema失败仍被称为当前故障

FRONTEND-FIRST-EXECUTION-OVERLAY:101仍将closed_loop_definition漏登记写为当前两项CI失败。
.project/schemas/project-contract.schema.json:14、32已登记；唯一执行记录:115、126已记录修复。本次主文档权威检查也成功。

建议：标为带时点的历史原问题及修复出处，避免反复修复旧故障；不能用该修复覆盖真实安装FAIL。

## 4. 代码、候选与证据交叉核对

- 当前schema14；T3仅first-party inert data-only，复用capability_settings、Core Store及正式bridge，保留旧pin/hash/epoch和旧文档。抽查入口：store-sqlite/lib.rs:13、528；domain/template_definition.rs:31、89、114；template_binding.rs:301、307；api/capabilities.rs:212、326、413。未发现此写集另建业务真值的证据；不是全仓所有SQL路径的完整证明。
- a63长链原回执实际存在，201208273字节，SHA b0a927ecddcf9106062c31adb5e450e54ba8e8a7c954a45e270d6588cafe7e40；summary为BACKEND_SUBSET_PASS_WHOLE_PARTIAL，绑定a63。
- 8475 schema升级与54请求生命周期原回执均存在并已现场算hash，分别fb851a6a7bd216c805cf2cacb4ec68907bf98db50c8d8d3ee1bcbb40d5846841、2d0b8e2a030078b9adea4a49adc4b5a388242cccbd8eb5c199253f8cfe361cc4。明确排除installed GUI及统一完整候选。
- 执行记录:803、805、818、822区分a63实际长链、8475构建、2adf验证期望修复；本轮没有发现借旧SHA冒充新候选完整闭环。历史REAL执行由当时收据证明，本轮只重读其身份，不冒充新runtime实测。
- Stitch MANIFEST的8个保全对象全部大小/SHA相符。未重新联网读取Stitch，不重做设计、原型交互或截图视觉验收。

## 5. 七维闭环仍欠什么

| 维度 | 本轮对照结论 |
| --- | --- |
| CL-01 | 正式单写者与对象/恢复边界保留；已有真实子链证据，未证明最终安装候选整体 |
| CL-02 | a63混合格式/OCR/英文转写/恢复子链有证据；完整承诺矩阵、中文识别、视频visual及质量边界仍欠 |
| CL-03 | Wiki/StackExchange/OpenAlex真实公开研究子链已有证据；工程human接纳不等于独立知识质量验收 |
| CL-04 | 有限关系/fragment实际可用；软件×版本×非企业特色×方向的全面矩阵与资格仍欠 |
| CL-05 | T3模板生命周期实际子集通过；任意第三方插件、技能、MCP等形态全接通未证明 |
| CL-06 | 当前本地27B业务尝试超时或只有reasoning而无最终答案；策略答复及真实云provider/材料/费用授权仍缺 |
| CL-07 | 最终同候选J1—6、原生安装/正常窗口退出/DPI/键盘/无障碍/性能及Owner验收尚未完成 |

以上是已公开保留的产品缺口，不应另算“发现隐瞒完成”。不能用本轮审计、CI、构建或T3通过关闭完整闭环。

## 6. 双端、PR与保留工作

北京时间23:03实时只读核对：本地HEAD/main/任务分支及GitHub main/codex/sync-20261019均为8d367bac；主checkout在新增本报告前干净。未发现同步漂移。
[PR201](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/201)已合并，head2adf5724→fc75de86；[CI39616983445](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39616983445)为8成功/11条件skip。
[PR202](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/202)已合并，head19b47ade→8d367bac；[CI39620182056](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39620182056)为3成功/16条件skip。
当前8d367bac的workflow_runs/check-runs均0：**exact-SHA main CI为NO_EVIDENCE**，最近main PASS为旧86a48671的[run39597792036](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39597792036)。现交接正确留待动态核对，尚不是已证实虚报；未触发新CI。

PR192/193已关闭但未merge，PR194已合入52147d6b，符合唯一记录:405—410。
18个worktree中主checkout干净、17个供体脏，共278条状态记录；与主工作区按文件字节比较119相同、159不同、路径缺失0。差异不直接等于未吸收或丢失，也不构成删除资格。
11个本地heads、3个实际远端heads；6个历史保留分支仍有10个“git cherry +”patch待归属，另3个backend分支虽为HEAD祖先仍占用脏worktree。本轮不合并、不删除。

## 7. 验证结果及修复顺序

| 检查 | 结果与实际边界 |
| --- | --- |
| scripts/ci/check_document_authority.py | exit0；输入hash7已核，外部/私人4项UNVERIFIED；结构PASS，未覆盖本文语义及迁移问题 |
| 原39项verify_archive --require-local-attachments | FAIL/exit1，源一致；旧路径缺失，不算归档整体验收PASS |
| 补充字节核对 | 冻结成员/附件、四份迁移原件、Stitch八对象分别读回；结果见本地readback run及AUDIT.json |
| 产品runtime/全测/安装/模型 | NOT_EXECUTED；本轮审计没有产生新产品运行资格 |
| 远端 | 只读API读回；未push、merge、dispatch、发布或清理 |

建议用一次小范围文档/验证修复关闭D01—05：先修安全迁移解析并验证原FAIL，再统一当前顺序/主题/授权/故障措辞；保留冻结源和负证据。之后恢复后端业务缺口，优先最终候选安装阻断与可独立推进的兼容矩阵/消费者，模型及云端必要业务选择保留待答。不要重复长审计或全量测试。

本报告及会话梳理仅本地新增，未commit/push；没有修改产品、现行权威或冻结原件。[机器摘要](AUDIT.json)与本目录MANIFEST记录审计身份。后继现场仍以活动指针和唯一执行记录为准。
