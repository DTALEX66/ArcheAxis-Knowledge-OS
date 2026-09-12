# R5 X04-01：单 Core 人/机启动身份契约

状态：Core/C# 已本地实现并通过定向真实进程测试；不是完整桌面/Q00/Q01验收通过。2026-09-13，依据
`crates/archeaxis-api/src/launch.rs`、`apps/ArcheAxis.Desktop/CoreSupervisor.cs`
及 R5 X03/X04，基线 c06b234ca335b9cbb2c1fde270851e2390c36b89 + 当前工作区。

## 决定和边界

继续只有一个 Core/Store 写入同一数据库。原生宿主拥有两份启动秘密，通过继承 stdin 一次传入；
人类请求使用 launch_token，机器侧 adapter 只能拿到 machine_token。机器不能调用令牌签发接口，
因为本契约不新增 HTTP 签发接口。两者绑定同一 session_id/工作空间，Core 重启即全部失效。
这解决角色隔离，不证明自然人实际操作、可信曝光、答题独立性或机器知识已获人工审核。

新协议为 `archeaxis.desktop-launch/v2`，schema 在
[`launch.schema.json`](../../packages/contracts/bootstrap/v2/launch.schema.json)。这是启动协议的独立主版本，
不是向未协商的 /api/v1 或旧启动格式偷偷增加字段。无 protocol 的旧输入严格保持原 actor 规则；
v2 必须显式 protocol、actor=human、两个64位hex令牌及32位hex会话ID。v2 不能缺字段后退回 v1。
未知 protocol、未知字段、重复 JSON key、令牌相同均在创建数据库/绑定监听器之前拒绝。
JSON Schema 不表达两个属性值不相等、重复 JSON key、文件系统安全性，Core 必须另作语义校验。

## 精确载荷与消费者

```json
{
  "protocol": "archeaxis.desktop-launch/v2",
  "actor": "human",
  "launch_token": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "machine_token": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "session_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
```

以上全部为公开合成测试值，产品必须用系统 CSPRNG 每次生成；不得写入 argv、日志、收据、持久配置或前端资源。
`text_worker` 可缺失/null；对象仍为现有 python/script/staging 三个路径，沿用 Core 的绝对路径、
禁 E/UNC/父目录、逐祖先拒绝链接以及解释器/脚本存在性校验。缺 worker 保持显式不可执行，不能伪称解析完成。

Core 的认证中间件保持 `x-archeaxis-launch-token` 唯一头、固定长度恒定工作量比较和 Origin 拒绝。
命中主令牌时覆盖请求 actor=human，命中机器令牌时覆盖 actor=machine；客户端头/body/model名均无权改变它。
`system/version` 在 v2 下回读 `launch_protocol` 和匹配的 `actor`，不返回任何令牌。
宿主握手必须核 protocol/actor/session_id/workspace_db 全部匹配后，才能交付机器连接信息给 adapter。
协议匹配失败即停止自己的 Core，不自动重试旧协议把机器请求送到人类令牌。

实施文件及接口：

- `crates/archeaxis-api/src/launch.rs`：解析 legacy/v2，集中语义验证；Session保存两个不可日志化令牌；
  authenticate选择可信角色，保留所有路由/Origin/重复头约束。
- `apps/ArcheAxis.Desktop/CoreSupervisor.cs`：StartAsync生成v2载荷并检查两种身份的握手；
  `SendAsync`使用人类令牌，`SendMachineAsync`使用机器令牌。当前项目adapter通过宿主方法调用，
  不直接导出连接对象或令牌；响应RequestMessage的认证头在返回前清除。后续跨进程adapter若需
  接收机器连接对象，必须单独实现受控stdin传递，不暴露人类令牌，不序列化到浏览器、磁盘或诊断。
- DeepTutor由项目侧adapter代为调用Core，浏览器不直持Core令牌；上游宿主接线仍是X03任务，
  本决定没有授权修改共享DeepTutor源码或复用其用户凭据。

## 验收与迁移

必须在同一个真实Core进程完成：主令牌创建个人accepted定义成功；机器令牌创建candidate成功，
机器伪造human头/body仍不能accepted、自审或写人类反馈；两者读回同一工作空间。
未知/相同/重复令牌头、旧会话令牌、Origin全部拒绝；重启两令牌失效；未授权请求仍不可得到版本/工作空间信息。
对旧格式重跑现有 launch_auth/workspace_ownership；C#握手、取消、端口冲突与生命周期同步更新。
启动JSON负例要证明拒绝发生在数据库创建前，不能只在JSON Schema测试里判失败。

无数据库迁移。回滚必须成对回退Core与宿主到旧启动格式，并停用机器adapter；不得为兼容旧Core将
machine_token替换成人类令牌。既有DB、事件、历史收据都保留。schema结构验证只证明载荷约束，
不证明生产认证、单写者、真实人机回流或Q00/Q01通过。

## 尚未闭合

该决定仅处理启动身份子项，不覆盖学习事件曝光/原回答版本字段、主张关系或结构寻址。
Core/C#已实现；只读独立代码审查未发现已确认提权问题，审查提出的真实权限/重启用例缺口和
响应认证头残留均已处理。共享缓存只读，按Cargo.lock核验的85个crate及公开索引已复制到项目缓存，
离线构建成功。Rust14项测试及C#真实Core/Python链路通过，见R5-EXECUTION对应run。
DeepTutor进程接线、默认窗口交互、人类曝光语义、独立完整审计仍未闭合。
