# B+C 线联调测试清单

## 1. Schema 测试

- [ ] course_pack.schema.json 校验 sample_course_pack.json
- [ ] context_pack.schema.json 校验 sample_context_pack.json
- [ ] taskpack.schema.json 校验 sample_taskpack.json
- [ ] execution_trace.schema.json 校验 sample_execution_trace.json
- [ ] machine_lesson.schema.json 校验 sample_machine_lesson.json
- [ ] intake_card.schema.json 校验 sample_intake_card.json
- [ ] engineering_contract.schema.json 校验 sample_engineering_contract.json
- [ ] obsidian_projection.schema.json 校验 sample_obsidian_projection.json

## 2. B线内部链路测试

- [ ] Research Note → Intake Card
- [ ] Intake Card → Engineering Contract
- [ ] Engineering Contract → ContextPack
- [ ] ContextPack → TaskPack
- [ ] TaskPack → ExecutionTrace
- [ ] ExecutionTrace → MachineLesson

## 3. C线对接测试

- [ ] TaskPack 可被 A线渲染为 Obsidian 任务页
- [ ] ExecutionTrace 可被 A线渲染为 Trace Report
- [ ] MachineLesson 可被 A线渲染为机器经验页
- [ ] CoursePack 可被 B线吸收为 KB 输入
- [ ] EngineeringContract 可被 KB 转 TaskPack

## 4. 安全测试

- [ ] 包含 shell_exec 的 TaskPack 被 blocked
- [ ] 包含 delete_file 的 TaskPack 被 blocked
- [ ] 包含 token/private key 的输入进入 REVIEW
- [ ] obsidian_projection 默认 write_policy = dry_run
- [ ] 不存在直接 production apply

## 5. 验收标准

```text
B线可以不依赖 Obsidian 独立跑通。
A线可以不依赖 B线，用 fixtures 独立开发。
C线可以验证双方的输入输出合同。
```
