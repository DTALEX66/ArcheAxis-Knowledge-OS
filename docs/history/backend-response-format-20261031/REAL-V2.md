# V2 有限真实模型验证：首题正确，拒答题达到输出上限

这次是新请求合同的有限组件验证，保留旧 real1/ar2 原失败。V2 不给 schema 正确值，不改问题、材料、prompt、模型、端点、2048 token、Core 120 秒及客户端 135 秒预算；不去围栏、不修补模型输出、不自动重试。

执行链为：`v2meta-fdcea03b` 两次精确 loopback inventory GET 均 200 → `v2plan-7e4a093f` 冻结 52 个选择成员及当期 metadata → `v2pre-aeeb40a8` preflight-only 通过、主程序未执行 → `v2real-e06657fb` 实际运行。模型清单不证明 loaded/ready 或普遍支持 schema。前三 run actual/wrapper 均 0；真实 run 的 adapter、entry、wrapper 均 1，source_consistent=true，clean 源码为 `152e66f6f58d163276c5899f2ea34f0968a32ed6`；Core 构建仍绑定此前 clean `89b21d4e`。

使用独立合成库、当前 Core/生产 worker 与原 bpr1 Python；只复制 Core、launcher、两个 scheduler 小文件共 27,932,123 B，另生成新 profile。全部原 17 routes 和默认 text 保留，只有 machine.answer 改为冻结的当前生产 worker。原 bpr1 不改写；这不是原 bpr1 或完整新安装包资格。

| 观察 | 实际结果 | 解释范围 |
| --- | --- | --- |
| 既有 text job | 成功，转换内容等于冻结合成 CONTEXT | 与模型推理分列 |
| 候选 package 授权负控 | HTTP 403 | 候选没有自动取得使用权 |
| 原题 before | HTTP 200；原始 JSON 为 frozen=true、writer=Rust Core；format_validation=VALID；固定量规 CORRECT | content/finish_reason=stop；worker 10.75 秒、输出 767 token；request/schema/hash/授权及持久 task 读回一致 |
| 拒答题 before | HTTP 503、INVALID_OUTPUT、answer_published=false、execution_state=UNVERIFIED | content/finish_reason=length；输出 2048=max_tokens、worker 23.42 秒。完整性守卫在 JSON 结构检查前拒绝非 stop 内容；不是本次 NO_FINAL，也不能推断具体 JSON 语法错误或普遍不支持 schema |
| 后续题与干预 | 未执行，首次失败停止 | 未做迁移前后、package 干预采用/使用、纠正或复测；学习效果 NOT_ESTABLISHED，F05 PARTIAL |

共 18 次 Core HTTP、两次正向候选请求；入口没有底层模型 transport 拦截，不能把候选计数当作全服务硬计量。首题 packet=null、asset_members=[]，前置 rule 成员采用和候选包准备不等于资产包干预生效。首题正确也不构成学习改善。

自有 Core PID 13056 terminate/wait 回收 exit1；精确端口 50971 的 IPv4/IPv6 两次观察 complete 且无 LISTEN。connect_ex=10035 仍 UNKNOWN，不称拒连、graceful 或全机 worker 清场。52 个选择成员、5 个混合成员与 override 指纹前后相同，root 另核当前 52 个文件完整 SHA；没有 cleanup/identity 次级错误覆盖主失败。选择成员身份不扩大为原包全部成员的重新资格。

root 首次只读检查脚本错把 runtime_before 当作 result 顶层字段，产生 KeyError；正确位置为 pre-inference-freeze。后继重新比较成功，原运行收据未改，该检查错误和目标 FAIL 分列保留。非作者独立复核及原始轻量收据 SHA 见 MANIFEST。实际进度仍沿唯一执行记录，不由本历史报告自动重试或提升预算。
