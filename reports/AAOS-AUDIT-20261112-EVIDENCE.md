# 证据继承表 · 2026-11-12

审计基线 main@157ee1db 加三处预存修改。以下原始 JSON 本轮实际读取并计算摘要，未重新执行对应测试。完整来源身份、补丁摘要与原结果保存在本地 [readback](../.project-local/runs/be268a2d33/audit-20261112/artifacts/receipt-readback.json)。不将历史候选重新绑定当前 HEAD。

|ID|能力/材料与环境|原始回执|继承方式及限制|SHA-256（回执）|
|---|---|---|---|---|
|E01|J1混合文件夹、知识、导出备份恢复|[j1-batch-folder.json](../.project-local/runs/be268a2d33/6d833f3811f1/artifacts/j1-batch-folder.json)|限定继承：合成7文件；staged；非安装UI；文本PDF；不证明全格式无损|`5d7280ff1cc0b1b472c70d40bfaf465a39cd1bdb27dafad807bf36c08dac7beb`|
|E02|J2三族真实网络|[public-research-receipt.json](../.project-local/runs/be268a2d33/03d213570808/artifacts/public-research-receipt.json)|限定继承：三主通道complete；原status PARTIAL；不证明DBpedia回退或当前网络可达|`5831ae57d0b4f6745721d2d9f2a00fa98d96787347a5ddec2bbcfdf7d7d04153`|
|E03|中文OCR|[common-chinese-ocr.json](../.project-local/runs/be268a2d33/238c39f40b46/artifacts/common-chinese-ocr.json)|限定继承：png/jpeg/pdf选中短语；整页准确率UNMEASURED；外置chi_sim|`752a76fa79607dc42d8b6cb3c58ffd37199e70ba8895dd9437f38c9f4f75798d`|
|E04|ASR三格式|[common-speech.json](../.project-local/runs/be268a2d33/90f135494810/artifacts/common-speech.json)|限定继承：wav/mp3/mp4选中短语；MP4仅音频；外置模型；非全转写准确率|`e4d95b65b1a7c657911572de03b48dc88bedd674a69aa70d885e6ffd29d6f877`|
|E05|本地模型使用知识|[receipt.json](../.project-local/runs/be268a2d33/4bb6fceb953b/artifacts/colearning-real-model/5d9879350562467fbd2892cd7930a9cd/receipt.json)|限定继承：真实模型回答；NO_FAILURE_OBSERVED；learning_improvement NOT_ESTABLISHED；grant null与无资产资格；未触发纠正分支|`d4fb513bdbfd887a09b167cc984c2b126586995e3ba16329f51cf84c2f727a56`|
|E06|故障与恢复|[receipt.json](../.project-local/task-runtime/aaos01-fault/7f62231394c14ae3b3ceb3b9f016023a/receipt.json)|限定继承：timeout/cancel/crash/invalid_input注入；staged父进程关系；非真实外部服务故障|`face8d47293467cfd7f5dede6d2bb85cef543d4c695953a42b98df3a508a1e3e`|
|E07|安装Core评分与恢复22步|[journey-receipt.json](../.project-local/install-acceptance-20261104/journey-receipt.json)|限定继承：安装Core/runtime/workers；无Tauri UI；合成材料；非Owner接受|`cd7ecc00eef4a91bbb87973892025520420ceef77041fc9a9a3bced2e48e811f`|
|E08|OpenMAIC staged生成读回|[openmaic-staged.json](../.project-local/runs/be268a2d33/openmaic-staged-20261107/artifacts/openmaic-staged.json)|受变化影响部分继承：140cfb42候选；合成模型7次；重启0额外；interactive diagram不渲染；HEAD新增code/game字段未被覆盖|`8c49632b84f0d919d94479253eaa71a999a52b8cc73225627f9cfd8c15b97ef7`|
|E09|OpenMAIC安装Core生成读回|[openmaic-installed.json](../.project-local/install-acceptance-20261107/openmaic-installed.json)|受变化影响部分继承：同manifest 2f3c77c4/core c569b40a；合成loopback；无UI；不证明新字段安装资格|`cd0f20cbd321742997d38be495e12f6a7ee8b3e84913f370776aa1331dbe3474`|

## 影响性变化与继承判断

