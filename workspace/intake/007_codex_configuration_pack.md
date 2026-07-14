# 007 Codex Configuration Pack

> Status: superseded. This intake is historical evidence; active policy moved to `AGENTS.md` and `docs/VERIFICATION_POLICY.md`. `.codex.example/` remains the only portable template.

## 目标

补齐 Codex 专用配置，但仍然只上传公开脱敏版本。真实 `.codex/`、连接器凭据、Token、API Key、SSH 私钥、会话状态都不进入仓库。

## 新增内容

| 分类 | 文件 | 说明 |
| --- | --- | --- |
| Codex 机器配置 | `config/codex_profile.yaml` | Codex 在 Cognitive-OS 仓库里的行为、权限、Git、网络、报告规则 |
| Codex 人读说明 | `workspace/configuration/CODEX.md` | Codex 配置分类、可上传/不可上传边界 |
| Codex 示例模板 | `.codex.example/config.example.toml` | 新电脑可参考的无密钥模板 |
| 模板说明 | `.codex.example/README.md` | 说明真实 `.codex/` 不应提交 |

## 关键边界

- 上传的是 Codex 配置模板，不是真实 Codex 本地配置。
- `.gitignore` 明确忽略真实 `.codex/`。
- `.codex.example/` 只用于存放公开模板。
