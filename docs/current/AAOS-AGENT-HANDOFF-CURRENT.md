# 当前 Agent 接手入口 · 2026-10-16

先读 [根权威](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[项目合同](../../PROJECT_CONTRACT.yaml)、[文档权威索引](../DOCUMENTATION_AUTHORITY_INDEX.md) 和 [路径路由](AAOS-AUTHORITY-ROUTES.json)。当前仍 **RUNNING_BY_OWNER / PARTIAL**，不从旧 COMPLETE 或历史权限推导当前事实。

## 当前工作和证据

整合检出 `.project-local/worktrees/optimization-20261014`，分支 `codex/character-memory-ui-20261015`，[PR193](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/193)。最新 SHA、dirty、远端与 CI 现场读取；本入口不能绑定自身提交。

[活动指针](AAOS-ACTIVE-EXECUTION.json) 选择原 UI 队列及 AX-HOST-20261013 / AX-UI-20261013 增量；[执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)保存时间线，[统一剩余任务](receipts/AAOS-REMAINING-EXECUTION-20261013.json)保存实际缺口。原始包归档不等于完成。

本轮[最新检查点](receipts/AAOS-SURFACE-INTEGRATION-20261016.json)：BE11 格式六操作资格已接入有限 Tauri 桥接和显式 UI 读回；FE10 教学 11/12 页可只读返回原课程且保留作答与教学正文。组合 quick 27 项通过，含151文件1449项前端、类型和合同检查；桥接定向1项通过。其后的退出探针小修另有67项回归与独立审查通过。顶部菜单随后通过最终27项quick门禁（152文件1459项前端），各次检查保留源码摘要。

最新已结束 CI `38798080182` **FAIL**：head `dbb99f87`、实际 PR merge checkout `01a6296c`；除安装生命周期及依赖汇总外，运行的产品检查通过。安装过程已保存文档，首次显式退出遇到 WebDriver target frame detached，未观测自然 exit 0，不追认通过。精确关闭模板修复见[退出回执](receipts/AAOS-INSTALLED-EXIT-TRANSPORT-20261016.json)，新 exact-SHA CI / installed 尚待验证。之前的合同登记、授权文件竞态和 CIM 查询失败已修复，旧 FAIL 留在[历史 CI 回执](receipts/AAOS-INTEGRATION-CI-REPAIR-20261016.json)。

前端按[七张参考图](AAOS-UI-REFERENCE-DIRECTION-20261015.json)实现全窗背景与内缩玻璃壳；首开、阅读两列/横向元数据及窄屏检查器/顶栏已局部实现，[14场景浏览器回执](receipts/AAOS-READER-RESPONSIVE-20261016.json)限定为受控宿主的真实渲染。[顶部横向菜单](receipts/AAOS-TOP-NAVIGATION-20261016.json)已实现并通过10个真实浏览器场景；图5双栏工作台正文与七图全量视觉尚未验收。**FE18 人物归 QODER，本 writer 不读取、复制或修改其检出。**

清理已完成13个目录对象规范化，以及逐项SHA验证的旧安装包/runtime副本归档。最近一次[候选 runtime 归档](receipts/AAOS-CANDIDATE-RUNTIME-ARCHIVE-20261016.json)净减少397,862,276字节，未重复累计旧回执；六份旧 runtime 3,754,808,790逻辑字节仍保留，未证明空闲，不计回收。

## 下一步与停止条件

继续图5工作台正文、当前 exact-SHA 安装 CI 与剩余 BE/FE；按任务台账推进，不重跑已经通过且源码未改变的全量检查。完整学习/教学、全格式原生编辑与往返、全部视觉和 Owner 资格仍未闭合。candidate5 的[限定恢复与分栏原生证明](receipts/AAOS-RECOVERY-AND-DOCK-20261016.json)以及历史4B/27B实测只绑定各自候选，不能代表当前整树或模型质量。

Owner 已确认账户**剩余额度 ≤15%**时停止新增开发和重型验证；现有 `archeaxis` 每5分钟检查有效窗口的最小剩余额度，UNKNOWN不是0。触发后 checkpoint 自有agents，整理摘要/问题/证据/交接，显式提交上传本轮公开且任务所属内容，核对本地与远端分支 SHA，再暂停目标和监控。额度重置不自动继续。

## 固定边界

正式宿主 `frontend/` + `src-tauri/`；Rust Core唯一SQLite/CAS业务写者，Python worker隔离。普通内容不依赖外部依据即可保存；权限、结构、完整性和特殊人工认可流程保持。新用户默认cosmic，有效旧主题保留，五主题共享布局与语义颜色。

独立writer用隔离检出，root负责集成和显式路径staging。只上传公开源码及脱敏回执；原始保全包、运行时、数据库、缓存、私人配置/session不上传。V01暂停、FT01–04及六项核心对话增量冻结；发布、Green替换、真实数据覆盖未授权。付费新供应商和新增模型仍按明确授权判断。

本地测试、候选源码、exact-SHA CI、已安装旅程与Owner验收分别记账。旧main、分支清理与已完成工程轮次不冒充当前状态；读取当前ref而非历史正文推断。

此前入口的全部字节已归档到[历史交接快照](../history/handoff-20261016/AAOS-AGENT-HANDOFF-before-surface-checkpoint.md)，摘要见最新检查点；原日期、SHA、FAIL/PARTIAL、权限和历史链接均保留。该快照仅为历史，不构成第二当前入口。