- E01：原回执 source=02bb7472+patch a588b375，七文件夹合成样本。到 HEAD 的 source/document/backup 相关 domain 文件无 diff；workers 中新 course worker、public research 回退与 routes 有变化。继承已测导入/保存/恢复机制，不能推出新增 provider 或当前完整安装闭包通过。
- E02：原 source=0087f69f+patch 0355b8f0；public_research domain 到 HEAD 仅格式化变化，三主通道结果直接继承为该次真实调用事实。上游配额/网络条件具有时效性，不据旧成功承诺今天可达；不重跑网络探针。
- E03/E04：原件、生成样本、外置资源与源补丁身份见原回执和 readback；继承选中短语/定位/重启行为。没有逐项比对机器当前OCR/模型安装环境，不泛化为当前默认安装可用。
- E05：本地真实模型为 qwen2.5-vl-7b-instruct；材料与裁判仍为fixture。原回答已正确，纠正/复测分支没有发生；context_grant=null、asset_effect=NOT_QUALIFIED，不能替代有范围资产采用效果。
- E08/E09：原候选source 140cfb42；本轮实际读取 git diff 140cfb42..157ee1db，变化为 interactive_outline/code.game字段、映射与闭包摘要共7文件。旧diagram读回结果继承，新code.challengeType、game.challenge/playerControls需将来增量验收；不因为分支/日期不同而要求重跑原旅程。

## 失败、声明与未证项

|编号|状态|依据与处理|
|---|---|---|
|E10|历史已失败，有后继|唯一执行记录：OpenMAIC staging四例Windows失败在干净0d373c04也存在；同平台问题保留。未取得该四例全部原始日志，本轮只记历史声明，不写当前失败。|
|E11|历史失败后修复|FSRS writer内等待旧风险已由当前 snapshot/compute/CAS源码替代。安装exit预算、session delete失败与nudge后继沿执行记录保留；没有重跑或重新认定根因。|
|E12|历史CI声明|执行记录记载PR286/308等精确SHA CI；本轮未查询云CI原始日志，因此不是本轮核实的当前CI绿色结论。|
|E13|没有找到同候选完整证据|正式UI消费DeepTutor新生成/反馈与OpenMAIC生成课程、真实模型教学质量、完整37平台特色、同次修订四消费者联合安装旅程。源码/单项旧PASS不填补这些空白。|
|E14|已有失败保留|中文OCR首次WinError10055后同候选通过、27B真实模型119秒超时见唯一执行记录；前者不改成无失败，后者不是当前产品必然故障。原始失败未逐一重新展开。|

## 本轮首次操作及最小未来补验

本轮只进行了源码/合同阅读、Git差异、原回执读回、公开官方资料核对与新审计文件静态检查；没有运行pytest/cargo test、构建、探针、模型、安装或UI旅程。

首次尝试用系统Python经 scripts/runtime/dev.py 分配审计环境，因缺PyYAML在prepare阶段失败，子命令未执行；之后仅调用其layout函数分配本仓审计临时目录。此为审计工具环境问题，不是产品测试失败；未安装依赖或改全局环境。rg的Scoop shim也不能启动，改用git ls-files/Select-String有界读取。

|触发条件|只新增/改变的验证|复用旧证据|
|---|---|---|
|T1正式接线完成|桥接参数/错误与生成候选→接纳→播放→作答→反馈一条新增UI链，确认离线草稿仍可保存|E01/E07保存恢复与评分链|
|T2可播放renderer完成|新元素/动作与未知版本退路、资源断开、恢复位置；交互HTML隔离另测|E08/E09候选生成读回；不重跑旧生成|
|T3生成claim改造完成|并发同ID模型只调用一次、进程中断UNKNOWN、迟到结果不自动采用|既有评分claim与E06|
|T4节点引用/当前性完成|同次修订在资料/研究/学习/AI四侧可见旧引用与新建议；节点回到段/页/时间点|既有对象固定版本与引用单项测试|
|T5有范围AI使用界面完成|不同领域失败案例纠正与独立新题复测；区分质量不改善/改善/无法判断|E05只复用本地真实推理通路|
|候选再次打包且包含PR309|仅新增code/game字段与资源闭包变化、必要宿主消费者；其他旧结果保持继承|E08/E09旧diagram|

静态报告检查结果记录于综合报告及本地 static-check.json；它只证明文档结构、引用和覆盖身份，不证明产品行为。
