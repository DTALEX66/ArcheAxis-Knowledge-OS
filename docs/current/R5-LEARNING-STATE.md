# Core FSRS 状态事务

本轮实现入口：`POST /api/v1/learning/reviews`。请求以
[review.schema.json](../../packages/contracts/learning/v1/review.schema.json)为准。
只有human身份可写；机器403，未知字段（包括客户端schedule_state）422。

必填item_key、client_event_id、correct。rating可省略：正确映射Good=3，错误映射Again=1；
显式rating=2/3/4要求correct=true，rating=1要求false。now可省略，由Core在写事务内取UTC时间；
显式时间须有日期、时间和时区，非法值400。客户端重试必须复用事件键及同一请求内容。

Core先检查幂等键，再从该item最后一个成功FSRS事件恢复state、step、stability、difficulty、
due、last_review；没有状态才初始化新卡。Python只计算，不打开数据库。
完整调度状态放入learning_events.outcome.schedule，与事件键/原收据在同一事务提交；
next_review保存原始精确到期时间，即使next_review_days=0也不丢分钟级调度。
未新增数据库表或迁移schema，旧事件、备份表集合保持原状。

首次成功201，完全相同重放200且duplicate=true，不再调用Python；同键不同item、结果、rating或now为409。
响应含event_id、streak_after、next_review_days、next_review、schedule_authority、schedule_state。
调度器不可用时仍追加人类复习，authority=unavailable、next_review=null、next_review_days=-2；
不走阶梯，不抹掉先前成功状态。同一失败事件重试返回原失败收据。

旧`/api/v1/learning/events`及其原幂等摘要保留，旧事件键须继续通过原入口重放。
新入口不将旧阶梯事件伪转换为FSRS状态。默认学习UI还需切到新入口；当前实现不等于GUI验收。
已验证Core API→真实FSRS worker→同库重开→继续复习；未证明独立发行包或真实用户库迁移。
SchedulerClient默认20秒，显式测试/调用上限60秒；stdin、stdout、stderr及进程退出共用截止时间。
请求/stdout各限64KiB，stderr限32KiB；超限、超时和异常退出均返回不可用，不生成阶梯间隔。
超时后终止并等待直接FSRS子进程，检查IO线程退出；管道被外部持有超过1秒则报告cleanup incomplete。
这是直接FSRS进程的治理，不是任意后代进程沙箱；系统kill/wait本身没有额外期限。
真实Windows进程句柄已证明超时子进程退出，Core事务级故障注入已证明复习保留且后续事务可写；
后者未走真实HTTP失败路由，不冒充默认GUI取消或任意孤儿进程清理通过。

回滚：停止新入口调用，成对撤回新增API/应用适配和domain函数；保留追加事件，不删除用户数据。
