# Asset/scoped 探针：有限合成端到端与绑定反例

这是现有 F05/CL/J 的后继探针记录；产品整体仍 PARTIAL，实际进度只读[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。3 文件候选为原 legacy 探针增加显式 `--asset-scoped` 分派、独立资产适配器及其合同测试；默认 legacy 语义不变，不新增 Runtime、表、API 或 SQLite 写入者。候选/部署身份及逐项证据见 [MANIFEST](MANIFEST.json)。

同一份合成知识、原问题、资料不足控制、独立应用题与 JSON 量规沿旧探针保留。首次基线前保存固定输入、量规、2048 输出 token/120 秒 Core 预算、原生产 prompt/worker SHA、既有 qwen3.5-4b/openai/loopback 路线，以及候选 package、成员和授权快照。R5 的“方法”在此有限例子中映射现行 `rule`，由 `knowledge_package` 包含，不创建新 enum。基线后仅改变 package 的采用状态和资产使用授权；不改原 knowledge、不接受 correction candidate、不换题/预算/prompt/thinking。正确原答走新 answer 比较并记 NO_FAILURE_OBSERVED；只有固定量规下确实错误的原答才创建精确 correction，随后在原 knowledge 上原题 retest。独立应用题前后使用不同 answer/request 身份；各只有 1 个样本，不宣称一般学习或模型参数改变。

真实 Core API 完成 candidate/rubric/adoption/use-grant/answer/correction/retest/withdrawal；资产包进入未修改的生产 worker 代码，由测试专有 wrapper 将模型 HTTP transport 换成内存合成响应并禁止该子进程 socket 连接。实际生产 prompt、请求编码和 response parser 都运行。5 个实际 worker 输入的 context SHA、packet SHA、成员版本与 Core 的 answer/retest 持久化内容逐一相等，完整 prior 保持。协议负控实际覆盖候选未采用、过期、consumer/purpose/operation 不符、串包、同请求省略资产/改变请求及成员撤回；拒绝后的全部原答回读不变。这些拒绝只证明边界，不是效果改善。

| 最终候选运行 | actual main | wrapper | 结果 |
| --- | ---: | ---: | --- |
| bkr-acorr3 | 0 | 0 | 合成错误基线→采用/授权→原题 retest 与独立题有限对比 |
| bkr-acorrect2 | 0 | 0 | 原答正确，未创建 correction；无测得改善 |
| bkr-abad2 | 1 | 0 | 独立题持续错误，TRANSFER_FAILURE_REVIEW；负控成功不改 actual FAIL |
| bkr-aunit2 | 0 | 0 | 66 legacy + 53 asset 合同测试，共 119 通过 |
| bkr-alint2 | 0 | 0 | 3 文件 Ruff E9/F63/F7/F82 通过 |

最终三 main 运行均源码一致，各 5 次**合成**模型 transport，实际模型调用 0；合成 usage 不是实测 token 或计费用量。Core 均为既有 C1 混合候选二进制，SHA `b6f5b591c2663bc03ee986a8b5aef25e1d414219373523c8b404f3a6512e103b`。没有重建当前产品、native/installer 运行或真实模型资产效果验证。观察到的自有 Core/Python worker 退出、端口关闭；Core terminate/reap 退出 1，不称优雅停止。

独立审查保留了 aprep3 的反例：把 correction 的 corrected_answer 改错，再使 persisted prior 自洽，原候选仍 main 0。nrm-prva2 用原 40 个 HTTP 响应内存重放、逐请求 SHA 相等，证实这是探针漏判，不是已证实的 Core 缺陷。aprep4 补逐字段纯校验，绑定 question、answer、知识、失败 ID、corrected_answer、reviewer、error_note 和新 candidate 身份/状态；bkr-areplay1 原对照 40/40 仍 0，串改反例在第 16 请求即时 1、余 24 不执行。nrm-prfix1 独立重跑确认同样结果。aprep2/aprep3、bkr-acorr1/acorr2/acorrect1/abad1 的早期 main 通过明确属于已知 validator 缺口的历史候选，不用于补足最终资格；旧候选、失败与后继收据全部保留。

bkr-asset1 是另一个证据层：当前源码的既有 machine_asset_context_api **5/5**，真实 Store/API + 真实 Python 子进程、合成回答，source_consistent=true。它不把旧 C1 main 变成当前产品通过。bkr-asize1 记录共享 Cargo debug/deps 新增 .d/.exe/.pdb 共 **188,517,889 bytes**，对应 fingerprint 另 **1,513 bytes**；该测试 run 的保全证据为 **4 文件/3,055 bytes**。这些是具名位置的 logical bytes，不是全 target 或物理磁盘增量；共享 cache 属可再生构建输出，不能作为唯一证据。

[real1 的 NO_FINAL_ANSWER](../colearning-real-model-20261031/README.md) 仍是固定题/预算下的真实失败，没有重试或为了通过调整设置。本记录只建立有限资产旅程和判定器的合成资格；真实 asset/scoped 效果、完整 F05、CL/J、安装态与 Owner 验收均未建立。

部署候选全部为 UTF-8 LF 无 BOM，raw Git blob 与目标路径过滤后 blob 相等。aprep4 的三 main 收据绑定保留的 CRLF 执行副本；bkr-anorm1 证明逐文件仅 CRLF→LF、文本与 AST 等价。最终 LF 文件另经 bkr-aunit2 的 119 合同、bkr-alint2 和 bkr-areplay2 同反例检查。bkr-aseal1 原 CRLF diff apply-check 失败保留；后继 LF diff 才用于部署。当前源码二进制构建及单一纠正分支 synthetic main 是后继未执行项，不能把换行证明或旧 C1 main 写成新产品资格。
