# 规则入口修复记录（2026-10-23）

本记录解释一次项目规则入口维护，不是产品进度、执行授权或第二任务账本。当前状态仍从[活动指针](../../current/AAOS-ACTIVE-EXECUTION.json)及其指向的唯一执行记录读取。Owner本次要求按交接执行，并判断是否有实际帮助；本次不启动产品开发。

## 判断与根因

问题不是所有历史状态彼此矛盾，而是多处入口复制日期状态，旧段仍使用“当前／最新”。活动指针已区分Owner范围、权限、监控和资格；重复入口增加了维护和误读成本。故保留既有权威机制，精简副本，不另造状态系统、不按字数比例删规则。已核对决定十八至二十二及SUP-025—028：双侧闭环、有限首版、外部原始上下文归属与各项未完成资格均不因精简改变。

开始时分支 `codex/sync-20261019`，HEAD `95b463c12dbd40744b43039add69c48ceaeba94e`；正常SSH只读查询远端main为 `8d367bac4a85bebfbb523503678ade0838faa73e`。两者不是一致声明。已有大量未提交修改，按修改前逐文件SHA保护；本次不认领或提交那些成果。

## 逐文件修改

| 文件 | 修改与保留 |
| --- | --- |
| 根AGENTS.md | 用一段读取说明代替日期状态堆叠；保留产品定义、单写者、普通保存、数据／安全、Git、许可和验收边界。历史整包工作流收敛为继承合同导航；不再要求默认读取旧包。移除失效WORK-LAB激活依赖。 |
| 根AUTHORITY.md | 移除首部重复状态，保留母定义、职责归属、权威顺序及现有规范导航。 |
| 根CLAUDE.md／GEMINI.md | 移除旧运行状态和重复范围正文，保留各自原生导入，共用同一项目规则与闭环定义。 |
| 文档职责索引／历史入口 | 移除两条复制状态，修正把旧归档边界当当前禁令的表格措辞，链接本次冻结归档。 |
| scripts/ci/check_document_authority.py | 复用现有门禁；只检查指定活跃入口的旧跨项目依赖、复制状态断言、共享指针与原生导入目标、循环及重复。历史文件不参加活跃状态扫描。 |
| tests/test_rules_entry_gate.py | 针对旧状态副本、历史说明、缺失／重复／越界／循环导入、普通链接不能替代原生导入添加回归。 |
| 唯一UI执行记录 | 仅追加本维护单元的结果和证据，不改变产品资格。 |

## 去重与历史映射

五份原入口完整字节保存在 `before/`；[MANIFEST.json](MANIFEST.json)登记原位置、完整SHA-256、字节数及26条首部／适配器旧状态原文的逐段行号。所有旧文字按**原文件位置**解释相对链接；冻结副本不作新指令，不注入客户端。

| 原位置／时点 | 当前或历史的解释 | 保留位置与解析来源 |
| --- | --- | --- |
| AGENTS／AUTHORITY首部10/23双侧范围 | 有效范围的重复说明，移除入口副本 | 两份before原件；决定二十二、SUP-028、活动指针owner_scope_current |
| 两入口10/23 AI专项 | 当次AI单元边界，不能冻结未来人类链 | before原件；决定二十一／二十二、AI边界规范、AI专项检查点 |
| 两入口10/23权限恢复与阻塞 | 恢复检查覆盖权限阻塞；旧失败保留，不提升产品资格 | before原件；execution_control.permission_recovery_current及permission_blocker_previous所指检查点 |
| 两入口10/22首版／暂停／恢复；AGENTS的UI、范围与监控 | 决定与事件分别依后继关系解析，监控与产品状态分开 | before原件；决定十八至二十、execution_control、唯一执行记录及原检查点 |
| AGENTS 10/19路由、10/21顺序；AUTHORITY 10/11路由 | 旧时点，不独立决定当前队列、交付或部署 | before原件；活动指针所选执行覆盖、授权字段与原来源 |
| AGENTS Project Mission、Implementation Workflow的旧范围／整包叙述 | 已由当前范围和任务选择覆盖的历史说明；适用合同继承 | before/AGENTS.md保留完整段落；根AUTHORITY、历史索引及SUP-020—028导航，不复制旧顺序 |
| CLAUDE／GEMINI的10/11运行段及正文 | 原生导入保留，旧状态／范围副本删除 | 两份before原件；AGENTS＋AUTHORITY＋唯一闭环定义 |
| 文档索引10/23两条首部说明及设计行 | 来源导航留表格，当前范围／禁令交回活动指针 | before/docs/DOCUMENTATION_AUTHORITY_INDEX.md；原规范与决定 |
| AGENTS旧跨项目全局标准路径 | 失效激活依赖，取消项目入口要求 | before/AGENTS.md原文；项目自身安全、工作流、验证规范继续适用 |

