# 低额度交接监控

本项目把账户通用 Codex 周期的“剩余百分比”作为外部输入，由
`scripts/maintenance/prepare_low_quota_handoff.py` 生成项目内审计报告。脚本不读取账户私有状态，也不读取 `.codex/`、`.zcode/`、`.hermes/`，不自动暂存、提交或推送。

每次额度检查运行：

```powershell
& .\\.venv\\Scripts\\python.exe scripts/maintenance/prepare_low_quota_handoff.py `
  --remaining-percent <实时百分比> `
  --output .project-local/runs/low-quota-handoff/current.json
```

当剩余值大于 2% 时报告为 `MONITORING`；小于或等于 2% 时报告为
`UPLOAD_REQUIRED`，并列出当前分支、HEAD、上游差异、工作树状态和可安全纳入交接的已跟踪权威文件。此时由执行者按精确路径整理错误总结、问题清单和交接摘要，完成提交后尝试推送，并以远端 SHA 回读确认双端一致。私有目录和未跟踪用户资料永远不会被自动纳入。
