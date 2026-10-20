# BE10 snapshot五接点独立静态复核

观察时点：2026-10-19T07:39:55.758983+08:00。**NO_REMAINING_BLOCKING_FINDING_WITHIN_STATIC_REVIEW_SCOPE**。产品仍待root统一门禁；不等于真实UI、模型、安装或完整BE10资格。本任务未运行测试/构建/服务、不写产品/public。

原P2已向root报告且修复关闭：Reader旧身份按钮曾发布整个snapshot，DocumentSnapshot默认按钮亦发布editor_json；publishDiagnostic把正文保留到全局entries，Reader过期/关闭clear无法清该副本。现Reader16使用showRaw=false，DocumentSnapshot13默认true保留其他调用行为；Reader127身份payload删除editor_json，fallback15不再声称正文留在诊断。新增Reader测试108–120用真实useDiagnostics观察，证明全文结构按钮不存在、identity点击不发布正文，关闭/invalidated后亦无正文。该新增例不单独推进TTL，但正文根本不进入entries，副本源已删除；既有expiry本地状态例75–76仍在。此为静态回读，实际测试结果由root收据给出。

五接点观察：

- API snapshot31–124：human准入、64KiB严格Handoff/context输入；同DEFERRED transaction读取existing workspace/restore epoch及原历史版本，先核raw长度≤8MiB、原UTF8 SHA对stored/reference，再解析doc；不混当前title/projection/blocks、不写业务DB。current_version变化返回STALE旧版本，不换新；入队前、事务后及序列化后TTL核对，24MiB有限响应。源认证/选区都UNVERIFIED，无执行/接纳。
- Snapshot Rust/JSON Schema/生成验证器：顶层未知字段拒绝，CURRENT/STALE、LOCAL_HUMAN_READ_ONLY、UNVERIFIED及false权限固定；editor_json保留未来结构，由只读projection错误边界处理。状态/哈希是既有身份绑定，不提升签名或来源资格。
- finite bridge：固定新operation/POST路由，不接受任意URL，只有对象body；请求64KiB、响应24MiB、3秒有限传输，既有host保管token。api/core.ts105–108验证具体Snapshot DTO，HTTP错误不会作为成功正文。
- projectHandoff.ts27–64：UTF8输入限额、解码键重复拒绝/深度限制、严格context与范围、期限；preview与原提案完整相等且规范fingerprint验真；snapshot绑定原producer/epoch/reference/proposal hash/期限；不将旧preview状态当读时状态。
- Reader及SpaceView page16：显式预览后再显式读全文；125依snapshot参考状态披露CURRENT→STALE，与120“预览时”分开。关闭/输入变更/恢复/invalidation/过期清正文，generation与mounted/open/visibility隔离迟到响应；恢复暂停，停放页面关闭portal；关闭使用可见焦点返回。SpaceView145复用交换组件并列挂载，不走Library.openDocument或普通document_version，不写workingstate。全文/非whole选区UNVERIFIED说明明确，未知来源与consumer声明未提升。

现有测试源码覆盖API真进程拒绝/历史版/坏hash/恢复/超限/全表前后不变、native owned Core有限调用、前端schema反例/实际指纹/状态变化/原草稿/晚回/期限/焦点。未声称测试全部已执行；此轮也未独立复跑root正在跑的统一测试。原policy报告边界不变，外部正文投递、OS URI、安装与完整用户旅程仍NEXT。

精确源码SHA见READBACK.json；root源码尚在统一测试阶段，后续若变更以实际最终hash与门禁为准。本报告仅写ignored目录。
