# 全仓公开权威入口修复 · 2026-10-10

状态：IMPLEMENTED_LOCAL / TESTED_LOCAL / BRANCH_PUBLISHED。治理载荷与两端readback见下文；latest元数据SHA动态读取Git。上次G01完成主要入口与定向门禁，但未覆盖全部直接阅读入口；不把上次PASS推导为本轮全面无漂移。

当前产品 PAUSED_BY_OWNER / PARTIAL，仅治理维护执行。六项核心能力增量 FROZEN_BY_OWNER，不加入当前任务。TaskPack原字节、历史证据SHA、失败记录及冻结能力保留；未修改UI配色、业务代码、私人Agent配置或任何其他项目。

## 已修复

- 正式src-tauri/README移除FastAPI正式宿主叙述，frontend/README修正旧固定六空间/紫晶主题及共享dist路径，crates/README不再把正式前端归为legacy。
- 当前Agent交接重写为简明当前路由/暂停/证据边界；旧各阶段原文按字节保存于 `docs/history/authority-repair-20261010/AAOS-AGENT-HANDOFF-before-repair.md`。
- 所有公开主导航与权威Concern索引加入当前状态与机器路由入口；治理/同步页旧“未发布”段落明确只对原时点有效。
- 旧根handoff、Hermes、早期truth权威顺序、Avalonia占位README增加适用范围说明，不删除原历史正文或改写旧证据。
- PROJECT_CONTRACT、TASK-GRAPH与schema const的digest失效路径统一指向已有 `docs/vnext-seed/operations/digest-canonicalization.md`，取消测试中旧缺失白名单。
- 路径身份注册覆盖公开导航、现行/继承/历史/冻结文件和旧别名；已有document-authority门禁验证路由、暂停与来源冻结边界、入口链接。

## 软件与模型读取方式

从AUTHORITY/AGENTS/README进入，再读取 `AAOS-AUTHORITY-ROUTES.json` 与活动指针。旧文档即使命名CURRENT或含“当前权威”，不能独立成为当前任务。历史任务合同仍按Concern及supersession继承，不因历史分类丢弃有效约束。

云端使用仓库相对路径；本机绝对共享资源路径不是云端存在证明。任意未更新的旧分支、离线导出、第三方缓存/向量索引或私人软件配置无法由本仓自动改写；使用前须刷新到交付SHA，否则标UNVERIFIED。本次不读取或修改私人配置/记忆/会话。

## 发布与资格

上次已发布基线 `fb590dfb060e51c348dce57226a4e0bbc1e19f31`；本轮最新治理修复需要独立提交/远程读回，不能复用旧发布结果。已有“全部上传，双端一致”授权保留为公开项目范围；安装、Release、V01及产品恢复不在本轮。

回退使用本轮精确diff或单个治理提交；修改前字节备份位于项目 `.project-local/runs/authority-repair-20261010/before/`。不得reset/clean或覆盖未知修改。

## 软件项目入口

AGENTS.md覆盖AGENTS兼容读取；新增CLAUDE.md、GEMINI.md和.github/copilot-instructions.md仅指向同一权威，已纳入目录所有权与路径路由，不复制第二套业务规则。未修改私人全局配置；实际软件上下文加载仍UNVERIFIED。

入口格式依据：[Claude Code](https://code.claude.com/docs/en/memory)、[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/)、[GitHub Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)、[Qoder AGENTS兼容说明](https://docs.qoder.com/zh/user-guide/rules)。软件可能被用户/组织关闭项目指令功能，文件存在不等于模型必然遵循。

系统边界补漏：根SYSTEM_BOUNDARY明确旧Green快照身份；docs/SYSTEM_BOUNDARY改为当前Core/宿主/保存及验收边界，旧正文按原字节保留。UI路线图与机器UI合同按当前任务映射，不提升旧导航为新固定结构。

## 本轮本地验证

- 公开文档身份覆盖：1229份，未分类0；机器路由和document-authority PASS，仓内来源hash核验7项，外部/私人locator4项UNVERIFIED。
- 定向治理测试71 PASS；canonical run `be268a2d33/b2f5115917a7`。首轮业务SQLite fixture启动权限失败、第二轮7个测试fixture缺少新路由失败均保留；修复fixture与导入位置后通过，不重标旧失败。文档测试使用 `--confcutdir=tests`，不初始化业务数据库。
- Ruff本轮5个Python文件PASS；task-graph schema及统一digest引用PASS；schema初次外部resolver失败，使用仓内资源注册后通过。目录路径门禁PASS，已有1个明确登记的未归属路径保留，不声称所有目录都拥有写权限。
- 本轮变更格式检查PASS，原字节归档另记；全仓格式仍有41项历史问题，保持FAIL，不伪装全仓全绿。保存来源不能为格式检查改写原字节。
- 实际各软件上下文加载、exact-SHA云端CI、安装、M01和真实效果验收未执行；产品暂停和六项增量冻结保持。

本地回执目录 `.project-local/runs/authority-repair-20261010/`，旧交接/边界保全hash见 `docs/history/authority-repair-20261010/MANIFEST.json`。

## 本轮发布回读

治理载荷提交 `338c17bb17c652e0651b536edaae9b2a96a01ba0`，Git树 `046d4b7f44258bafc35ff562f2f32617b88b7e38`。GitHub原生API读取main、codex/Audit、codex/aaos-gov-ui-20261008，三个ref均等于载荷SHA；主检出与代码检出同步到该SHA。AGENTS/AUTHORITY/路径路由/CLAUDE/GEMINI/Copilot六个关键文件远程字节与Git对象相同，GitHub About已更新并读回。本机回执为 `.project-local/runs/authority-repair-20261010/PAYLOAD-DELIVERY-READBACK.json`。

本页后续readback元数据提交不改变载荷证据身份，最新HEAD/远程ref动态读取。原始ZIP/DOCX/PDF与本地运行证据仍Git-ignored，只上传可提交公开文本、索引与治理源码。最终提交态定向71测试PASS，run `be268a2d33/65d9ddddc308`；退出时pyreadline对象清理警告保留，进程exit=0，不作为额外产品资格。

严格 `git diff --cached --check` 对原文Markdown的14处尾部空白为FAIL；这些是原文Markdown换行字节，保持hash不修剪。排除原文的治理diff检查PASS，不将严格原命令重标PASS。全仓格式41项历史问题仍FAIL。

**CI_VERIFIED_EXACT_SHA 未获得**：推送服务器报告required a0-gates expected，自动check仅按其当前结果记录，不以推送成功替代全门禁。未手动恢复V01、安装、发布或产品开发。
