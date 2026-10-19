# EOL四文件候选独立审阅

观察时点：2026-10-18T22:38:59.127862+00:00。结论 **NO_BLOCKING_FINDING_FOR_SERIAL_APPLICATION**；提案仍 **NOT_APPLIED**。仅只读源码/补丁/既存回执并独立计算字节哈希；未重跑测试、创建Git仓库、运行服务或写产品。结果仅写本报告；本目录原11文件测量候选及其封存记录未变。

审阅冻结入口：`../hub-lifecycle-gap-20261019/README.md` 已标已冻结，manifest SHA256 `d1dec7c86a9eb046a10b1a71b82638e2440d512eea43292cf301c3046f1e4fe2`；patch SHA256 `8d1cba0c7d235ba4729c8fc92b840afacffe020fafb45ff3fd2fdee017ceb74a` 与manifest一致。当前产品四份preimage和候选四份after逐项匹配。

## 关键核对

- .gitattributes 保留原文件全部字节，新增保护恰为清单中的16个具体冻结目录 `/** -text`；不泛化全部history，后继目录须先登记并验证。精确目录规则同时覆盖其MANIFEST及深层成员，原Oct09/10规则保留。
- 可变pdf-extract manifest变更严格仅94个CRLF→LF，JSON语义不变。详情生成物变化严格仅两处raw SHA绑定旧值→新值；许可、资格、runtime与声明状态未提升。原generator、validator、Node guard三者与当前产品逐字相同，未放松guard或评估生成JS。
- 新Git回归从有限自有fixture执行init/add/checkout-index，实际guard检查检出字节，三类归档代表逐字相等，并继续对新增空白raw drift拒绝。每次Git子进程清除全部大小写兼容的 `GIT_*`，不继承真实index/worktree/object路由；cwd为fixture，真实产品Git未被此测试操作。验证runner额外以六个伪造定位环境注入运行该回归并PASS。
- FINAL-VERIFICATION 的6项检查均exit0：Node10、Python11、clean Node/Python guard、注入定位负控与apply check；这是既有SYNTHETIC隔离Git证据，不是我重新执行或原生资格。独立回读16份MANIFEST及470个成员，现有原字节SHA均等于其已记录before/checkout值，零冻结成员漂移。初次深路径失败、早期430计数和resource-catalog既存来源漂移均明确保留，未冒称整仓或catalog全门禁PASS。
- prepare_eol_candidate.py保留早期未清理Git环境的构造代码，但已有 `assert not PROPOSAL.exists() and not PRE.exists()` 阻止在此冻结目录重复制备；最新可重复验证入口是verify_candidate.py，其Git分支清理定位环境。不要把早期脚本当新的正式产品入口。

## 被审四文件身份

|路径|before SHA256|after SHA256|
|---|---|---|
|`.gitattributes`|`98a94ad33303945bf1613e290ca9ae7e5f2286b4f81227adfe48c600c10e6564`|`28d699fb79d13f5c9d2294791a5c6e1208be54cebb91fa76ed84b3e6a6cddca1`|
|`config/capability-packages/pdf-extract.manifest.json`|`2ecafecb8dc5c6f8b9ef6a29573a6ef30816113f7fc7587450697b10eb02f2c5`|`d16cbc49ec6feae44452bed2b54b999ef6b17899f93430f332c5007b5e668241`|
|`frontend/src/api/generated/capability-package-details.ts`|`e950b70f6a789a0fd4ddc3ce444b059230760704d09708055e66a4ec5e3d6a0d`|`712144d4a73272d57fe9b0549179888edc797f12fbf368b3464336d02e982e44`|
|`tests/contract/test_capability_package_details_node.mjs`|`3986a82f956c1c2bc7f648a40d3fe85b72653ef7f64fc6899f77321a1317797b`|`5e988c3ef9885f24ef83ea3dbec6785bda6a5898962c23560fe01287a19c8e7d`|

FINAL-VERIFICATION.json SHA256 `4af93a95705bb902918ef89b3093cfa50efa4bdd1a583a7673ad8c3bc2c53c5a`；FROZEN-MANIFEST-READBACK.json SHA256 `9d1665152c1bbb0b24dda47eaebd6e40527127c0863979a92f9d76eaf32d4485`。本报告完成前再次确认候选四文件与manifest相符。此后任何候选变化均需新revision及复核；root串行应用后按项目门禁验证，勿通过重新规范冻结原件消除换行差异。
