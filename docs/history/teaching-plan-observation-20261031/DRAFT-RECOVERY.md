# R6 E08 的有限后端草稿冷恢复

本片段验证尚未发布的 typed TeachingDraft 和冻结 pending_record，区别于本目录此前已提交教学记录的 22 HTTP 旅程。不改产品代码，不把自由文本中的“开始”“替换教程”当作专门功能，也不提升 R6 E08 整体、UI 或完整闭环资格。

`e08-a208217f` 实际使用 bpr1 Python `-I -B`，只读复用已封存的 V2 mixed runtime；新 DB/staging/收据全部在自己的 canonical run，运行载荷复制为 0。当前 Core 的构建身份为 `cfcore-339a6bb6` / clean `89b21d4e`、SHA `043834e07c50f84c6eed51fafa24879b8a8570d537323445a121096596b05a1a`；本次 harness 执行绑定 clean `387c6898bd9ba7fcf29fa59b3bc2bc9010ba2944`，actual/wrapper0、source_consistent=true。其间产品源代码没有变化，未重新构建或修改原包/旧 DB。

| 边界 | 实际观察 |
| --- | --- |
| 冻结草稿 | 人工 Requirement/Proposal 为最少父项；typed Observation 草稿与 pending_record 完整字段匹配后保存。旧 state_revision 写入 409，当前冻结记录未发布时清草稿 422，原状态保留 |
| 第一次中断 | 保存 pending 后停止 Core，尚未发送 teaching create；重启 GET ui-state 与原快照相等，pending 记录 GET404，没有自动发布 |
| 第二次中断 | 明确 POST 得到 201 后故意保留草稿再停止 Core；不是丢网络 ACK 的实测。再次重启时已存记录和未清草稿都精确保留 |
| 明确调和 | 显式同 body POST 得到 200/duplicate=true，与原 RecordView 相等；只有该 exact saved record 已存在，清草稿 PUT 才得到 200。随后 state 与已发布记录精确读回 |

正常累计 19 次业务 HTTP，上限 30，每次客户端 socket timeout=30 秒、无自动重试；该 timeout 不是全旅程 wall-clock watchdog。三次自有 Core 顺序启动，各 terminate/wait 回收 exit1；端口 52648/52669/52677 的 IPv4/IPv6 两相 complete 且无 LISTEN。三次 connect_ex=10035 仍 UNKNOWN，不称拒连、优雅退出或全机进程清场。

最终关闭自有 Core 后，harness 用 SQLite mode=ro 仅计数；root 另以 mode=ro/query_only 独立核相同四表：teaching_records=3、jobs=0、learning_events=0、learning_assessments=0。不读取旧 DB、凭据或个人正文；这三条均为本旅程合成人工记录，not_scored，不构成人类真实学习或独立掌握证据。本旅程 worker/job/model 操作及外部 URL 请求为 0。

原 52 个选择成员、5 个 mixed 成员、四份相关产品源代码和 override 指纹前后一致，root 另核当前 52/5 文件完整 SHA；原 17 routes/profile 保留。选择成员核验不扩大为原包全量资格，观察前后相同不等于 OS 强制只读沙箱。

执行前 root 与非作者独立静态审阅 v1；保留原件，v2 仅提前登记 owned child 以及先保留异常 counts 再断言，没有改变 fixture/预算/预期。v2 与执行、root 及独立后审的完整 SHA 见同目录 MANIFEST。

仍未验证专门实践状态、教程选择/跳过/替换、外部打开、独立 mastery、真实 UI/IME、备份恢复或 `/recover`、安装及完整 R6/CL/F05。这里的恢复是同一个合成库的冷重启及显式请求调和，不代替其他恢复旅程；V2 模型失败和清理 HOLD 不因本片段通过而改变。实际进度只在唯一执行记录维护。
