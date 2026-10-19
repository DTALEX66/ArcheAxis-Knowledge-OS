# 最小完整切片及证据边界

原BE10本期要求握手、能力发现、对象引用/状态和只读关联，以及五类handoff准备；真实写入是后阶段。本提案只将已经应用的纯投影接到既有真实CLI消费者，不新增端口/注册器/执行框架。

四类提案都从用户明确输入的strict Payload读取有限用途metadata，经专用ObserverClient真实握手和固定objects读结果确认冻结引用；context保留来源/选区/用途和REFERENCE_METADATA_ONLY，task为明确目标且NOT_GRANTED，asset格式/损失保持UNVERIFIED/UNKNOWN，candidate保留证据和PENDING_HUMAN_REVIEW/NOT_ASSESSED。receipt用严格原提案计算规范digest绑定，保留UNKNOWN/CONFLICT。PREPARED仅为metadata准备，不是投递或接纳。

新6项真实进程检查覆盖五类positive、摘要绑定、上下文/任务/资产/候选不扩权、所有业务表前后不变、无title/body/token/路径泄漏；未列入/错误version/hash和真正human fixture改版后旧引用拒绝；错误CAP/goal、receipt绕过原提案、身份错误/过期PREPARED/不一致状态拒绝；过期原件可产生UNKNOWN而不折算成功；断连不使用缓存成功；额外URL/命令/snapshot/正文/执行scope/argv拒绝；错误token/consumer/producer、非法auth根字段、格式损坏和超限stdin有限拒绝，不回显输入。

仅测试fixture通过human接口制造一次版本变更；CLI没有human凭据，也不创建业务DB。真实Core均由测试以tempfile目录和端口0启动，仅Drop kill+wait自己创建的进程；没有用户服务/浏览器启动。未逐个独立记录Core PID/端口，因此不宣称独立端口审计完成。

失败轨迹：首轮19项PASS属于补充auth负例前版本；owned镜像负对照真实101为预期失败并保留原日志；最终恢复后20项PASS。编译有既有domain/application warning，未改无关源码。没有安装、模型调用、收费、网络外发、真实私有资料、跨项目写入。

精确命令/开始结束时间/退出码/原回执hash见validation.json。最终patch、manifest和当前入口见CURRENT.md。正式产品仍NOT_APPLIED，须root串行应用后统一验证。
