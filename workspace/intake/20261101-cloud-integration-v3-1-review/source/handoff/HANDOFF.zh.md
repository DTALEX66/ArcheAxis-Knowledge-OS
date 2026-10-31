# v3.1补件：补丁承接与防重复应用

## 明确结论
**原v3的最终主补丁已经包含detector、资源重绑、安全锁、UTC和wheel修复。不要再叠加各中间候选。**

原v3归档SHA-256：`de984bf8917d24f4bc837221f76983dde20973f8285808e1fa6c351a5c68ac43`（本轮实际复核）。
最终主补丁：`patches/aaos-isolated.patch`，SHA-256 `09026d19c181fb563324d7343d1d200618412c540c692619aad084be00b607bb`，与原包delivery-identity一致。
云端基线：`8d367bac4a85bebfbb523503678ade0838faa73e`；31个已跟踪路径修改，另2个新测试位于`patches/new-files/`，它们不是31路径patch的一部分，已按原identity核hash。

## 文件角色与应用顺序
- **FINAL_BASELINE_DELTA**：只有主补丁。在精确云端基线的隔离复现副本使用一次；不是对任意最新主线的升级包。
- **FINAL_NEW_FILE_COMPANION**：两个真实Core测试新增文件。精确基线复现时与主补丁配套；若目标已有同名文件，应核差异，不能整文件覆盖。
- **INTERMEDIATE_EVIDENCE_DO_NOT_STACK**：detector candidate、resource-security-rebind、candidate-uv.lock、sleep UTC candidate，以及wheel candidate的两份副本。均为调试/审计历史，不是额外步骤。最终主补丁之后再次应用可能冲突或重复改动。
- v3.1正在制作的**新定向补丁**若有，必须明确“基于v3最终已应用状态”还是“基于原云端基线”，单列hash/目标/测试；不能与上述历史candidate同名混淆，也不能宣称它自动适用于用户本地版本。

完整路径、角色、SHA和适用策略见`patch-classification.json/.csv`。

## 实际验证方法与原始证据
本轮没有修改原v3压缩包或只读解压证据。先核归档、主patch与新增文件hash；再读取已授权恢复仓库的**精确baseline Git对象**，在本补件自己的derived-baseline-comparison目录还原各candidate涉及的原文件，分别实际运行candidate与主patch对应路径，逐字节比较输出。

6份中间patch制品（wheel有重复副本）共12次`git apply`退出0；全部候选输出与最终主patch相应文件字节相同。日志和命令见`candidate-output-comparison.json`、`equivalence.stdout/.stderr/.exit`，脚本`audit_patch_inventory.py`与`check_candidate_outputs.py`可复现。

**注意hunk与效果不同：**uv.lock candidate及resource generated TS的hunk文本不能逐块直接嵌入主patch；difflib和Git diff对相同上下文的分组/移动呈现不同。但对同一baseline实际应用后的文件完全相同，已通过上述字节比较证明。不得把表中`hunk_body_contained=false`误读为需要额外应用它们。

## 用户本地70dfc397：最小承接，不覆盖
用户报告本地`70dfc397`有13路径不能直接适用。本轮**没有取得用户本地源码，也没有独立验证这13路径的逐项内容或数量**；该状态按用户反馈记录，不能编造路径清单或宣称已解决冲突。

不要求将本地退回云端baseline，不要求整文件覆盖，也不自动`git apply --reject`、强制合并或覆盖锁文件。建议正式本地Codex按“功能意图”处理：
1. 先用本地已有代码判断每项修复是已存在、已等价替代、仍缺失还是不适用；保存本地未提交改动。
2. 对确有缺口处移植最小语义差异；不要为了复用云端行号撤回本地改进。13处不适用不等于13项功能失效。
3. detector应接本地既有模型/代码定位合同；资源catalog应由本地原始来源生成；安全锁应基于本地锁解析且同步其manifest/hash，不能把旧cloud uv.lock整份覆盖到新项目。
4. 冲突只补核相关接口/调用/状态/错误路径，继承未变范围的云端证据；无需再无差别跑186项或整个云端审计。

**云端PASS不是本地PASS。**本地若业务源码、锁、生成合同或宿主不同，只需做其差异触发的定向验证；Windows/原生/真实外部模型等未在云端资格化范围不能免测。拒绝盲目复用与避免重复全量测试并不矛盾。

## 本补件资格
本文件只完成第5项补丁承接说明及真实包内关系核验；不是AAOS新增集成、不是本地合并成功，也不是detector/reproduce v3.1定向修复已通过。后者等待相应候选与原始测试后追加独立审计。
