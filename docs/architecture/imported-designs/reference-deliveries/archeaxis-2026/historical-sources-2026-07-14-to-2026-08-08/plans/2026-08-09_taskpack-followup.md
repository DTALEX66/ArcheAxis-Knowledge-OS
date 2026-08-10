# B/C/R TaskPack 后续执行列表

> **范围**：严格依据 `codex-taskpacks/` 中当前跟踪的三个任务包；不把桌面发布验证、格式扩展或历史完成声明冒充 B/C/R 任务完成。
>
> **任务包来源**：
> - `codex-taskpacks/B线_CODEX任务包.md`
> - `codex-taskpacks/C线_CODEX任务包.md`
> - `codex-taskpacks/定时推送与项目雷达_CODEX任务包.md`
>
> **当前基线**：canonical 工作区 `feat/p1-compat-kernel-hardening`，HEAD `84a0dfd...`；用户 WIP `tests/fixtures/readability_article.html` 必须保持不动。所有运行时报告写入 `.hermes/task-runtime/`，不写入真实资料源。

## 一、执行前唯一门禁

### G0：任务包身份与基线确认

- [ ] 读取三个任务包全文、记录字节数/行数/任务图。
- [ ] 确认当前任务包以仓库跟踪文件为权威；若出现外部归档、旧矩阵或同名任务 ID，先记录冲突，不替换权威。
- [ ] 固定执行 worktree、HEAD、允许修改路径、禁止路径和回滚句柄。
- [ ] 生成 `.hermes/task-runtime/taskpack-baseline.json`，只记录元数据和哈希，不记录秘密或资料全文。
- [ ] 后续每项状态只能使用：`UNVERIFIED`、`IN_PROGRESS`、`BLOCKED`、`VERIFIED`；任务包声明本身不能作为 `VERIFIED` 证据。

## 二、B线：IR → KB → Cognitive-OS 最小核心闭环

依赖顺序：`B1 → B2 → B3 → B4 → B5 → B6`。

### B1：建立 shared schema 引用

- [ ] 确认 `shared-contracts/schemas/*.json` 是三个项目共同读取的路径。
- [ ] 确认三个项目实际使用同一套 schema，而不是复制的旧文件。
- [ ] 用全部相关 fixtures 执行 schema validation。
- [ ] 验收必须同时满足：fixtures 全部通过；错误 fixture 能指出具体字段；schema 路径不存在时 fail closed。
- [ ] 证据：命令、fixture 数量、失败字段、schema 哈希、退出码。

### B2：IR 生成 IntakeCard

- [ ] 使用 `research_note.md` 和 raw research text 各执行一次真实生成。
- [ ] 验证输出 `intake_card.json`。
- [ ] 验收字段必须完整且非空：`why`、`what_to_absorb`、`what_not_to_absorb`、`risk_level`。
- [ ] 验证不执行外部项目代码、不自动安装、不读 token/key。
- [ ] 验证同一语义输入的稳定/可追溯输出与错误输入的明确失败。

### B3：IR 生成 EngineeringContract

- [ ] 以 B2 的 `intake_card.json` 为真实输入生成 `engineering_contract.json`。
- [ ] 验收字段必须完整：`goal`、`deliverables`、`acceptance_criteria`、`blocked_actions`。
- [ ] 验证 IntakeCard → EngineeringContract 的字段映射、风险约束和禁止动作没有丢失。
- [ ] 对缺字段、非法 `risk_level`、空 deliverables 增加失败测试。

### B4：KB 生成 ContextPack

- [ ] 以 B3 的 `engineering_contract.json` 加 source evidence 生成 `context_pack.json`。
- [ ] 验收字段必须存在：`goal`、`sources`、`evidence`、`constraints`。
- [ ] 验证 source evidence 可回读、路径受项目边界约束、外部资料源只读。
- [ ] 验证没有把推测内容标为 evidence，没有把绝对本机路径暴露为普通产品字段。

### B5：KB 生成 TaskPack

- [ ] 以 B4 的 `context_pack.json` 生成 `taskpack.json`。
- [ ] 验收字段必须存在：`steps`、`allowed_tools`、`blocked_tools`、`success_criteria`、`risk_level`。
- [ ] 验证 `blocked_tools` 与 `allowed_tools` 不冲突。
- [ ] 验证步骤真正请求的工具与声明的允许工具分离，不能把策略列表冒充执行列表。
- [ ] 验证高风险、缺 evidence、未知字段、工具冲突均 fail closed。

