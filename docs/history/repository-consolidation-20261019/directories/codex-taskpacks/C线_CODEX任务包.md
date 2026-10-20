# C线 CODEX 任务包

## 目标

建立 A线和B线之间的合同、fixtures 和联调测试。

## C线不开发业务功能

C线只负责：

```text
schema
fixture
validator
integration test
report
```

## 第一批任务

### Task C1：schema validation 脚本

输出：

```text
shared-contracts/validators/validate_fixtures.py
```

验收：

```text
所有 fixtures 通过 schemas 校验
错误时输出具体字段
```

### Task C2：B → A TaskPack 投影测试

输入：

```text
sample_taskpack.json
sample_obsidian_projection.json
```

输出：

```text
integration report
```

验收：

```text
projection target_path 合法
write_policy 为 dry_run
```

### Task C3：B → A Trace 报告测试

输入：

```text
sample_execution_trace.json
```

验收：

```text
trace_id 与 task_id 存在
status 合法
steps 非空
```

### Task C4：B → A MachineLesson 测试

输入：

```text
sample_machine_lesson.json
```

验收：

```text
lesson / anti_pattern / next_constraint 不为空
```

### Task C5：A → B CoursePack 测试

输入：

```text
sample_course_pack.json
```

验收：

```text
course_id / sections / cards / review_items 存在
```

### Task C6：生成联调报告

输出：

```text
reports/B_C_integration_report.md
```

内容：

```text
通过项
失败项
blocked 项
下一步修复建议
```
