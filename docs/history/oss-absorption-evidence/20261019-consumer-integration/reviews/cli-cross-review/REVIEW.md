# BE10 CLI consumer 独立交叉复核

结论：**NO_BLOCKING_FINDING_FOR_CLI_CONSUMER_APPLICATION**。未发现产品实现的实际阻断缺陷；可由唯一writer串行应用本切片。BE10整体仍PARTIAL，外部产品、真实投递/执行、native/安装和Owner资格未获证明。

冻结patch SHA256：`aeb7e489f63a04e839512d48f7141662d90a4ebf8ae3cb642b6b14f35a88bf16`。4成员after与3份preimage均独立重算匹配；三个原验证回执hash也匹配。没有修改原提案或产品、没有重新运行已经通过的相同测试、未启动任何服务。

## 实际调用链与边界

- strict Input/Action仅从stdin反序列化，64KiB/5秒继承边界保留，argv一律拒绝；ClientAdmission私有token仅stdin存在，不进入输出。未知auth、URL、命令、snapshot、body、执行scope等字段严格拒绝，不能传入伪造已认证快照。
- prepare_handoff/prepare_receipt实际调用既有ObserverClient::connect；先真实握手，再固定GET objects。client只向明确admission的IPv4 loopback端口发有限GET，身份/namespace/workspace/restore epoch、协议、响应payload、有限大小/时间和总请求deadline均复用正式已应用客户端。
- snapshot由真实客户端读取，prepare检查每个冻结来源/版本/hash在allowlist；任务保持NOT_GRANTED、候选PENDING_HUMAN_REVIEW/NOT_ASSESSED、选区/格式UNVERIFIED、manifest UNKNOWN。receipt必须带严格original，经既有全DTO规范digest绑定及身份/到期/CURRENT检查，UNKNOWN/CONFLICT无成功映射。
- stdout成功是严格metadata DTO，失败为有限枚举码；没有输入、serde错误原文、token、HTTP正文或内部错误回显分支。CLI没有文件/DB打开、任意方法/URL、队列、重试或自动执行调用。

## 进程回归是否验证原问题

新6项确实启动owned临时Core与真实CLI：四类非回执及receipt正例、原提案digest匹配、全业务表前后快照不变、有限错误/无token与合成私人正文输出；真实human fixture改版后旧引用拒绝；断连不从caller缓存生成成功；错误CAP、身份、过期PREPARED和不一致状态均拒绝。额外字段/argv/认证错配与超限输入有真实子进程覆盖。

最终20项来自6新process+6旧observer process+8纯投影，非累计历史19项。owned镜像移除引用allowlist守卫后，真实新增回归失败101；恢复源码后重新编译20项通过。回执标注源一致、child/outer均0，红控保持预期FAIL。这里只审阅/核验已有证据，不将其升为正式产品消费已应用资格。

## 非阻断覆盖精度建议

超限stdin负例目前为重复合成标记组成的非法JSON，既可能命中大小门禁也可能命中JSON拒绝，因此它单独不能区分“大小限制消失但JSON仍拒绝”。实现的take(65537)+长度检查是明确有效的；后续如维护stdin边界回归，可改为一个原本合法的对象加足量JSON空白至64KiB以上，并与边界内合法输入成对检查。**本建议不要求扩大本轮应用范围或重复已通过测试。**

最小应用门禁仍按CURRENT：核对3 preimage/1新增目标后串行合入，实际仓库运行project_handoff_process、project_observer_process和project_handoff_projection，禁止将UNKNOWN/CONFLICT、无泄漏或无业务写入门禁降级。新CLI未随安装器分发，不能用可执行源码推导已安装消费。
