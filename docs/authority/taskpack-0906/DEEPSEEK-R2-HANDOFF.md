# DeepSeek → GPT 交接文档：DP-R2 返修包 R01–R09（本地交付）

> 状态：**已按用户 2026-09-07 指令上传交接**（工作分支 codex/full-loop-0906 推送远端、双端一致；main 未动）。
> 本文件是 DeepSeek 侧的 R2 收口交接；权威逐项证据在 `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md` 的 R2 段，派生证据在 ignored run 目录 `.project-local/runs/be268a2d33/b883e3d42ebc/`。
> 2026-09-07 起由 BULK-0907（P00–P28）承接并继续扩展本入口；本文件随之更新摘要，不另建相互竞争的结果文档。
> **BULK-0907 进度摘要见 `DEEPSEEK-RESULTS.md` 的「BULK-0907 中期回执」段**（P00–P05/P08–P10/P12/P15/P17/P18/P21/P22 完成、
> P06 PARTIAL、P23 未收口、P07/P11/P13/P14/P16/P19/P20/P24–P28 待续；191 passed 聚合验证）。

## 一、一句话结论

DP-R2 的 R01–R09 已执行并本地验证：R1 的分级误判已纠偏，4 个测试文件的独立预期/负例已加固（含 R1 的
`test_quality_regressions.py` 在本入口一并回归），16 处历史链接已精确修复，20 项旧资产已补完语义审阅，缓存分类与
DS03/DS06 证据已降级为可复现口径，合并回归 91 passed / 106 subtests。**R08 = PARTIAL**（DS06 原始执行命令/输出哈希
EVIDENCE_INCOMPLETE；DOCX 引擎已更正为 `worker_office._docx_text`，stdlib ZIP/XML，非 python-docx）。
**本轮未改生产实现 / schema / 生成器 / Rust / C# / 数据库 / 锁 / CI / AGENTS.md / 根契约 / 冻结 TASKS；未删任何目录/缓存/用户资产；E 盘未访问；未读私密 `.hermes` 内容与凭据。**

## 二、交接物清单

### A. 权威结果（唯一回执）
- `docs/authority/taskpack-0906/DEEPSEEK-RESULTS.md`：追加两段——「R2 接收审查纠偏」+「R2 验收表（R01–R09）」。R1 历史实测数值原样保留，未回写。

### B. 测试改动（按轮：R1 为 6 测试/样例 + 1 回执；R2 实际改动为 3 测试 + 5 文档 + 回执类追加）
| 文件 | 归属 | 内容 |
|---|---|---|
| `tests/workers/test_text_ndjson.py` | R1 改动 + R2(R04) | R2：锚点/坏编码改独立精确预期（`expected_ranges` + `expected_invalid_text`）+ `char_end` 偏移 1 负控制 |
| `tests/workers/test_quality_regressions.py` | R1 改动 | R1 新增手算 CER/WER 矩阵；R2/R09 合并回归执行该文件（非 R2 遗漏） |
| `tests/contract/test_deepseek_contract_cases.py` | R1 新增 + R2(R05) | 坏 SHA/坏 URI 单字段化 + 嵌套 context 命中校验 + 内存 schema 弱化负控制 + 删 F401 + 改注释（untracked） |
| `tests/workers/test_document_fixture_matrix.py` | R1 新增 + R2(R06) | fail-closed `setUp`（`ARCHEAXIS_RUN_ROOT` 必填）+ 隔离子进程负例（untracked） |
| `tests/fixtures/vnext/documents/canvas-zh-group.canvas` | R1 新增 | 本轮未改 |
| `tests/fixtures/vnext/documents/sample-overlap.srt` | R1 新增 | 本轮未改 |

### C. 历史文档链接修正（R02，16 处，仅改目标字符串，正文/日期/结论未动）
- `docs/architecture/imported-designs/inspiration-research-root/{01_DO_NOT_REPEAT,02_LESSONS_LEARNED,03_ENV_KNOWN_ISSUES}.md`：各 4 处移除 `../`（共 12）。
- `docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/README.md`：`../../../` → `../../../../`（1）。
- `docs/truth/H0_H1_STATUS_HANDOFF.md`：3 处 `../../taskpacks/` → `../taskpacks/`。
- 重扫回执 `r02-links-receipt.json`：16 目标 missing=0（scope 仅限这五份，非全仓）。

### D. 派生证据（ignored run 目录 `.project-local/runs/be268a2d33/b883e3d42ebc/`）
- `r02-links-receipt.json`、`r03-semantic-review.json`（20 项）、`r07-cache-classification.json`、`r08-ds03-evidence.json`、`r08-ds06-evidence.json`。旧 ds01–ds09 证据未覆盖。

## 三、实测结果（R09 逐命令 exit code / run ID）