### B6：Cognitive-OS 执行 mock TaskPack

- [ ] 以 B5 的 `taskpack.json` 执行一个低风险 mock 任务。
- [ ] 验收输出 `execution_trace.json` 与 `machine_lesson.json`。
- [ ] 低风险任务必须 `success`。
- [ ] 高风险任务必须 `blocked`，不得执行绕过审批/风险边界的动作。
- [ ] 所有步骤都必须有 trace；失败步骤、阻断原因和下一约束可回读。
- [ ] 验证重启后 trace/lesson 仍可读；不能只验证内存对象。

## 三、C线：合同、fixtures 与联调测试

C线不开发业务功能，只做 `schema / fixture / validator / integration test / report`。

### C1：schema validation 脚本

- [ ] 以 `shared-contracts/validators/validate_fixtures.py` 为唯一公共验证入口。
- [ ] 覆盖 B线与 R线所有任务包要求的 fixtures。
- [ ] 所有合法 fixtures 通过。
- [ ] 对每个非法 fixture 输出具体字段错误并返回非零退出码。
- [ ] 验证器不得写真实资料源、不得读秘密、不得执行 fixture 中的指令。

### C2：B → A TaskPack 投影测试

输入：`sample_taskpack.json`、`sample_obsidian_projection.json`。

- [ ] 生成 integration report。
- [ ] 验收 `projection.target_path` 合法且在允许根目录内。
- [ ] 验收 `write_policy == dry_run`。
- [ ] 验证禁止写入正式 Obsidian Vault；路径逃逸、绝对外部路径和非 dry-run 均失败。

### C3：B → A Trace 报告测试

输入：`sample_execution_trace.json`。

- [ ] 验收 `trace_id` 存在。
- [ ] 验收 `task_id` 存在。
- [ ] 验收 `status` 属于 schema 合法枚举。
- [ ] 验收 `steps` 非空且每一步有可核对状态/证据。
- [ ] 缺 trace、缺 task、空 steps、非法 status 必须失败。

### C4：B → A MachineLesson 测试

输入：`sample_machine_lesson.json`。

- [ ] 验收 `lesson` 非空。
- [ ] 验收 `anti_pattern` 非空。
- [ ] 验收 `next_constraint` 非空。
- [ ] 验证 MachineLesson 来源 trace 可追溯，不能由无证据的自由文本伪造。

### C5：A → B CoursePack 测试

输入：`sample_course_pack.json`。

- [ ] 验收 `course_id` 存在。
- [ ] 验收 `sections` 存在且非空。
- [ ] 验收 `cards` 存在且结构合法。
- [ ] 验收 `review_items` 存在且可被 B线吸收。
- [ ] 验证缺字段、空数组、重复 ID、错误来源均失败。

### C6：生成联调报告

输出：`reports/B_C_integration_report.md`。

- [ ] 报告逐项列出通过项。
- [ ] 报告逐项列出失败项及具体字段/路径。
- [ ] 报告逐项列出 blocked 项及阻断原因。
- [ ] 报告给出下一步修复建议和回滚边界。
- [ ] 报告引用真实命令、退出码、fixture 哈希和运行时证据；不能只复制任务包文字。

## 四、项目雷达线：R1 → R6

R线不负责真正发送通知；第一阶段只负责收集结构、筛选表、评分、Profile、IntakeCard 候选、fixtures 和 schema validation。

### R1：新增 schemas

- [ ] 确认并冻结：`daily_brief.schema.json`、`github_project_candidate.schema.json`、`open_source_project_profile.schema.json`。
- [ ] 为三类 schema 准备合法和非法 fixtures。
- [ ] 全部合法 fixtures 通过 jsonschema validation。
- [ ] 非法字段、缺字段、错误类型、风险值越界均 fail closed。

### R2：新增 Project Radar 模块骨架

- [ ] 保持目录边界：`Inspiration-Research/project_radar/collectors/`。
- [ ] 保持目录边界：`Inspiration-Research/project_radar/scoring/`。
- [ ] 保持目录边界：`Inspiration-Research/project_radar/outputs/`。
- [ ] 保持目录边界：`Inspiration-Research/project_radar/filters/`。
- [ ] 模块骨架只定义合同和边界，不自动 clone、安装或执行候选项目。
- [ ] 为每个目录增加最小 import/contract 测试。

