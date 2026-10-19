# EOL 与冻结字节修复候选

状态：PROPOSED_NOT_APPLIED；隔离行为验证 PASS（SYNTHETIC）。主仓、真实 index、配置、候选宿主与原生旅程均未写入/启动/停止。HUB004 生命周期调研按 root 新指令暂停，优先处理归档可靠性。

## 已复现缺陷

`.gitattributes` 的 `* text=auto eol=lf` 会把当前 CRLF capability manifest 规范为 LF；原详情投影却绑定 CRLF 原字节。实际复制 33 个有限公共来源，在**独立 Git 仓库**执行 add→checkout-index：原字节 Node guard 与 Python details --check 均 PASS，检出后两者均 FAIL。未关闭 guard、未放松 SHA、未把重新排版 JSON 当原身份。

10 项固定来源中仅 `config/capability-packages/pdf-extract.manifest.json` 存在 94 个 CRLF。其余九项（包括 crosswalk 与 core-document schema）当前均 LF、Git clean 字节不变。manifest 身份从 `2ecafecb8dc5c6f8b9ef6a29573a6ef30816113f7fc7587450697b10eb02f2c5` 正确变为 `d16cbc49ec6feae44452bed2b54b999ef6b17899f93430f332c5007b5e668241`。

归档也存在同类风险：当前已登记 16 个冻结目录，最终按 MANIFEST 的 `members`（dict/list）及 `files`（list）三种结构核验 **470 个成员**，其中 **335 个成员含 CRLF**。原件均匹配各自 MANIFEST；原属性未为这些新目录提供 -text。早期 EOL-EVIDENCE 仅统计 members 结构的 430 项，最终 FINAL-VERIFICATION 的 470 项覆盖另外两份 files 格式清单，是最终计数。

## 精确四文件候选

完整 before/after SHA-256 在 `manifest.json`，原件在 `preimages/`，候选在 `proposal/`。

|文件|行为|
|---|---|
|`.gitattributes`|仅为 manifest.json 列出的 16 个具体冻结目录添加 -text，中文注释解释证据保全及后继归档规则；不通配全部 history|
|`config/capability-packages/pdf-extract.manifest.json`|当前可变声明规范为 LF；声明内容不变，raw identity 诚实变化|
|`frontend/src/api/generated/capability-package-details.ts`|使用原 generator 从新原字节重生成，不手改 hash、不提升任何真实性/资格/运行状态|
|`tests/contract/test_capability_package_details_node.mjs`|真实 Git clean/checkout 后运行真实 guard；保全三种代表性冻结来源；继续拒绝后续 raw drift；子进程清除 inherited GIT_* 定位环境|

新增目录**不会被自动覆盖**。后继归档须在首次 git add 前：登记自己的精确冻结目录 -text，封 MANIFEST，然后在隔离 Git clean/checkout 或 staged blob 中回读原件字节和 SHA。可变 current 文档继续 LF；不能为了新归档改写冻结旧 MANIFEST，也不能把全部历史目录当可变源码。原有 Oct09/10 精确保护规则原样保留。

## 验证及可重复入口

在项目根运行：

```powershell
.venv/Scripts/python.exe -B .project-local/audits/hub-lifecycle-gap-20261019/verify_candidate.py
```

runner 只写本审计目录的新 UUID 子目录；检验主仓四项 preimage 未变及候选 after hash，再构造独立 Git index。它没有 commit、真实 index、全局 gitconfig、外部服务、真实模型或浏览器操作。深层冻结归档 fixture 仅对 Git 子进程使用 `-c core.longpaths=true`；Python 仅对本 fixture 的深路径使用 Win32 extended path。

- 原源码搭配新回归：9 PASS / 1 FAIL，失败于 clean 后 guard；保留在 `verification.json`。
- 最终候选：Node 10 PASS，Python details 11 PASS。
- 候选 clean 后 Node guard 与 Python generator --check 均 PASS。
- 注入六项 synthetic GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE/GIT_COMMON_DIR/GIT_OBJECT_DIRECTORY/GIT_ALTERNATE_OBJECT_DIRECTORIES，Node Git 回归仍 PASS；未触及真实 Git 定位。
- 完整 checkout 回读：16 份 MANIFEST 与全部 470 个冻结成员，before=after，零冻结原件修改；逐份 MANIFEST hash 在 `FROZEN-MANIFEST-READBACK.json`，逐成员在 `FINAL-VERIFICATION.json`。
- `git apply --check` PASS。产品应用、构建、运行时资格为 NOT_EXECUTED。

初次完整冻结 fixture 遇 Windows 260 字符路径限制；已保留失败说明并采用仅 fixture 的路径处理复验，不修改系统/用户 Git 配置。

## 独立存在的 resource-catalog 漂移（本提案不掩盖）

`generate_resource_catalog.py --check` 在原字节 baseline 已失败，并非本修复引入。qualification 的 17 个唯一 SHA 来源中有三处不匹配：

1. `entries[3].evidence.version.source_refs[1]` 与 `entries[5].evidence.version.source_refs[1]` 仍记录 core-contract.ts 的 `44553fce…`；当前实际为 `4718df2184917a5f0c1d87220da9d71b9479a67d9dede886a7ed778af30edcaf`。
2. `sources[7]` 的 THIRD_PARTY_NOTICES.md 记录 `8d156936…`，当前 raw 为 `0d38b51c…`，规范 LF 后为 `cbec6ff7…`，仍不相等，**不能只归因 EOL**。

已在隔离目录实际运行原 `generate_core_document.py`，由当前 core-document.schema.json、file-format-qualification.schema.json、core-command.schema.json 生成的 core-contract.ts 正好是 `4718df21…`，与当前文件一致。精确来源 SHA 和三处位置在 `CASCADE-EVIDENCE.json`。

正确后续链路：审阅三份当前 Schema + 原 generator 及生成 DTO 的实际变化 → 审阅 notices 的实际内容/换行变化 → 仅更新当前 qualification 的明确来源引用并追加有原因、旧/新 SHA 的 rebind 记录，保持原 qualification/activation 状态 → 从 crosswalk、qualification、SUPPLY_CHAIN_LEDGER、FREEZE-REGISTER 原 generator 重生成 resource-catalog.ts → 执行其独立定向回归。保留历史 previous_sha/current_sha 记录与冻结快照，不把 hash refresh 当许可或安装资格。此次四文件不含这条链的修改。

## 封存入口

`manifest.json` / `proposed.patch` / `preimages/` / `proposal/` / `FINAL-VERIFICATION.json` 为 root 串行应用入口。`verification.json` 保留原 EOL RED 与早期 GREEN；`EOL-EVIDENCE.json` 保留最初 33 来源对照；`FROZEN-MANIFEST-READBACK.json` 为最终 16 清单零变化摘要。后续不得原位修改冻结候选；变化需新 revision 与重新验证。