| 命令 | exit | 结果 |
|---|---|---|
| `dev.py --pytest -- tests/workers/test_text_ndjson.py tests/workers/test_document_fixture_matrix.py tests/workers/test_quality_regressions.py tests/contract -q` | 0 | **91 passed / 106 subtests / 0 fail / 0 skip / 6 warnings**，run `be268a2d33/c148b2f98ca4` |
| `dev.py -- python scripts/contracts/generate_vocabulary.py --check` | 0 | `{"status":"pass","drift":[]}`，run `be268a2d33/3ee5909fd70d` |
| `dev.py -- python -m ruff check tests/workers/test_document_fixture_matrix.py tests/contract/test_deepseek_contract_cases.py` | 0 | All checks passed，run `be268a2d33/ee357add2873` |
| `dev.py -- python -m ruff check tests/workers/test_text_ndjson.py tests/workers/test_quality_regressions.py` | 1 | 4 项 **baseline**（I001、SIM117×2、UP012），run `be268a2d33/99a9158555dd`；本轮未新增 |
| `dev.py -- python scripts/check_repository_conventions.py --source worktree` | 0 | passed，run `be268a2d33/7c3f19fd1885` |
| `git diff --check` | 0 | 无空白/冲突标记错误 |

计数变化：R1 合并回归 88 → R2 **91 passed**（106 subtests 不变）= +2（R05 拆分 +2 用例）+1（R06 fail-closed 负例）；其余无回退。

R03 独立跑批（20 项资产的测试覆盖）：14 文件 `97 passed`（run `be268a2d33/8b1e5a5e84fe`）+ 4 文件 `52 passed`（run `be268a2d33/e0e3a2a77fde`）。

## 四、待 GPT 裁决清单（按优先级）

1. **R03 语义裁决**（20 项）：`r03-semantic-review.json` 中每项的 `target_proposal`（建议 Rust 领域/存储 vs Python 计算适配目标）与 `gpt_decision_needed` 尚未定夺。本轮只做事实核查，未改代码/权威清单；空 `__init__` 记 `EMPTY_MODULE`，`app/adapters/anki_zotero.py` 生产调用方 NOT_FOUND（仅测试 import）。
2. **Ruff baseline**：`test_text_ndjson.py` / `test_quality_regressions.py` 的 I001、SIM117×2、UP012 为存量 4 项，是否 `--fix` 由 GPT 决定（本轮未做全文件 `--fix`/格式化，避免噪音）。
3. **R08 DS06**：旧 `ds06-format-cases.json` 未记录「原始执行命令 / 输出哈希」，已标 EVIDENCE_INCOMPLETE；如需补齐须授权重跑缺证据单例（本轮未装浏览器/模型、未跑网络/真实账号）。
4. **`.hermes` 误写复核**：R1 一次误写 `ds09-run.ps1` 至 `.hermes/task-runtime/` 已删；因不读私密 `.hermes` 内容，当前状态标注 UNVERIFIED，交 GPT 凭可公开执行记录复核。
5. **`d/All projects` 归属**：更正为「含 `Cognitive-Loop-OS/.hermes` 子目录、所有权/内容未完成核验，保留」，禁止读取其 `.hermes` 追索所有权。
6. **旧 DS11–DS15**：仍停手，未造任何假接口/假完成条件，等 GPT 先给契约/错误分类/覆盖回执/资源限制、tokens/组件/状态表/服务接口、冻结旧→新映射、状态机/权限/撤销/时间语义、候选 manifest/哈希/逐项结果。

## 五、回滚边界

回滚按「每轮实际差异」描述；不整文件恢复，不把证据目录删除当作回滚动作：

- **R2 本轮差异**：`tests/workers/test_text_ndjson.py`、`tests/contract/test_deepseek_contract_cases.py`、
  `tests/workers/test_document_fixture_matrix.py` 回退 R2 新增方法/用例；5 份历史文档回退 16 处链接目标字符串；
  `DEEPSEEK-RESULTS.md` 与 `DEEPSEEK-R2-HANDOFF.md` 回退 R2/BULK 追加内容。
- **R1 差异（如需一并回退）**：`test_quality_regressions.py` 回退 R1 新增方法；`test_document_fixture_matrix.py`、
  `test_deepseek_contract_cases.py` 与 2 个 vnext fixture 为 R1 整文件新增（连同 R2 差异回退即删除）；`DEEPSEEK-RESULTS.md` 为 R1 新建。
- **证据目录**：`.project-local/runs/be268a2d33/b883e3d42ebc/` 等 run 证据保持原位、只读，不作为回滚删除对象（旧 ds01–ds09 未被覆盖）。

## 六、未触碰项（边界确认）

生产实现、`packages/contracts/v1/*.schema.json`、生成器、Rust（`crates/*`）、C#（`apps/ArcheAxis.Desktop`）、数据库、锁文件、CI 策略、`AGENTS.md`、根契约、冻结 `TASKS.json`、`.hermes`（只读，未新写）、E 盘、模型库/工具链/资料副本。
