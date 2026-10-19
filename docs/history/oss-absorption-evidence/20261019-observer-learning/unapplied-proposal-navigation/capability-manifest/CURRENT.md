# OSS-HUB-003 能力包manifest准备提案

状态：**ISOLATED_PROPOSAL_PASS / NOT_APPLIED / OSS-HUB-003 PARTIAL**。产品唯一writer为root，本目录仅ignored提案与隔离验证；没有正式产品写入。

- 可应用补丁：`capability-manifest.patch`，SHA-256 `8557b74fc2bd1219bb7dd146fcc79ca56d4d9245608f66c7eda4a3ec9b2c6e55`；7个全新文件，`git apply --check` exit0。
- 前后身份：`code-manifest.json`。7份before均null（本观察时正式目录不存在），after为冻结字节；无lib.rs/依赖/lock/配置写入冲突。`proposal/`保留可审阅完整文件。
- 原有公共来源：`SOURCE-REFERENCES.json`，仅CAP map、68供体crosswalk、worker routes、Core API Cargo、一个公共schema及LICENSE的精确镜像；没有复制环境、账户、私人资料、共享工具、模型或业务库。
- 正式字段与复用说明：`proposal/docs/contracts/capability-package-v1.md`。支持六贡献点、固定ID/版本、兼容、来源hash、权限/数据/网络/费用声明、依赖/许可、有限I/O、取消/退出/UNKNOWN、降级损失、更新/回退策略。不包含安装/连接/启用/资格状态或任意命令/endpoint/provider/密钥。
- 当前实际验证：`pytest-acceptance.json`（57共享case及语义/原字节/负对照，共122项PASS）、`typescript-acceptance.json`（现有TS5.9.3严格编译与@ts-expect-error负例PASS）、`ruff-acceptance.json`（3份新Python PASS）；child均exit0且proposal字节在门禁期间不变。
- 失败：`FAILURES.md`，首轮Windows超长PYTEST_CURRENT_TEST错误及原回执/日志保留；Ruff中间3项诊断已修。各组不累计为整仓通过。

## 应用前后最小门禁

root先确认本任务7个目标仍不存在，复核patch/hash并git apply --check后单writer应用。用现有canonical dev runner执行`tests/contract/test_capability_package_contract.py`，再运行生成器--check、现有TypeScript检查和changed-file Ruff；若已引用公共Schema发生变化，先分析兼容性及明确更新fixtures，不能静默改hash追绿。维护既有唯一进度与来源导航，不建立第二registry或状态台账。

本prepare切片**没有Rust Core DTO/正式API准入、page17真实包绑定、外部MCP、安装/启用/更新/卸载/回滚运行时、模型路由迁移、真实许可资格或原生/安装/Owner验收**。validate_manifest只验证声明及公共引用，不是授予安装/执行权限的admission gate。未知许可/版本仍未核实。

BE10 agent已协调：本轮handoff manifest_identity保持严格UNKNOWN-only，不重复复制已知identity类型；以后root串行应用并实现真正known identity校验，再升级引用。此处已知identity定义为schema/package_id/version/原manifest UTF-8字节SHA；单有hash不证明注册、可用、接纳或授权。

独立验证树在`validation-workspace/`，脚本命令/环境/日志由回执记录；不能将这个镜像当当前正式源码或生产环境。没有服务/浏览器/后台进程启动。没有执行网络或付费操作。所有新写入都在本ignored目录。