没有修改冻结Owner原始来源、活动指针、决定账本、闭环定义、路由登记或产品代码；本次before是公开项目规则的冻结证据，不包含私人会话与凭据。未新增执行账本。

## 检查与客户端加载边界

所有命令使用项目 `.venv/Scripts/python.exe`；测试和日志经 `scripts/runtime/dev.py --run-id ...` 写入忽略的 `.project-local/`。完整命令、退出码与原始日志在本地 `rules-entry-*20261023` 各run的 `artifacts/execution.json`、`logs/execution.log`；最终保全与任务范围核对见 `.project-local/artifacts/rules-entry-repair-20261023/verification.json`。

- 定向测试：`scripts/runtime/dev.py --run-id rules-entry-tests-final-20261023 --pytest -- tests/test_rules_entry_gate.py tests/test_documentation_authority_index.py tests/test_truth_authority_supersession.py -q`。
- 现有文档门禁：修复后 `scripts/runtime/dev.py --run-id rules-entry-gate-repaired-20261023 -- .venv/Scripts/python.exe scripts/ci/check_document_authority.py`；结果文案收尾后以 `--run-id rules-entry-gate-closure-20261023` 再核最终结构。
- 定向Ruff：`scripts/runtime/dev.py --run-id rules-entry-lint-final-20261023 -- .venv/Scripts/python.exe -m ruff check scripts/ci/check_document_authority.py tests/test_rules_entry_gate.py`。
- 另核对JSON／YAML可解析、关键路由目标、原文备份SHA、未认领修改SHA及本次增量diff。

已先运行RED：10项因新检查函数尚不存在失败；实现后10项GREEN。初次Ruff报告内部遍历函数引用循环变量，改为显式传参修复；失败日志保留。其余最终结果以唯一执行记录和本地verification的实际检查为准，不以预写命令冒充PASS。

现有27项定向测试及最终Ruff通过。首轮聚合文档门禁发现精简时误移除了四个入口的显式身份路由，以及AGENTS中既有冻结对话导航；已补回这些有用的稳定链接，未削弱门禁。修复后文档门禁PASS。保全检查确认56个未认领文件SHA不变、五份原文归档SHA匹配，关键路由存在且JSON／YAML可解析；最终逐文件摘要与各命令结果见verification。

当前终端 `Get-Command claude,gemini` 均未发现命令；这不证明其他安装方式不存在，也未诊断其版本／模式。依据[Claude官方导入与AGENTS说明](https://code.claude.com/docs/en/memory)及[Gemini官方导入说明](https://geminicli.com/docs/cli/gemini-md/)，保留既有 `@AGENTS.md`／`@./AGENTS.md` 等原生导入。Claude当前官方文档说明其原生AGENTS模式会对已导入的AGENTS去重；实际本机行为仍**UNVERIFIED**。Gemini可配置同时发现多个文件名，不能未经读取其实际模式就假定不会重复；本次不读取或修改用户级设置。

新会话人工检查步骤（未执行）：

1. 在本仓根启动实际使用的客户端，先用其 `--version` 和当前版本帮助确认命令；不用模型执行产品任务。
2. Claude输入 `/memory`，检查共享规则文件是否加载；Gemini输入 `/memory show`，必要时按该版本支持的 `/memory reload` 重载后再看。核实AGENTS全文只出现一次，并读回活动指针与当前决定；普通Markdown链接不视为全文加载。
3. 让该会话只读报告人类／AI／双向范围、监控、权限检查与产品资格各自的来源。文件加载与能正确应用规则分别记结果；无法查看诊断时保持UNVERIFIED，不能用模型口头“已读取”代替加载清单。

没有运行产品构建、模型推理、原生／安装／Owner验收或云端CI；没有提交、推送、合并、发布或Green替换。

## 回退

修改前八份逐字节备份及时间／SHA在 `.project-local/artifacts/rules-entry-repair-20261023/before/` 与 `baseline.json`，五份入口还有本公开冻结副本。本次任务增量patch及修改后摘要存于同一私有artifact目录。回退先比较修改后摘要；有后续修改时人工合并本次反向差异，不能整文件覆盖、reset或clean。仅本次新建且确认无人后续修改的测试／归档可按清单单独撤销；保留其他会话的原有修改。
