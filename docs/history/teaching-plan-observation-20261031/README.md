# 文字实践观察绑定计划版本：有限后端资格

这是既有 R6 E04/E07/E08 的有限历史证据，实际状态只导航[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)，不建立第二队列。

## 问题与最小实现

R6 原包要求纯文字即可记录实践，结果绑定原任务及计划版本，修订保留历史，无产物/工具/联网或掌握证明不阻断普通记录。原 Observation 仅允许无父项，无法关联 Proposal/Revision；以 Delivery 或 TeachBack 代替会改变含义或引入交付前置。

当前改动仅在 teaching::parent_shape 允许 Observation 的父项为 Proposal/Revision，保留 None。沿用同一 teaching_records、Core 写入者、已有 API、知识/课程绑定和撤回规则；TeachBack/Delivery 不放宽，无新增库、表、API、enum 或运行时。文本中的开始、自报、困难、跳过和替换仍为人工陈述，未实现专门实践状态机或独立掌握判定。

## 旧 Core 实际 HTTP RED

bkr-obsred1 在独立新 DB 用旧保全 Core（SHA 6b503641cb971ddc0135f79237e036c138cae0db8986cd3510ccefa06b75de6d）进行 10 个真实 loopback HTTP 调用。合成 FACTUAL_CLAIM/candidate 创建 201，Requirement/Proposal/Revision 201；同一未接纳知识的 Delivery 409，Observation 挂 Revision 实际 422。重启后 3 条原记录精确读回；teaching_records=3、learning_events=0、learning_assessments=0。

RED child/wrapper 0 表示成功复现缺口，不是产品通过。HEAD 71569d174b517a2fce7656e742a2040d26fdc1ff，dirty=false，source_consistent=true。原程序未复制或改写。自有 PID 38284/39568 均 terminate/reap exit 1，端口 59859/59873 关闭，不称 graceful。凭据只在内存，没有进入收据。

## 当前正式源码 API/domain GREEN

bkr-obsapi1 的 teaching_state_api 9/9（原 8 + 新 1），bkr-obsdom1 的 teaching_records 20/20（原 19 + 新 1）；均 actual child/wrapper 0、source_consistent=true、dirty=true。统一 HEAD 同上，稳定 patch 5bbc8d12939e37a3aa12e2723705bc77d0b079b7517258f25d6401fc9768444e；包含 root 协调的其他文档变更，本记录仅认领 MANIFEST 三份源/测试。

API 真实 Router/Store 夹具使用未接纳 FACTUAL_CLAIM/candidate，文字观察保存和两版计划关联通过，Delivery 仍 409；重开精确读回、幂等/冲突、机器拒绝、异知识拒绝、撤回保全与晚到写入拒绝通过，learning_events/learning_assessments 无新增。领域测试覆盖已有课程身份不得丢失/替换、知识一致、完整祖先导出/导入及撤回，not_scored 不变。没有任何模型、worker 或外部工具任务。

## 当前 release 构建与实际 backend 候选 HTTP GREEN

root 的 obuild1 执行 `cargo build --release --locked --offline -p archeaxis-api` 实际 child/wrapper 0；bpr1 producer/wrapper 0，正式 backend-only pack，三者与源码测试同 HEAD/稳定 dirty patch，source_consistent=true。最终 backend manifest 为 16,947 个成员，SHA `e2e22f8e04dfc9250d5eb6a293c3bbea310fa8b7aa3c2a7535f667129bb84a95`。本次仅核现有 manifest 与必要成员，未再遍历/重 hash 整包或复制程序。

obsgreen1 实际用包内 `runtime/python.exe -I -B` 执行已审 harness，加载同包 `start-backend.py` 与原 `worker-profile.json`，执行同包 release Core，fresh DB 位于 obsgreen1/artifacts/observation-data，不使用或覆盖候选 data。Core 19,177,472 B / SHA `07a9fe002eff4953cdada860e0cc4afe3395cee4d177c91b7dc15c8cbd0a9ee2`；launcher SHA `5a468951c9e7c324d66723ac1eb70cdf42508dafcdf37ffa3524998d2a9018f9`；profile SHA `62614ce3da3770b0bf93a02e33de54e7de174e0800d3e11f0c1a79a1e0b76053`。三者前后身份相等且与 pack manifest 匹配。包内 Python 91,648 B / SHA `88b9e780cfdc38597c7f53e20f7165262befa28d9a5e9470360d349e172ecf37`，实际执行命令和精确成员身份均保留。

实际 22 个 loopback HTTP 请求，FINITE_PLAN_OBSERVATION_HTTP_GREEN，child/wrapper 0、source_consistent=true。RED/GREEN 的全部 10 个共同请求 method/path/body 逐值相等，knowledge_id 均为 `k_7cd6fe5456d1163b5fd0acc2`；同一 Observation 从旧 422 变为 201，未接纳知识的 Delivery 仍 409。另一个 Observation 绑定原 Proposal；准确重试 200、同 ID 改文 409。两次自有启动之间五条记录精确读回；撤回 Proposal 影响四条记录（含原计划），晚到 Observation 409；历史 record/content_sha256 保全，not_scored 不变，最终 teaching_records=5、learning_events=0、learning_assessments=0。

自有 PID 17128/4904 terminate/reap exit 1，端口 51258/51288 均关闭，不称 graceful。实际使用候选 Python 解释器不等于执行 scheduler/ASR/model worker：本旅程 worker/model/外部工具任务均为 0。包内库存存在不代表全部能力运行通过；manifest 的 ASSERTED_NOT_VERIFIED 构建来源字段没有被改写，其旁独立 build/pack/run 收据提供本轮来源与运行证据。

## 仍未验证

UI 消费者、实际教程打开/跳过/替换交互、专门 start/self-report 状态、独立 mastery、scheduler/ASR 等 worker 业务、原生安装/升级/Owner 验收及完整 R6/CL 均未验。不把后端无评分文字保存扩大为人类真实学习效果。全项目后测与实际包资格见[后继计量](../storage-cleanup/2026-10-31-backend-runtime-in-place/ACTUAL-PREPARATION.md)，原 PARTIAL/退出1保留。

## Harness 有限复核

后继 observation_http_runtime.py 每次调用传 timeout=30，发送前限制累计请求小于 40；正常 GREEN 22 个业务请求，两次自有启动。Core client 无自动重试；status 0 或非预期状态立即失败并 finally 清理。30 秒是 urllib socket timeout，并非严格整段 wall-clock watchdog；本次短 loopback JSON 路由不调用 worker，不能将其宣称为通用网络硬截止保证。

实际 launcher readiness 上限 30 秒；stop 仅针对本 harness 的 Popen，terminate 后等 15 秒，必要 kill 再等 15 秒，记录 PID/退出码/端口关闭。无按端口杀任意进程。候选模式核 launcher/profile/Core 显式 SHA，限定本仓 ignored 内精确无链接路径，fresh DB 位于 GREEN run；这三份文件前后身份均入收据。该后继 harness 已由 root 在 obsgreen1 按上述实际候选运行；边界仅限这次 22 请求。

原 RED harness、收据及准备阶段失败证据保留原字节。

后继不同对象边界见 [typed 教学草稿冷恢复](DRAFT-RECOVERY.md)：它保留自己的源码、候选和真实 HTTP 身份，不扩签本页原 22 请求或完整 R6 资格。
