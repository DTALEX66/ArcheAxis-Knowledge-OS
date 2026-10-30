# 剩余49项规范化只读复核（公开历史候选）

结论 **PARTIAL，未通过规范化验收**。源码SHA：`f10dedee225ad7b049b99668d3c3a43d8d105bd8`。原50项中已处理的 `declared-routes` 排除，不重复计收益。本批仍为13空目录、36非空；原23访问拒绝项现均可浅层列举。49项OWNER/DACL普通令牌只读成功；未删除、搬迁、改ACL/owner，回收0B。0项取得清理资格不等于没有Owner授权，也不等于规范化通过。

## 角色纠正与保留原因

`runs/<worktree-id>/<run-id>` 第一层10位hex可能是worktree命名空间容器，metadata属于第二层run；容器根缺 `run-metadata.json` 不构成归属失败。13空项中11个是容器形状，2个是旧具名run；公开线索尚未证明精确生产者关联、退休、消费者处理及闲置。当前Git仅登记主worktree不代表旧容器无人使用。

22项非空测试输出疑似可再生成，仍缺锁定重建输入、唯一失败保留与负控fixture映射，不更改测试权限。其余14项为1历史失败、2部署/安装运行、6被引用证据、5未知载荷或工作流角色，均保留。原23旧拒绝项中7项找到历史精确pytest basetemp命令；命令存在不代表当前载荷已满足再生资格。无项满足先决条件，未探测DELETE handle。

## ID复算及旧结论修正

实际算法在 `scripts/runtime/dev.py:72`：Windows规范绝对路径字符串casefold后SHA-256前10位。当前根的反斜杠与正斜杠变体经 `PureWindowsPath` 词法规范后均为 `be268a2d33`，正控制通过；不访问外部路径。

87个公开worktree路径候选原hash与Windows规范复算一致。240项扩展集合实际是“原始路径形状文本前缀”，包含URL误提取，不能称为240个有效绝对worktree路径；其中15项原hash经Windows词法规范发生变化（重复或尾分隔符等）。本候选明确纠正此前过强表述；全部240项重新规范复算，仍未匹配11个空hex。这个有限文本集合未匹配不能证明所有历史路径均已穷尽。原始证据保持不变，规范复算统计、来源SHA及算法文件hash见MANIFEST。

限定producer/current/consolidation/intake公开历史搜索仅命中 `653cf721` 的Claude交接原始引用，没有退休或替代证明。`scripts/runtime/paths.py` 当前及all-ref路径历史未命中；不从不存在文件推断算法。

## 证据边界与后续

MANIFEST列49项脱敏分类及原始本地证据hash/退出码。原49行SDDL、owner SID和外部路径候选正文只保留ignored证据，不进入公开文件。元数据不冒充正文SHA；没有递归载荷扫描、全仓计量、正文替代哈希或闲置证明。

归属未知保持待证据，不反复升级为Owner确认问题。后续按精确生产者/历史worktree关联、退休、闲置及保全证据继续；不新增权限或降低清理规则。
