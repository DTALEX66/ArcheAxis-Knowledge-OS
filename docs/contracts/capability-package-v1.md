# 能力包manifest v1：有限声明准备合同

OSS-HUB-003准备切片。规范是`packages/contracts/v2/capability-package.schema.json`；TS来自同源生成器。没有新建CAP/供体/worker注册器、安装器、执行API或产品状态台账。**Schema合法及引用通过不等于已实现、已安装、已启用、已连接、已授权或许可合格。**

## 现有真值与字段

- `package_id/version`仅声明包的稳定身份与有限x.y.z版本；不自动向任何目录注册，不宣称某包存在。贡献点限`format_conversion/template/learning_activity/graph_visual/model_service/tool_protocol`。
- `capability_ids`只引用Atlas现有ID，由现有`config/capability-map.v1.json`读回；`resource_keys`及依赖引用现有68供体crosswalk的stable_key。68个历史条目不是68个可安装包，供体原分类/观察时间不由manifest改写。
- `runtime_capabilities`只可引用现有`services/python-workers/routes.json`且必须由所选CAP映射，不携带script、command、endpoint或provider字段。空列表允许未来声明，不能显示可执行。
- `compatibility.host_versions`在本切片特指现有Core API crate `crates/archeaxis-api/Cargo.toml`版本的半开区间；不代表桌面安装版或模型服务版本。合同引用为项目公共Schema路径与精确SHA，避免只凭crate版本推导接口兼容。依赖版本区间为声明，null明确未核实，不代替现场版本检查。
- `permissions`描述请求的用途、显式选定对象、网络和费用范围；始终要求单独显式grant。写入仍由Rust Core，凭据只由宿主引用，本地失败不静默发云端，execution/knowledge acceptance恒false。该字段不能成为执行grant来源。
- `license`保留UNVERIFIED或DECLARED_ONLY，允许未知expression为null；没有VERIFIED/商用通过字段。SPDX表达式仅声明，许可语义/上游权利和模型许可需另行审查。notice仅公共项目引用，不读取账户资料。
- `inputs/outputs`明确有限kind、Schema身份及字节上限，不内嵌prompt/正文/代码/任意JSON。
- `lifecycle`记录取消、有限退出、预算与UNKNOWN；已映射runtime必须声明host取消与bounded cleanup。取消与超时不等于provider已停止，仍需独立cleanup证据，不自动重试。
- `fallback`只允许明确unavailable或列明损失的degraded，不自动降级。`update`仅reviewed replacement，要求保存前一identity和原件，不授予数据迁移，也不证明回退运行时已实现。

## 身份、校验及隐私

`CapabilityManifestIdentity`包含schema/package_id/version/sha256，hash在manifest外计算，绑定**精确UTF-8原字节**而非重新排版后的JSON，避免自哈希及身份漂移。SHA不是签名、许可、接纳或运行资格。

`parse_manifest_bytes`限制256KiB、拒绝重复JSON键及无效JSON，只返回有限identity。严格Schema之外，`validate_manifest`执行现有CAP/catalog/routes联结、版本区间/当前Core兼容、路径与公共来源SHA、依赖唯一性、运行取消/退出、remote声明一致性检查。源引用读取前逐级拒绝symlink/reparse point、私有段、绝对路径、冒号和穿越；只读明确公共引用，最大4MiB，不扫描Home/磁盘或共享模型根。错误只返回有限码，不回显未受信输入。

installed/enabled/connected/configured/qualified等运行事实不进入manifest；它们继续由现有catalog qualification/运行观察/回执各自拥有。今后接入目录也只能投影，不能复制现有注册表或覆盖未知状态。MCP、模型、转换器等实际连接继续使用宿主现有协议和权限，不允许manifest启动任意代码。

## 准备切片验收与未交付

共享正反case覆盖六贡献点、声明远端、明确损失、拒绝安装状态/执行/自动接纳/静默云端/私有字段/任意命令、错误CAP/供体/route、契约SHA漂移、危险路径、错误版本与生命周期。Python真实Draft202012与只读semantic gate都应通过，TS从Schema生成且可编译；Schema结构检查不能替代semantic联结。

本切片仅Schema、生成类型、只读验证器与测试准备。Rust Core DTO/正式API准入、page17包投影、真实许可资格、资源/版本现场观察、安装/更新/卸载/回滚运行时、模型服务适配、外部MCP与原生/安装/Owner验收均未交付。OSS-HUB-003整体及OSS-HUB-004保持PARTIAL/NOT_EXECUTED相应状态。

BE10当前future handoff先保持manifest identity UNKNOWN；后继唯一writer应用本合同并做实际身份校验后，才可引用known identity。该引用也不提升执行/接纳权。
