# 2026-10-10 仓库同步交付范围

> **2026-10-10 当前路由与状态**：产品执行 PAUSED_BY_OWNER，整体 PARTIAL；当前请求仅授权归档和权威/引用治理修复。旧“下一队列/未发布/两树不同”属于历史日期快照；上次源码已发布，本轮最新状态读 [修复回读](AAOS-AUTHORITY-REPAIR-20261010.md)。读取任何旧路径前先按 [路径身份路由](AAOS-AUTHORITY-ROUTES.json) 分类，不从文件名CURRENT、旧COMPLETE或旧grant推导授权。六项核心能力增量 FROZEN_BY_OWNER，不自动排队；V01暂停、FT01–04冻结。

> **2026-10-10 最新仓库同步：BRANCH_PUBLISHED**。公开源码、任务包和文档已推送；源码快照 `3c1265be1017f565a64701b513bac3e51d724584`、Git树 `982dafceddc85b8e023f3d028b86805b9592f041` 经GitHub原生API及远程refs读回匹配，main与两个任务分支一致，本地主检出和代码检出已收敛。当前交付元数据的最新SHA以实际Git HEAD/远程ref为准。旧段落“源码不同/未commit/push/云端缺文件”仅为旧时点；不再表示当前仓库状态。安装/产品任务仍暂停，整体PARTIAL与FAIL保留。**CI_VERIFIED_EXACT_SHA未获得**：推送响应显示required a0-gates仍expected，服务器接收提交不等于CI通过。


用户授权“全部上传 双端仓库一致”，授权当前项目公开源码、合同、文档、任务包与可提交归档的 commit/push，以及不改写历史的本地分支收敛。产品执行仍按原指令暂停，V01/FT01–04及安装/发布边界不变。

本次以已验证 gov-ui-20261008 内容统一主检出，保全主检出独有15份历史文档；覆盖前字节与逐路径SHA保存在本地 `.project-local/runs/upload-sync-20261010/`。不提交ignored运行证据、缓存、数据库、环境、私有配置或凭据。源码与本地/云端Git树一致分别读最终交付readback；本页不声称尚未发生的push、CI或安装通过。

最新UF13回执保留整体PARTIAL、前端997/108及47门禁回归通过、SIMULATED限制、schema与资源资格漂移两项FAIL和未应用Library候选。历史各阶段回执绑定原源码时点，不因上传提升为当前真实运行或已安装资格。

云端提交前main读回为 `4b9828c4058901c0b1fd2c75c528238c55e0ec89`，writer原HEAD为 `fc5d4adc7acc28e38c2e6046ef06c0be2eed721d`。最终SHA、树、GitHub读回及工作区清洁状态由本机交付回执记录；推送只交付当前源码，不宣称CI_VERIFIED_EXACT_SHA。
