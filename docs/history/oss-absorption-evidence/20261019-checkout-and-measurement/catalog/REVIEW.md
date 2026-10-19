# Resource catalog 来源重绑审阅

状态：候选已冻结，PROPOSED_NOT_APPLIED；定向隔离验证 PASS（SYNTHETIC）。本轮仅写此 ignored 审计目录，root 为主仓唯一 writer。没有访问模型/凭据/私人状态，没有启动浏览器、宿主、服务或推理。

## 实际来源变化

旧引用不是无从追溯的任意 hash：两个 Core 行记录的 `44553fce7686b765a77b39a963ce137786dd06a83e3127a8982ddb112fa11775` 与本次现场 HEAD 的 core-contract.ts 原字节完全一致；notices 旧值 `8d15693693371a22ef5fb157de83523af576718338f914855a2dc1c075c7f260` 也对应 HEAD notices。原件已保存于 `head-sources/`，当前三项 preimage 在 `preimages/`。

审阅三份当前 Schema 和原 generator，实际重新生成 DTO 后确认：

- core-document.schema.json 仅增 `LearningItemsDto.items[].display_title`，可选 string，长度 1..80；required、旧字段与 DocumentDto 均不变。
- core-command.schema.json、file-format-qualification.schema.json、generate_core_document.py 与现场 HEAD 原字节一致。
- 全部生成 definitions 中仅 LearningItemsDto 变化，且是上述精确增量。实际原 generator 生成 core-contract.ts SHA 为 `4718df2184917a5f0c1d87220da9d71b9479a67d9dede886a7ed778af30edcaf`，与当前文件完全一致。因此两个 `SOURCE_CONTRACT` 引用可作有理由的新绑定，不能据此授予运行资格。

notices 除 CRLF 外，实际追加 Neural Creator Dashboard 视觉算法来源、固定上游版本、既有完整 MIT NOTICE 的资源路由、吸收与排除范围。其描述与仓内 neural-creator-NOTICE.txt、AAOS-OSS-UI-DONORS-20261019.md 及现有吸收回执相符。本轮只核对已登记的来源和归属说明，未重新访问上游、未重新核验权利或许可资格。候选保留当前正文的全部字符，仅换行为 LF；新 SHA 为 `cbec6ff7bfd24fee26aa8c5c1380145bfa27dd53659eff1911fb4b7e0e99ab09`，避免 raw CRLF hash 再被 Git clean 改变。

精确比较与实际追加的 notices 文本在 `SOURCE-REVIEW.json`，不以文件名或 manifest 存在代替实现。

## 资格判断

68 行 qualification 均为 `INHERITED_ONLY`，绑定原历史交叉登记与账本；历史 `currently_usable` 不属于当前宿主实测。两个受影响 Core 行 runtime 为 `NOT_RUN`，license 为 `HISTORICAL_SOURCE_NOT_CURRENT`，activation 为 `CURRENT_PAGE_REFERENCE_ONLY`。page15 明确把历史 tier/currently_usable 与当前运行读回分开。

因此本次没有需要根据新 DTO/归属声明撤销的当前运行 PASS，也没有依据授予新的当前资格。保留历史原值及来源；追加审阅元数据明确本次 current runtime 为 `UNKNOWN_NOT_REOBSERVED_BY_THIS_SOURCE_REVIEW`、资格 `NOT_GRANTED_BY_HASH_REBIND`。这既不删除历史真实证据，也不把旧字段延续为今天的已安装/许可/执行事实。逐行断言所有 license、permissions、runtime、qualification 和 activation 原样不变。

## 最小三文件 write set

1. `THIRD_PARTY_NOTICES.md`：当前可变文件 CRLF→LF，正文字符不变。
2. `docs/current/AAOS-RESOURCE-QUALIFICATION-20261010.json`：仅更新两项 Core source_refs 与一项 top-level notices SHA，追加 `source_binding_review_20261019` 的 old/new/reason/边界；旧 refresh 记录不覆盖、不删除。
3. `frontend/src/api/generated/resource-catalog.ts`：用原 generate_resource_catalog.py 从上述当前来源重生成。

完整 before/after SHA 在 `manifest.json`；精确候选是 `proposal-v2/`（其他复制文件只作验证来源，不属 write set）。冻结旧归档与原 MANIFEST 零修改。不新增注册器，不改代码、协议、依赖、许可判断、安装或执行状态。

## 定向验证

- 原实际来源：generator --check FAIL；原 `test_resource_catalog_projection.py` 为 **1 FAIL / 15 PASS**，失败原因 core-contract 来源漂移，保留完整回执。
- 候选：原 generator 生成及 --check PASS；同一合同 **16 PASS**。
- 独立 Git 仓库 add→checkout-index：clean 后原 generator --check PASS、同一合同 **16 PASS**。真实 index、对象库及配置未写入；子进程不继承 GIT_* 定位环境。
- 原 core generator 实际重生成：与当前 core-contract.ts 字节相等。
- 保留68个原始条目及115项冲突，来源 SHA 逐项匹配；原合同继续覆盖重复/缺失行、来源漂移、缺失来源、危险路径拒绝。
- 主仓三项 preimage 在生成结束仍精确匹配；git apply --check PASS。

`verification.json` 是最终 RED/GREEN/clean 回执。首轮 fixture 漏复制 generator 固定 crosswalk/freeze 输入，在 ignored 内停止，原文件保留在 proposal/、baseline/；新 v2 补齐并完整验证，失败登记在 INTERMEDIATE-FAILURES.json。

重复定向核验：`.venv/Scripts/python.exe -B .project-local/audits/resource-catalog-source-rebind-20261019/verify.py`。仅写本审计的新 UUID 输出；一次性构造及完整 Git clean 过程保存在 run.py 与 verification.json。

## 对真实验收的影响

这是来源声明、归属文本与派生投影修复，没有新增可执行能力，也不重跑或声称真实模型/原生验收。既有真实验收仍有效描述其原版本、原候选和原字节；本提案不会追溯修改其结果。resource-catalog.ts 字节已变，未来新 bundle/candidate 的 hash 会变化，不能把旧候选 PASS 原样挂到新候选。root 应把新来源身份记入接续回执，并按其新候选的风险门禁重新构建/限定验证；本轮只有定向合同与 clean 检出资格，产品整体验收仍原边界。
