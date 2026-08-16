# GitHub 交付（上传与审核）指南

> 由 WORK-LAB workflow-assistance 增强模块提供统一的 GitHub 上传/审核加速能力。
> 目的：让本项目的上传云端库与审核流程标准化、加速、可审计。

## 1. 云端库

- 仓库：DTALEX66/ArcheAxis-Knowledge-OS
- 远程：https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git
- 凭据：git credential manager（gho_ OAuth token，git credential fill 获取，不硬编码、不落盘）

- 注意：remote 为 HTTPS，凭据走 git credential manager。

## 2. 上传加速（把改动推上云端库）

```bash
python "D:\All projects\WORK-LAB\10-workflow\workflow-assistance\scripts\workflow\github_upload_accelerator.py" --repo ArcheAxis-Knowledge-OS
python "D:\All projects\WORK-LAB\10-workflow\workflow-assistance\scripts\workflow\github_upload_accelerator.py" --repo ArcheAxis-Knowledge-OS -m "feat: your change summary"
```

- 安全：无 -m 只体检（DIRTY_NO_ACTION），绝不误提交/误推送；不 force-push。

## 3. 审核加速（PR 合并前检查）

```bash
python "D:\All projects\WORK-LAB\10-workflow\workflow-assistance\scripts\workflow\github_review_accelerator.py" --repo DTALEX66/ArcheAxis-Knowledge-OS --pr <PR号>
```

一次拿到 mergeable / mergeable_state / CI check-runs → APPROVE 或 BLOCK + 理由。

## 4. 使用建议
- 每次改动先体检再提交，保持云端库与本地一致；
- 合并前跑审核加速器确认 APPROVE；
- 提交信息用 conventional 前缀（feat/fix/docs），加速器自动补；
- 共用库内容（大文件/权重）不上传，只上传链接与列表；
- 脚本本体在 WORK-LAB 仓库（单一来源），本项目只引用不复制。
