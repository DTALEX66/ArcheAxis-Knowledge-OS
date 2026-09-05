# HANDOFF — T15 Windows 集成、全格式与双侧资格验收（CODEX）

交接人：DeepSeek（集成者）· 2026-09-05 · 难度：高 · 目标代理：CODEX
依赖：T01/T03/T04/T05/T06/T07/T08/T09/T10/T11/T12/T13/T14（全部前置）

## 目标
- 按任务包 07-ACCEPTANCE.md 在干净 Windows 包执行真实 UI/进程/本地模型/云端与 MCP 链；
- 每核心格式贯通到知识及使用；批量、断网、错回执、崩溃恢复；
- 出当前 SHA/tree、fixture/模型版本、产物哈希及逐项结果；问题退回所属任务；
- G01–G16、G17A、G18 候选资格与 G19 吸收完整性逐项记录；required 项不能 skip 算通过；
  核心格式功能通过、精度分层实测；不得用手写 PASS 代替用户操作。

## 上下文
- 07-ACCEPTANCE.md（任务包）列出 G01–G19 门清单与证据要求；
- 各前置任务证据目录：docs/authority/taskpack-0905/Txx/（DeepSeek/CODEX 分别落盘）+ reports/vnext/；
- 资格脚本位置建议 scripts/ci/qualify_vnext.py（本任务允许路径内创建）。

## 允许路径（任务包 T15）
tests/journey/**、tests/integration/closed-loop/**、scripts/ci/qualify_vnext.py、reports/vnext/**。

## 验收（任务包 T15）
- G01–G16、G17A、G18、G19 逐项记录；required 不能 skip；
- 禁止 mock 回退成功；禁止以构建/手工 JSON 冒充闭环。

## 环境事实
- 干净 Windows 包候选：本地 Green/发布流程产出或临时 staging（packaging 脚本 T16 前可用手工 staging）；
- 本地模型链可用；云端链凭据缺（G 门中云端相关项在无凭据时记录 BLOCKED-CREDENTIALS 而非 PASS）。

## 输出契约
- qualify_vnext.py 可重跑且逐项输出证据（真实命令/日志/哈希）；收据 reports/vnext/T15-qualification-*.json；
- 报告：通过/失败/阻塞清单 + 问题→任务回退表 + 精确 SHA。
