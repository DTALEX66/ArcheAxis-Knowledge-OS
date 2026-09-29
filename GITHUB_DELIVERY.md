# GitHub 交付参考（可选 WORK-LAB 协调工具）

本仓库独立运行。交付以本仓库 `AGENTS.md`、当前 Authority 与 GitHub 规则为准；WORK-LAB 工具不是构建、测试或发布的必需依赖。

当前仓库身份：`DTALEX66/ArcheAxis-Knowledge-OS`。实际传输协议由 Git remote、URL rewrite 和 SSH 覆盖决定，不能从文档里的 URL 推断。

如需使用 WORK-LAB 的可选工具，先确认其当前代码中存在以下入口：

```powershell
$upload = 'D:\All projects\WORK-LAB\packages\client-neutral-core\scripts\github_upload_accelerator.py'
$review = 'D:\All projects\WORK-LAB\packages\client-neutral-core\scripts\github_review_accelerator.py'
python $upload --repo ArcheAxis-Knowledge-OS --repo-root 'D:\All projects\ArcheAxis-Knowledge-OS'
```

上例只诊断。实际写入须在任务专属分支上明确给出 `--message` 和重复的 `--file`（仓库相对文件路径）。脚本默认只本地提交；远端交付另加 `--push`，创建 PR 再加 `--create-pr`。本项目自身的测试和交付门禁仍须独立执行。

```powershell
python $upload --repo ArcheAxis-Knowledge-OS --repo-root 'D:\All projects\ArcheAxis-Knowledge-OS' --message 'docs: update delivery guide' --file GITHUB_DELIVERY.md
python $review --repo DTALEX66/ArcheAxis-Knowledge-OS --pr <PR号>
```

审核工具仅提供只读预检建议；`APPROVE` 不等于 GitHub 审批、合并或发布。认证身份、保护规则和 required checks 必须以当前读回为准。
