# 已冻结的运行配置与迁移原件

状态：FROZEN_HISTORICAL_NOT_RUNTIME_CONFIGURATION。此目录不参与自动资源发现、模型选择或运行配置。

`MANIFEST.json` 记录两个旧模型 profile 的原路径、归档路径、完整 SHA-256 和字节数；
原件逐字节保留，旧位置已移除。原 profile 的实测声明只属于其历史时间点。
`ollama-local-runtime.retired.yaml` 是从当前能力清单退出的旧服务条目。

当前运行选择及绑定入口见 [项目外置依赖说明](../../environment/EXTERNAL_DEPENDENCIES.md)。
OCR 现行调用方使用 `config/model-profiles/current-local.yaml`；历史模型池只用于历史合同回归。
恢复归档文件不自动重新激活旧端点或旧测量结论。
