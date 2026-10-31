# Vault Windows 分隔符分类：旧 HTTP RED / 当前源码 GREEN

本历史记录一个有限后端分类修复，不建立新的执行队列；当前状态仅导航[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。没有读取任何 vault 正文、遍历用户 vault、导入文件、开放新的 vault bridge 或调用模型。

## 已证实缺口与最小修复

原 `classify_one` 只按 `/` 切分路径段，而已有路径安全检查同时认识 `/` 与 `\`。因此 Windows 或混合分隔符可漏识 `.obsidian` 和 `.trash`：应用状态被归为可导入附件，已删除笔记被归为可导入知识。

修复只将 `lower.split('/')` 改为 `lower.split(['/', '\'])`；API 测试追加 39 行、一个回归用例。不新增 API/枚举/数据库/Runtime，不改变普通保存或新建扫描器。分类仍只是名称上的建议，不是读取磁盘、导入内容或操作外部 vault 的授权。

## 分层证据

**旧二进制真实 HTTP RED — vault-red1。** 使用已保全 Core `6b503641cb971ddc0135f79237e036c138cae0db8986cd3510ccefa06b75de6d`（27,844,096 B），原位置 `.project-local/runs/be268a2d33/bkr-r6green1/artifacts/practice-runtime/core/archeaxis-api.exe`，独立新 DB，仅发送七个合成路径字符串给 POST `/api/v1/vault/members`。这是复用旧程序的实际 HTTP，不是新源码程序。

旧响应 HTTP 200，但前三项错误分类：`.obsidian\workspace.json`、`vault/.OBSIDIAN\plugins\state.json` 被判 attachment/import_as_source，`vault\.trash/deleted.md` 被判 note/import_as_knowledge。共 importable=6、excluded_as_application_state=0。正常 notes、附件和 `.obsidian-data` 前缀对照仍可导入；`vault\..\outside.md` 保持 refuse。

RED wrapper/child exit 0 表示成功复现缺口，不是产品通过。原 Core/profile 前后身份保持，未复制载荷。自有 PID 33512 terminate/reap 后 exit 1，端口 64111 关闭；不称 graceful。

**实际新源码 API/领域 GREEN。** `vapi1` 使用当前正式 Rust 源及真实 Router/Store 测试夹具：`contract_vault_members` 8/8（原 7 + 新 1），同七个字符串验证前三项全部 app_config/exclude_application_state、importable=3、excluded=3、越界仍拒绝且原名称保留。并行纳入的 `contract_semantic_search` 4/4 仅合成 worker 回归，不是模型质量或 vault 运行资格。

`vdom1` 当前源码 `vault_members::classifier_tests` 14/14，40 filtered out。两个 GREEN run 均实际 child/wrapper exit 0、source_consistent=true、dirty=true。

没有新 Core exe 构建或新二进制 HTTP GREEN。不能把旧 HTTP 反例与当前源码测试拼成同一新安装候选的 HTTP/原生验收。

## 身份与边界

HEAD `e792dadc062033a93914b433278cd1a41b6d368b`。RED 为 clean；API/领域 GREEN 为稳定 dirty patch `6ee00f37206a138433014e683efa4bed72c2ade0c3c48b54dc175897d970bf55`。该整仓 patch 包含 root 协调的其他变更，本记录只认领 MANIFEST 中两份源码。

- 领域源码 SHA：`7fe8087ffaddb17976505daf4c209e8908e71008272135a1d8e457ea86722a74`。
- API 回归源码 SHA：`9bd54b1684ffe7faf22ffdb420cd8ceabbca3e4bc430e14a9b7407ae0331cd5a`。
- 原 patch SHA：`0856e7a36132f682ef49d3c78981d120c5b9be118844d2023b44e90ca154bfbe`。

原 RED、候选、patch、格式检查、执行收据与实际日志均保留；MANIFEST 逐文件记录轻量证据 SHA。本次仅封存，未重跑/深度 hash 共享 cache，也未读取任何 runtime DB。模型调用 0；分类业务读取 vault 正文 0。UI/安装/实际用户 vault 与完整跨软件能力仍未验，危险的 vault links record 外部 Markdown 权利没有因此开放。
