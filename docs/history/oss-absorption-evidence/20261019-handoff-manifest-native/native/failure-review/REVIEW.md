# Native failure review — webdriver-934ae2333af5

结论：本次真实候选宿主旅程 FAIL；材料/陪伴/取消均 NOT_EXECUTED。没有现成可独立执行它们的明确 CLI 或环境 mode。以下为只读分析及待实施建议，不是实现或新验收。

## 已保存事实

- 精确回执：`.project-local/runs/be268a2d33/webdriver-934ae2333af5/tmp/journey/receipt.json`；源码一致 `source_consistent=true`。host SHA256 `6b70a7f8b92563094a28a5cb7f1a018215c513da2117b91d77d2027e16a1c3ca`，Core SHA256 `cdb5537eb124a4ec1783e860e21e6b88c3fb11fe0cc91b366ef8213a57a47d36`。
- 同目录 `data/archeaxis.sqlite` 仅使用 SQLite URI `mode=ro` 读取 machine_tasks 元数据/诊断。原 answer 实际 requested/observed 均为 `aaos-deep-27b-mtp`，74.95s，effective max_tokens=1024，finish_reason=stop；它仍是待判断的模型候选。
- retest UI invoke503；Core `runtime.execution.failed` 行 `MODEL_CALL_TIMEOUT`，discovery=0.0s，model_request elapsed=118.03s，worker timeout=118s，max_tokens=1024，error_type=TimeoutError，answer_published=false，provider_stop_state=UNKNOWN。这是已确认的失败审计，不能写作推理成功，也不能断言服务停机或 provider 已停止。
- CLI requested=2048 与保存 DEEP effective=1024 已明确分开；本次没有预算歧义，不建议改预算或配置来绕失败。
- import/read/anchor/claim/learn/practice/review 分阶段 PASS；工程整体仍 FAIL，closed_loop_verified=false，Owner acceptance NOT_EXECUTED。未到恢复/整工作区备份后段，也未到材料/陪伴，不能将前段 PASS 当整体验收。

## 入口阻塞定位

- `scripts/probes/aaos01_tauri_webdriver_loop.py:1149-1150` 仅有 grouped-material-companion 两个追加开关；`:1190-1193` 约束 material→saved DEEP、cancel→material；`:1186-1187` 又约束 saved DEEP→require actual AI loop+explicit model；`:1170-1171` 要求完整 grouped + actual model + authored intervention。
- 唯一正式调用在同文件 `:1677-1696`，传入 `run_grouped_loop`；没有独立材料/陪伴分支。
- `aaos01_grouped_owner_loop.py:914-915` 二次守卫依赖；`:1209-1215` 先跑原 answer/人工工程纠正/retest，并在 retest 未成功时抛错；`:1216-1219` 才 `mc.run`，`:1230` 才冷重开，`:1253` 才备份恢复后 `mc.reopen`；`:1317-1322` 的取消还位于完整恢复/旧授权拒绝链之后。
- 仅有 `AAOS01_TEACHING_DRAFT_ONLY` / `AAOS01_LEARNING_DRAFT_ONLY` 两个独立草稿分支，均不是材料/陪伴 mode。`aaos01_material_companion_loop.py` 只有 helper，没有 CLI/main。

## 下一最小完整可实施切片

新增一个显式独立 family，建议两个互斥 mode（名称待 writer 定）：`--material-companion-recovery-loop` 与 `--material-companion-cancel-loop`。两者要求显式已授权 model 与实际模型 opt-in，但不要求 grouped/answer/retest/工程纠正；不要简单放宽现有 grouped 开关依赖。拒绝与其他旅程、installer 或故障注入混用，解析拒绝必须先于进程启动。

