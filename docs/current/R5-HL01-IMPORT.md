# R5 HL01 来源导入

HL01 注册表位于 `docs/current/R5-HL01-SOURCE-REGISTRY.json`，由
`scripts/generate_hl01_source_registry.py` 从 R5 `research-v15` 原件确定性生成。
当前注册表包含 215 条候选记录（40 方法、35 研究、36 学科、104 资源）。

导入必须显式指定数据库、注册表、命令幂等键和权益状态：

```powershell
$py = '.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe'
& $py scripts/import_hl01_registry.py `
  --db '.project-local/runs/<run-id>/knowledge.sqlite' `
  --registry 'docs/current/R5-HL01-SOURCE-REGISTRY.json' `
  --command-id 'hl01-r5-<stable-id>' `
  --rights-status permission-recorded
```

数据库必须先由现有迁移入口创建并应用 `workspace.sqlite` 与
`knowledge-governance.sqlite`。CLI 会在写入前校验注册表完整性、仓库根边界、
源文件 SHA-256 和字节数；完成后回读 command/job/receipt 与 Core 来源数量。
相同命令键可安全重放；权益状态或来源内容改变会拒绝重放。

注册表只登记候选来源，不激活当前知识资格。私有历史、外置模型库、共享工具库、
Green 目录、真实资料库、测试资料库和 `.hermes/.zcode/.codex` 不属于此 CLI 的
默认输入；需要这些内容时必须另行取得明确授权并建立独立收据。
