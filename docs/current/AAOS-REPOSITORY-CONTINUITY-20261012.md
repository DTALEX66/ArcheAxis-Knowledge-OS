# 仓库身份与跨会话接续 · 2026-10-12

本文件仅汇集当前仓库交付观察和接续方法，不建立第二业务权威。规则读[根入口](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[项目合同](../../PROJECT_CONTRACT.yaml)及 concern 对应索引；任务路由只读[活动指针](AAOS-ACTIVE-EXECUTION.json)，产品进度只读该指针指定的执行记录。整体 RUNNING_BY_OWNER / PARTIAL。

## 已并入主线的来源与证据

- 仓库：`DTALEX66/ArcheAxis-Knowledge-OS`；正常接续分支 `main`。本机根 `D:\All projects\ArcheAxis-Knowledge-OS` 是本机登记，云端使用其实际检出根。
- [PR #184](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/184) 已合并；合并 SHA `1a322045490075e68e4d8b5f26bdd706d3e4089a`。
- 候选 SHA `fca7e7150c0e356b832730531f942af3f49b1b95`；候选与合并 Git tree 均为 `9956bf790352ec4bfbeb0b96b3faeef2e05dcf11`。
- [候选 CI 38268676998](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/38268676998) 必需门禁 PASS，包括实际 CI Windows 安装、原生旅程、升级与卸载；材料为合成测试。未要求的 skipped 不计作已测能力。
- [合并 SHA CI 38272440912](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/38272440912) 与候选 CI 分开；本记录建立时仍在运行，接手需读取实际结论。
- 公开源码、合同、权威索引及公开回执已进入 main；本地 runtime、数据库、模型文件、raw 测试材料、凭据和私人软件配置不上传。公开回执中的本地路径是证据 locator，不保证云端存在。
- 后续治理元数据的最新 SHA 由 `git rev-parse HEAD` 和远程 ref 读取；本文件不自引用自己的提交 SHA。

## 分支清理与本地资料保留

已清理 25 个远程旧分支和 2 个本地分支，包括已合并的 `codex/Audit`。观察时远程只剩 `main` 与 `codex/minimax-aaos-cosmic-ui-20261001`。

2026-10-13 更新：Owner 明确要求「删了吧」后，cosmic 远程分支已删除，PR #158 已关闭；本轮 `git ls-remote --heads origin` 回读仅有 `main`，SHA `23f22a4928c69db2667b76b9c5cb84a2cd24252c`。本地 cosmic 供体工作区新增的 `AGENTS.md`、`README.md` 未提交差异保留，不把删除远程 ref 扩大为覆盖本地资料。当前修复使用独立隔离工作区；修复分支发布后需再次读取远程，不能把本次观察当永久状态。

[PR #185](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/185) 权威接续已合并，合并 SHA 为上述 `23f22a49…`；[该 SHA CI 38274429552](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/38274429552) 已动态核实 `completed/success`。这是该 SHA 的 CI 资格，不能覆盖随后未提交的取消、外发、便携恢复和职责界面增量。

cosmic 分支保留 2 个唯一提交 `fec7a18f`、`627e74ff`，涉及 14 个历史 Avalonia 宿主/测试文件。它提供背景、玻璃界面与配色约束参考；正式宿主是 `frontend/` 和 `src-tauri/` 的 Tauri/React。直接合并会把冻结供体实现和旧测试假设带入当前产品，不能据分支名认为它是正式 cosmic 主题升级。需要复用时提取具体视觉行为并按当前宿主验证；此分支不是运行依赖或活动执行队列。

9 个本地历史工作区含未提交差异，不能强行删除或认定已全部入 main：`aaos-longpath-app-20261007`、`aaos-ui-core-integration-20261007`、`aaos-ui-newui-20261007`、`f15-folder-ingest-20261007`、`framework-20261011`、`gov-ui-20261008`、`supply-bind-20261007`、`v3-era`、`worker-quality-0906`，均位于本项目 `.project-local/worktrees/`。它们不是当前 main 源码的替代入口；其未知工作与用户资产保留。

## 换会话或软件的最小接续

1. 读取 `git status --short`、当前 branch/HEAD、`git worktree list --porcelain`、有效 remote；不由旧 handoff 固定 SHA 推断当前事实，不覆盖 dirty。
2. 读取根规则、[文档索引](../DOCUMENTATION_AUTHORITY_INDEX.md)、[配置索引](../CONFIGURATION_AUTHORITY_INDEX.md)、活动指针与[路径身份路由](AAOS-AUTHORITY-ROUTES.json)。历史 TaskPack、暂停、授权、COMPLETE 与 raw receipt 保持原日期和来源身份。
3. 需要工具、模型或资料时先读[共享资源路径索引](../SHARED_RESOURCE_PATH_INDEX.md)，只对所需精确对象核实存在、类型、版本与运行状态。云端不执行本机绝对路径，不凭目录存在宣称模型可用，不扫描私人配置或整个磁盘。
4. 当前源码从 main 核对；旧工作区与 donor 分支须另行审计，不据相同仓库名推断一致。使用 `git merge-base --is-ancestor` 和 Git tree 核对交付身份；网络只读也不自动授予远程写入。
5. 按当前明确任务判断授权；本轮允许公开治理资料 commit/push/PR/merge。历史临时 27B 加载、非沙箱实测或分支清理许可不成为新会话无限授权。发布、Green 替换、真实数据覆盖和付费/私有材料外发仍须对应授权。
6. 沿项目 canonical gate 验证，区分本地、exact-SHA CI、CI 安装、本机安装、REAL 模型与 Owner 验收；缺失、失败、取消及 required skip 不写 PASS。

## 产品仍未完成的范围

当前 native 资格尚不能覆盖所有最新源码增量；机器取消与 owned task 收尾、文档便携包回导/媒体 CAS 往返、模型与工具职责呈现、有界视频视觉资格、外发最后授权检查到首次发送的竞态、云端真实调用、27B 资源/质量与加速比较、独立学习效果及 Owner 验收仍按活动执行记录推进。分支收敛和权威导航更新不将这些项目标为完成。
