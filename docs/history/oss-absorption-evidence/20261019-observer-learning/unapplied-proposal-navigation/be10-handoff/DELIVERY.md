# BE10 五类handoff本期合同准备提案

状态：**ISOLATED_PROPOSAL_PASS / NOT_APPLIED / BE10整体PARTIAL**。根Agent是唯一产品writer；本目录不应用产品、不替代当前执行台账。

- 补丁：`be10-handoff.patch`，10文件，SHA-256 `5b427bda72524459e49c6d992d22d6ab7215c0cf99ff2b61147ffab7bbf59997`；`git apply --check=0`。
- manifest：`code-manifest.json`，SHA-256 `b48f6d955fc89aeef477d3a28967a767a8af80793bfe77aa68dddada9bd6fabc`。仅两个既有lib各增加一个module export，其余新增；原始lib字节保存在`preimages/`。
- 五类用途：context来源/选区/用途/metadata-only授权；task明确目标/CAP/贡献点且NOT_GRANTED；asset格式/原件或衍生来源/损失回执或UNKNOWN；candidate修订/claim hash/证据/PENDING_HUMAN_REVIEW；receipt绑定原提案key/kind/规范化SHA，保留UNKNOWN和CONFLICT。
- 严格DTO/schema与实际纯投影分层；API层复用已有sha2，无新依赖、HTTP端口、DB、正文、任务执行或跨产品修改。
- 与HUB003对齐六贡献点词汇；manifest identity严格UNKNOWN-only，不复制注册器、权限或安装状态。后继入口`.project-local/audits/capability-manifest-next-20261019/CURRENT.md`，仍需根Agent串行应用，不能把提案当已注册。

## 实际验证

最终canonical三轮：8项API纯投影、2项Rust合同（新67共享case与既有Observer27case）、2项Python schema/来源一致性，共12项测试PASS，child/outer均0且source_consistent=true。11种正例纯投影通过，提案SHA跨Python/Rust一致；拒绝STALE、过期、非allowlist、版本/hash变化、来源/损失缺引用、错误候选状态和同key改内容冒用回执。

真实红控只在owned临时镜像回退先前key/kind-only比较，冲突内容回归实际失败；最终proposal保持digest比较。一次copy2旧mtime使Cargo仍执行红控产物导致7/8失败，未计PASS；改内容比较+copyfile后日志确认重编译并8/8绿。完整原始失败/历史66case记录均在`validation.json`索引，不删除、不改退出码。

最终10项proposal与编译镜像hash逐项一致。source镜像复用既有最小Rust树，只同步既有crate公开源码/manifests、Cargo.lock、Observer schema及一个CAP map；复制范围与hash见`validation-baseline.json`。没有整仓/依赖/缓存/环境/历史复制或可写hardlink。target独立在本审计目录。

## 未完成边界与根Agent应用入口

此为本期准备合同及可运行纯投影，未做真实投递/写入、持久化去重、外部产品UI/native/deep link、安装或Owner验收；选区与格式资格UNVERIFIED，证据语义NOT_ASSESSED。认证由上游既有ObserverClient负责，手工DTO不提供认证。不能因此宣布完整BE10或exactly-once已完成。

根Agent先核对两个lib preimage及git apply --check，独占writer应用后运行`project_handoff_projection`、contracts `project_handoff/project_observer`和Python `test_project_handoff_contract.py`。HUB003若先改lib，须人工保留两边module export并重封preimage，不能覆盖他人更改。其余现行门禁由根Agent按实际合并范围执行。回滚仅移除本10文件改动，不能批量restore现有修改。