1. 沿现有 webdriver main 的独立 configuration-plan/character-memory 分支模式分派，复用 host/Core build binding、fresh owned work/data_root、close/restart/finally/owned cleanup。不要接续或写本次失败库。
2. 复用同一 `GroupedUI`、read-only bridge、pointer/wheel/reveal 和受保护导航确认；独立入口必须具有与 grouped 相同的 pointer/wheel 命令适配，不能只复制 plan 分支的 element/action 命令。不要 JS改表单/open、绕过确认或通过 bridge 写业务数据。
3. 创建一份明确 authored 的 project-local TXT，通过实际上传/阅读/建立版本化草稿并 Core exact document_get 固定 document_id/version/hash。可提取 grouped `:950-1054` 的现有 UI建文档最小部分；无需知识审批、course、assessment、学习或 original answer。业务正文/标题与诊断身份分别核验。
4. 复用 `save_deep_model_binding(...,purposes=("material","companion"))`：函数现已支持该子集。只写新合成工作区的产品配置，保留1024/120与原授权模型，不改 provider/global settings。校验读取目录/保存/重开没有推理任务，不借用失败工作区配置。
5. recovery mode：复用 `mc.run`（两个真实目的、preview→同plan确认、状态200也须有效非空content回答、exact model binding），同进程导航恢复，cold restart→`read_saved_model_configuration`→`mc.reopen`；若本切片需保留当前既有备份恢复资格，再复用 page19 UI一致备份/确认恢复/恢复候选确认→cold restart→配置当前restore_epoch→`mc.reopen(...,"backup_restore")`。不要新建第二套回执验证器。
6. cancel mode：不先要求成功普通回答或 `mc.run`，直接复用 `mc.run_cancel`→cold restart→`mc.reopen_cancel`。该 helper 的所谓“prior restore draft”只是注释，真实动作 `ui.page("02",confirm_navigation=True)` 可适用于新owned workspace；接线仍须保留trusted alert处理。每purpose preview/confirm后先观察Core admission，再UI取消、等待原调用终态；不得把cancel ACK本身当终态。
7. 保留 exact request/session/plan、无answer、取消专属reason、原回执不变、history accepted→cancelled、冷重开正确原请求和observer attach后zero执行断言。provider_stop始终UNKNOWN，worker_started UNVERIFIED，startup calls UNVERIFIED，除非另有独立真实证据。取消mode成功只能标Core准入及UI取消/恢复成功，不能标已观察provider推理停止。
8. 独立receipt使用新key/schema并标边界，不调用 `assert_actual_ai_chain`，不伪造其通过；完整grouped原FAIL保留。每阶段立即落失败诊断，材料失败应终止本mode，绝不fallback为mock/重新生成请求。

## 最小有意义回归与实际验收

- 现有 `tests/test_material_companion_native_probe.py`：receipt错误identity/model/plan/destination/empty/nonterminal负例、重复/503/pending call拒绝、cancel专属身份/无answer/providerstop负例、cancel observer原身份、恢复需显式只读路径、wait_execution终态采集。扩展这些，不仅检查源码字符串。
- 现有 `tests/test_grouped_native_owner_probe.py`：saved binding拒绝既有配置、model/epoch/budget负例、配置重开不推理、原授权恢复、受信pointer/wheel/navigation；`tests/test_probe_identity_regression.py`：真实业务视图+诊断/Core身份、隐藏/同名错对象、learning disclosures。保持现有行为。
- 新入口的行为回归：无显式opt-in/model、互斥mode或混用时在launch前拒绝；用注入fake launch/UI/readonly read记录实际dispatch，证明不调用run_ai_stage、answer/retest和任何bridge写操作；不能只assert flag字符串存在。
- 对cancel-only编排增加正向fixture：没有成功回执/旧学习/旧restore草稿也能完成两个目的的Core-admitted取消→原身份冷重开；错request/session/plan、仅ACK未终态、late answer、旧成功请求被恢复、自动重复execution均RED。
- recovery mode分阶段测试：错误/超时/200但失败body不能落PASS；cold/backup restore后receipt不变、配置当前epoch有效、观察窗口无新execution。只有后续真实候选宿主执行才能标REAL；本review未执行上述测试或原生。

边界：本次未启动/停止服务、模型、浏览器；未发推理；未改产品、提案、失败回执/SQLite/冻结快照。只写此指定ignored目录的REVIEW.md和evidence.json。未从118秒超时猜测服务状态或建议改预算。