### R3：实现筛选表生成器

输入：`github_project_candidate` 列表。

输出：`daily_github_ai_project_screening.csv`、`daily_github_ai_project_screening.md`。

- [ ] 字段完整：`repo`、`category`、`summary`、`recommended_target`、`absorption_mode`、`risk_level`、`scores`、`next_action`。
- [ ] CSV 与 Markdown 使用同一排序和同一输入快照。
- [ ] 空输入、重复 repo、缺 repo、非法 URL/许可证/风险值均有明确处理。
- [ ] 输出不包含 token/key、网页指令或未验证的安全/质量结论。

### R4：实现项目评分器

- [ ] 分别计算：`token_saving`、`efficiency_gain`、`local_first`、`system_fit`、`risk_penalty`、`total`。
- [ ] 验证评分范围、权重、风险扣分和总分可解释。
- [ ] 验证 critical 风险不会被高分覆盖。
- [ ] 相同输入产生稳定结果；缺字段和非法数值 fail closed。

### R5：从高分项目生成 IntakeCard

- [ ] 仅允许 `total >= 3.5`。
- [ ] 必须满足 `risk_level != critical`。
- [ ] 必须满足 `absorption_mode in adapter/direct/reference`。
- [ ] 不满足任一规则的项目只能进入 review/blocked，不得生成可执行吸收任务。
- [ ] 生成的 IntakeCard 回到 B2 schema/字段验收，并保留评分来源。

### R6：生成日报结构

输出：`daily_brief_YYYY-MM-DD.json`、`daily_brief_YYYY-MM-DD.md`。

- [ ] 包含：`gold`、`design`、`technology`、`ai`、`github_ai_projects`、`recommended_intake_cards`。
- [ ] JSON 通过 `daily_brief.schema.json`。
- [ ] Markdown 与 JSON 使用同一快照，不引入未验证项目或幻影统计。
- [ ] 不实现真正通知发送；只输出可供后续调度器消费的结构。
- [ ] 与 B2 IntakeCard、C1 validator、C6 report 可联调。

## 五、严格依赖顺序与完成门槛

1. `G0` 任务包身份/基线门禁。
2. `B1` 与 `R1` schema 固化。
3. `C1` 公共 validation 入口。
4. `B2 → B3 → B4 → B5 → B6` 核心链路。
5. `R2 → R3 → R4 → R5 → R6` 项目雷达链路。
6. `C2 → C3 → C4 → C5` 跨线投影/联调测试。
7. `C6` 生成最终 B/C 联调报告。
8. 只有上述任务各自达到 `VERIFIED`，才能称为 B/C/R 任务包完成；CI 绿色、模块存在、历史报告或安装器 PASS 都不能替代任务包验收。

## 六、任务包之外的独立发布门禁（不计入 B/C/R 完成）

这些是当前产品发布闭环的独立队列，必须单独追踪：

- [ ] PDF 依赖进入最终 runtime、bundle、安装器，并用真实 PDF 完成转换、job、delivery、receipt、重启读回。
- [ ] DOCX/PPTX/XLSX/CSV/PDF/HTML/PNG/JPG/MP3/WAV/MP4 的逐格式真实二进制矩阵完整；无真实样本的格式保持 `UNVERIFIED`。
- [ ] WebView 文件选择器点击级导入证据；HTTP API 结果不能替代 UI 证据。
- [ ] 失败 → retry → replay → delivery → receipt → restart readback 证据完整。
- [ ] `0.4.5/0.5.0` 版本身份漂移修复，并完成 exact-SHA 构建身份链。
- [ ] PR #68/#69 的 exact-head CI、merge-SHA main CI、构建来源和安装器内容回读。
- [ ] NSIS 生命周期、便携 internal preview、签名/发布资格分别验收；不以内部预览替代正式发布。
- [ ] 最终正式发布决策仍保持 fail-closed，直到所有宣称能力均有安装版证据。

## 七、状态报告格式

每次推进只报告：

```text
任务 ID
状态：UNVERIFIED / IN_PROGRESS / BLOCKED / VERIFIED
实际输入
实际输出
命令与退出码
证据路径
未完成项
回滚边界
```

不得报告单一“完成百分比”，不得把源码存在、单测通过、安装器启动或公开 Release 其中任一项扩展为整个任务包完成。
